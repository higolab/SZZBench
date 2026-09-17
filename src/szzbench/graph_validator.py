from __future__ import annotations

from pathlib import Path
from typing import Any
import re

from .findings import ValidationResult
from .graph_operations import PATH_FIELDS_BY_OPERATION, REQUIRED_FIELDS_BY_OPERATION, SUPPORTED_GRAPH_OPERATIONS
from .graph_scenario import graph_bfc_entries, graph_bic_entries, graph_faults, graph_fixes, load_graph_scenario
from .graph_simulator import simulate_graph_scenario
from .paths import PathValidationError, validate_repo_relative_path

GRAPH_ID_RE = re.compile(r"^SZZG-\d{4}$")

ALLOWED_EVALUATION_POLICIES = {
    "exact_set",
    "partial_credit",
    "top_k",
    "direct_only",
    "origin_aware",
    "reintroduction_direct",
    "relaxed_with_credit",
}


def validate_graph_scenario_file(
    path: Path,
    *,
    strict_paths: bool = False,
    simulate: bool = False,
) -> tuple[dict[str, Any] | None, ValidationResult]:
    data, result = load_graph_scenario(path)
    if data is None:
        return None, result
    result.extend(validate_graph_static(data, scenario_path=path, strict_paths=strict_paths))
    if simulate and not result.has_errors():
        result.extend(simulate_graph_scenario(data))
    return data, result


def validate_graph_static(data: dict[str, Any], *, scenario_path: Path | None = None, strict_paths: bool = False) -> ValidationResult:
    result = ValidationResult()
    for key in ["schema_version", "meta", "repository", "commits", "bugs"]:
        if key not in data:
            result.error("GE010", f"Missing required top-level field '{key}'.", key)

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
        if "factors" in meta and not isinstance(meta.get("factors"), list):
            result.error("GE016", "meta.factors must be a list.", "meta.factors")

    if repository is None:
        result.error("GE020", "'repository' must be an object.", "repository")
    else:
        for key in ["name", "default_branch"]:
            if key not in repository:
                result.warning("GW021", f"repository.{key} is missing.", f"repository.{key}")

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
        parents = commit.get("parents", [])
        if not isinstance(parents, list):
            result.error("GE036", "commit.parents must be a list.", f"{loc}.parents")
            parents = []
        for parent in parents:
            if not isinstance(parent, str):
                result.error("GE037", "Each parent id must be a string.", f"{loc}.parents")
            elif parent not in seen:
                # Require topological order for the MVP graph generator.
                if parent in commit_by_id or any(isinstance(c, dict) and c.get("id") == parent for c in commits):
                    result.error("GE038", f"Parent '{parent}' must appear before commit '{cid}' for graph generation.", f"{loc}.parents")
                else:
                    result.error("GE039", f"Unknown parent commit '{parent}'.", f"{loc}.parents")
        if commit.get("role") == "merge" and len(parents) < 2:
            result.warning("GW040", f"Commit '{cid}' has role merge but fewer than two parents.", loc)
        if len(parents) >= 2 and commit.get("role") not in {"merge", "bug_fixing", "bug_introducing", "squash_merge"}:
            result.warning("GW041", f"Commit '{cid}' has multiple parents but role is not explicitly merge-like.", loc)
        for ref_key in ["cherry_pick_of", "backport_of"]:
            ref = commit.get(ref_key)
            if ref is not None:
                if not isinstance(ref, str):
                    result.error("GE042", f"{ref_key} must be a string when present.", f"{loc}.{ref_key}")
                elif ref not in commit_by_id:
                    result.error("GE043", f"{ref_key} refers to unknown or later commit '{ref}'.", f"{loc}.{ref_key}")
        operations = commit.get("operations", [])
        if operations is None:
            operations = []
        if not isinstance(operations, list):
            result.error("GE044", "commit.operations must be a list.", f"{loc}.operations")
            continue
        if not operations and not commit.get("allow_empty") and len(parents) < 2:
            result.warning("GW045", f"Commit '{cid}' has no operations and is not allow_empty.", loc)
        for j, op in enumerate(operations):
            _validate_operation(op, result, f"{loc}.operations[{j}]", strict_paths=strict_paths)

    result.extend(_validate_graph_acyclic(commits))

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

        bic_entries = graph_bic_entries(bug)
        bfc_entries = graph_bfc_entries(bug)
        if not bic_entries:
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
        for key in ["required", "relevant", "related_origins", "related_but_not_correct"]:
            _validate_commit_list(commit_level.get(key), commit_by_id, result, f"expected_szz.commit_level.{key}")
        acceptable = commit_level.get("acceptable_related")
        if isinstance(acceptable, list):
            for i, item in enumerate(acceptable):
                if isinstance(item, str):
                    if item not in commit_by_id:
                        result.error("GE121", f"expected_szz acceptable_related refers to unknown commit '{item}'.", f"expected_szz.commit_level.acceptable_related[{i}]")
                elif isinstance(item, dict):
                    cid = item.get("commit")
                    if isinstance(cid, str) and cid not in commit_by_id:
                        result.error("GE121", f"expected_szz acceptable_related refers to unknown commit '{cid}'.", f"expected_szz.commit_level.acceptable_related[{i}].commit")
    variants = expected.get("evaluation_variants")
    if isinstance(variants, list):
        for i, variant in enumerate(variants):
            if not isinstance(variant, dict):
                result.error("GE122", "Each evaluation variant must be an object.", f"expected_szz.evaluation_variants[{i}]")
                continue
            cl = variant.get("commit_level")
            if isinstance(cl, dict):
                _validate_commit_list(cl.get("required"), commit_by_id, result, f"expected_szz.evaluation_variants[{i}].commit_level.required")
    for policy, loc in policies:
        if policy not in ALLOWED_EVALUATION_POLICIES:
            result.warning("GW123", f"Unknown evaluation_policy '{policy}'.", loc)


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


def _validate_graph_acyclic(commits: list[Any]) -> ValidationResult:
    result = ValidationResult()
    parent_map: dict[str, list[str]] = {}
    for commit in commits:
        if isinstance(commit, dict) and isinstance(commit.get("id"), str):
            parent_map[commit["id"]] = [p for p in commit.get("parents", []) if isinstance(p, str)]
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
