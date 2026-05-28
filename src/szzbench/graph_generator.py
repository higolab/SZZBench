from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import shutil
from datetime import datetime, timezone

from .findings import ValidationResult
from .gitutils import GitError, init_repo, parse_author, run_git
from .graph_operations import apply_graph_operation_to_filesystem
from .graph_scenario import load_graph_scenario
from .graph_validator import validate_graph_scenario_file
from .operations import OperationError
from .graph_verifier import verify_graph_generated_repo


class GraphGenerationError(RuntimeError):
    pass


def generate_graph_repository(
    scenario_path: Path,
    out_dir: Path,
    *,
    force: bool = False,
    verify: bool = True,
) -> tuple[dict[str, dict[str, Any]], ValidationResult | None]:
    scenario_path = scenario_path.resolve()
    out_dir = out_dir.resolve()
    repo_dir = out_dir / "repo"
    metadata_dir = out_dir / "metadata"

    _, validation_result = validate_graph_scenario_file(scenario_path)
    if validation_result.has_errors():
        raise GraphGenerationError("Graph scenario validation failed. Run 'szzbench validate-graph' for details.")

    scenario, load_result = load_graph_scenario(scenario_path)
    if scenario is None or load_result.has_errors():
        raise GraphGenerationError("Failed to load graph scenario.")

    if out_dir.exists():
        if not force:
            raise GraphGenerationError(f"Output directory already exists: {out_dir}. Use --force to overwrite.")
        shutil.rmtree(out_dir)

    repo_dir.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)

    generation_log: list[str] = []
    commit_map: dict[str, dict[str, Any]] = {}
    graph_map: dict[str, Any] = {"commits": {}, "branches": {}}

    def log(message: str) -> None:
        generation_log.append(message)

    try:
        default_branch = scenario.get("repository", {}).get("default_branch", "main")
        init_repo(repo_dir, default_branch)
        branch_heads: dict[str, str] = {}
        log(f"Initialized Git repository at {repo_dir}")

        for commit_spec in scenario.get("commits", []):
            cid = commit_spec["id"]
            branch = commit_spec.get("branch") or default_branch
            parents = [p for p in commit_spec.get("parents", []) if isinstance(p, str)]
            log(f"Preparing graph commit {cid} on branch {branch}: {commit_spec.get('message', '')}")

            _checkout_for_commit(repo_dir, branch, parents, commit_map, branch_heads, default_branch)

            is_merge = len(parents) >= 2
            if is_merge:
                _prepare_merge(repo_dir, parents[1:], commit_map, log)

            _apply_cherry_pick_or_backport_if_needed(repo_dir, commit_spec, commit_map, log)

            for op in commit_spec.get("operations", []) or []:
                op_type = op.get("type")
                if op_type == "apply_squash":
                    _apply_squash(repo_dir, op, commit_map, log)
                elif op_type == "apply_patch_from":
                    _apply_patch_from(repo_dir, op, commit_map, log)
                else:
                    apply_graph_operation_to_filesystem(repo_dir, op)

            actual_hash = _commit_current_state(
                repo_dir,
                message=commit_spec.get("message") or cid,
                author=commit_spec.get("author"),
                date=commit_spec.get("date"),
                allow_empty=bool(commit_spec.get("allow_empty")),
            )
            branch_heads[branch] = actual_hash
            commit_map[cid] = {
                "hash": actual_hash,
                "message": commit_spec.get("message"),
                "author": commit_spec.get("author"),
                "date": commit_spec.get("date"),
                "role": commit_spec.get("role"),
                "branch": branch,
                "parents": parents,
            }
            graph_map["commits"][cid] = {
                "hash": actual_hash,
                "branch": branch,
                "parents": parents,
                "parent_hashes": [commit_map[p]["hash"] for p in parents if p in commit_map],
                "role": commit_spec.get("role"),
                "cherry_pick_of": commit_spec.get("cherry_pick_of"),
                "backport_of": commit_spec.get("backport_of"),
                "rebase_of": commit_spec.get("rebase_of"),
            }
            graph_map["branches"] = branch_heads.copy()
            log(f"Created graph commit {cid}: {actual_hash}")

        shutil.copy2(scenario_path, metadata_dir / "scenario.graph.yml")
        (metadata_dir / "commit-map.json").write_text(json.dumps(commit_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (metadata_dir / "graph-map.json").write_text(json.dumps(graph_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (metadata_dir / "validation-result.json").write_text(json.dumps(validation_result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        verify_result = None
        if verify:
            verify_result = verify_graph_generated_repo(repo_dir, scenario_path, metadata_dir / "commit-map.json", metadata_dir / "graph-map.json")
            (metadata_dir / "verify-result.json").write_text(json.dumps(verify_result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if verify_result.has_errors():
                raise GraphGenerationError("Generated graph repository failed verification.")

        log("Graph generation completed successfully.")
        (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
        return commit_map, verify_result
    except (OperationError, GitError, OSError) as exc:
        log(f"ERROR: {exc}")
        error_info = {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
        (metadata_dir / "generation-error.json").write_text(json.dumps(error_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
        raise GraphGenerationError(str(exc)) from exc


def _checkout_for_commit(
    repo_dir: Path,
    branch: str,
    parents: list[str],
    commit_map: dict[str, dict[str, Any]],
    branch_heads: dict[str, str],
    default_branch: str,
) -> None:
    if not parents:
        # The initial default branch is an unborn branch immediately after
        # git init; checking it out before the first commit fails on some Git
        # versions.  For the default branch, the current worktree is already
        # the correct target.
        if branch != default_branch:
            _checkout_or_create_branch(repo_dir, branch, None)
        return

    first_parent = parents[0]
    if first_parent not in commit_map:
        raise GraphGenerationError(f"Parent commit '{first_parent}' has not been generated yet.")
    parent_hash = commit_map[first_parent]["hash"]

    if branch in branch_heads:
        run_git(repo_dir, ["checkout", branch])
        head = run_git(repo_dir, ["rev-parse", "HEAD"]).stdout.strip()
        if head != parent_hash:
            run_git(repo_dir, ["reset", "--hard", parent_hash])
    else:
        _checkout_or_create_branch(repo_dir, branch, parent_hash)


def _checkout_or_create_branch(repo_dir: Path, branch: str, start_point: str | None) -> None:
    if start_point:
        run_git(repo_dir, ["checkout", "-B", branch, start_point])
    else:
        run_git(repo_dir, ["checkout", "-B", branch])


def _prepare_merge(repo_dir: Path, extra_parent_ids: list[str], commit_map: dict[str, dict[str, Any]], log) -> None:
    for parent_id in extra_parent_ids:
        if parent_id not in commit_map:
            raise GraphGenerationError(f"Merge parent '{parent_id}' has not been generated yet.")
        parent_hash = commit_map[parent_id]["hash"]
        log(f"Merging parent {parent_id}: {parent_hash}")
        try:
            run_git(repo_dir, ["merge", "--no-ff", "--no-commit", parent_hash])
        except GitError as exc:
            raise GraphGenerationError(f"Merge failed for parent '{parent_id}'. Conflict resolution is not implemented in this MVP: {exc}") from exc


def _apply_cherry_pick_or_backport_if_needed(repo_dir: Path, commit_spec: dict[str, Any], commit_map: dict[str, dict[str, Any]], log) -> None:
    source_id = commit_spec.get("cherry_pick_of") or commit_spec.get("backport_of")
    if not source_id or commit_spec.get("operations"):
        return
    if source_id not in commit_map:
        raise GraphGenerationError(f"cherry_pick_of/backport_of source '{source_id}' has not been generated yet.")
    source_hash = commit_map[source_id]["hash"]
    log(f"Applying source commit without committing: {source_id} {source_hash}")
    run_git(repo_dir, ["cherry-pick", "--no-commit", source_hash])


def _apply_squash(repo_dir: Path, op: dict[str, Any], commit_map: dict[str, dict[str, Any]], log) -> None:
    for source_id in op.get("from_commits", []) or []:
        if source_id not in commit_map:
            raise GraphGenerationError(f"apply_squash refers to unknown commit '{source_id}'.")
        source_hash = commit_map[source_id]["hash"]
        log(f"Applying squash source {source_id}: {source_hash}")
        run_git(repo_dir, ["cherry-pick", "--no-commit", source_hash])


def _apply_patch_from(repo_dir: Path, op: dict[str, Any], commit_map: dict[str, dict[str, Any]], log) -> None:
    source_id = op.get("commit")
    if not isinstance(source_id, str):
        raise GraphGenerationError("apply_patch_from requires a commit id.")
    if source_id not in commit_map:
        raise GraphGenerationError(f"apply_patch_from refers to unknown commit '{source_id}'.")
    source_hash = commit_map[source_id]["hash"]
    args = ["cherry-pick", "--no-commit"]
    mainline = op.get("mainline", op.get("parent"))
    if mainline is not None:
        args.extend(["--mainline", str(mainline)])
    args.append(source_hash)
    log(f"Applying patch from {source_id}: {source_hash}")
    run_git(repo_dir, args)


def _commit_current_state(repo_dir: Path, *, message: str, author: str | None, date: str | None, allow_empty: bool = False) -> str:
    run_git(repo_dir, ["add", "-A"])
    status = run_git(repo_dir, ["status", "--porcelain"]).stdout.strip()
    merge_in_progress = (repo_dir / ".git" / "MERGE_HEAD").exists()
    args = ["commit", "-m", message]
    if allow_empty and not status and not merge_in_progress:
        args.insert(1, "--allow-empty")
    elif not status and not merge_in_progress:
        raise GitError("commit would be empty")

    name, email = parse_author(author)
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = name
    env["GIT_AUTHOR_EMAIL"] = email
    env["GIT_COMMITTER_NAME"] = name
    env["GIT_COMMITTER_EMAIL"] = email
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    run_git(repo_dir, args, env=env)
    return run_git(repo_dir, ["rev-parse", "HEAD"]).stdout.strip()
