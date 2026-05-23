from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .findings import ValidationResult
from .gitutils import GitError, git_blame_line, git_hash_exists, git_message, git_parent, git_show, run_git
from .graph_scenario import graph_bfc_entries, graph_bic_entries, graph_faults, graph_fixes, load_graph_scenario
from .operations import find_all_occurrences


def load_json_file(path: Path, *, code: str) -> tuple[dict[str, Any], ValidationResult]:
    result = ValidationResult()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        result.error(code, f"Cannot read {path.name}: {exc}", str(path))
        return {}, result
    except json.JSONDecodeError as exc:
        result.error(code, f"Invalid {path.name}: {exc}", str(path))
        return {}, result
    if not isinstance(data, dict):
        result.error(code, f"{path.name} must contain a JSON object.", str(path))
        return {}, result
    return data, result


def verify_graph_generated_repo(
    repo_dir: Path,
    scenario_path: Path,
    commit_map_path: Path | None = None,
    graph_map_path: Path | None = None,
) -> ValidationResult:
    result = ValidationResult()
    scenario, load_result = load_graph_scenario(scenario_path)
    result.extend(load_result)
    if scenario is None:
        return result

    if commit_map_path is None:
        commit_map_path = repo_dir.parent / "metadata" / "commit-map.json"
    if graph_map_path is None:
        graph_map_path = repo_dir.parent / "metadata" / "graph-map.json"

    commit_map, cm_result = load_json_file(commit_map_path, code="GE600")
    result.extend(cm_result)
    graph_map, gm_result = load_json_file(graph_map_path, code="GE610")
    result.extend(gm_result)
    if cm_result.has_errors():
        return result

    _verify_commits(repo_dir, scenario, commit_map, graph_map, result)
    _verify_bugs(repo_dir, scenario, commit_map, result)
    _verify_expected_szz(scenario, commit_map, result)
    return result


def _verify_commits(repo_dir: Path, scenario: dict[str, Any], commit_map: dict[str, Any], graph_map: dict[str, Any], result: ValidationResult) -> None:
    for i, commit_spec in enumerate(scenario.get("commits", []) or []):
        if not isinstance(commit_spec, dict):
            continue
        cid = commit_spec.get("id")
        loc = f"commits[{i}]"
        if cid not in commit_map:
            result.error("GE620", f"commit-map.json does not contain logical commit id '{cid}'.", loc)
            continue
        actual_hash = commit_map[cid].get("hash") if isinstance(commit_map.get(cid), dict) else None
        if not actual_hash:
            result.error("GE621", f"commit-map entry for '{cid}' lacks hash.", loc)
            continue
        if not git_hash_exists(repo_dir, actual_hash):
            result.error("GE622", f"Git hash for logical commit '{cid}' does not exist: {actual_hash}", loc)
            continue
        try:
            actual_message = git_message(repo_dir, actual_hash)
            if commit_spec.get("message") is not None and actual_message != commit_spec.get("message"):
                result.error("GE623", f"Commit message mismatch for '{cid}'.", f"{loc}.message")
        except GitError as exc:
            result.error("GE624", f"Cannot inspect commit '{cid}': {exc}", loc)
        _verify_parents(repo_dir, commit_spec, commit_map, actual_hash, result, loc)
        graph_entry = (graph_map.get("commits", {}) or {}).get(cid) if isinstance(graph_map, dict) else None
        if isinstance(graph_entry, dict):
            expected_branch = commit_spec.get("branch")
            if expected_branch is not None and graph_entry.get("branch") != expected_branch:
                result.error("GE625", f"graph-map branch mismatch for '{cid}'.", f"{loc}.branch")


def _verify_parents(repo_dir: Path, commit_spec: dict[str, Any], commit_map: dict[str, Any], actual_hash: str, result: ValidationResult, loc: str) -> None:
    expected_parent_ids = [p for p in commit_spec.get("parents", []) or [] if isinstance(p, str)]
    expected_parent_hashes = [commit_map[p]["hash"] for p in expected_parent_ids if p in commit_map and isinstance(commit_map[p], dict)]
    try:
        raw = run_git(repo_dir, ["rev-list", "--parents", "-n", "1", actual_hash]).stdout.strip()
    except GitError as exc:
        result.error("GE626", f"Cannot inspect parent list: {exc}", loc)
        return
    actual_parent_hashes = raw.split()[1:]
    if expected_parent_hashes and actual_parent_hashes != expected_parent_hashes:
        result.error(
            "GE627",
            f"Parent mismatch. Expected {expected_parent_hashes}, got {actual_parent_hashes}.",
            f"{loc}.parents",
        )
    if len(expected_parent_ids) >= 2 and len(actual_parent_hashes) < 2:
        result.error("GE628", "Expected a merge commit but generated commit has fewer than two parents.", f"{loc}.parents")


def _verify_bugs(repo_dir: Path, scenario: dict[str, Any], commit_map: dict[str, Any], result: ValidationResult) -> None:
    for i, bug in enumerate(scenario.get("bugs", []) or []):
        if not isinstance(bug, dict):
            continue
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        for entry in graph_bic_entries(bug):
            cid = entry.get("commit")
            if cid not in commit_map:
                result.error("GE650", f"bug {bid} BIC refers to unknown logical commit '{cid}'.", loc)
        for entry in graph_bfc_entries(bug):
            cid = entry.get("commit")
            if cid not in commit_map:
                result.error("GE651", f"bug {bid} BFC refers to unknown logical commit '{cid}'.", loc)
        for j, fault in enumerate(graph_faults(bug)):
            _verify_location(repo_dir, commit_map, fault, result, f"{loc}.faults[{j}]", kind="fault", bug_id=str(bid))
        for j, fix in enumerate(graph_fixes(bug)):
            _verify_location(repo_dir, commit_map, fix, result, f"{loc}.fixes[{j}]", kind="fix", bug_id=str(bid))
        _verify_basic_blame(repo_dir, commit_map, bug, result, loc, str(bid))


def _verify_location(
    repo_dir: Path,
    commit_map: dict[str, Any],
    entry: dict[str, Any],
    result: ValidationResult,
    loc: str,
    *,
    kind: str,
    bug_id: str,
) -> None:
    commit_id = entry.get("commit")
    file_path = entry.get("file")
    statement = entry.get("statement") or entry.get("added_statement")
    if not isinstance(commit_id, str) or commit_id not in commit_map:
        return
    if not isinstance(file_path, str):
        if entry.get("entity") is not None:
            result.info("GI660", f"bug {bug_id} {kind} uses entity-level oracle; file content check skipped.", loc)
        return
    revision = commit_map[commit_id]["hash"]
    try:
        content = git_show(repo_dir, revision, file_path)
    except GitError as exc:
        if entry.get("fix_type") == "file_deletion" and kind == "fix":
            result.info("GI661", f"bug {bug_id} fix is file deletion; file is absent at fix commit as expected.", loc)
        else:
            result.error("GE662", f"Cannot read {kind}.file for bug {bug_id}: {exc}", loc)
        return
    if isinstance(statement, str) and statement:
        count = len(find_all_occurrences(content, statement))
        if count == 0:
            result.error("GE663", f"bug {bug_id} {kind} statement not found at commit '{commit_id}'.", loc)
        elif count > 1:
            result.warning("GW664", f"bug {bug_id} {kind} statement appears {count} times at commit '{commit_id}'.", loc)


def _verify_basic_blame(repo_dir: Path, commit_map: dict[str, Any], bug: dict[str, Any], result: ValidationResult, loc: str, bug_id: str) -> None:
    bfc_entries = graph_bfc_entries(bug)
    faults = graph_faults(bug)
    if not bfc_entries or not faults:
        return
    bfc_id = bfc_entries[-1].get("commit")
    if bfc_id not in commit_map:
        return
    bfc_hash = commit_map[bfc_id]["hash"]
    parent_hash = git_parent(repo_dir, bfc_hash)
    if not parent_hash:
        return
    first_fault = faults[0]
    ffile = first_fault.get("file")
    stmt = first_fault.get("statement")
    if not isinstance(ffile, str) or not isinstance(stmt, str) or not stmt:
        return
    try:
        parent_content = git_show(repo_dir, parent_hash, ffile)
    except GitError as exc:
        result.warning("GW700", f"bug {bug_id}: basic blame check skipped: {exc}", loc)
        return
    line_number = None
    for line_index, line in enumerate(parent_content.splitlines(), start=1):
        if stmt in line:
            line_number = line_index
            break
    if line_number is None:
        result.warning("GW701", f"bug {bug_id}: fault.statement not present in final BFC parent; basic blame unavailable.", loc)
        return
    try:
        blamed_hash = git_blame_line(repo_dir, parent_hash, ffile, line_number)
    except GitError as exc:
        result.warning("GW702", f"bug {bug_id}: basic blame check failed: {exc}", loc)
        return
    expected_hashes = {
        commit_map[entry["commit"]]["hash"]
        for entry in graph_bic_entries(bug)
        if entry.get("commit") in commit_map and entry.get("role") in {"direct", "reintroducing", "contributing"}
    }
    if blamed_hash in expected_hashes:
        result.info("GI703", f"bug {bug_id}: basic git blame reaches an expected graph BIC.", loc)
    else:
        result.warning("GW703", f"bug {bug_id}: basic git blame reaches {blamed_hash}, not expected graph BIC hash(es).", loc)


def _verify_expected_szz(scenario: dict[str, Any], commit_map: dict[str, Any], result: ValidationResult) -> None:
    expected = scenario.get("expected_szz")
    if not isinstance(expected, dict):
        return
    commit_level = expected.get("commit_level")
    if isinstance(commit_level, dict):
        for key in ["required", "relevant", "related_origins", "related_but_not_correct"]:
            for cid in commit_level.get(key, []) or []:
                if isinstance(cid, str) and cid not in commit_map:
                    result.error("GE680", f"expected_szz.{key} refers to unknown logical commit '{cid}'.", f"expected_szz.commit_level.{key}")
    variants = expected.get("evaluation_variants")
    if isinstance(variants, list):
        for i, variant in enumerate(variants):
            if not isinstance(variant, dict):
                continue
            cl = variant.get("commit_level")
            if isinstance(cl, dict):
                for cid in cl.get("required", []) or []:
                    if isinstance(cid, str) and cid not in commit_map:
                        result.error("GE681", f"evaluation variant refers to unknown logical commit '{cid}'.", f"expected_szz.evaluation_variants[{i}]")
