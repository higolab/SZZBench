from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
import json
import shutil

from .cleaner import replaceable_output_problem
from .findings import ValidationResult
from .gitutils import (
    MAX_GENERATED_COMMITS,
    CommitMetadata,
    GitError,
    deterministic_author,
    format_timestamp,
    git_author_date,
    git_message,
    git_refs,
    git_unmerged_paths,
    init_repo,
    json_safe_timestamp,
    parse_author,
    parse_timestamp,
    resolve_commit_metadata,
    run_git,
    run_git_with_input,
    timestamp_to_git_raw,
)
from .graph_operations import CommitGeneratorPlan, apply_graph_operation_to_filesystem, commit_generator_changes, commit_generator_plan
from .graph_scenario import load_graph_scenario
from .graph_validator import validate_graph_scenario_file
from .operations import OperationError, normalize_newlines
from .graph_verifier import verify_graph_generated_repo
from .manifest import write_manifest
from .paths import PathValidationError, safe_join


class GraphGenerationError(RuntimeError):
    pass


# Temporary ref used while importing generated commits with ``git fast-import``.
_GENERATED_IMPORT_REF = "refs/szzbench/generated"


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
        if not force and out_dir.is_dir():
            raise GraphGenerationError(f"Output directory already exists: {out_dir}. Use --force to overwrite.")
        problem = replaceable_output_problem(out_dir, scenario_path)
        if problem is not None:
            raise GraphGenerationError(f"{problem}.")
        try:
            shutil.rmtree(out_dir)
        except OSError as exc:
            raise GraphGenerationError(f"Cannot remove the previous output {out_dir}: {exc}") from exc

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
        if _scenario_uses_operation(scenario, "chmod"):
            # core.filemode is false by default for Windows compatibility; a
            # scenario that models mode changes needs Git to record them.
            run_git(repo_dir, ["config", "core.filemode", "true"])
            log("Enabled core.filemode because the scenario uses chmod operations")
        branch_heads: dict[str, str] = {}
        log(f"Initialized Git repository at {repo_dir}")

        for index, commit_spec in enumerate(scenario.get("commits", [])):
            cid = commit_spec["id"]
            branch = commit_spec.get("branch") or default_branch
            parents = [p for p in commit_spec.get("parents", []) if isinstance(p, str)]
            if index > 0 and not parents:
                # _checkout_for_commit would commit it on top of the current HEAD (issue #134).
                raise GraphGenerationError(
                    f"Commit '{cid}' declares no parents, but only the first commit may be a root (GE048)."
                )
            log(f"Preparing graph commit {cid} on branch {branch}: {commit_spec.get('message', '')}")

            _checkout_for_commit(repo_dir, branch, parents, commit_map, branch_heads, default_branch)

            metadata = resolve_commit_metadata(scenario, commit_spec, index)
            inherits = _apply_inherit_options(repo_dir, commit_spec, commit_map, metadata, log)

            generated_ids = _expand_commit_generators(repo_dir, scenario, cid, branch, parents, commit_spec, metadata, commit_map, log)
            if generated_ids:
                graph_map.setdefault("generated_commits", {})[cid] = list(generated_ids)

            conflicted_paths: list[str] = []
            is_merge = len(parents) >= 2
            if is_merge:
                conflicted_paths.extend(_prepare_merge(repo_dir, parents[1:], commit_map, commit_spec, log))

            revert_source_hash = _apply_revert_if_needed(repo_dir, commit_spec, commit_map, conflicted_paths, log)
            _apply_cherry_pick_or_backport_if_needed(repo_dir, commit_spec, commit_map, conflicted_paths, log)

            for op in commit_spec.get("operations", []) or []:
                op_type = op.get("type")
                if op_type == "apply_squash":
                    _apply_squash(repo_dir, op, commit_map, log)
                elif op_type == "apply_patch_from":
                    _apply_patch_from(repo_dir, op, commit_map, log)
                elif op_type == "commit_generator":
                    continue  # already expanded into real commits above
                else:
                    apply_graph_operation_to_filesystem(repo_dir, op)

            subject, body = _build_commit_message(repo_dir, cid, commit_spec, commit_map, inherits, revert_source_hash)
            actual_hash = _commit_current_state(
                repo_dir,
                message=subject,
                body=body,
                metadata=metadata,
                allow_empty=bool(commit_spec.get("allow_empty")) or bool(generated_ids),
            )
            branch_heads[branch] = actual_hash
            commit_map[cid] = {
                "hash": actual_hash,
                "message": subject,
                "author": metadata.author,
                "date": json_safe_timestamp(commit_spec.get("date")),
                "author_date": metadata.author_date,
                "committer_date": metadata.committer_date,
                "role": commit_spec.get("role"),
                "branch": branch,
                "parents": parents,
            }
            if body:
                commit_map[cid]["body"] = body
            if generated_ids:
                commit_map[cid]["generated_commits"] = list(generated_ids)
            if inherits:
                commit_map[cid]["inherits"] = inherits
            if conflicted_paths:
                commit_map[cid]["resolved_conflicts"] = sorted(set(conflicted_paths))
            graph_map["commits"][cid] = {
                "hash": actual_hash,
                "branch": branch,
                "parents": parents,
                "parent_hashes": [commit_map[p]["hash"] for p in parents if p in commit_map],
                "role": commit_spec.get("role"),
                "cherry_pick_of": commit_spec.get("cherry_pick_of"),
                "backport_of": commit_spec.get("backport_of"),
                "rebase_of": commit_spec.get("rebase_of"),
                "revert_of": commit_spec.get("revert_of"),
            }
            for passthrough_key in ("squashes", "interactive_rebase", "rebase_conflict_resolution", "reverts", "revert_conflict_resolution"):
                if passthrough_key in commit_spec:
                    graph_map["commits"][cid][passthrough_key] = commit_spec[passthrough_key]
            if generated_ids:
                graph_map["commits"][cid]["generated_commits"] = list(generated_ids)
            graph_map["branches"] = branch_heads.copy()
            log(f"Created graph commit {cid}: {actual_hash}")

        graph_section = scenario.get("graph") if isinstance(scenario.get("graph"), dict) else {}
        ref_lifecycle = graph_section.get("ref_lifecycle") if isinstance(graph_section, dict) else None
        if isinstance(ref_lifecycle, dict):
            graph_map["ref_lifecycle"] = _apply_ref_lifecycle(repo_dir, ref_lifecycle, commit_map, branch_heads, default_branch, log)
            graph_map["branches"] = {name: h for name, h in branch_heads.items() if name not in graph_map["ref_lifecycle"]["deleted_branches"]}
        graph_map["refs"] = git_refs(repo_dir)

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
        # written last: an output without it is incomplete (issue #93)
        write_manifest(metadata_dir, scenario_id=str(scenario.get("meta", {}).get("id") or out_dir.parent.name),
                       scenario_path=scenario_path, commit_map=commit_map, verified=verify)
        return commit_map, verify_result
    # ValueError includes PathValidationError; a path the file system refuses
    # (a NUL byte) used to end generation in a traceback (issue #136)
    except (OperationError, ValueError, GitError, OSError, GraphGenerationError) as exc:
        log(f"ERROR: {exc}")
        error_info = {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
        (metadata_dir / "generation-error.json").write_text(json.dumps(error_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
        if isinstance(exc, GraphGenerationError):
            raise
        raise GraphGenerationError(str(exc)) from exc


def _scenario_uses_operation(scenario: dict[str, Any], op_type: str) -> bool:
    for commit_spec in scenario.get("commits", []) or []:
        if not isinstance(commit_spec, dict):
            continue
        for op in commit_spec.get("operations", []) or []:
            if isinstance(op, dict) and op.get("type") == op_type:
                return True
    return False


def _checkout_for_commit(
    repo_dir: Path,
    branch: str,
    parents: list[str],
    commit_map: dict[str, dict[str, Any]],
    branch_heads: dict[str, str],
    default_branch: str,
) -> None:
    if not parents:
        # Only the first commit gets here (a later one is refused, GE048).  The
        # initial default branch is an unborn branch immediately after git init;
        # checking it out before the first commit fails on some Git versions.
        # For the default branch, the current worktree is already the correct
        # target.
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


# ---------------------------------------------------------------------------
# History rewriting fidelity (issue #17)
# ---------------------------------------------------------------------------


def _rewrite_source_id(commit_spec: dict[str, Any]) -> str | None:
    """Return the logical commit a rebased/cherry-picked commit was derived from."""
    for key in ("rebase_of", "cherry_pick_of", "backport_of"):
        value = commit_spec.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _apply_inherit_options(
    repo_dir: Path,
    commit_spec: dict[str, Any],
    commit_map: dict[str, dict[str, Any]],
    metadata: CommitMetadata,
    log,
) -> dict[str, Any] | None:
    """Handle ``inherit_message`` / ``inherit_author_date`` for rewritten commits.

    ``git rebase`` and ``git cherry-pick`` keep the subject and the author date
    of the original commit while the committer date is new.  When either
    option is set the source is ``rebase_of`` (or ``cherry_pick_of`` /
    ``backport_of``).  Returns a record of what was inherited, or ``None``.
    """
    inherit_message = bool(commit_spec.get("inherit_message"))
    inherit_author_date = bool(commit_spec.get("inherit_author_date"))
    if not inherit_message and not inherit_author_date:
        return None
    source_id = _rewrite_source_id(commit_spec)
    if source_id is None:
        raise GraphGenerationError(
            f"Commit '{commit_spec.get('id')}' sets inherit_message/inherit_author_date but has no rebase_of, cherry_pick_of or backport_of."
        )
    if source_id not in commit_map:
        raise GraphGenerationError(f"Rewrite source '{source_id}' of commit '{commit_spec.get('id')}' has not been generated yet.")
    source_hash = commit_map[source_id]["hash"]
    record: dict[str, Any] = {"source": source_id, "source_hash": source_hash, "message": False, "author_date": False}
    if inherit_message and commit_spec.get("message") is None:
        record["message"] = True
        record["subject"] = git_message(repo_dir, source_hash)
    if inherit_author_date:
        metadata.author_date = format_timestamp(parse_timestamp(git_author_date(repo_dir, source_hash)))
        metadata.author_date_is_default = False
        record["author_date"] = True
        log(f"Commit {commit_spec.get('id')} inherits author date {metadata.author_date} from {source_id}")
    return record


def _prepare_merge(
    repo_dir: Path,
    extra_parent_ids: list[str],
    commit_map: dict[str, dict[str, Any]],
    commit_spec: dict[str, Any],
    log,
) -> list[str]:
    conflicted: list[str] = []
    for parent_id in extra_parent_ids:
        if parent_id not in commit_map:
            raise GraphGenerationError(f"Merge parent '{parent_id}' has not been generated yet.")
    hashes = [commit_map[parent_id]["hash"] for parent_id in extra_parent_ids]
    # All extra parents go into ONE git merge: a second `git merge --no-commit`
    # while MERGE_HEAD exists is refused ("You have not concluded your merge"),
    # so merging them one at a time can never produce an octopus commit.  With
    # several heads git uses the octopus strategy, which does not resolve
    # conflicts; `resolution` therefore only applies to two-parent merges.
    log(f"Merging parent(s) {', '.join(extra_parent_ids)}: {', '.join(hashes)}")
    try:
        run_git(repo_dir, ["merge", "--no-ff", "--no-commit", *hashes])
    except GitError as exc:
        what = f"Merge of parent '{extra_parent_ids[0]}'" if len(extra_parent_ids) == 1 else f"Octopus merge of parents {extra_parent_ids}"
        conflicted.extend(_resolve_conflicts_or_fail(repo_dir, commit_spec, what, exc, log))
    _require_merge_heads(repo_dir, extra_parent_ids, hashes, commit_spec)
    return conflicted


def _require_merge_heads(repo_dir: Path, extra_parent_ids: list[str], hashes: list[str], commit_spec: dict[str, Any]) -> None:
    """Stop when ``git merge`` would not record every declared extra parent (issue #173).

    Git records each head once and drops a head already reachable from another
    one; for a merge with nothing left to record it says "Already up to date"
    and leaves no MERGE_HEAD.  The commit would then get fewer parents than
    declared ("commit would be empty", or GE627/GE628 at verification), so the
    parent that was dropped is named here instead.  Validation reports the same
    parent lists as GE049.
    """
    try:
        recorded = (repo_dir / ".git" / "MERGE_HEAD").read_text(encoding="utf-8").split()
    except FileNotFoundError:
        recorded = []
    remaining = list(recorded)
    reasons: list[str] = []
    seen = [p for p in commit_spec.get("parents", []) if isinstance(p, str)][:1]   # the first parent
    for parent_id, parent_hash in zip(extra_parent_ids, hashes):
        if parent_hash in remaining:
            remaining.remove(parent_hash)
        else:
            reasons.append(f"{parent_id} is listed twice" if parent_id in seen else f"{parent_id} is already merged")
        seen.append(parent_id)
    if not reasons:
        return
    declared = ", ".join(seen)
    what = "no second parent" if not recorded else f"{len(recorded) + 1} parents, not {len(seen)}"
    raise GraphGenerationError(
        f"merge of {declared} for commit '{commit_spec.get('id')}' recorded {what}: {'; '.join(reasons)} (GE049)."
    )


def _resolve_conflicts_or_fail(repo_dir: Path, commit_spec: dict[str, Any], what: str, exc: GitError, log) -> list[str]:
    """After a failed merge/cherry-pick/revert, apply ``resolution`` or raise.

    ``resolution`` maps repository paths to their resolved content (``null``
    deletes the path).  All unmerged paths must be covered.
    """
    cid = commit_spec.get("id")
    conflicted = git_unmerged_paths(repo_dir)
    if not conflicted:
        raise GraphGenerationError(f"{what} failed for commit '{cid}' without reporting conflicts: {exc}") from exc
    resolution = commit_spec.get("resolution")
    if not isinstance(resolution, dict) or not resolution:
        raise GraphGenerationError(
            f"{what} for commit '{cid}' reported conflicts in {conflicted}. "
            "Add 'resolution: {path: content}' to the commit to supply the resolved files."
        ) from exc
    log(f"{what} for commit {cid} reported conflicts in {conflicted}; applying resolution")
    resolved_paths = {Path(str(key)).as_posix() for key in resolution}
    missing = [path for path in conflicted if path not in resolved_paths]
    if missing:
        raise GraphGenerationError(f"resolution of commit '{cid}' does not cover conflicted paths {missing}.") from exc
    for rel_path, content in resolution.items():
        if not isinstance(rel_path, str):
            raise GraphGenerationError(f"resolution keys of commit '{cid}' must be repository paths.")
        target = safe_join(repo_dir, rel_path)
        if content is None:
            if target.exists():
                target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(normalize_newlines(str(content)), encoding="utf-8", newline="\n")
    # git add marks the written paths as resolved; every conflicted path was
    # checked against the resolution above.
    run_git(repo_dir, ["add", "-A"])
    return conflicted


def _finish_sequencer_step(repo_dir: Path, command: str) -> None:
    """Clear cherry-pick/revert state after a conflict was resolved manually.

    ``--quit`` keeps the index and worktree but removes CHERRY_PICK_HEAD /
    REVERT_HEAD, so the subsequent ``git commit`` is an ordinary commit.
    """
    try:
        run_git(repo_dir, [command, "--quit"])
    except GitError:
        pass


def _apply_revert_if_needed(
    repo_dir: Path,
    commit_spec: dict[str, Any],
    commit_map: dict[str, dict[str, Any]],
    conflicted_paths: list[str],
    log,
) -> str | None:
    source_id = commit_spec.get("revert_of")
    if source_id is None:
        return None
    if not isinstance(source_id, str) or source_id not in commit_map:
        raise GraphGenerationError(f"revert_of source '{source_id}' of commit '{commit_spec.get('id')}' has not been generated yet.")
    source_hash = commit_map[source_id]["hash"]
    if commit_spec.get("operations") and not commit_spec.get("apply_revert"):
        # Backward compatibility (SZZG-0084/0085): when a revert_of commit has
        # operations they describe the (possibly partial) revert by hand, like
        # cherry_pick_of with operations.  Only the message footer is added.
        # apply_revert: true runs the real revert first and the operations after it.
        log(f"revert_of {source_id}: operations describe the revert; git revert is skipped (set apply_revert: true to run it)")
        return source_hash
    args = ["revert", "--no-commit", "--no-edit"]
    mainline = commit_spec.get("mainline")
    if mainline is not None:
        args.extend(["--mainline", str(mainline)])
    args.append(source_hash)
    log(f"Reverting {source_id} {source_hash} without committing")
    try:
        run_git(repo_dir, args)
    except GitError as exc:
        conflicted_paths.extend(_resolve_conflicts_or_fail(repo_dir, commit_spec, f"Revert of '{source_id}'", exc, log))
        _finish_sequencer_step(repo_dir, "revert")
    return source_hash


def _apply_cherry_pick_or_backport_if_needed(
    repo_dir: Path,
    commit_spec: dict[str, Any],
    commit_map: dict[str, dict[str, Any]],
    conflicted_paths: list[str],
    log,
) -> None:
    source_id = commit_spec.get("cherry_pick_of") or commit_spec.get("backport_of")
    if not source_id or commit_spec.get("operations"):
        return
    if source_id not in commit_map:
        raise GraphGenerationError(f"cherry_pick_of/backport_of source '{source_id}' has not been generated yet.")
    source_hash = commit_map[source_id]["hash"]
    log(f"Applying source commit without committing: {source_id} {source_hash}")
    try:
        run_git(repo_dir, ["cherry-pick", "--no-commit", source_hash])
    except GitError as exc:
        conflicted_paths.extend(_resolve_conflicts_or_fail(repo_dir, commit_spec, f"Cherry-pick of '{source_id}'", exc, log))
        _finish_sequencer_step(repo_dir, "cherry-pick")


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


def _cherry_pick_trailer_sources(commit_spec: dict[str, Any], commit_map: dict[str, dict[str, Any]]) -> list[str]:
    """Hashes named by ``(cherry picked from commit ...)`` trailers, in order."""
    sources: list[str] = []
    direct = commit_spec.get("cherry_pick_of") or commit_spec.get("backport_of")
    if isinstance(direct, str):
        sources.append(direct)
    for op in commit_spec.get("operations", []) or []:
        if isinstance(op, dict) and op.get("type") == "apply_patch_from" and isinstance(op.get("commit"), str):
            sources.append(op["commit"])
    hashes: list[str] = []
    for source_id in sources:
        if source_id not in commit_map:
            raise GraphGenerationError(f"cherry_pick_trailer of commit '{commit_spec.get('id')}' refers to unknown commit '{source_id}'.")
        source_hash = commit_map[source_id]["hash"]
        if source_hash not in hashes:
            hashes.append(source_hash)
    if not hashes:
        raise GraphGenerationError(
            f"Commit '{commit_spec.get('id')}' sets cherry_pick_trailer but has no cherry_pick_of, backport_of or apply_patch_from source."
        )
    return hashes


def _build_commit_message(
    repo_dir: Path,
    cid: str,
    commit_spec: dict[str, Any],
    commit_map: dict[str, dict[str, Any]],
    inherits: dict[str, Any] | None,
    revert_source_hash: str | None,
) -> tuple[str, str]:
    """Return (subject, body) for the logical commit.

    The subject stays exactly what the scenario specifies so the verifier's
    subject check keeps working; trailers/footers only go into the body.
    """
    subject = commit_spec.get("message")
    if subject is None and inherits and inherits.get("message"):
        subject = inherits["subject"]
    if subject is None and revert_source_hash is not None:
        subject = f'Revert "{git_message(repo_dir, revert_source_hash)}"'
    if subject is None:
        subject = cid
    body_lines: list[str] = []
    if commit_spec.get("cherry_pick_trailer"):
        for source_hash in _cherry_pick_trailer_sources(commit_spec, commit_map):
            body_lines.append(f"(cherry picked from commit {source_hash})")
    if revert_source_hash is not None:
        body_lines.append(f"This reverts commit {revert_source_hash}.")
    return str(subject), "\n".join(body_lines)


# ---------------------------------------------------------------------------
# Ref lifecycle (issue #17)
# ---------------------------------------------------------------------------


def _apply_ref_lifecycle(
    repo_dir: Path,
    ref_lifecycle: dict[str, Any],
    commit_map: dict[str, dict[str, Any]],
    branch_heads: dict[str, str],
    default_branch: str,
    log,
) -> dict[str, Any]:
    """Delete branches / create lightweight tags after all commits exist."""
    record: dict[str, Any] = {"deleted_branches": [], "tags": {}}

    tags = ref_lifecycle.get("tags") or []
    if not isinstance(tags, list):
        raise GraphGenerationError("graph.ref_lifecycle.tags must be a list of {name, commit} objects.")
    for tag in tags:
        if not isinstance(tag, dict) or not isinstance(tag.get("name"), str) or not isinstance(tag.get("commit"), str):
            raise GraphGenerationError("graph.ref_lifecycle.tags entries must be objects with string 'name' and 'commit'.")
        target_id = tag["commit"]
        if target_id not in commit_map:
            raise GraphGenerationError(f"graph.ref_lifecycle.tags refers to unknown logical commit '{target_id}'.")
        target_hash = commit_map[target_id]["hash"]
        run_git(repo_dir, ["tag", tag["name"], target_hash])
        record["tags"][tag["name"]] = {"commit": target_id, "hash": target_hash}
        log(f"Created tag {tag['name']} at {target_id} ({target_hash})")

    delete_branches = ref_lifecycle.get("delete_branches") or []
    if not isinstance(delete_branches, list) or not all(isinstance(name, str) for name in delete_branches):
        raise GraphGenerationError("graph.ref_lifecycle.delete_branches must be a list of branch names.")
    for name in delete_branches:
        if name not in branch_heads:
            raise GraphGenerationError(f"graph.ref_lifecycle.delete_branches refers to unknown branch '{name}'.")
        current = run_git(repo_dir, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        if current == name:
            if default_branch in branch_heads and default_branch not in delete_branches:
                run_git(repo_dir, ["checkout", default_branch])
            else:
                run_git(repo_dir, ["checkout", "--detach"])
        run_git(repo_dir, ["branch", "-D", name])
        record["deleted_branches"].append(name)
        log(f"Deleted branch {name}")
    return record


# ---------------------------------------------------------------------------
# commit_generator expansion (issue #18)
# ---------------------------------------------------------------------------


def _expand_commit_generators(
    repo_dir: Path,
    scenario: dict[str, Any],
    owner_id: str,
    branch: str,
    parents: list[str],
    commit_spec: dict[str, Any],
    owner_metadata: CommitMetadata,
    commit_map: dict[str, dict[str, Any]],
    log,
) -> list[str]:
    """Create the real commits requested by ``commit_generator`` operations.

    The generated commits are linear ancestors of the owning commit on the
    current branch.  Each one appends a line to one of ``files`` files under
    ``path`` (a directory).  Commits are written with ``git fast-import`` in
    one process, so thousands of them take well under a second.
    """
    ops = [op for op in commit_spec.get("operations", []) or [] if isinstance(op, dict) and op.get("type") == "commit_generator"]
    if not ops:
        return []

    meta = scenario.get("meta") if isinstance(scenario.get("meta"), dict) else {}
    scenario_id = str(meta.get("id") or owner_id)

    plan: list[CommitGeneratorPlan] = []
    for op in ops:
        try:
            entry = commit_generator_plan(op, owner_id)
        except ValueError as exc:
            raise GraphGenerationError(str(exc)) from None
        if entry.count != entry.requested:
            log(f"commit_generator count {entry.requested} of commit {owner_id} capped at {MAX_GENERATED_COMMITS}")
        plan.append(entry)

    total = sum(entry.count for entry in plan)
    if total == 0:
        return []

    # The `<owner>.g<N>` namespace is reserved for generated commits.  Refuse
    # to run when a scenario commit (declared before *or* after the owner) or
    # an already generated commit uses one of the ids we are about to allocate;
    # silently overwriting a logical id would corrupt commit-map/graph-map.
    planned_ids = [f"{owner_id}.g{n}" for n in range(1, total + 1)]
    scenario_ids = {str(c.get("id")) for c in scenario.get("commits", []) or [] if isinstance(c, dict) and c.get("id") is not None}
    collisions = [gid for gid in planned_ids if gid in scenario_ids or gid in commit_map]
    if collisions:
        raise GraphGenerationError(
            f"commit_generator of commit '{owner_id}' would allocate generated commit id(s) {collisions} that are already "
            "used by scenario commits; the '<owner>.g<N>' namespace is reserved for generated commits, rename those commits."
        )

    # Generated commits are dated strictly inside the interval between the
    # actual parent and the owner, separately for the author and the committer
    # date, so that both sequences stay chronological
    # (parent < g1 < ... < gN < owner).  The bounds are the *effective* dates
    # recorded in commit-map (author_date / committer_date; the original
    # ``date`` is only a fallback for entries that lack them).  Without a
    # parent the day before the owner is used.  When an interval is shorter
    # than total + 1 seconds a strict order is impossible at Git's one-second
    # resolution: that date kind is clamped to the parent's timestamp
    # (non-decreasing, never after the owner) and the placement is recorded.
    parent_entry = commit_map[parents[0]] if parents and parents[0] in commit_map else None
    author_dates, author_placement = _place_generated_dates(
        _effective_parent_date(parent_entry, "author_date"), parse_timestamp(owner_metadata.author_date), total, "author", owner_id, log
    )
    committer_dates, committer_placement = _place_generated_dates(
        _effective_parent_date(parent_entry, "committer_date"), parse_timestamp(owner_metadata.committer_date), total, "committer", owner_id, log
    )
    placement = "spaced" if author_placement == committer_placement == "spaced" else "clamped"
    placement_detail = {"author": author_placement, "committer": committer_placement}

    parent_hash = run_git(repo_dir, ["rev-parse", "--verify", "-q", "HEAD"]).stdout.strip() if parents else ""

    written: set[str] = set()      # the files of this import so far, none of them in the worktree yet

    def read_existing(rel_path: str) -> str:
        try:
            existing = safe_join(repo_dir, rel_path)
        except PathValidationError as exc:
            raise GraphGenerationError(f"commit_generator of commit '{owner_id}' produced an invalid path '{rel_path}': {exc}") from exc
        _refuse_generated_path_below_a_file(repo_dir, rel_path, owner_id)
        _refuse_a_collision_within_the_import(written, rel_path, owner_id)
        written.add(rel_path)
        try:
            return existing.read_text(encoding="utf-8") if existing.exists() else ""
        except (OSError, ValueError) as exc:      # a directory, a file that is not UTF-8 (issue #175)
            reason = exc.strerror if isinstance(exc, OSError) and exc.strerror else str(exc)
            raise GraphGenerationError(f"commit_generator of commit '{owner_id}' cannot append to '{rel_path}': {reason}") from exc

    stream: list[bytes] = []
    generated: list[dict[str, Any]] = []
    previous_id: str | None = parents[0] if parents else None
    # file names and contents come from graph_operations, which the simulator shares (issue #175)
    for sequence, (generator, rel_path, content) in enumerate(commit_generator_changes(plan, read_existing), start=1):
        gid = planned_ids[sequence - 1]
        author = deterministic_author(scenario_id, gid)
        author_date = format_timestamp(author_dates[sequence - 1])
        committer_date = format_timestamp(committer_dates[sequence - 1])
        message = f"Update {rel_path} ({generator} {sequence}/{total})"
        stream.append(
            _fast_import_commit(sequence, message, author, author_date, committer_date, parent_hash if sequence == 1 else None, rel_path, content)
        )
        generated.append(
            {
                "id": gid,
                "message": message,
                "author": author,
                "author_date": author_date,
                "committer_date": committer_date,
                "timestamp_placement": placement,
                "timestamp_placement_detail": dict(placement_detail),
                "role": "generated",
                "branch": branch,
                "parents": [previous_id] if previous_id else [],
                "generated_by": owner_id,
                "path": rel_path,
            }
        )
        previous_id = gid

    marks_path = repo_dir / ".git" / "szzbench-fast-import-marks"
    args = ["fast-import", "--quiet", "--done", f"--export-marks={marks_path}"]
    log(f"Creating {total} generated commit(s) for {owner_id} with git fast-import")
    run_git_with_input(repo_dir, args, b"".join(stream) + b"done\n")
    marks: dict[int, str] = {}
    for line in marks_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].startswith(":"):
            marks[int(parts[0][1:])] = parts[1]
    marks_path.unlink()
    if len(marks) != total:
        raise GraphGenerationError(f"git fast-import produced {len(marks)} commit(s) for '{owner_id}', expected {total}.")

    last_hash = marks[total]
    # Move the current branch (and the worktree) onto the generated history.
    run_git(repo_dir, ["reset", "--hard", last_hash])
    run_git(repo_dir, ["update-ref", "-d", _GENERATED_IMPORT_REF])

    generated_ids: list[str] = []
    for entry in generated:
        gid = entry.pop("id")
        entry_hash = marks[len(generated_ids) + 1]
        commit_map[gid] = {"hash": entry_hash, **entry}
        generated_ids.append(gid)
    log(f"Created generated commits {generated_ids[0]} .. {generated_ids[-1]} (last {last_hash})")
    return generated_ids


def _refuse_a_collision_within_the_import(written: set[str], rel_path: str, owner_id: str) -> None:
    """A generated file below an earlier generated file of the same import, or at the path
    of a directory that holds one.  The worktree has neither yet, so the check above cannot
    see them, and ``git fast-import`` would silently replace the earlier file with a
    directory, or the directory with the file (PR #226 review)."""
    for parent in PurePosixPath(rel_path).parents:
        if parent.as_posix() in written:
            raise GraphGenerationError(f"commit_generator of commit '{owner_id}' cannot write '{rel_path}': "
                                       f"{parent.as_posix()} is a file it generates")
    below = next((path for path in sorted(written) if path.startswith(rel_path + "/")), None)
    if below is not None:
        raise GraphGenerationError(f"commit_generator of commit '{owner_id}' cannot write '{rel_path}': "
                                   f"it is a directory of {below}, a file it generates")


def _refuse_generated_path_below_a_file(repo_dir: Path, rel_path: str, owner_id: str) -> None:
    """A generated file below an existing file: ``git fast-import`` would silently
    replace that file with a directory (issue #175)."""
    parent = Path(rel_path).parent
    while parent != Path("."):
        if (repo_dir / parent).is_file():
            raise GraphGenerationError(f"commit_generator of commit '{owner_id}' cannot write '{rel_path}': "
                                       f"{parent.as_posix()} is a file")
        parent = parent.parent


def _effective_parent_date(parent_entry: dict[str, Any] | None, kind: str) -> datetime | None:
    """The parent's effective author/committer date from commit-map (``date`` only as a fallback)."""
    if parent_entry is None:
        return None
    value = parent_entry.get(kind) or parent_entry.get("date")
    return parse_timestamp(value) if value else None


def _place_generated_dates(
    lower: datetime | None,
    upper: datetime,
    total: int,
    kind: str,
    owner_id: str,
    log,
) -> tuple[list[datetime], str]:
    """Return ``total`` timestamps strictly inside ``(lower, upper)`` and how they were placed.

    ``lower`` is the parent's effective date of this kind (``None`` without a
    parent: the day before ``upper`` is used).  With at least ``total + 1``
    seconds available the dates are spaced evenly ("spaced").  Otherwise they
    are clamped to the parent's timestamp, non-decreasing and never after the
    owner ("clamped"); when the owner is not later than the parent at all, the
    owner's date is used for every generated commit.
    """
    if lower is None:
        lower = upper - timedelta(days=1)
    interval_seconds = int((upper - lower).total_seconds())
    if interval_seconds >= total + 1:
        step = interval_seconds / (total + 1)
        return [lower + timedelta(seconds=int(step * n)) for n in range(1, total + 1)], "spaced"
    log(
        f"commit_generator of commit {owner_id}: only {interval_seconds}s between the parent's and the owner's {kind} date "
        f"for {total} generated commit(s); {kind} dates clamped to the parent's {kind} date (non-decreasing, never after the owner)"
    )
    if interval_seconds < 0:
        return [upper for _ in range(total)], "clamped"
    return [lower + timedelta(seconds=min(n, interval_seconds)) for n in range(1, total + 1)], "clamped"


def _fast_import_commit(
    mark: int,
    message: str,
    author: str,
    author_date: str,
    committer_date: str,
    from_hash: str | None,
    rel_path: str,
    content: str,
) -> bytes:
    name, email = parse_author(author)
    author_identity = f"{name} <{email}> {timestamp_to_git_raw(author_date)}"
    committer_identity = f"{name} <{email}> {timestamp_to_git_raw(committer_date)}"
    message_bytes = message.encode("utf-8")
    content_bytes = content.encode("utf-8")
    parts = [
        f"commit {_GENERATED_IMPORT_REF}\n".encode("utf-8"),
        f"mark :{mark}\n".encode("utf-8"),
        f"author {author_identity}\n".encode("utf-8"),
        f"committer {committer_identity}\n".encode("utf-8"),
        f"data {len(message_bytes)}\n".encode("utf-8"),
        message_bytes,
        b"\n",
    ]
    if from_hash:
        parts.append(f"from {from_hash}\n".encode("utf-8"))
    parts.append(f"M 100644 inline {rel_path}\n".encode("utf-8"))
    parts.append(f"data {len(content_bytes)}\n".encode("utf-8"))
    parts.append(content_bytes)
    parts.append(b"\n\n")
    return b"".join(parts)


# ---------------------------------------------------------------------------
# Commit creation
# ---------------------------------------------------------------------------


def _commit_current_state(
    repo_dir: Path,
    *,
    message: str,
    metadata: CommitMetadata,
    body: str = "",
    allow_empty: bool = False,
) -> str:
    run_git(repo_dir, ["add", "-A"])
    status = run_git(repo_dir, ["status", "--porcelain"]).stdout.strip()
    merge_in_progress = (repo_dir / ".git" / "MERGE_HEAD").exists()
    args = ["commit", "-m", message]
    if body:
        args.extend(["-m", body])
    if allow_empty and not status and not merge_in_progress:
        args.insert(1, "--allow-empty")
    elif not status and not merge_in_progress:
        raise GitError("commit would be empty")

    run_git(repo_dir, args, env=metadata.git_env())
    return run_git(repo_dir, ["rev-parse", "HEAD"]).stdout.strip()
