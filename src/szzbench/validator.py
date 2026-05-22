from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .findings import ValidationResult
from .operations import SUPPORTED_OPERATIONS, FUTURE_OPERATIONS, OperationError, apply_operation_to_memory, find_all_occurrences
from .paths import PathValidationError, validate_repo_relative_path
from .scenario import load_yaml

ALLOWED_ROLES = {
    "initial", "bug_introducing", "bug_fixing", "distractor", "refactoring",
    "formatting", "test_change", "merge", "revert", "cleanup", "feature_addition",
}

def validate_scenario_file(path: Path, *, simulate: bool = False) -> tuple[dict[str, Any] | None, ValidationResult, dict[str, dict[str, str]] | None]:
    data, result = load_yaml(path)
    if data is None:
        return None, result, None
    result.extend(validate_static(data, scenario_path=path))
    snapshots = None
    if simulate and not result.has_errors():
        snapshots, sim_result = simulate_commits(data)
        result.extend(sim_result)
        if snapshots is not None and not sim_result.has_errors():
            result.extend(validate_oracle_against_snapshots(data, snapshots))
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
