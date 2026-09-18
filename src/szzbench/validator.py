from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable
import difflib
import re

from .findings import ValidationResult
from .operations import SUPPORTED_OPERATIONS, FUTURE_OPERATIONS, OperationError, apply_operation_to_memory, find_all_occurrences
from .paths import PathValidationError, validate_repo_relative_path
from .scenario import load_yaml

ALLOWED_ROLES = {
    "initial", "bug_introducing", "bug_fixing", "distractor", "refactoring",
    "formatting", "test_change", "merge", "revert", "cleanup", "feature_addition",
}

# --- opt-in lint vocabulary (shared with graph_validator) -------------------

# Schema keys and operation names that must not be used as scenario factors.
RESERVED_FACTOR_WORDS = frozenset({
    "expected_szz", "faults", "fixes", "fault", "fix", "bug_fixing_commits",
    "bug_introducing_commits", "issues", "work_items", "clone_relationships",
    "bug_instances", "evaluation_variants", "developer_hints", "allow_empty",
    "commit_generators", "commit_generator", "write_file", "replace", "rename_file",
    "move_file", "copy_file", "delete_file", "move_entity", "copy_entity",
    "write_binary_file", "write_generated_text_file", "chmod", "insert_after",
    "cherry_pick_of", "backport_of", "rebase_of", "edit", "drop",
})

# Explicit answer cues that disclose a commit's oracle role (issue #8).
#
# The words between "introduce" and "bug" may be hyphenated
# ("introduce context-sensitive bug"), and a commit can admit its role without
# the word "bug" at all ("introduce ambiguous faulty statement"), so the gap
# accepts hyphens and the vocabulary includes fault words on their own.
LEAK_ROLE_RE = re.compile(
    r"introduc\w*\s+([\w-]+\s+){0,3}bugs?\b|bug[- ]introduc|\bBIC\b|\bBFC\b|distractor|"
    r"intermediate change|initial state|\bnoise\b|\bunrelated\b|\breplay|reintroduc|"
    r"\bbuggy\b|\bfaulty\b|\bfault(?:y|s)?\b\s+(?:statement|line|code|commit)|"
    r"(?:with|containing|introduces?)\s+(?:a\s+|the\s+)?(?:[\w-]+\s+){0,2}bugs?\b",
    re.IGNORECASE,
)
#: A message that starts with a scenario logical id (``c1: ...``).  Kept for the
#: W411 message; :func:`logical_id_reference` is the general check.
LOGICAL_ID_PREFIX_RE = re.compile(r"^[a-z]{1,2}\d+:", re.IGNORECASE)
#: An id-shaped token used as a prefix anywhere in the message.  Issue and
#: work-item identifiers are written ``ISSUE-482`` / ``WI-001`` and keep their
#: hyphen, so they do not match; ``c2:``, ``Rel1:`` and ``WI-001 c2:`` do.
LOGICAL_ID_TOKEN_RE = re.compile(r"(?<![\w-])[A-Za-z]{1,4}\d+:")


def logical_id_reference(message: str, commit_ids: Iterable[str] = ()) -> str | None:
    """Return the logical-id prefix a message exposes, or ``None``.

    A commit id of the same scenario counts wherever it appears, because
    ``WI-001 c2: ...`` discloses exactly as much as ``c2: ...`` and
    ``suspected c0`` names a commit in the benchmark's own vocabulary.
    """
    for commit_id in commit_ids:
        if not isinstance(commit_id, str) or not commit_id:
            continue
        match = re.search(rf"(?<![\w-]){re.escape(commit_id)}(?![\w-])", message, re.IGNORECASE)
        if match:
            return match.group(0)
    match = LOGICAL_ID_TOKEN_RE.search(message)
    return match.group(0) if match else None
# operation type -> field whose text is written into the repository
LEAK_CONTENT_FIELDS = {"write_file": "content", "replace": "new", "insert_after": "content"}

# Declared ghost classes (issue #7): checked only when a scenario opts in.
ADD_ONLY_FIX_FACTORS = frozenset({"addition-only-fix", "ghost-fix", "add_only_fix"})
DELETE_ONLY_BIC_FACTORS = frozenset({"deletion-only-bic", "line-deletion-bic"})
ADD_ONLY_FIX_TYPES = frozenset({"line_addition", "file_creation"})

# Factors that declare a legitimate rewrite of the fault line / a tangled BFC.
FAULT_REWRITE_FACTOR_RE = re.compile(r"after-bic|rewrite|refactor|format|whitespace|rename|move|inline|extract")
TANGLED_BFC_FACTOR_RE = re.compile(r"tangled|distractor|candidate")
#: A scenario may pair an addition-only fix with deleted lines *on purpose* —
#: a distractor's comment, an adjacent unrelated edit.  When it declares that,
#: W420 is not a finding but the scenario's subject (issues #6, #7).
DECLARED_BFC_NOISE_RE = re.compile(r"tangled|noise|distractor|adjacent-edit")


def validate_scenario_file(
    path: Path,
    *,
    simulate: bool = False,
    lint: bool = False,
) -> tuple[dict[str, Any] | None, ValidationResult, dict[str, dict[str, str]] | None]:
    """Validate a classic scenario.yml.

    ``lint`` enables the opt-in W4xx lints; the snapshot-based lints need the
    in-memory simulation, so ``lint`` implies ``simulate``.
    """
    data, result = load_yaml(path)
    if data is None:
        return None, result, None
    result.extend(validate_static(data, scenario_path=path))
    snapshots = None
    if (simulate or lint) and not result.has_errors():
        snapshots, sim_result = simulate_commits(data)
        result.extend(sim_result)
        if snapshots is not None and not sim_result.has_errors():
            result.extend(validate_oracle_against_snapshots(data, snapshots))
    if lint and not result.has_errors():
        result.extend(lint_scenario(data, snapshots))
    return data, result, snapshots

def validate_static(data: dict[str, Any], *, scenario_path: Path | None = None) -> ValidationResult:
    result = ValidationResult()
    for key in ["schema_version", "meta", "repository", "commits", "bugs"]:
        if key not in data:
            result.error("E010", f"Missing required top-level field '{key}'.", key)
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else None
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else None
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    bugs = data.get("bugs") if isinstance(data.get("bugs"), list) else []
    if meta is None:
        result.error("E010", "'meta' must be an object.", "meta")
    else:
        for key in ["id", "title", "category", "factors"]:
            if key not in meta:
                result.error("E010", f"meta is missing required field '{key}'.", f"meta.{key}")
        if not isinstance(meta.get("factors", []), list):
            result.error("E010", "meta.factors must be a list.", "meta.factors")
        if scenario_path is not None and "id" in meta:
            parent = scenario_path.parent.name
            if parent != meta["id"]:
                result.warning("W001", f"meta.id is '{meta['id']}', but scenario directory is '{parent}'.", "meta.id")
    if repository is None:
        result.error("E010", "'repository' must be an object.", "repository")
    else:
        for key in ["name", "default_branch", "language"]:
            if key not in repository:
                result.error("E010", f"repository is missing required field '{key}'.", f"repository.{key}")
    if not isinstance(data.get("commits"), list):
        result.error("E010", "'commits' must be a list.", "commits")
    if not isinstance(data.get("bugs"), list):
        result.error("E010", "'bugs' must be a list.", "bugs")
    if len(commits) == 0:
        result.error("E011", "At least one commit is required.", "commits")

    commit_ids: list[str] = []
    commit_by_id: dict[str, dict] = {}
    for i, commit in enumerate(commits):
        loc = f"commits[{i}]"
        if not isinstance(commit, dict):
            result.error("E010", "Each commit must be an object.", loc)
            continue
        for key in ["id", "message", "operations"]:
            if key not in commit:
                result.error("E010", f"commit is missing required field '{key}'.", f"{loc}.{key}")
        cid = commit.get("id")
        if isinstance(cid, str):
            if cid in commit_by_id:
                result.error("E020", f"Duplicate commit id '{cid}'.", f"{loc}.id")
            commit_by_id[cid] = commit
            commit_ids.append(cid)
        role = commit.get("role")
        if role is not None and role not in ALLOWED_ROLES:
            result.error("E030", f"Unknown commit role '{role}'.", f"{loc}.role")
        operations = commit.get("operations")
        if not isinstance(operations, list):
            result.error("E010", "commit.operations must be a list.", f"{loc}.operations")
            continue
        for j, op in enumerate(operations):
            op_loc = f"{loc}.operations[{j}]"
            if not isinstance(op, dict):
                result.error("E010", "Each operation must be an object.", op_loc)
                continue
            op_type = op.get("type")
            if not isinstance(op_type, str):
                result.error("E041", "operation.type is required and must be a string.", f"{op_loc}.type")
                continue
            if op_type not in SUPPORTED_OPERATIONS:
                if op_type in FUTURE_OPERATIONS:
                    result.error("E900", f"Operation '{op_type}' is recognized but not supported by the initial generator.", f"{op_loc}.type")
                else:
                    result.error("E040", f"Unknown operation type '{op_type}'.", f"{op_loc}.type")
                continue
            required = {"write_file": ["path", "content"], "replace": ["path", "old", "new"]}[op_type]
            for key in required:
                if key not in op:
                    result.error("E041", f"Operation '{op_type}' is missing required field '{key}'.", f"{op_loc}.{key}")
            path = op.get("path")
            if isinstance(path, str):
                try:
                    validate_repo_relative_path(path)
                except PathValidationError as exc:
                    result.error("E050", f"Invalid path '{path}': {exc}", f"{op_loc}.path")
    bug_ids: set[str] = set()
    index_by_commit = {cid: i for i, cid in enumerate(commit_ids)}
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        if not isinstance(bug, dict):
            result.error("E010", "Each bug must be an object.", loc)
            continue
        bid = bug.get("id")
        if not isinstance(bid, str):
            result.error("E010", "bug.id is required and must be a string.", f"{loc}.id")
            bid = f"<bug[{i}]>"
        elif bid in bug_ids:
            result.error("E021", f"Duplicate bug id '{bid}'.", f"{loc}.id")
        else:
            bug_ids.add(bid)
        bfc = bug.get("bug_fixing_commit")
        bics = bug.get("bug_introducing_commits")
        if not isinstance(bfc, str):
            result.error("E010", "bug_fixing_commit is required and must be a string.", f"{loc}.bug_fixing_commit")
        elif bfc not in commit_by_id:
            result.error("E060", f"bug {bid} refers to unknown bug_fixing_commit '{bfc}'.", f"{loc}.bug_fixing_commit")
        if not isinstance(bics, list):
            result.error("E010", "bug_introducing_commits is required and must be a list.", f"{loc}.bug_introducing_commits")
            bics = []
        elif len(bics) == 0:
            result.error("E082", f"bug {bid} has an empty bug_introducing_commits list.", f"{loc}.bug_introducing_commits")
        elif len(bics) != len(set(bics)):
            result.error("E083", f"bug {bid} has duplicate BIC entries.", f"{loc}.bug_introducing_commits")
        for bic in bics:
            if not isinstance(bic, str):
                result.error("E010", "Each bug_introducing_commits entry must be a string.", f"{loc}.bug_introducing_commits")
                continue
            if bic not in commit_by_id:
                result.error("E061", f"bug {bid} refers to unknown bug-introducing commit '{bic}'.", f"{loc}.bug_introducing_commits")
            elif isinstance(bfc, str) and bfc in commit_by_id and index_by_commit[bic] >= index_by_commit[bfc]:
                result.error("E070", f"BIC '{bic}' must precede BFC '{bfc}' in the initial linear-history model.", loc)
        fault = bug.get("fault")
        if isinstance(fault, dict):
            fcommit = fault.get("commit")
            if isinstance(fcommit, str):
                if fcommit not in commit_by_id:
                    result.error("E062", f"bug {bid} fault.commit refers to unknown commit '{fcommit}'.", f"{loc}.fault.commit")
                elif fcommit not in bics:
                    result.error("E080", f"bug {bid} fault.commit '{fcommit}' is not listed in bug_introducing_commits.", f"{loc}.fault.commit")
        fix = bug.get("fix")
        if isinstance(fix, dict):
            fix_commit = fix.get("commit")
            if isinstance(fix_commit, str):
                if fix_commit not in commit_by_id:
                    result.error("E063", f"bug {bid} fix.commit refers to unknown commit '{fix_commit}'.", f"{loc}.fix.commit")
                elif fix_commit != bfc:
                    result.error("E081", f"bug {bid} fix.commit '{fix_commit}' does not match bug_fixing_commit '{bfc}'.", f"{loc}.fix.commit")
        if isinstance(bfc, str) and bfc in commit_by_id:
            role = commit_by_id[bfc].get("role")
            if role is not None and role != "bug_fixing":
                result.warning("W090", f"bug {bid} BFC '{bfc}' has role '{role}', not 'bug_fixing'.", loc)
        for bic in bics:
            if isinstance(bic, str) and bic in commit_by_id:
                role = commit_by_id[bic].get("role")
                if role is not None and role != "bug_introducing":
                    result.warning("W091", f"bug {bid} BIC '{bic}' has role '{role}', not 'bug_introducing'.", loc)
    return result

def simulate_commits(data: dict[str, Any]) -> tuple[dict[str, dict[str, str]] | None, ValidationResult]:
    result = ValidationResult()
    files: dict[str, str] = {}
    snapshots: dict[str, dict[str, str]] = {}
    for i, commit in enumerate(data.get("commits", [])):
        cid = commit.get("id", f"<commit[{i}]>")
        before = deepcopy(files)
        for j, op in enumerate(commit.get("operations", [])):
            try:
                apply_operation_to_memory(files, op)
            except OperationError as exc:
                result.error("E2XX", f"Operation failed in commit '{cid}': {exc}", f"commits[{i}].operations[{j}]")
                return None, result
        if files == before:
            result.error("E250", f"Commit '{cid}' produces no changes.", f"commits[{i}]")
            return None, result
        snapshots[cid] = deepcopy(files)
    return snapshots, result

def validate_oracle_against_snapshots(data: dict[str, Any], snapshots: dict[str, dict[str, str]]) -> ValidationResult:
    result = ValidationResult()
    commits = data.get("commits", [])
    index_by_commit = {c.get("id"): i for i, c in enumerate(commits) if isinstance(c, dict)}
    for i, bug in enumerate(data.get("bugs", [])):
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        fault = bug.get("fault", {})
        fix = bug.get("fix", {})
        bfc = bug.get("bug_fixing_commit")
        if isinstance(fault, dict):
            fcommit = fault.get("commit")
            ffile = fault.get("file")
            change_type = fault.get("change_type")
            if fcommit in snapshots and isinstance(ffile, str):
                snap = snapshots[fcommit]
                if ffile not in snap:
                    result.error("E300", f"bug {bid} fault.file '{ffile}' does not exist at fault.commit '{fcommit}'.", f"{loc}.fault.file")
                elif change_type != "omission":
                    stmt = fault.get("statement")
                    if not isinstance(stmt, str):
                        result.error("E301", f"bug {bid} fault.statement is required for non-omission bugs.", f"{loc}.fault.statement")
                    else:
                        count = len(find_all_occurrences(snap[ffile], stmt))
                        if count == 0:
                            result.error("E301", f"bug {bid} fault.statement does not exist at fault.commit '{fcommit}'.", f"{loc}.fault.statement")
                        elif count > 1:
                            result.warning("W301", f"bug {bid} fault.statement appears {count} times at fault.commit '{fcommit}'.", f"{loc}.fault.statement")
        if isinstance(fix, dict):
            fix_commit = fix.get("commit")
            fix_file = fix.get("file")
            if fix_commit in snapshots and isinstance(fix_file, str):
                snap = snapshots[fix_commit]
                if fix_file not in snap:
                    result.error("E310", f"bug {bid} fix.file '{fix_file}' does not exist at fix.commit '{fix_commit}'.", f"{loc}.fix.file")
                else:
                    fix_text = fix.get("added_statement") or fix.get("statement")
                    if isinstance(fix_text, str):
                        if fix_text not in snap[fix_file]:
                            result.error("E311", f"bug {bid} fix statement does not exist at fix.commit '{fix_commit}'.", f"{loc}.fix")
                    else:
                        result.error("E311", f"bug {bid} fix.statement or fix.added_statement is required.", f"{loc}.fix")
        if isinstance(bfc, str) and bfc in index_by_commit and index_by_commit[bfc] > 0:
            parent_id = commits[index_by_commit[bfc] - 1].get("id")
            parent_snapshot = snapshots.get(parent_id, {})
            if isinstance(fault, dict) and fault.get("change_type") != "omission":
                ffile = fault.get("file")
                stmt = fault.get("statement")
                if isinstance(ffile, str) and isinstance(stmt, str):
                    if ffile not in parent_snapshot:
                        result.warning("W320", f"bug {bid} fault.file is absent in the BFC parent '{parent_id}'.", loc)
                    elif stmt not in parent_snapshot[ffile]:
                        result.warning("W320", f"bug {bid} fault.statement is not present immediately before BFC '{bfc}'.", loc)
            if isinstance(fix, dict):
                fix_file = fix.get("file")
                fix_text = fix.get("added_statement") or fix.get("statement")
                if isinstance(fix_file, str) and isinstance(fix_text, str) and fix_file in parent_snapshot:
                    if fix_text in parent_snapshot[fix_file]:
                        result.warning("W330", f"bug {bid} fix statement is already present before BFC '{bfc}'.", loc)
        if isinstance(fault, dict) and fault.get("change_type") == "omission":
            if "statement" in fault:
                result.warning("W350", f"bug {bid} is omission, but fault.statement is present.", f"{loc}.fault.statement")
            if "missing_statement" not in fault:
                result.error("E351", f"bug {bid} is omission, but fault.missing_statement is missing.", f"{loc}.fault.missing_statement")
    return result


# --- opt-in lints (shared helpers) ------------------------------------------

def lint_factors(factors: Any, result: ValidationResult, *, prefix: str, location: str = "meta.factors") -> None:
    """Vocabulary lint for meta.factors.

    Emits ``<prefix>400`` (factor is a schema key / operation name),
    ``<prefix>401`` (empty factor list) and ``<prefix>402`` (hyphen and
    underscore styles mixed within one scenario).
    """
    if not isinstance(factors, list):
        return
    if not factors:
        result.warning(f"{prefix}401", "meta.factors is empty; declare at least one semantic factor.", location)
        return
    names = [f for f in factors if isinstance(f, str)]
    for i, name in enumerate(names):
        if name in RESERVED_FACTOR_WORDS:
            result.warning(f"{prefix}400", f"Factor '{name}' is a schema key or operation name, not a semantic factor.", f"{location}[{i}]")
    if any("-" in n for n in names) and any("_" in n for n in names):
        result.warning(f"{prefix}402", "Factors mix hyphen and underscore styles; use one convention per scenario.", location)


#: What a scenario is for (issue #14).  ``control`` verifies that a method
#: handles a specific input condition and may well be solvable by a cheap rule;
#: ``discriminating`` is designed so the declared baselines do not solve it.
#: ``szzbench baselines`` checks the declaration against the measurement.
SCENARIO_TIERS = ("control", "discriminating")


def lint_tier(meta: Any, result: ValidationResult, *, prefix: str) -> None:
    """``<prefix>460``: every scenario declares a tier from the vocabulary."""
    tier = meta.get("tier") if isinstance(meta, dict) else None
    if tier is None:
        result.warning(f"{prefix}460", "meta.tier is missing; declare 'control' or 'discriminating'.", "meta.tier")
    elif tier not in SCENARIO_TIERS:
        result.warning(f"{prefix}460", f"meta.tier '{tier}' is not one of {SCENARIO_TIERS}.", "meta.tier")


def lint_leakage(commits: Iterable[Any], bfc_ids: set[str], result: ValidationResult, *, prefix: str) -> None:
    """Answer-cue lint for commit messages and written file contents (issue #8).

    Emits ``<prefix>410`` (role wording in a non-BFC message), ``<prefix>411``
    (logical-id prefix in any message) and ``<prefix>412`` (role wording in
    text written by write_file / replace.new / insert_after.content).
    """
    commits = list(commits)
    commit_ids = [c.get("id") for c in commits if isinstance(c, dict) and isinstance(c.get("id"), str)]
    for i, commit in enumerate(commits):
        if not isinstance(commit, dict):
            continue
        cid = commit.get("id", f"<commit[{i}]>")
        loc = f"commits[{i}]"
        message = commit.get("message")
        if isinstance(message, str):
            exposed = logical_id_reference(message, commit_ids)
            if exposed:
                result.warning(f"{prefix}411", f"Commit '{cid}' message exposes the logical-id prefix '{exposed}'.", f"{loc}.message")
            if cid not in bfc_ids:
                leak = LEAK_ROLE_RE.search(message)
                if leak:
                    result.warning(f"{prefix}410", f"Commit '{cid}' is not a bug-fixing commit, but its message discloses a role: '{leak.group(0)}'.", f"{loc}.message")
        operations = commit.get("operations")
        if not isinstance(operations, list):
            continue
        for j, op in enumerate(operations):
            if not isinstance(op, dict):
                continue
            field = LEAK_CONTENT_FIELDS.get(op.get("type"))
            if field is None or not isinstance(op.get(field), str):
                continue
            leak = LEAK_ROLE_RE.search(op[field])
            if leak:
                path = op.get("path", "?")
                result.warning(f"{prefix}412", f"Commit '{cid}' writes role wording '{leak.group(0)}' into '{path}' ({op.get('type')}.{field}).", f"{loc}.operations[{j}].{field}")


def factor_matches(factors: Any, pattern: re.Pattern[str]) -> bool:
    return isinstance(factors, list) and any(isinstance(f, str) and pattern.search(f) for f in factors)


# --- opt-in lints (classic suite) -------------------------------------------

def lint_scenario(data: dict[str, Any], snapshots: dict[str, dict[str, str]] | None) -> ValidationResult:
    """Run the W4xx lints on a statically valid classic scenario.

    ``snapshots`` (from :func:`simulate_commits`) enables the ghost-invariant
    and fault-line-integrity lints; without it only the vocabulary and
    leakage lints run.
    """
    result = ValidationResult()
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    factors = meta.get("factors")
    commits = [c for c in (data.get("commits") or []) if isinstance(c, dict)]
    bugs = [b for b in (data.get("bugs") or []) if isinstance(b, dict)]
    bfc_ids = {b.get("bug_fixing_commit") for b in bugs if isinstance(b.get("bug_fixing_commit"), str)}

    lint_factors(factors, result, prefix="W")
    lint_tier(data.get("meta"), result, prefix="W")
    lint_leakage(commits, bfc_ids, result, prefix="W")
    if snapshots is not None:
        result.extend(_lint_ghost_invariants(commits, bugs, factors, snapshots))
        result.extend(_lint_fault_line_integrity(commits, bugs, factors, snapshots))
    return result


def _parent_snapshot(commits: list[dict[str, Any]], index: int, snapshots: dict[str, dict[str, str]]) -> dict[str, str]:
    if index <= 0:
        return {}
    return snapshots.get(commits[index - 1].get("id"), {})


def _removed_lines(before: dict[str, str], after: dict[str, str]) -> dict[str, list[tuple[int, str]]]:
    """Lines of ``before`` that are deleted or modified in ``after``, per path.

    Each entry is ``(line_index_in_before, text)``.
    """
    removed: dict[str, list[tuple[int, str]]] = {}
    for path, old in before.items():
        new = after.get(path)
        if new == old:
            continue
        old_lines = old.splitlines()
        if new is None:
            removed[path] = list(enumerate(old_lines))
            continue
        matcher = difflib.SequenceMatcher(None, old_lines, new.splitlines(), autojunk=False)
        hits = [(k, old_lines[k]) for tag, i1, i2, _, _ in matcher.get_opcodes() if tag in {"delete", "replace"} for k in range(i1, i2)]
        if hits:
            removed[path] = hits
    return removed


def _added_lines(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    """Lines of ``after`` that do not come from ``before``, per path."""
    added: dict[str, list[str]] = {}
    for path, new in after.items():
        old = before.get(path)
        if new == old:
            continue
        new_lines = new.splitlines()
        if old is None:
            if new_lines:
                added[path] = new_lines
            continue
        matcher = difflib.SequenceMatcher(None, old.splitlines(), new_lines, autojunk=False)
        hits = [new_lines[k] for tag, _, _, j1, j2 in matcher.get_opcodes() if tag in {"insert", "replace"} for k in range(j1, j2)]
        if hits:
            added[path] = hits
    return added


def _lint_ghost_invariants(
    commits: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    factors: Any,
    snapshots: dict[str, dict[str, str]],
) -> ValidationResult:
    """W420/W421: declared add-only BFCs and delete-only BICs must be exactly that."""
    result = ValidationResult()
    factor_set = {f for f in factors if isinstance(f, str)} if isinstance(factors, list) else set()
    add_only_declared = bool(factor_set & ADD_ONLY_FIX_FACTORS)
    delete_only_declared = bool(factor_set & DELETE_ONLY_BIC_FACTORS)
    index_by_commit = {c.get("id"): i for i, c in enumerate(commits)}
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        fault = bug.get("fault") if isinstance(bug.get("fault"), dict) else {}
        fix = bug.get("fix") if isinstance(bug.get("fix"), dict) else {}
        bfc = bug.get("bug_fixing_commit")
        bics = [b for b in (bug.get("bug_introducing_commits") or []) if isinstance(b, str)]
        omission_add_only = fault.get("change_type") == "omission" and fix.get("fix_type") in ADD_ONLY_FIX_TYPES
        declared_noise = any(DECLARED_BFC_NOISE_RE.search(f) for f in factor_set)
        if (add_only_declared or omission_add_only) and not declared_noise and bfc in index_by_commit and bfc in snapshots:
            reason = "declared as an addition-only fix" if add_only_declared else "an omission bug with an addition-only fix_type"
            before = _parent_snapshot(commits, index_by_commit[bfc], snapshots)
            for path, hits in sorted(_removed_lines(before, snapshots[bfc]).items()):
                first = hits[0][1].strip()
                result.warning("W420", f"bug {bid} is {reason}, but BFC '{bfc}' deletes or modifies {len(hits)} existing line(s) in '{path}' (first: '{first}').", loc)
        if delete_only_declared:
            for bic in bics:
                if bic not in index_by_commit or bic not in snapshots:
                    continue
                before = _parent_snapshot(commits, index_by_commit[bic], snapshots)
                for path, lines in sorted(_added_lines(before, snapshots[bic]).items()):
                    result.warning("W421", f"bug {bid} is declared as a deletion-only BIC, but BIC '{bic}' adds {len(lines)} line(s) in '{path}' (first: '{lines[0].strip()}').", loc)
    return result


def _track_line_authors(commits: list[dict[str, Any]], snapshots: dict[str, dict[str, str]]) -> dict[str, dict[str, list[str]]]:
    """Per commit, the commit id that last changed each line of each file.

    A simple difflib-based blame over the linear history: equal blocks keep
    their author, inserted or replaced lines are attributed to the commit.
    """
    authors: dict[str, list[str]] = {}
    previous: dict[str, str] = {}
    by_commit: dict[str, dict[str, list[str]]] = {}
    for commit in commits:
        cid = commit.get("id")
        current = snapshots.get(cid)
        if current is None:
            continue
        next_authors: dict[str, list[str]] = {}
        for path, content in current.items():
            new_lines = content.splitlines()
            old_content = previous.get(path)
            if old_content is None or path not in authors:
                next_authors[path] = [cid] * len(new_lines)
                continue
            old_authors = authors[path]
            merged: list[str] = []
            matcher = difflib.SequenceMatcher(None, old_content.splitlines(), new_lines, autojunk=False)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    merged.extend(old_authors[i1:i2])
                elif tag in {"insert", "replace"}:
                    merged.extend([cid] * (j2 - j1))
            next_authors[path] = merged
        authors = next_authors
        previous = current
        by_commit[cid] = {p: list(a) for p, a in authors.items()}
    return by_commit


def _lint_fault_line_integrity(
    commits: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    factors: Any,
    snapshots: dict[str, dict[str, str]],
) -> ValidationResult:
    """W430/W431: the fault line survives to the BFC and the BFC only removes BIC lines."""
    result = ValidationResult()
    index_by_commit = {c.get("id"): i for i, c in enumerate(commits)}
    rewrite_declared = factor_matches(factors, FAULT_REWRITE_FACTOR_RE)
    tangled_declared = factor_matches(factors, TANGLED_BFC_FACTOR_RE)
    authors_by_commit = _track_line_authors(commits, snapshots) if not tangled_declared else {}
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        fault = bug.get("fault") if isinstance(bug.get("fault"), dict) else {}
        bfc = bug.get("bug_fixing_commit")
        bics = {b for b in (bug.get("bug_introducing_commits") or []) if isinstance(b, str)}
        if bfc not in index_by_commit:
            continue
        bfc_index = index_by_commit[bfc]
        stmt = fault.get("statement")
        ffile = fault.get("file")
        fcommit = fault.get("commit")
        if (
            not rewrite_declared
            and fault.get("change_type") != "omission"
            and isinstance(stmt, str) and isinstance(ffile, str)
            and fcommit in index_by_commit
        ):
            for k in range(index_by_commit[fcommit] + 1, bfc_index):
                cid = commits[k].get("id")
                if cid in bics or cid not in snapshots:
                    continue
                before = _parent_snapshot(commits, k, snapshots)
                after = snapshots[cid]
                if ffile in before and stmt in before[ffile] and stmt not in after.get(ffile, ""):
                    result.warning("W430", f"bug {bid}: intermediate non-BIC commit '{cid}' removes the fault statement from '{ffile}' before BFC '{bfc}'; declare the rewrite with a factor if intended.", f"commits[{k}]")
        if not tangled_declared and bfc_index > 0 and bfc in snapshots:
            parent_id = commits[bfc_index - 1].get("id")
            before = snapshots.get(parent_id, {})
            parent_authors = authors_by_commit.get(parent_id, {})
            for path, hits in sorted(_removed_lines(before, snapshots[bfc]).items()):
                line_authors = parent_authors.get(path, [])
                foreign = sorted({line_authors[k] for k, _ in hits if k < len(line_authors) and line_authors[k] not in bics})
                if foreign:
                    first = next(text for k, text in hits if k < len(line_authors) and line_authors[k] in foreign).strip()
                    result.warning("W431", f"bug {bid} BFC '{bfc}' deletes or modifies line(s) in '{path}' last changed by non-BIC commit(s) {foreign} (first: '{first}'); declare a tangled BFC with a factor if intended.", loc)
    return result


# --- index consistency ------------------------------------------------------

def validate_index_file(index_path: Path, root: Path, scenario_filename: str) -> ValidationResult:
    """Check one index.yml against the scenario directories under ``root``.

    IE codes are errors, IW codes warnings; locations are prefixed with the
    index path so that results for several indexes can be merged.
    """
    result = ValidationResult()
    prefix = index_path.as_posix()
    data, load_result = load_yaml(index_path)
    if data is None:
        for finding in load_result.findings:
            result.error("IE001", f"Cannot load index: {finding.message}", prefix)
        return result
    entries = data.get("scenarios")
    if not isinstance(entries, list):
        result.error("IE002", "'scenarios' must be a list.", f"{prefix}:scenarios")
        return result
    if not root.is_dir():
        result.error("IE003", f"Scenario root '{root.as_posix()}' is not a directory.", prefix)
        return result
    count = data.get("scenario_count")
    if count is not None and count != len(entries):
        result.error("IE010", f"scenario_count is {count}, but the index lists {len(entries)} entries.", f"{prefix}:scenario_count")

    expected_rel = lambda sid: f"{root.name}/{sid}/{scenario_filename}"  # noqa: E731
    seen: set[str] = set()
    for i, entry in enumerate(entries):
        loc = f"{prefix}:scenarios[{i}]"
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            result.error("IE020", "Index entry must be an object with a string id.", loc)
            continue
        sid = entry["id"]
        if sid in seen:
            result.error("IE021", f"Duplicate index entry '{sid}'.", f"{loc}.id")
            continue
        seen.add(sid)
        scenario_file = root / sid / scenario_filename
        if not scenario_file.is_file():
            result.error("IE022", f"Index entry '{sid}' has no scenario file at '{expected_rel(sid)}'.", loc)
            continue
        path_value = entry.get("path")
        if isinstance(path_value, str) and Path(path_value).as_posix() != expected_rel(sid):
            result.warning("IW023", f"Index entry '{sid}' path is '{path_value}', expected '{expected_rel(sid)}'.", f"{loc}.path")
        scenario_data, scenario_load = load_yaml(scenario_file)
        if scenario_data is None:
            detail = "; ".join(f.message for f in scenario_load.findings)
            result.error("IE042", f"Scenario file for '{sid}' cannot be loaded: {detail}", loc)
            continue
        meta = scenario_data.get("meta") if isinstance(scenario_data.get("meta"), dict) else {}
        if meta.get("id") != sid:
            result.error("IE040", f"Index entry id '{sid}' does not match meta.id '{meta.get('id')}' in {expected_rel(sid)}.", f"{loc}.id")
        if "title" in entry and entry.get("title") != meta.get("title"):
            result.error("IE041", f"Index entry '{sid}' title '{entry.get('title')}' does not match meta.title '{meta.get('title')}'.", f"{loc}.title")

    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / scenario_filename).is_file() and child.name not in seen:
            result.error("IE030", f"Scenario directory '{root.name}/{child.name}' has no index entry.", f"{prefix}:scenarios")
    return result


def validate_scenario_indexes(scenarios_root: Path, advanced_scenarios_root: Path) -> ValidationResult:
    """Validate scenarios/index.yml and advanced-scenarios/index.yml."""
    result = ValidationResult()
    result.extend(validate_index_file(scenarios_root / "index.yml", scenarios_root, "scenario.yml"))
    result.extend(validate_index_file(advanced_scenarios_root / "index.yml", advanced_scenarios_root, "scenario.graph.yml"))
    return result
