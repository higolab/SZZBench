from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
import tempfile

from .findings import ValidationResult
from .graph_operations import CommitGeneratorPlan, commit_generator_changes, commit_generator_plan, decode_content_base64
from .operations import OperationError, insert_after_once, normalize_newlines, replace_once
from .paths import PathValidationError, validate_repo_relative_path

#: The mode Git records for a file whose owner may execute it (``SimFile.mode``).
EXECUTABLE = "100755"


@dataclass(frozen=True)
class SimFile:
    content: str | bytes
    #: ``EXECUTABLE`` or ``None`` (100644).  Only ``chmod`` sets it, and a scenario
    #: with a ``chmod`` is generated with ``core.filemode`` enabled, so a mode change
    #: is a change exactly when the generator records one (issue #175).
    mode: str | None = None


Snapshot = dict[str, SimFile]


def simulate_graph_scenario(data: dict[str, Any]) -> ValidationResult:
    """Run a lightweight graph generation simulation.

    The simulator tracks repository file contents per logical commit.  It is
    intentionally conservative: it catches operation-level failures before Git
    generation, but it does not try to model every detail of Git's merge
    machinery.
    """
    result = ValidationResult()
    simulated_snapshots(data, result)
    return result


def git_performed_features(data: dict[str, Any]) -> list[str]:
    """The commits whose content generation lets Git compute, as ``"<commit>: <what>"``.

    ``graph_generator`` builds these with ``git merge``, ``git revert`` or
    ``git cherry-pick``: merges, ``revert_of`` without operations or with
    ``apply_revert``, ``cherry_pick_of`` / ``backport_of`` without operations,
    and the ``apply_patch_from`` / ``apply_squash`` operations; a conflict
    ``resolution`` is applied only where Git reports a conflict.  The in-memory
    model approximates merges and patches file by file and does not model the
    rest, so a scenario with any of them is simulated with Git (issue #94).
    The conditions are the generator's own.
    """
    features: list[str] = []
    for commit in data.get("commits") or []:
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        cid = commit["id"]
        found: list[str] = []
        if len([parent for parent in commit.get("parents") or [] if isinstance(parent, str)]) >= 2:
            found.append("merge")
        if commit.get("revert_of") is not None and (not commit.get("operations") or commit.get("apply_revert")):
            found.append("git revert")
        if (commit.get("cherry_pick_of") or commit.get("backport_of")) and not commit.get("operations"):
            found.append("git cherry-pick")
        for op in commit.get("operations") or []:
            if isinstance(op, dict) and op.get("type") in ("apply_patch_from", "apply_squash") and op["type"] not in found:
                found.append(op["type"])
        if commit.get("resolution"):
            found.append("resolution")
        features.extend(f"{cid}: {what}" for what in found)
    return features


def simulate_graph_scenario_with_git(scenario_path: Path, data: dict[str, Any], features: list[str]) -> ValidationResult:
    """Simulate by generating the scenario with Git in a temporary directory.

    For a scenario with Git-computed commits (:func:`git_performed_features`)
    the generator itself is the only faithful model.  A generation failure is
    GE203, located at the commit that failed; success is recorded as GI203.
    Verification is not run: that is ``verify-graph``'s job.
    """
    # graph_generator imports the validator, which imports this module
    from .graph_generator import GraphGenerationError, generate_graph_repository

    result = ValidationResult()
    with tempfile.TemporaryDirectory(prefix="szzbench-simulate-") as tmp:
        out = Path(tmp) / "out"
        try:
            generate_graph_repository(scenario_path, out, force=True, verify=False)
        except GraphGenerationError as exc:
            failed = _failing_commit(out / "metadata" / "generation.log")
            where, location = "", "commits"
            if failed is not None:
                where = f" at commit '{failed}'"
                location = next((f"commits[{index}]" for index, commit in enumerate(data.get("commits") or [])
                                 if isinstance(commit, dict) and commit.get("id") == failed), location)
            result.error("GE203", f"Generating the scenario with Git failed{where}: {exc}", location)
            return result
    result.info("GI203", "Simulated by generating the scenario with Git, which computes "
                + ", ".join(features) + ".", "commits")
    return result


def _failing_commit(log_path: Path) -> str | None:
    """The commit a failed generation was preparing, read from its generation.log."""
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    current: str | None = None
    for line in lines:
        if line.startswith("Preparing graph commit "):
            current = line[len("Preparing graph commit "):].split(" ", 1)[0]
        elif current is not None and line.startswith(f"Created graph commit {current}:"):
            current = None
    return current


def simulated_snapshots(data: dict[str, Any], result: ValidationResult | None = None, *,
                        given: dict[str, Snapshot] | None = None) -> dict[str, Snapshot]:
    """The snapshot the simulation reaches at every commit; its findings go to ``result``.

    A commit in ``given`` is not simulated: its snapshot is the one given.  The
    drift test (tests/test_simulator_drift.py) gives the generated trees of the
    commits Git computes and compares every other snapshot with the generated
    tree (issue #175).
    """
    result = result if result is not None else ValidationResult()
    given = given or {}
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    states: dict[str, Snapshot] = {}
    parent_map: dict[str, list[str]] = {}

    for i, commit in enumerate(commits):
        if not isinstance(commit, dict):
            continue
        cid = commit.get("id")
        if not isinstance(cid, str):
            continue
        loc = f"commits[{i}]"
        parents = [p for p in commit.get("parents", []) or [] if isinstance(p, str)]
        parent_map[cid] = parents
        if cid in given:
            states[cid] = _clone_snapshot(given[cid])
            continue
        try:
            snapshot = _checkout_snapshot(parents, states, parent_map)
        except OperationError as exc:
            result.error("GE200", f"Graph simulation cannot prepare commit '{cid}': {exc}", f"{loc}.parents")
            states[cid] = {}
            continue

        # the generator commits commit_generator files first, as commits of their own
        generated, had_operation_error = _expand_commit_generators(snapshot, commit, cid, loc, result)
        before_operations = _clone_snapshot(snapshot)
        for j, op in enumerate(commit.get("operations", []) or []):
            op_loc = f"{loc}.operations[{j}]"
            if not isinstance(op, dict) or op.get("type") == "commit_generator":
                continue
            try:
                _apply_simulated_operation(snapshot, op, states, parent_map)
            except (OperationError, ValueError, PathValidationError) as exc:
                result.error("GE201", f"Graph simulation failed for commit '{cid}': {exc}", op_loc)
                had_operation_error = True

        # an owner of generated commits is committed with --allow-empty, as the generator does
        if not had_operation_error and len(parents) < 2 and not commit.get("allow_empty") and not generated:
            if snapshot == before_operations:
                result.error("GE202", f"Commit '{cid}' would be empty during graph generation.", loc)
        states[cid] = snapshot

    return states


def _expand_commit_generators(snapshot: Snapshot, commit: dict[str, Any], cid: str, loc: str,
                              result: ValidationResult) -> tuple[int, bool]:
    """Write the files of ``commit``'s ``commit_generator`` operations as generation writes them.

    ``(generated commits, failed)``.  The names and contents come from
    ``graph_operations.commit_generator_changes``, which the generator uses; a
    ``count`` of 0 writes nothing (issue #175).
    """
    plans: list[tuple[str, CommitGeneratorPlan]] = []      # (location, plan)
    for j, op in enumerate(commit.get("operations", []) or []):
        if isinstance(op, dict) and op.get("type") == "commit_generator":
            try:
                plans.append((f"{loc}.operations[{j}]", commit_generator_plan(op, cid)))
            except ValueError as exc:
                result.error("GE201", f"Graph simulation failed for commit '{cid}': {exc}", f"{loc}.operations[{j}]")
                return 0, True
    owners = [op_loc for op_loc, plan in plans for _ in range(plan.count)]     # the operation of each generated commit

    def read_file(path: str) -> str:
        path = _validated_path(path)
        existing = snapshot.get(path)
        if existing is None:
            return ""
        if isinstance(existing.content, str):
            return existing.content
        try:
            return normalize_newlines(existing.content.decode("utf-8"))
        except UnicodeDecodeError:
            raise OperationError(f"commit_generator cannot append to binary file: {path}") from None

    done = 0
    try:
        for _, path, content in commit_generator_changes([plan for _, plan in plans], read_file):
            _set_file(snapshot, path, SimFile(content), "commit_generator")     # fast-import writes 100644
            done += 1
    except (OperationError, PathValidationError) as exc:
        result.error("GE201", f"Graph simulation failed for commit '{cid}': {exc}", owners[done])
        return done, True
    return done, False


def _checkout_snapshot(parents: list[str], states: dict[str, Snapshot], parent_map: dict[str, list[str]]) -> Snapshot:
    if not parents:
        return {}
    first_parent = parents[0]
    if first_parent not in states:
        raise OperationError(f"parent commit has not been simulated: {first_parent}")
    snapshot = _clone_snapshot(states[first_parent])
    for extra_parent in parents[1:]:
        if extra_parent not in states:
            raise OperationError(f"merge parent has not been simulated: {extra_parent}")
        ancestor_id = _nearest_common_ancestor(first_parent, extra_parent, parent_map)
        ancestor = states.get(ancestor_id, {}) if ancestor_id else {}
        snapshot = _merge_snapshots(snapshot, states[extra_parent], ancestor)
    return snapshot


def _clone_snapshot(snapshot: Snapshot) -> Snapshot:
    return dict(snapshot)


def _merge_snapshots(left: Snapshot, right: Snapshot, ancestor: Snapshot) -> Snapshot:
    merged = _clone_snapshot(left)
    for path in set(left) | set(right) | set(ancestor):
        ancestor_file = ancestor.get(path)
        left_file = left.get(path)
        right_file = right.get(path)
        if right_file == ancestor_file:
            continue
        if left_file == ancestor_file or left_file == right_file:
            if right_file is None:
                merged.pop(path, None)
            else:
                merged[path] = right_file
            continue
        raise OperationError(f"merge conflict for path: {path}")
    return merged


def _nearest_common_ancestor(a: str, b: str, parent_map: dict[str, list[str]]) -> str | None:
    a_distances = _ancestor_distances(a, parent_map)
    b_distances = _ancestor_distances(b, parent_map)
    common = set(a_distances) & set(b_distances)
    if not common:
        return None
    return min(common, key=lambda cid: (a_distances[cid] + b_distances[cid], a_distances[cid], cid))


def _ancestor_distances(start: str, parent_map: dict[str, list[str]]) -> dict[str, int]:
    distances: dict[str, int] = {}
    queue: list[tuple[str, int]] = [(start, 0)]
    while queue:
        cid, distance = queue.pop(0)
        if cid in distances and distances[cid] <= distance:
            continue
        distances[cid] = distance
        for parent in parent_map.get(cid, []):
            queue.append((parent, distance + 1))
    return distances


def _apply_simulated_operation(
    snapshot: Snapshot,
    op: dict[str, Any],
    states: dict[str, Snapshot],
    parent_map: dict[str, list[str]],
) -> None:
    op_type = op.get("type")

    if op_type == "write_file":
        path = _validated_path(op["path"])
        _set_file(snapshot, path, SimFile(normalize_newlines(str(op["content"])), _mode(snapshot, path)), op_type)
        return

    if op_type == "replace":
        path = _validated_path(op["path"])
        content = _require_text(snapshot, path, "replace")
        old = normalize_newlines(str(op["old"]))
        new = normalize_newlines(str(op["new"]))
        _set_file(snapshot, path, SimFile(replace_once(content, old, new, op.get("occurrence")), snapshot[path].mode), op_type)
        return

    if op_type == "insert_after":
        path = _validated_path(op["path"])
        content = _require_text(snapshot, path, "insert_after")
        anchor = normalize_newlines(str(op["anchor"]))
        inserted = normalize_newlines(str(op["content"]))
        _set_file(snapshot, path, SimFile(insert_after_once(content, anchor, inserted, op.get("occurrence")), snapshot[path].mode), op_type)
        return

    if op_type == "delete_file":
        path = _validated_path(op["path"])
        if path not in snapshot:
            raise OperationError(f"delete target does not exist: {path}")
        del snapshot[path]
        return

    if op_type in {"rename_file", "move_file"}:
        src = _validated_path(op["from"])
        dst = _validated_path(op["to"])
        if src not in snapshot:
            raise OperationError(f"{op_type} source does not exist: {src}")
        if dst in snapshot and not op.get("overwrite", False):
            raise OperationError(f"{op_type} target already exists: {dst}")
        _set_file(snapshot, dst, snapshot[src], op_type)      # the file keeps its mode
        del snapshot[src]
        return

    if op_type == "copy_file":
        src = _validated_path(op["from"])
        dst = _validated_path(op["to"])
        if src not in snapshot:
            raise OperationError(f"copy source does not exist: {src}")
        if dst in snapshot and not op.get("overwrite", False):
            raise OperationError(f"copy target already exists: {dst}")
        _set_file(snapshot, dst, snapshot[src], op_type)      # shutil.copy2 copies the mode
        return

    if op_type in {"move_entity", "copy_entity"}:
        src = _validated_path(op["from_file"])
        dst = _validated_path(op["to_file"])
        content = _require_text(snapshot, src, op_type)
        if dst in snapshot and not op.get("overwrite", True):     # the generator's default (issue #175)
            raise OperationError(f"{op_type} target file already exists: {dst}")
        header = _entity_operation_header(op_type, op)
        if dst in snapshot and op.get("append", False):
            previous = _require_text(snapshot, dst, op_type)
            new_content = previous.rstrip() + "\n\n" + header + content
        else:
            new_content = header + content
        _set_file(snapshot, dst, SimFile(new_content, _mode(snapshot, dst)), op_type)
        if op_type == "move_entity" and op.get("remove_source_file", False):
            del snapshot[src]
        return

    if op_type == "chmod":
        path = _validated_path(op["path"])
        if path not in snapshot:
            raise OperationError(f"chmod target does not exist: {path}")
        # Git records 100755 when the owner may execute the file, 100644 otherwise
        executable = int(str(op["mode"]), 8) & 0o100
        snapshot[path] = SimFile(snapshot[path].content, EXECUTABLE if executable else None)
        return

    if op_type == "write_binary_file":
        path = _validated_path(op["path"])
        _set_file(snapshot, path, SimFile(decode_content_base64(op["content_base64"]), _mode(snapshot, path)), op_type)
        return

    if op_type == "write_generated_text_file":
        path = _validated_path(op["path"])
        lines = int(op["lines"])
        template = str(op["template"])
        content = "\n".join(_render_template_line(template, line_no) for line_no in range(1, lines + 1)) + "\n"
        _set_file(snapshot, path, SimFile(content, _mode(snapshot, path)), op_type)
        return

    if op_type == "format_file":
        path = _validated_path(op["path"])
        content = _require_text(snapshot, path, "format_file")
        formatted = "\n".join(line.rstrip() for line in content.splitlines()) + "\n"
        _set_file(snapshot, path, SimFile(formatted, snapshot[path].mode), op_type)
        return

    if op_type == "apply_patch_from":
        _apply_patch_from_commit(snapshot, str(op["commit"]), op, states, parent_map)
        return

    if op_type == "apply_squash":
        from_commits = op.get("from_commits", []) or []
        if not isinstance(from_commits, list):
            raise OperationError("apply_squash.from_commits must be a list")
        for source_id in from_commits:
            if not isinstance(source_id, str):
                raise OperationError("apply_squash.from_commits entries must be commit ids")
            _apply_patch_from_commit(snapshot, source_id, op, states, parent_map)
        return

    if op_type == "apply_patch":
        raise OperationError("apply_patch is recognized by the graph schema but is not implemented in this MVP")


def _apply_patch_from_commit(
    snapshot: Snapshot,
    source_id: str,
    op: dict[str, Any],
    states: dict[str, Snapshot],
    parent_map: dict[str, list[str]],
) -> None:
    if source_id not in states:
        raise OperationError(f"apply_patch_from refers to unknown or later commit '{source_id}'")
    source_parents = parent_map.get(source_id, [])
    if not source_parents:
        before: Snapshot = {}
    else:
        mainline = int(op.get("mainline", op.get("parent", 1)))
        if mainline < 1 or mainline > len(source_parents):
            raise OperationError(f"apply_patch_from mainline parent out of range for '{source_id}'")
        parent_id = source_parents[mainline - 1]
        before = states.get(parent_id, {})
    _apply_snapshot_diff(snapshot, before, states[source_id], source_id)


def _apply_snapshot_diff(snapshot: Snapshot, before: Snapshot, after: Snapshot, source_id: str) -> None:
    for path in set(before) | set(after):
        before_file = before.get(path)
        after_file = after.get(path)
        current_file = snapshot.get(path)
        if before_file == after_file:
            continue
        if after_file is None:
            if current_file is None:
                continue
            if current_file != before_file:
                raise OperationError(f"apply_patch_from patch for '{source_id}' does not apply cleanly to {path}")
            del snapshot[path]
            continue
        if before_file is None:
            if current_file is None or current_file == after_file:
                snapshot[path] = after_file
                continue
            raise OperationError(f"apply_patch_from patch for '{source_id}' would overwrite {path}")
        if current_file == before_file:
            snapshot[path] = after_file
        elif current_file == after_file:
            continue
        else:
            raise OperationError(f"apply_patch_from patch for '{source_id}' does not apply cleanly to {path}")


def _validated_path(path: str) -> str:
    validate_repo_relative_path(path)
    return Path(path).as_posix()


def _require_text(snapshot: Snapshot, path: str, op_type: str) -> str:
    if path not in snapshot:
        target = "target" if op_type in {"replace", "format_file"} else "source file"
        raise OperationError(f"{op_type} {target} does not exist: {path}")
    content = snapshot[path].content
    if not isinstance(content, str):
        raise OperationError(f"{op_type} cannot operate on binary file: {path}")
    return content


def _set_file(snapshot: Snapshot, path: str, value: SimFile, op_type: str) -> None:
    """Store ``value`` at ``path``.

    A path that is a directory of the snapshot, or that lies below one of its
    files, cannot hold a file in the generated worktree either (issue #175).
    """
    if path not in snapshot:
        if any(other.startswith(path + "/") for other in snapshot):
            raise OperationError(f"{op_type} target is a directory: {path}")
        for parent in PurePosixPath(path).parents:
            if parent.as_posix() in snapshot:
                raise OperationError(f"{op_type} target lies below the file {parent.as_posix()}: {path}")
    snapshot[path] = value


def _mode(snapshot: Snapshot, path: str) -> str | None:
    """The mode a file keeps when an operation rewrites it in place."""
    existing = snapshot.get(path)
    return existing.mode if existing is not None else None


def _render_template_line(template: str, line_no: int) -> str:
    return template.replace("${line}", str(line_no)).replace("{line}", str(line_no))


def _entity_operation_header(op_type: str, op: dict[str, Any]) -> str:
    entity = op.get("entity", {})
    name = entity.get("name") or entity.get("signature") or "unknown"
    return f"// SZZBench {op_type}: {name}\n"
