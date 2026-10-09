from __future__ import annotations

from datetime import datetime, timezone

from pathlib import Path
from typing import Any
import re

from .evaluator import _commit_level_policy, _selected_evaluation_variant, classify_prediction
from .findings import ValidationResult
from .graph_operations import (PATH_FIELDS_BY_OPERATION, REQUIRED_FIELDS_BY_OPERATION, SUPPORTED_GRAPH_OPERATIONS,
                               decode_content_base64)
from .graph_scenario import (commit_id_of, graph_bfc_entries, graph_bic_entries, graph_faults, graph_fixes, load_graph_scenario,
                             ref_lifecycle_problems)
from .graph_simulator import git_performed_features, simulate_graph_scenario, simulate_graph_scenario_with_git
from .gitutils import (GitError, format_timestamp, history_graph, parse_timestamp, planned_generated_commits,
                       reachable_commit_ids)
from .operations import OperationError, resolve_line_ending, type_label
from .paths import PathValidationError, file_system_key, validate_repo_relative_path
from .policies import SUPPORTED_EVALUATION_POLICIES
from .validator import (COMMIT_MESSAGE_RULE, check_commit_metadata, check_scheduled_dates, commit_message_problem, lint_author_coincidence,
                        lint_defeats, lint_difficulty, lint_factors, lint_leakage, lint_readme_header, lint_tier,
                        timestamp_problem)

GRAPH_ID_RE = re.compile(r"^SZZG-\d{4}$")

#: The schema_version of a graph scenario since the suite was frozen (README, issue #19);
#: every shipped one declares it (issue #152).
GRAPH_SCHEMA_VERSION = "graph-1.0"

#: The operations whose ``line_ending`` / ``encoding`` graph generation reads
#: (``graph_operations._apply_graph_operation``); GE061 checks them there (issue #152).
LINE_ENDING_OPERATIONS = frozenset({"write_file", "replace", "insert_after"})
ENCODING_OPERATIONS = frozenset({"write_file", "replace", "insert_after", "move_entity", "copy_entity",
                                 "write_generated_text_file", "format_file"})

# Shared with the evaluator via szzbench.policies (kept under the old name for callers).
ALLOWED_EVALUATION_POLICIES = SUPPORTED_EVALUATION_POLICIES

# History-rewrite metadata that must point at earlier commits (like GE043 for
# cherry_pick_of / backport_of).  rebase_of may be a list for squash-rebases.
REWRITE_REFERENCE_KEYS: dict[str, tuple[type, ...]] = {
    "rebase_of": (str, list),
    "squashes": (list,),
    "revert_of": (str,),
}

#: The keys by which a commit declares that it rewrites earlier commits, which a
#: branch may then leave behind (GW151); ``revert_of`` keeps its target.
REWRITE_DECLARATION_KEYS = ("rebase_of", "squashes")

#: The operation fields whose value is text generation writes or matches.  They
#: were read through str(): a blank `content:` wrote the text `None` into the file,
#: and the error came later, as "replace.old not found" on another operation (issue #151).
TEXT_FIELDS_BY_OPERATION = {"write_file": ("content",), "replace": ("old", "new"), "insert_after": ("anchor", "content")}

# Consumer-compatible role vocabulary (issue #19); see graph_verifier / evaluator.
ALLOWED_BIC_ROLES = frozenset({"direct", "origin", "contributing", "reintroducing"})
ALLOWED_BFC_ROLES = frozenset({"complete_fix", "partial_fix"})

# Operations whose generated result only approximates the declared intent.
#: Operations whose generated result only approximates the intent.  ``commit_generator``
#: and ``chmod`` used to be listed here; since the generator expands commit_generator into
#: real commits and enables core.filemode for chmod scenarios, both are faithful and the
#: codes GW441/GW442 are retired.
APPROXIMATE_OPERATIONS: dict[str, tuple[str, str]] = {
    "move_entity": ("GW440", "move_entity is a file-level approximation: the whole source file is copied under a marker header, no entity is extracted."),
    "copy_entity": ("GW440", "copy_entity is a file-level approximation: the whole source file is copied under a marker header, no entity is extracted."),
    "apply_patch": ("GW443", "apply_patch is recognized by the schema but not implemented; generation will fail."),
}

# expected_szz.commit_level lists that may name an origin BIC.
EXPECTED_SZZ_COMMIT_LISTS = ("required", "acceptable_related", "related_origins", "related_but_not_correct", "relevant")


def validate_graph_scenario_file(
    path: Path,
    *,
    strict_paths: bool = False,
    simulate: bool = False,
    lint: bool = False,
) -> tuple[dict[str, Any] | None, ValidationResult]:
    """Validate a scenario.graph.yml.

    ``lint`` enables the opt-in GW4xx lints, which are static (they do not
    need the simulation) and run only when no error was found.
    """
    data, result = load_graph_scenario(path)
    if data is None:
        return None, result
    result.extend(validate_graph_static(data, scenario_path=path, strict_paths=strict_paths))
    if simulate and not result.has_errors():
        # what generation lets Git compute is checked by generating with Git (#94)
        features = git_performed_features(data)
        if features:
            result.extend(simulate_graph_scenario_with_git(path, data, features))
        else:
            result.extend(simulate_graph_scenario(data))
    if lint and not result.has_errors():
        result.extend(lint_graph_scenario(data, scenario_path=path))
    return data, result


def validate_graph_static(data: dict[str, Any], *, scenario_path: Path | None = None, strict_paths: bool = False) -> ValidationResult:
    result = ValidationResult()
    for key in ["schema_version", "meta", "repository", "commits", "bugs"]:
        if key not in data:
            result.error("GE010", f"Missing required top-level field '{key}'.", key)
    schema_version = data.get("schema_version")
    if isinstance(schema_version, str) and "graph" in schema_version and schema_version != GRAPH_SCHEMA_VERSION:
        # any string containing "graph" passed GE001 (issue #152)
        result.error("GE002", f"schema_version is '{schema_version}'; a graph scenario declares "
                     f'schema_version: "{GRAPH_SCHEMA_VERSION}".', "schema_version")

    meta = data.get("meta") if isinstance(data.get("meta"), dict) else None
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else None
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    bugs = data.get("bugs") if isinstance(data.get("bugs"), list) else []

    if meta is None:
        result.error("GE011", "'meta' must be an object.", "meta")
    else:
        scenario_id = meta.get("id")
        if not isinstance(scenario_id, str):
            result.error("GE012", "meta.id is required and must be a string.", "meta.id")
        elif not GRAPH_ID_RE.match(scenario_id):
            result.error("GE013", "meta.id must use the SZZG-XXXX format.", "meta.id")
        if scenario_path is not None and scenario_path.name != "scenario.graph.yml":
            result.warning("GW014", "Graph scenarios should be stored in a file named scenario.graph.yml.", str(scenario_path))
        for key in ["title", "category", "factors"]:
            if key not in meta:
                result.warning("GW015", f"meta.{key} is missing.", f"meta.{key}")
            elif key != "factors" and not isinstance(meta[key], str):
                result.error("GE017", f"meta.{key} must be a string, not {type_label(meta[key])}.", f"meta.{key}")
        if "factors" in meta and not isinstance(meta.get("factors"), list):
            result.error("GE016", "meta.factors must be a list.", "meta.factors")

    if repository is None:
        result.error("GE020", "'repository' must be an object.", "repository")
    else:
        for key in ["name", "default_branch"]:
            if key not in repository:
                result.warning("GW021", f"repository.{key} is missing.", f"repository.{key}")
        for key in ["name", "default_branch", "language"]:
            if key in repository and not isinstance(repository[key], str):
                # default_branch: 1 reached git as an int (issue #152)
                result.error("GE022", f"repository.{key} must be a string, not {type_label(repository[key])}.",
                             f"repository.{key}")
        if "base_date" in repository:
            problem = timestamp_problem(repository["base_date"])
            if problem is not None:
                result.error("GE071", f"repository.base_date {problem}.", "repository.base_date")

    if not isinstance(data.get("commits"), list):
        result.error("GE030", "commits must be a list.", "commits")
        commits = []
    if not commits:
        result.error("GE031", "commits must not be empty.", "commits")

    commit_by_id: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for i, commit in enumerate(commits):
        loc = f"commits[{i}]"
        if not isinstance(commit, dict):
            result.error("GE032", "Each commit must be an object.", loc)
            continue
        cid = commit.get("id")
        if not isinstance(cid, str) or not cid:
            result.error("GE033", "commit.id is required and must be a non-empty string.", f"{loc}.id")
            cid = f"<commit[{i}]>"
        elif cid in seen:
            result.error("GE034", f"Duplicate commit id '{cid}'.", f"{loc}.id")
        else:
            seen.add(cid)
            commit_by_id[cid] = commit
        branch = commit.get("branch")
        if branch is not None and not isinstance(branch, str):
            result.error("GE035", "commit.branch must be a string when present.", f"{loc}.branch")
        if "message" in commit and not isinstance(commit["message"], str):
            # str() made `message: 123` the subject '123', and a blank one fell back to the
            # commit id; verification was the first to object, or nothing did (issue #151)
            result.error("GE040", f"commit.message must be a string when present, not {type_label(commit['message'])}.",
                         f"{loc}.message")
        elif isinstance(commit.get("message"), str):
            # the rule of E012: a trailing newline or a body failed generation at verification
            # (GE623); a commit without message (inherit_message, revert_of) is not affected (issue #163)
            problem = commit_message_problem(commit["message"])
            if problem is not None:
                result.error("GE070", f"Commit '{cid}' message {problem}. {COMMIT_MESSAGE_RULE}", f"{loc}.message")
        check_commit_metadata(commit, cid, loc, result, timestamp_code="GE071", author_code="GE072")   # issue #152
        parents = commit.get("parents", [])
        if not isinstance(parents, list):
            result.error("GE036", "commit.parents must be a list.", f"{loc}.parents")
            parents = []
        elif i > 0 and not parents:
            # Only the first commit is a root.  The generator used to commit a later
            # parentless commit on top of whatever it had checked out, and record it
            # as a root (issue #134); a misspelt key ended up the same way.
            near_miss = next((key for key in commit if isinstance(key, str) and key != "parents"
                              and key.lower().rstrip("s") == "parent"), None)
            hint = f"; it has a '{near_miss}' key, and the key is 'parents'" if near_miss else ""
            result.error(
                "GE048",
                f"Commit '{cid}' declares no parents, but only the first commit may be a root: "
                f"a second root is not supported{hint}.",
                f"{loc}.parents",
            )
        for parent in parents:
            if not isinstance(parent, str):
                result.error("GE037", "Each parent id must be a string.", f"{loc}.parents")
            elif parent not in seen:
                # Require topological order for the MVP graph generator.
                if parent in commit_by_id or any(isinstance(c, dict) and c.get("id") == parent for c in commits):
                    result.error("GE038", f"Parent '{parent}' must appear before commit '{cid}' for graph generation.", f"{loc}.parents")
                else:
                    result.error("GE039", f"Unknown parent commit '{parent}'.", f"{loc}.parents")
        role = commit.get("role")
        if role is not None and not isinstance(role, str):
            # The graph suite has no role vocabulary, but a role is text: a list or a
            # mapping raised TypeError in the merge-like test below, and passed
            # without a finding on a commit with one parent (issue #150)
            result.error("GE041", f"commit.role must be a string when present, not {type_label(role)}.", f"{loc}.role")
        elif role == "merge" and len(parents) < 2:
            result.warning("GW040", f"Commit '{cid}' has role merge but fewer than two parents.", loc)
        elif len(parents) >= 2 and role not in {"merge", "bug_fixing", "bug_introducing", "squash_merge"}:
            result.warning("GW041", f"Commit '{cid}' has multiple parents but role is not explicitly merge-like.", loc)
        for ref_key in ["cherry_pick_of", "backport_of"]:
            ref = commit.get(ref_key)
            if ref is not None:
                if not isinstance(ref, str):
                    result.error("GE042", f"{ref_key} must be a string when present.", f"{loc}.{ref_key}")
                elif ref not in commit_by_id:
                    result.error("GE043", f"{ref_key} refers to unknown or later commit '{ref}'.", f"{loc}.{ref_key}")
        _validate_rewrite_references(commit, cid, commit_by_id, result, loc)
        operations = commit.get("operations", [])
        if operations is None:
            operations = []
        if not isinstance(operations, list):
            result.error("GE044", "commit.operations must be a list.", f"{loc}.operations")
            continue
        # A commit with no operations is not empty when git supplies its content:
        # `revert_of` runs `git revert`, `cherry_pick_of`/`backport_of` run `git cherry-pick`
        # (docs/generator-options.md §3).  Marking those `allow_empty` would be false.
        replayed = any(commit.get(k) for k in ("revert_of", "cherry_pick_of", "backport_of"))
        if not operations and not commit.get("allow_empty") and not replayed and len(parents) < 2:
            result.warning("GW045", f"Commit '{cid}' has no operations and is not allow_empty.", loc)
        for j, op in enumerate(operations):
            _validate_operation(op, result, f"{loc}.operations[{j}]", strict_paths=strict_paths)

    check_scheduled_dates(data, result, code="GE071", graph=True)    # PR #236 review
    result.extend(_validate_graph_acyclic(commits))
    result.extend(_validate_merge_parents(commits))
    if not result.has_errors():          # the history model needs well-formed commits
        result.extend(_validate_branch_rewinds(data))
    _validate_ref_lifecycle(data, result)

    if not isinstance(data.get("bugs"), list):
        result.error("GE080", "bugs must be a list.", "bugs")
        bugs = []
    bug_ids: set[str] = set()
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        if not isinstance(bug, dict):
            result.error("GE081", "Each bug must be an object.", loc)
            continue
        bid = bug.get("id")
        if not isinstance(bid, str):
            result.error("GE082", "bug.id is required and must be a string.", f"{loc}.id")
            bid = f"<bug[{i}]>"
        elif bid in bug_ids:
            result.error("GE083", f"Duplicate bug id '{bid}'.", f"{loc}.id")
        else:
            bug_ids.add(bid)

        # graph_bic_entries iterates the value as it comes: an int raised, and a
        # string became one commit per character (issue #127).
        raw_bics = bug.get("bug_introducing_commits")
        malformed_bics = raw_bics is not None and not isinstance(raw_bics, list)
        bic_entries = [] if malformed_bics else graph_bic_entries(bug)
        bfc_entries = graph_bfc_entries(bug)
        if malformed_bics:
            result.error("GE084", f"bug {bid}: bug_introducing_commits must be a list, not {type(raw_bics).__name__}.",
                         f"{loc}.bug_introducing_commits")
        elif not bic_entries:
            if _declares_expect_no_bic(data.get("expected_szz")):
                result.info(
                    "GI086",
                    f"bug {bid} declares no bug-introducing commits; accepted because expected_szz declares expect_no_bic.",
                    f"{loc}.bug_introducing_commits",
                )
            else:
                result.error("GE084", f"bug {bid} must define bug_introducing_commits.", f"{loc}.bug_introducing_commits")
        if not bfc_entries:
            result.error("GE085", f"bug {bid} must define bug_fixing_commits or bug_fixing_commit.", f"{loc}.bug_fixing_commits")
        for j, entry in enumerate(bic_entries):
            _validate_commit_ref_entry(entry, commit_by_id, result, f"{loc}.bug_introducing_commits[{j}]", "BIC")
        for j, entry in enumerate(bfc_entries):
            _validate_commit_ref_entry(entry, commit_by_id, result, f"{loc}.bug_fixing_commits[{j}]", "BFC")

        for j, fault in enumerate(graph_faults(bug)):
            _validate_location_entry(fault, commit_by_id, result, f"{loc}.faults[{j}]", require_statement=False)
        for j, fix in enumerate(graph_fixes(bug)):
            _validate_location_entry(fix, commit_by_id, result, f"{loc}.fixes[{j}]", require_statement=False)

    _validate_expected_szz(data.get("expected_szz"), commit_by_id, result)
    _warn_inferred_commit_level(data, result)
    _validate_context_sections(data, commit_by_id, result)
    return result


def _validate_operation(op: Any, result: ValidationResult, loc: str, *, strict_paths: bool) -> None:
    if not isinstance(op, dict):
        result.error("GE050", "Each operation must be an object.", loc)
        return
    op_type = op.get("type")
    if not isinstance(op_type, str):
        result.error("GE051", "operation.type is required and must be a string.", f"{loc}.type")
        return
    if op_type not in SUPPORTED_GRAPH_OPERATIONS:
        result.error("GE052", f"Unknown graph operation type '{op_type}'.", f"{loc}.type")
        return
    for key in REQUIRED_FIELDS_BY_OPERATION.get(op_type, []):
        if key not in op:
            result.error("GE053", f"Operation '{op_type}' is missing required field '{key}'.", f"{loc}.{key}")
    for key in PATH_FIELDS_BY_OPERATION.get(op_type, []):
        value = op.get(key)
        if isinstance(value, str):
            try:
                validate_repo_relative_path(value)
            except PathValidationError as exc:
                result.error("GE054", f"Invalid path '{value}': {exc}", f"{loc}.{key}")
        elif key in op:
            result.error("GE055", f"Operation field '{key}' must be a string path.", f"{loc}.{key}")
    if strict_paths and op_type in {"move_entity", "copy_entity"} and not isinstance(op.get("entity"), dict):
        result.error("GE056", f"Operation '{op_type}' must define an entity object.", f"{loc}.entity")
    _validate_operation_values(op, op_type, result, loc)


#: The values generation reads from three operations, checked before it runs (issue #172).
_OCTAL_MODE = re.compile(r"[0-7]{3,4}")
#: The operations that write the file at one path to another.  Two paths that differ only in
#: letter case are one file on a case-insensitive file system: a case-only rename failed on
#: macOS and succeeded on Linux (issue #175).  The paths are compared by
#: ``paths.file_system_key``, as the simulators compare the paths of a snapshot (issue #153).
_CASE_SENSITIVE_PAIRS = {
    "rename_file": ("from", "to"),
    "move_file": ("from", "to"),
    "copy_file": ("from", "to"),
    "move_entity": ("from_file", "to_file"),
    "copy_entity": ("from_file", "to_file"),
}


def _validate_operation_values(op: dict[str, Any], op_type: str, result: ValidationResult, loc: str) -> None:
    for key in TEXT_FIELDS_BY_OPERATION.get(op_type, ()):
        if key in op and not isinstance(op[key], str):
            result.error("GE053", f"Operation '{op_type}' field '{key}' must be a string, not {type_label(op[key])}.",
                         f"{loc}.{key}")
    if op_type == "chmod" and "mode" in op:
        mode = op["mode"]
        if not (isinstance(mode, str) and _OCTAL_MODE.fullmatch(mode)):
            hint = " (YAML reads an unquoted 0755 as the integer 493)" if isinstance(mode, int) else ""
            result.error("GE057", f"chmod mode must be a quoted string of octal digits such as '755', not {mode!r}{hint}.",
                         f"{loc}.mode")
    if op_type == "write_binary_file" and "content_base64" in op:
        try:
            decode_content_base64(op["content_base64"])   # the generator's own reading (PR #214 review)
        except ValueError as exc:
            result.error("GE058", f"write_binary_file content_base64 is not base64 ({exc}); ASCII whitespace is "
                         "ignored, any other character outside the alphabet is not.", f"{loc}.content_base64")
    if op_type == "write_generated_text_file" and "lines" in op:
        lines = op["lines"]
        if not (isinstance(lines, int) and not isinstance(lines, bool) and lines >= 0):
            result.error("GE059", f"write_generated_text_file lines must be a non-negative integer, not {lines!r}.",
                         f"{loc}.lines")
    # line_ending and encoding were read by generation only, and commit_generator's
    # count by --simulate and generation, which generate-graph does not simulate (issue #152)
    if op_type in LINE_ENDING_OPERATIONS:
        try:
            resolve_line_ending(op)                       # the generator's own reading
        except OperationError as exc:
            result.error("GE061", f"Operation '{op_type}' {exc}.", f"{loc}.line_ending")
    if op_type in ENCODING_OPERATIONS and op.get("encoding") is not None:
        problem = _encoding_problem(op["encoding"])
        if problem is not None:
            result.error("GE061", f"Operation '{op_type}' encoding {problem}.", f"{loc}.encoding")
    if op_type == "commit_generator":
        for key, least in (("count", 0), ("files", 1)):
            value = op.get(key)
            if key in op and not (isinstance(value, int) and not isinstance(value, bool) and value >= least):
                what = "a non-negative integer" if least == 0 else "a positive integer"
                result.error("GE062", f"commit_generator {key} must be {what}, not {value!r}.", f"{loc}.{key}")
    if op_type in _CASE_SENSITIVE_PAIRS:
        source_key, target_key = _CASE_SENSITIVE_PAIRS[op_type]
        source, target = op.get(source_key), op.get(target_key)
        if (isinstance(source, str) and isinstance(target, str) and source != target
                and file_system_key(source) == file_system_key(target)):
            result.error("GE060", f"{op_type} from '{source}' to '{target}' changes only the letter case or the Unicode "
                         "normalization; macOS (and Windows, for letter case) sees one file there, so what generation "
                         "makes of it would depend on the platform.", f"{loc}.{target_key}")


def _encoding_problem(value: Any) -> str | None:
    """Why graph generation cannot open a file with ``encoding=value``, or None.

    The graph operations hand the name to Python unchecked, which accepts any
    text codec it knows (``latin-1``, ``utf-16``); an unknown one, or a codec
    that is not a text encoding (``base64``), made generation fail.
    """
    if not isinstance(value, str):
        return f"must be the name of a text encoding such as 'utf-8', not {type_label(value)}"
    try:
        "".encode(value)                                  # the lookup open(encoding=...) makes
    except (LookupError, ValueError):                     # ValueError: a NUL in the name, the 'undefined' codec
        return f"{value!r} is not a text encoding Python knows"
    return None


def _validate_commit_ref_entry(entry: Any, commit_by_id: dict[str, dict[str, Any]], result: ValidationResult, loc: str, label: str) -> None:
    if isinstance(entry, str):
        cid = entry
    elif isinstance(entry, dict):
        cid = entry.get("commit")
        if "role" in entry and not isinstance(entry.get("role"), str):
            result.error("GE090", f"{label} role must be a string.", f"{loc}.role")
    else:
        result.error("GE091", f"{label} entry must be a string or object.", loc)
        return
    if not isinstance(cid, str):
        result.error("GE092", f"{label} entry must contain a commit id.", loc)
    elif cid not in commit_by_id:
        result.error("GE093", f"{label} refers to unknown commit '{cid}'.", loc)


def _validate_location_entry(entry: dict[str, Any], commit_by_id: dict[str, dict[str, Any]], result: ValidationResult, loc: str, *, require_statement: bool) -> None:
    commit = entry.get("commit")
    if not isinstance(commit, str):
        result.error("GE100", "Location entry must contain commit.", f"{loc}.commit")
    elif commit not in commit_by_id:
        result.error("GE101", f"Location entry refers to unknown commit '{commit}'.", f"{loc}.commit")
    file_value = entry.get("file")
    if file_value is not None:
        if isinstance(file_value, str):
            try:
                validate_repo_relative_path(file_value)
            except PathValidationError as exc:
                result.error("GE102", f"Invalid file path '{file_value}': {exc}", f"{loc}.file")
        else:
            result.error("GE103", "Location file must be a string when present.", f"{loc}.file")
    if require_statement and not isinstance(entry.get("statement"), str):
        result.error("GE104", "Location entry requires a statement.", f"{loc}.statement")
    if "entity" in entry and not isinstance(entry.get("entity"), dict):
        result.error("GE105", "Location entity must be an object when present.", f"{loc}.entity")


def _declares_expect_no_bic(expected: Any) -> bool:
    """True when expected_szz.commit_level or any evaluation variant sets expect_no_bic: true.

    Such a scenario intentionally has no bug-introducing commit in the repository
    (an externally caused fault), so an empty bug_introducing_commits list is valid.
    """
    if not isinstance(expected, dict):
        return False
    commit_level = expected.get("commit_level")
    if isinstance(commit_level, dict) and commit_level.get("expect_no_bic") is True:
        return True
    variants = expected.get("evaluation_variants")
    if isinstance(variants, list):
        for variant in variants:
            if isinstance(variant, dict):
                cl = variant.get("commit_level")
                if isinstance(cl, dict) and cl.get("expect_no_bic") is True:
                    return True
    return False


def _validate_expected_szz(expected: Any, commit_by_id: dict[str, dict[str, Any]], result: ValidationResult) -> None:
    if expected is None:
        result.warning("GW120", "expected_szz is missing.", "expected_szz")
        return
    if not isinstance(expected, dict):
        result.error("GE120", "expected_szz must be an object.", "expected_szz")
        return
    policies = []
    commit_level = expected.get("commit_level")
    if isinstance(commit_level, dict):
        policy = commit_level.get("evaluation_policy")
        if isinstance(policy, str):
            policies.append((policy, "expected_szz.commit_level.evaluation_policy"))
        _validate_oracle_lists(commit_level, commit_by_id, result, "expected_szz.commit_level")
    variants = expected.get("evaluation_variants")
    if variants is not None and not isinstance(variants, list):
        # read only as a list, so anything else passed unnoticed (issue #127)
        result.error("GE122", "expected_szz.evaluation_variants must be a list of evaluation variants.",
                     "expected_szz.evaluation_variants")
    if isinstance(variants, list):
        for i, variant in enumerate(variants):
            if not isinstance(variant, dict):
                result.error("GE122", "Each evaluation variant must be an object.", f"expected_szz.evaluation_variants[{i}]")
                continue
            name = variant.get("name")
            if not isinstance(name, str) or not name:
                # the evaluator selects a variant by its name; without one it is never scored (issue #127)
                result.error("GE122", "Each evaluation variant must have a non-empty string name.",
                             f"expected_szz.evaluation_variants[{i}].name")
            cl = variant.get("commit_level")
            if isinstance(cl, dict):
                _validate_oracle_lists(cl, commit_by_id, result, f"expected_szz.evaluation_variants[{i}].commit_level")
                variant_policy = cl.get("evaluation_policy")
                if isinstance(variant_policy, str):
                    policies.append((variant_policy, f"expected_szz.evaluation_variants[{i}].commit_level.evaluation_policy"))
    for policy, loc in policies:
        if policy not in ALLOWED_EVALUATION_POLICIES:
            result.warning("GW123", f"Unknown evaluation_policy '{policy}'.", loc)
    # A default_variant the evaluator cannot resolve makes it score commit_level
    # instead, with at most a note at every evaluation (SZZG-0136).  What counts
    # is that the key is there: a blank `default_variant:` loads as None, and the
    # evaluator then falls back without any note (PR #105 review).
    if "default_variant" in expected and _selected_evaluation_variant(expected, None, []) is None:
        default_variant = expected["default_variant"]
        what = ("is blank (a YAML null)" if default_variant is None
                else f"{default_variant!r} names no evaluation variant")
        names = [v.get("name") for v in variants if isinstance(v, dict)] if isinstance(variants, list) else []
        result.error("GE129", f"default_variant {what} (declared: {', '.join(map(str, names)) or 'none'}); the "
                     "evaluator would score commit_level instead. Name a declared variant, or remove "
                     "default_variant to make commit_level the default.",
                     "expected_szz.default_variant")
    branch_level = expected.get("branch_level")
    if branch_level is not None:
        # Scored per declared BFC since 2026-09-22 (docs/evaluation-policies.md section 1.5).
        if not isinstance(branch_level, dict) or not branch_level:
            result.error("GE127", "expected_szz.branch_level must be a non-empty object mapping branch names to {bfc, required}.", "expected_szz.branch_level")
        else:
            for name, spec in branch_level.items():
                loc = f"expected_szz.branch_level.{name}"
                if not isinstance(spec, dict):
                    result.error("GE127", f"{loc} must be an object with bfc and required.", loc)
                    continue
                bfc = spec.get("bfc")
                if not isinstance(bfc, str):
                    result.error("GE127", f"{loc}.bfc is required and must be a commit id.", f"{loc}.bfc")
                elif bfc not in commit_by_id:
                    result.error("GE128", f"{loc}.bfc refers to unknown commit '{bfc}'.", f"{loc}.bfc")
                if not isinstance(spec.get("required"), list):
                    # a blank `required:` is None and would become an oracle that expects nothing
                    result.error("GE127", f"{loc}.required must be a list of commit ids (write [] for an intentionally empty answer).", f"{loc}.required")
                else:
                    _validate_commit_list(spec["required"], commit_by_id, result, f"{loc}.required")


def _warn_inferred_commit_level(data: dict[str, Any], result: ValidationResult) -> None:
    """GW130: a commit-level oracle the evaluator would have to infer (issue #118).

    With no ``required`` and no ``expect_no_bic: true``, the evaluator takes the
    required set from bugs[] and notes it at every evaluation: a warning about a
    scenario the user did not write, which no check had asked to declare.  As
    for GE129, the evaluator is asked, for each oracle it can score: every
    evaluation variant, and ``commit_level`` unless ``default_variant`` names a
    variant to score instead (SZZG-0022 keeps its whole oracle in variants).
    """
    expected = data.get("expected_szz")
    if not isinstance(expected, dict):
        return                                          # GW120 / GE120
    oracles = []
    if _selected_evaluation_variant(expected, None, []) is None:
        oracles.append((None, "expected_szz.commit_level", "expected_szz.commit_level"))
    variants = expected.get("evaluation_variants")
    for i, variant in enumerate(variants if isinstance(variants, list) else []):
        if isinstance(variant, dict) and isinstance(variant.get("name"), str):
            oracles.append((variant["name"], f"expected_szz.evaluation_variants[{i}].commit_level",
                            f"evaluation variant '{variant['name']}'"))
    for name, loc, subject in oracles:
        policy = _commit_level_policy(data, "advanced-scenarios", name)
        if policy.required_inferred:
            inferred = (f"take {', '.join(policy.required)} from bugs[]" if policy.required
                        else "find nothing in bugs[] and score an empty required set")
            result.warning("GW130", f"{subject} declares no required commits and no expect_no_bic: true, so the "
                           f"evaluator would {inferred} and note it at every evaluation. Declare required (or "
                           "expect_no_bic: true for an intentionally empty oracle).", loc)


def _validate_oracle_lists(commit_level: dict[str, Any], commit_by_id: dict[str, dict[str, Any]],
                           result: ValidationResult, loc: str) -> None:
    """The commit lists of one oracle, ``commit_level`` or a variant's: GW130
    hands either to the evaluator, which reads every one of them (PR #124
    review: ``acceptable_related: 5`` was neither checked nor survivable)."""
    for key in ["required", "relevant", "related_origins", "related_but_not_correct"]:
        _validate_commit_list(commit_level.get(key), commit_by_id, result, f"{loc}.{key}")
    acceptable = commit_level.get("acceptable_related")
    if acceptable is not None and not isinstance(acceptable, list):
        result.error("GE124", f"{loc}.acceptable_related must be a list when present.", f"{loc}.acceptable_related")
    for i, item in enumerate(acceptable if isinstance(acceptable, list) else []):
        if isinstance(item, str):
            if item not in commit_by_id:
                result.error("GE121", f"expected_szz acceptable_related refers to unknown commit '{item}'.", f"{loc}.acceptable_related[{i}]")
        elif isinstance(item, dict):
            cid = item.get("commit")
            if isinstance(cid, str) and cid not in commit_by_id:
                result.error("GE121", f"expected_szz acceptable_related refers to unknown commit '{cid}'.", f"{loc}.acceptable_related[{i}].commit")


def _validate_commit_list(value: Any, commit_by_id: dict[str, dict[str, Any]], result: ValidationResult, loc: str) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        result.error("GE124", f"{loc} must be a list when present.", loc)
        return
    for i, cid in enumerate(value):
        if not isinstance(cid, str):
            result.error("GE125", f"{loc} entries must be commit ids.", f"{loc}[{i}]")
        elif cid not in commit_by_id:
            result.error("GE126", f"{loc} refers to unknown commit '{cid}'.", f"{loc}[{i}]")


def _validate_context_sections(data: dict[str, Any], commit_by_id: dict[str, dict[str, Any]], result: ValidationResult) -> None:
    for section_name in ["work_items", "issues", "developer_hints"]:
        section = data.get(section_name)
        if section is not None and not isinstance(section, list):
            result.error("GE140", f"{section_name} must be a list when present.", section_name)
    _validate_issue_documents(data, result)
    for i, hint in enumerate(data.get("developer_hints", []) or []):
        if not isinstance(hint, dict):
            continue
        commit = hint.get("commit")
        if isinstance(commit, str) and commit not in commit_by_id:
            result.error("GE141", f"developer_hints[{i}] refers to unknown commit '{commit}'.", f"developer_hints[{i}].commit")
        refs = hint.get("referenced_commits")
        if isinstance(refs, list):
            for j, ref in enumerate(refs):
                if isinstance(ref, str) and ref not in commit_by_id:
                    result.error("GE142", f"developer_hints[{i}] references unknown commit '{ref}'.", f"developer_hints[{i}].referenced_commits[{j}]")


REPORTED_LINE_RE = re.compile(r"^Reported:\s*(\S+)\s*$", re.M)


def _canonical_timestamp(value: Any) -> str | None:
    """The instant as ISO 8601 in UTC (``...Z``), or None if ``value`` is not a timestamp.

    Accepts a str or the ``datetime`` PyYAML makes of an unquoted value.  The
    instant is converted to UTC first, so two spellings of one moment -- ``Z``
    and ``+09:00`` -- canonicalise to the same string and compare equal;
    ``format_timestamp`` alone keeps the offset and would not.
    """
    if not isinstance(value, (str, datetime)) or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return format_timestamp(parse_timestamp(value).astimezone(timezone.utc))
    except (GitError, ValueError, TypeError):
        return None


def _validate_issue_documents(data: dict[str, Any], result: ValidationResult) -> None:
    """GW470/GW471/GW472: an issue's tool-visible document must exist and state its report date.

    decisions/tool-visible-context.md: an ``issues[]`` entry may name the
    ``document`` a commit writes into the repository and the ``reported_at``
    timestamp that document states.  Both are copies of each other, so they are
    checked against the ``write_file`` operations rather than trusted.

    ``reported_at`` may arrive as a str or as the ``datetime`` PyYAML makes of an
    unquoted ISO 8601 value; both are normalised and compared as instants with
    the document's ``Reported:`` line.  Anything else is GW472, never silence.
    The containers are re-checked here because validate_graph_static has only
    *reported* their types (GE030/GE044); it has not replaced them.
    """
    issues = data.get("issues")
    if not isinstance(issues, list):
        return
    written: dict[str, str] = {}
    commits = data.get("commits")
    for commit in commits if isinstance(commits, list) else []:
        if not isinstance(commit, dict):
            continue
        operations = commit.get("operations")
        for op in operations if isinstance(operations, list) else []:
            if isinstance(op, dict) and op.get("type") == "write_file" and isinstance(op.get("path"), str) and isinstance(op.get("content"), str):
                written[op["path"]] = op["content"]
    for i, issue in enumerate(issues):
        if not isinstance(issue, dict):
            continue
        document, reported_at = issue.get("document"), issue.get("reported_at")
        canonical = _canonical_timestamp(reported_at) if reported_at is not None else None
        if reported_at is not None and canonical is None:
            result.warning("GW472", f"issues[{i}].reported_at is not an ISO 8601 timestamp: {reported_at!r} ({type(reported_at).__name__}).", f"issues[{i}].reported_at")
        if isinstance(document, str):
            if document not in written:
                result.warning("GW470", f"issues[{i}] names document '{document}', but no commit writes it (write_file).", f"issues[{i}].document")
            elif canonical is not None:
                match = REPORTED_LINE_RE.search(written[document])
                stated = _canonical_timestamp(match.group(1)) if match else None
                if match is None:
                    result.warning("GW471", f"issues[{i}] says reported_at {canonical}, but '{document}' has no 'Reported: <timestamp>' line.", f"issues[{i}].reported_at")
                elif stated is None:
                    result.warning("GW471", f"issues[{i}]: '{document}' states 'Reported: {match.group(1)}', which is not an ISO 8601 timestamp.", f"issues[{i}].reported_at")
                elif stated != canonical:
                    result.warning("GW471", f"issues[{i}] says reported_at {canonical}, but '{document}' states Reported: {stated}.", f"issues[{i}].reported_at")
        elif reported_at is not None:
            result.warning("GW470", f"issues[{i}] has reported_at but names no document a tool could read it from.", f"issues[{i}].reported_at")


def _validate_graph_acyclic(commits: list[Any]) -> ValidationResult:
    result = ValidationResult()
    parent_map: dict[str, list[str]] = {}
    for commit in commits:
        if isinstance(commit, dict) and isinstance(commit.get("id"), str):
            # GE036 reports parents that are not a list; iterating `parents: 42` raised (issue #152)
            parents = commit.get("parents")
            parent_map[commit["id"]] = [p for p in parents if isinstance(p, str)] if isinstance(parents, list) else []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(cid: str) -> None:
        if cid in visited:
            return
        if cid in visiting:
            result.error("GE150", f"Commit graph contains a cycle at '{cid}'.", f"commits.{cid}")
            return
        visiting.add(cid)
        for parent in parent_map.get(cid, []):
            if parent in parent_map:
                visit(parent)
        visiting.remove(cid)
        visited.add(cid)

    for cid in parent_map:
        visit(cid)
    return result


def _validate_merge_parents(commits: list[Any]) -> ValidationResult:
    """GE049: a merge parent that Git would not record (issue #173).

    ``git merge`` records each head once, and drops a head that is already
    reachable from another one -- from the first parent or from another head
    of the same merge.  A parent listed twice, or an extra parent that is an
    ancestor of another parent, therefore leaves the generated commit with
    fewer parents than declared, and verification fails (GE627/GE628).  The
    first parent is always recorded (the generator merges with ``--no-ff``).
    """
    result = ValidationResult()
    parent_map: dict[str, list[str]] = {}
    for commit in commits:
        if isinstance(commit, dict) and isinstance(commit.get("id"), str) and isinstance(commit.get("parents"), list):
            parent_map[commit["id"]] = [p for p in commit["parents"] if isinstance(p, str)]

    def reaches(starts: list[str], target: str) -> bool:
        stack, seen = list(starts), set()
        while stack:
            cid = stack.pop()
            if cid == target:
                return True
            if cid not in seen:
                seen.add(cid)
                stack.extend(parent_map.get(cid, []))
        return False

    for i, commit in enumerate(commits):
        if not isinstance(commit, dict) or not isinstance(commit.get("parents"), list):
            continue
        cid = commit.get("id")
        parents = [p for p in commit["parents"] if isinstance(p, str)]
        for k, parent in enumerate(parents[1:], start=1):
            if parent in parents[:k]:
                result.error(
                    "GE049",
                    f"Commit '{cid}' lists parent '{parent}' twice: Git records each parent once, "
                    "so it would not record this merge as declared.",
                    f"commits[{i}].parents",
                )
                continue
            covering = next((other for other in parents if other != parent and reaches([other], parent)), None)
            if covering is not None:
                result.error(
                    "GE049",
                    f"Commit '{cid}' lists parent '{parent}', which is already an ancestor of its parent '{covering}': "
                    "Git does not record an already merged parent, so it would not record this merge as declared.",
                    f"commits[{i}].parents",
                )
    return result


def _validate_branch_rewinds(data: dict[str, Any]) -> ValidationResult:
    """GW151: a first parent off the branch that leaves commits unreachable (issue #174).

    A branch's tip is the last commit declared on it.  When a commit's branch
    already exists and its first parent is not the branch's tip, the generator
    checks the branch out and resets it to that parent (``_checkout_for_commit``).
    If the tip is an ancestor of the parent, that is a fast-forward (SZZG-0052
    and SZZG-0128 ``c4``) and nothing is reported.  Otherwise the branch no
    longer contains the commits only its old tip reached, and those that no
    ref reaches once generation has finished (``gitutils.reachable_commit_ids``:
    no branch, tag or HEAD) are not in ``git log --all``.  Not reported: a
    commit on a branch ``graph.ref_lifecycle.delete_branches`` deletes, and one
    that a commit's ``rebase_of`` or ``squashes`` names -- they are left behind
    on purpose.  A commit two resets leave behind is named at the later one.
    """
    result = ValidationResult()
    graph = data.get("graph") if isinstance(data.get("graph"), dict) else {}
    lifecycle = graph.get("ref_lifecycle") if isinstance(graph.get("ref_lifecycle"), dict) else {}
    if any(lifecycle.get(key) is not None and not isinstance(lifecycle.get(key), list)
           for key in ("tags", "delete_branches")):
        return result                    # the generator refuses it before it moves a ref
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else {}
    default_branch = str(repository.get("default_branch") or "main")
    try:
        commits, parents_of = history_graph(data)
        reachable = reachable_commit_ids(data)
    except (TypeError, ValueError, OverflowError):
        # a value the generator refuses, such as a commit_generator count of .inf
        # (OverflowError); --simulate and generation report it
        return result
    deleted = {name for name in lifecycle.get("delete_branches") or [] if isinstance(name, str)}
    rewritten: set[str] = set()
    for commit in commits:
        for key in REWRITE_DECLARATION_KEYS:
            value = commit.get(key)
            rewritten.update(v for v in (value if isinstance(value, list) else [value]) if isinstance(v, str))

    def branch_of(commit: dict[str, Any]) -> str:
        return str(commit.get("branch") or default_branch)

    def ancestors(cid: str) -> set[str]:
        seen: set[str] = set()
        stack = [cid]
        while stack:
            current = stack.pop()
            if current not in seen:
                seen.add(current)
                stack.extend(parents_of.get(current, []))
        return seen

    tips: dict[str, str] = {}
    resets: list[tuple[int, str, str, str, str]] = []   # (index, commit, branch, old tip, first parent)
    left_behind_by: dict[str, int] = {}                 # commit -> the last reset that left it behind
    for i, commit in enumerate(data.get("commits") or []):
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        cid, branch = commit["id"], branch_of(commit)
        parents = [p for p in commit.get("parents") or [] if isinstance(p, str)]
        if parents and branch in tips and tips[branch] != parents[0]:
            behind = ancestors(tips[branch]) - ancestors(parents[0])
            for c in commits:
                if c["id"] in behind:
                    left_behind_by[c["id"]] = len(resets)
            resets.append((i, cid, branch, tips[branch], parents[0]))
        tips[branch] = cid

    lost = [c["id"] for c in commits
            if c["id"] in left_behind_by and c["id"] not in reachable
            and branch_of(c) not in deleted and c["id"] not in rewritten]
    for k, (i, cid, branch, old_tip, first_parent) in enumerate(resets):
        named = [c for c in lost if left_behind_by[c] == k]
        if not named:
            continue                     # a fast-forward, or nothing is lost
        them = "it" if len(named) == 1 else "them"
        result.warning(
            "GW151",
            f"Commit '{cid}' resets branch '{branch}' from its tip '{old_tip}' to its first parent "
            f"'{first_parent}', which is not a fast-forward: after generation no ref reaches "
            f"{', '.join(repr(c) for c in named)}, so git log --all does not show {them}. If the rewrite "
            f"is intended, name {them} in a later commit's rebase_of or squashes; otherwise keep {them} "
            f"with a graph.ref_lifecycle tag, or put '{cid}' on another branch.",
            f"commits[{i}].parents",
        )
    return result


def _validate_ref_lifecycle(data: dict[str, Any], result: ValidationResult) -> None:
    """GE152-GE158: ``graph.ref_lifecycle`` as the generator applies it (issue #229).

    Only the generator read the section, after every commit existed.  The
    rules are ``graph_scenario.ref_lifecycle_problems``, which the generator
    asks too before it changes a ref; here the commits are the scenario's
    and those its ``commit_generator`` operations plan, and the branches
    those some commit is on.
    """
    graph = data.get("graph")
    if not isinstance(graph, dict) or "ref_lifecycle" not in graph:
        return
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else {}
    default_branch = str(repository.get("default_branch") or "main")
    commit_ids: set[str] = set()
    branches: set[str] = set()
    for commit in data.get("commits") if isinstance(data.get("commits"), list) else []:
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        commit_ids.add(commit["id"])
        branches.add(str(commit.get("branch") or default_branch))
        try:
            commit_ids.update(planned_generated_commits(commit["id"], commit))
        except (TypeError, ValueError, OverflowError):
            pass                         # operations or a count the generator refuses (GE044, --simulate)
    for code, location, message in ref_lifecycle_problems(graph["ref_lifecycle"], commit_ids=commit_ids,
                                                          branches=branches, default_branch=default_branch):
        result.error(code, message, location)


def _validate_rewrite_references(
    commit: dict[str, Any],
    cid: str,
    commit_by_id: dict[str, dict[str, Any]],
    result: ValidationResult,
    loc: str,
) -> None:
    """GE046/GE047: rebase_of, squashes and revert_of must name earlier commits."""
    for ref_key, allowed_types in REWRITE_REFERENCE_KEYS.items():
        value = commit.get(ref_key)
        if value is None:
            continue
        if not isinstance(value, allowed_types):
            expected = " or ".join(t.__name__ for t in allowed_types)
            result.error("GE046", f"{ref_key} must be a {expected} when present.", f"{loc}.{ref_key}")
            continue
        refs = value if isinstance(value, list) else [value]
        for k, ref in enumerate(refs):
            ref_loc = f"{loc}.{ref_key}[{k}]" if isinstance(value, list) else f"{loc}.{ref_key}"
            if not isinstance(ref, str):
                result.error("GE046", f"{ref_key} entries must be commit ids.", ref_loc)
            elif ref == cid or ref not in commit_by_id:
                result.error("GE047", f"{ref_key} refers to unknown or later commit '{ref}'.", ref_loc)


# --- opt-in lints (graph suite) ---------------------------------------------

def lint_graph_scenario(data: dict[str, Any], *, scenario_path: Path | None = None) -> ValidationResult:
    """Run the GW4xx lints on a statically valid graph scenario.

    Ghost invariants (add-only BFC / delete-only BIC) are not implemented for
    the graph suite.

    ``scenario_path`` enables the lints that compare the scenario against its
    sibling README; without it they are skipped.
    """
    result = ValidationResult()
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    commits = [c for c in (data.get("commits") or []) if isinstance(c, dict)]
    bugs = [b for b in (data.get("bugs") or []) if isinstance(b, dict)]
    bfc_ids = {e["commit"] for b in bugs for e in graph_bfc_entries(b) if isinstance(e.get("commit"), str)}

    lint_factors(meta.get("factors"), result, prefix="GW")
    lint_tier(meta, result, prefix="GW")
    lint_difficulty(meta, result, prefix="GW")
    lint_defeats(meta, result, prefix="GW")
    for i, bug in enumerate(bugs):
        for j, entry in enumerate(graph_bic_entries(bug)):
            role = entry.get("role")
            if isinstance(role, str) and role not in ALLOWED_BIC_ROLES:
                result.error(
                    "GE403",
                    f"BIC role '{role}' is a non-canonical spelling; canonical roles are {sorted(ALLOWED_BIC_ROLES)}. "
                    "Consumers normalize known aliases, but a scenario declares the canonical spelling.",
                    f"bugs[{i}].bug_introducing_commits[{j}].role",
                )
        for j, entry in enumerate(graph_bfc_entries(bug)):
            role = entry.get("role")
            if isinstance(role, str) and role not in ALLOWED_BFC_ROLES:
                result.error("GE404", f"BFC role '{role}' is not in {sorted(ALLOWED_BFC_ROLES)}.", f"bugs[{i}].bug_fixing_commits[{j}].role")
    lint_leakage(commits, bfc_ids, result, prefix="GW")
    lint_author_coincidence(data, "advanced-scenarios", result, prefix="GW")
    _lint_approximate_operations(commits, result)
    _lint_origin_coverage(bugs, data, result)
    if scenario_path is not None:
        _lint_readme_history(commits, scenario_path, result)
        lint_readme_header(data, "advanced-scenarios", scenario_path, result, prefix="GW")
    return result


#: A line of a README ``## Expected history`` block: ``c1: introduce bug (replace A.java)``.
README_HISTORY_LINE = re.compile(r"^(?P<id>[A-Za-z]\w*): (?P<phrase>[^(]+?) \((?P<ops>.*)\)\s*$")
README_HISTORY_BLOCK = re.compile(r"^## Expected history\s*\n+```text\n(?P<body>.*?)\n```", re.S | re.M)


def _readme_operation_summary(commit: dict[str, Any]) -> str:
    """Render a commit's operations the way the README blocks spell them."""
    parts = []
    for op in commit.get("operations") or []:
        if not isinstance(op, dict):
            continue
        kind = op.get("type")
        if kind in ("rename_file", "copy_file", "move_file"):
            parts.append(f"{kind} {op.get('from')} -> {op.get('to')}")
        elif "path" in op:
            parts.append(f"{kind} {op['path']}")
        else:
            parts.append(str(kind))
    return "; ".join(parts)


def _lint_readme_history(commits: list[dict[str, Any]], scenario_path: Path, result: ValidationResult) -> None:
    """GW454: the README's ``## Expected history`` block contradicts the scenario.

    Only the parenthesised operation list is checked, because that part is
    mechanically derivable from ``commits``; the surrounding phrase is prose and
    is left to the author.  READMEs that describe the history in prose instead
    of this shape have no such block and are not linted.  The block is a copy of
    data that lives in the scenario file, so it drifts silently whenever a
    commit's operations change -- which is exactly how SZZG-0001, SZZG-0003 and
    SZZG-0017 went stale when their histories were repaired for the graph-1.0
    freeze.
    """
    readme = scenario_path.with_name("README.md")
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return
    block = README_HISTORY_BLOCK.search(text)
    if block is None:
        return
    by_id = {c["id"]: c for c in commits if isinstance(c.get("id"), str)}
    for line in block.group("body").splitlines():
        if not line.strip():
            continue
        match = README_HISTORY_LINE.match(line)
        if match is None:
            continue
        commit = by_id.get(match.group("id"))
        if commit is None:
            result.warning(
                "GW454",
                f"README 'Expected history' names commit '{match.group('id')}', which the scenario does not define.",
                f"{readme.name}:## Expected history",
            )
            continue
        expected = _readme_operation_summary(commit)
        if match.group("ops") != expected:
            result.warning(
                "GW454",
                f"README 'Expected history' describes commit '{match.group('id')}' as "
                f"'({match.group('ops')})' but the scenario's operations are '({expected})'.",
                f"{readme.name}:## Expected history",
            )


def _lint_approximate_operations(commits: list[dict[str, Any]], result: ValidationResult) -> None:
    """GW440-GW443: operations whose generated result only approximates the intent."""
    for i, commit in enumerate(commits):
        for j, op in enumerate(commit.get("operations") or []):
            if not isinstance(op, dict):
                continue
            entry = APPROXIMATE_OPERATIONS.get(op.get("type"))
            if entry is not None:
                code, message = entry
                result.warning(code, f"Commit '{commit.get('id', f'<commit[{i}]>')}': {message}", f"commits[{i}].operations[{j}]")


def _expected_szz_commit_ids(expected: Any) -> set[str]:
    """Every commit id named by expected_szz.commit_level or any evaluation variant."""
    ids: set[str] = set()
    if not isinstance(expected, dict):
        return ids
    levels = [expected.get("commit_level")]
    variants = expected.get("evaluation_variants")
    for variant in variants if isinstance(variants, list) else []:
        if isinstance(variant, dict):
            levels.append(variant.get("commit_level"))
    for level in levels:
        if not isinstance(level, dict):
            continue
        for key in EXPECTED_SZZ_COMMIT_LISTS:
            values = level.get(key)
            if isinstance(values, list):
                ids.update(cid for cid in (commit_id_of(v) for v in values) if cid is not None)
    return ids


def _lint_origin_coverage(bugs: list[dict[str, Any]], data: dict[str, Any], result: ValidationResult) -> None:
    """The direct/origin contract, checked on the scenario file (issue #3, D10).

    GW450 an origin BIC that expected_szz never mentions, in any variant.
    GW451 an origin that the *default* variant does not list as related_origins,
          so predicting it is a plain false positive rather than a recognised
          origin (contract D2).
    GW452 a scenario with an origin and no ``origin-aware`` variant, so there is
          no way to score a tool that reports origins as context (D3).
    GW453 an ``origin-aware`` variant that does not in fact accept the origin.

    Which variant is the default, and whether a variant accepts a prediction,
    are the evaluator's questions: both come from ``_commit_level_policy`` and
    ``classify_prediction`` rather than from reading the YAML here.  An earlier
    version read ``expected_szz.commit_level`` directly and inspected
    ``acceptable_related`` membership, and was wrong twice - it ignored
    ``default_variant`` when a base commit_level existed, and it called a
    variant accepting when a leftover ``related_but_not_correct`` entry or
    ``expect_no_bic`` meant the evaluator rejected the same prediction
    (PR #45 review).

    An origin that is itself ``required`` is exempt from GW451-GW453: it is the
    answer, not context, and an origin-aware variant would be identical to the
    default (SZZG-0018).
    """
    expected = data.get("expected_szz")
    mentioned = _expected_szz_commit_ids(expected)
    try:
        default = _commit_level_policy(data, "advanced-scenarios", None)
    except Exception:                                   # a malformed oracle is other checks' business
        return
    required = set(default.required)
    related_origins = set(default.related_origins)
    variants = expected.get("evaluation_variants") if isinstance(expected, dict) else None
    variant_names = {v.get("name") for v in (variants if isinstance(variants, list) else [])
                     if isinstance(v, dict) and isinstance(v.get("name"), str)}

    origins: list[str] = []
    for i, bug in enumerate(bugs):
        for j, entry in enumerate(graph_bic_entries(bug)):
            role = entry.get("role")
            cid = entry.get("commit")
            if not (isinstance(role, str) and "origin" in role and isinstance(cid, str)):
                continue
            loc = f"bugs[{i}].bug_introducing_commits[{j}]"
            label = bug.get("id", f"<bug[{i}]>")
            if cid not in mentioned:
                result.warning("GW450", f"bug {label} BIC '{cid}' has role '{role}' but appears in no expected_szz list (commit_level or any variant).", loc)
                continue
            if cid in required:
                continue
            if cid not in origins:
                origins.append(cid)
            if cid not in related_origins:
                result.warning("GW451", f"bug {label} BIC '{cid}' has role '{role}' but the default commit_level does not list it under related_origins (direct/origin contract D2).", loc)
    if not origins:
        return
    if "origin-aware" not in variant_names:
        result.warning("GW452", "scenario declares an origin BIC but offers no 'origin-aware' evaluation variant (direct/origin contract D3).", "expected_szz.evaluation_variants")
        return
    try:
        variant = _commit_level_policy(data, "advanced-scenarios", "origin-aware")
    except Exception:
        return
    scored = classify_prediction(variant, sorted(required | set(origins)))
    if scored.status != "PASS":
        result.warning("GW453", f"the 'origin-aware' variant does not accept the direct BICs together with origin(s) {sorted(origins)}: the evaluator returns {scored.status} (direct/origin contract D3).", "expected_szz.evaluation_variants")
