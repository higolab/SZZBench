from __future__ import annotations

from pathlib import Path
import json

from .findings import ValidationResult
from .gitutils import GitError, git_blame_line, git_hash_exists, git_message, git_parent, git_show
from .operations import find_all_occurrences
from .scenario import load_yaml

def _load_commit_map(path: Path) -> tuple[dict, ValidationResult]:
    result = ValidationResult()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        result.error("E600", f"Cannot read commit-map.json: {exc}", str(path))
        return {}, result
    except json.JSONDecodeError as exc:
        result.error("E600", f"Invalid commit-map.json: {exc}", str(path))
        return {}, result
    return data, result

def verify_generated_repo(repo_dir: Path, scenario_path: Path, commit_map_path: Path | None = None) -> ValidationResult:
    result = ValidationResult()
    scenario, load_result = load_yaml(scenario_path)
    result.extend(load_result)
    if scenario is None:
        return result
    if commit_map_path is None:
        commit_map_path = repo_dir.parent / "metadata" / "commit-map.json"
    commit_map, cm_result = _load_commit_map(commit_map_path)
    result.extend(cm_result)
    if cm_result.has_errors():
        return result
    for commit_spec in scenario.get("commits", []):
        cid = commit_spec.get("id")
        if cid not in commit_map:
            result.error("E600", f"commit-map.json does not contain logical commit id '{cid}'.", f"commits.{cid}")
            continue
        actual_hash = commit_map[cid].get("hash")
        if not actual_hash:
            result.error("E600", f"commit-map entry for '{cid}' lacks hash.", f"commits.{cid}")
            continue
        if not git_hash_exists(repo_dir, actual_hash):
            result.error("E601", f"Git hash for logical commit '{cid}' does not exist: {actual_hash}", f"commits.{cid}")
            continue
        try:
            actual_message = git_message(repo_dir, actual_hash)
            if actual_message != commit_spec.get("message"):
                result.error("E602", f"Commit message mismatch for '{cid}'.", f"commits.{cid}.message")
        except GitError as exc:
            result.error("E601", f"Cannot inspect commit '{cid}': {exc}", f"commits.{cid}")
    for i, bug in enumerate(scenario.get("bugs", [])):
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        fault = bug.get("fault", {})
        fix = bug.get("fix", {})
        bfc = bug.get("bug_fixing_commit")
        bics = bug.get("bug_introducing_commits", [])
        if isinstance(fault, dict):
            fcommit = fault.get("commit")
            ffile = fault.get("file")
            stmt = fault.get("statement")
            if fcommit in commit_map and isinstance(ffile, str) and fault.get("change_type") != "omission":
                fhash = commit_map[fcommit]["hash"]
                try:
                    content = git_show(repo_dir, fhash, ffile)
                    if isinstance(stmt, str):
                        count = len(find_all_occurrences(content, stmt))
                        if count == 0:
                            result.error("E301", f"bug {bid} fault.statement not found at fault.commit '{fcommit}'.", f"{loc}.fault.statement")
                        elif count > 1:
                            result.warning("W301", f"bug {bid} fault.statement appears {count} times at fault.commit '{fcommit}'.", f"{loc}.fault.statement")
                except GitError as exc:
                    result.error("E300", f"Cannot read fault.file for bug {bid}: {exc}", f"{loc}.fault.file")
        if isinstance(fix, dict):
            fix_commit = fix.get("commit")
            fix_file = fix.get("file")
            fix_text = fix.get("added_statement") or fix.get("statement")
            removed_text = fix.get("removed_statement")
            if fix_commit in commit_map and isinstance(fix_file, str):
                fix_hash = commit_map[fix_commit]["hash"]
                try:
                    content = git_show(repo_dir, fix_hash, fix_file)
                    if isinstance(fix_text, str) and fix_text not in content:
                        result.error("E311", f"bug {bid} fix statement not found at fix.commit '{fix_commit}'.", f"{loc}.fix")
                    if isinstance(removed_text, str) and removed_text in content:
                        result.error("E312", f"bug {bid} fix.removed_statement is still present at fix.commit '{fix_commit}'.", f"{loc}.fix.removed_statement")
                except GitError as exc:
                    result.error("E310", f"Cannot read fix.file for bug {bid}: {exc}", f"{loc}.fix.file")
        if isinstance(fault, dict) and fault.get("change_type") != "omission" and bfc in commit_map:
            bfc_hash = commit_map[bfc]["hash"]
            parent_hash = git_parent(repo_dir, bfc_hash)
            ffile = fault.get("file")
            stmt = fault.get("statement")
            if parent_hash and isinstance(ffile, str) and isinstance(stmt, str):
                try:
                    parent_content = git_show(repo_dir, parent_hash, ffile)
                    line_number = None
                    for line_index, line in enumerate(parent_content.splitlines(), start=1):
                        if stmt in line:
                            line_number = line_index
                            break
                    if line_number is None:
                        result.warning("W700", f"bug {bid}: fault.statement not present in BFC parent; basic blame unavailable.", loc)
                    else:
                        blamed_hash = git_blame_line(repo_dir, parent_hash, ffile, line_number)
                        expected_hashes = {commit_map[bic]["hash"] for bic in bics if bic in commit_map}
                        if blamed_hash in expected_hashes:
                            result.info("I700", f"bug {bid}: basic git blame reaches expected BIC.", loc)
                        else:
                            result.warning("W700", f"bug {bid}: basic git blame reaches {blamed_hash}, not expected BIC(s) {sorted(bics)}.", loc)
                except GitError as exc:
                    result.warning("W700", f"bug {bid}: basic blame check failed: {exc}", loc)
    return result
