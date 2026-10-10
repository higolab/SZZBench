from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import tempfile

from .findings import ValidationResult
from .graph_operations import CommitGeneratorPlan, commit_generator_changes, commit_generator_plan, decode_content_base64
from .operations import OperationError, insert_after_once, normalize_newlines, replace_once, text_field
from .paths import PathValidationError, file_path_conflict, validate_repo_relative_path

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
    """Replay a graph scenario in memory, as ``validate-graph --simulate`` does when Git computes no commit of it.

    The replay keeps the files of every commit (:func:`simulated_snapshots`)
    and reports the operations generation would refuse (GE201) and the commits
    it would find empty (GE202).  It models file operations only.  A commit
    whose content generation lets Git compute (:func:`git_performed_features`)
    is GE200, and nothing is replayed: ``validate-graph --simulate`` generates
    such a scenario with Git instead (:func:`simulate_graph_scenario_with_git`).
    The replay used to approximate merges and patches file by file, code that
    no command reached once those scenarios went to Git (issues #94, #183).
    """
    result = ValidationResult()
    refused = _commits_git_computes(data)
    for index, cid, found in refused:
        result.error("GE200", f"The in-memory simulation does not model commit '{cid}', whose content Git computes "
                     f"({', '.join(found)}); validate-graph --simulate generates such a scenario with Git.",
                     f"commits[{index}]")
    if not refused:
        simulated_snapshots(data, result)
    return result


def git_performed_features(data: dict[str, Any]) -> list[str]:
    """The commits whose content generation lets Git compute, as ``"<commit>: <what>"``.

    ``graph_generator`` builds these with ``git merge``, ``git revert`` or
    ``git cherry-pick``: merges, ``revert_of`` without operations or with
    ``apply_revert``, ``cherry_pick_of`` / ``backport_of`` without operations,
    and the ``apply_patch_from`` / ``apply_squash`` operations; a conflict
    ``resolution`` is applied only where Git reports a conflict.  The in-memory
    model does not model any of them, so a scenario with one is simulated with
    Git (issue #94).  The conditions are the generator's own.
    """
    return [f"{cid}: {what}" for _, cid, found in _commits_git_computes(data) for what in found]


def _commits_git_computes(data: dict[str, Any]) -> list[tuple[int, str, list[str]]]:
    """``(index, id, what Git computes)`` for every commit :func:`git_performed_features` lists."""
    computed: list[tuple[int, str, list[str]]] = []
    for index, commit in enumerate(data.get("commits") or []):
        if isinstance(commit, dict) and isinstance(commit.get("id"), str):
            found = _computed_by_git(commit)
            if found:
                computed.append((index, commit["id"], found))
    return computed


def _computed_by_git(commit: dict[str, Any]) -> list[str]:
    """What generation lets Git compute in ``commit`` (see :func:`git_performed_features`)."""
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
    return found


def simulate_graph_scenario_with_git(scenario_path: Path, data: dict[str, Any], features: list[str]) -> ValidationResult:
    """Simulate by generating the scenario with Git in a temporary directory.

    For a scenario with Git-computed commits (:func:`git_performed_features`)
    the generator itself is the only faithful model.  A generation failure is
    GE203, located at the commit that failed.  The generated repository is
    then verified as ``generate-graph`` verifies it, and each verification
    error is GE203 too, with the verifier's code, message and location
    (issue #173): a scenario that passes generates.  Success is recorded as
    GI203.
    """
    # graph_generator imports the validator, which imports this module
    from .graph_generator import GraphGenerationError, generate_graph_repository
    from .graph_verifier import verify_graph_generated_repo

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
        verification = verify_graph_generated_repo(out / "repo", scenario_path, out / "metadata" / "commit-map.json",
                                                   out / "metadata" / "graph-map.json")
        for finding in verification.findings:
            if finding.severity == "ERROR":
                result.error("GE203", f"The scenario generated with Git fails verification: "
                             f"{finding.code} {finding.message}", finding.location or "commits")
        if result.has_errors():
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
    tree (issue #175).  Any other commit Git computes is a ``ValueError``: the
    replay does not model it (issue #183).
    """
    result = result if result is not None else ValidationResult()
    given = given or {}
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    states: dict[str, Snapshot] = {}

    for i, commit in enumerate(commits):
        if not isinstance(commit, dict):
            continue
        cid = commit.get("id")
        if not isinstance(cid, str):
            continue
        loc = f"commits[{i}]"
        parents = [p for p in commit.get("parents", []) or [] if isinstance(p, str)]
        if cid in given:
            states[cid] = _clone_snapshot(given[cid])
            continue
        computed = _computed_by_git(commit)
        if computed:
            raise ValueError(f"the in-memory simulation does not model commit '{cid}', whose content Git computes "
                             f"({', '.join(computed)}); give its snapshot, or simulate the scenario with Git")
        try:
            snapshot = _checkout_snapshot(parents, states)
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
                _apply_simulated_operation(snapshot, op)
            except (OperationError, ValueError, PathValidationError) as exc:
                result.error("GE201", f"Graph simulation failed for commit '{cid}': {exc}", op_loc)
                had_operation_error = True

        # an owner of generated commits is committed with --allow-empty, as the generator does
        if not had_operation_error and not commit.get("allow_empty") and not generated:
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


def _checkout_snapshot(parents: list[str], states: dict[str, Snapshot]) -> Snapshot:
    """The snapshot a commit starts from: its parent's, or none for a root.

    A commit with a second parent is a merge, which Git computes and the
    replay does not model (``_computed_by_git``).  A parent that has not been
    simulated is unknown or declared later: GE039 and GE038 stop validation
    before any simulation runs, so only a direct call reaches the GE200 its
    error becomes.
    """
    if not parents:
        return {}
    if parents[0] not in states:
        raise OperationError(f"parent commit has not been simulated: {parents[0]}")
    return _clone_snapshot(states[parents[0]])


def _clone_snapshot(snapshot: Snapshot) -> Snapshot:
    return dict(snapshot)


def _apply_simulated_operation(snapshot: Snapshot, op: dict[str, Any]) -> None:
    op_type = op.get("type")

    if op_type == "write_file":
        path = _validated_path(op["path"])
        _set_file(snapshot, path, SimFile(normalize_newlines(text_field(op, "content")), _mode(snapshot, path)), op_type)
        return

    if op_type == "replace":
        path = _validated_path(op["path"])
        content = _require_text(snapshot, path, "replace")
        old = normalize_newlines(text_field(op, "old"))
        new = normalize_newlines(text_field(op, "new"))
        _set_file(snapshot, path, SimFile(replace_once(content, old, new, op.get("occurrence")), snapshot[path].mode), op_type)
        return

    if op_type == "insert_after":
        path = _validated_path(op["path"])
        content = _require_text(snapshot, path, "insert_after")
        anchor = normalize_newlines(text_field(op, "anchor"))
        inserted = normalize_newlines(text_field(op, "content"))
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

    if op_type == "apply_patch":
        raise OperationError("apply_patch is recognized by the graph schema but is not implemented in this MVP")

    # apply_patch_from and apply_squash are computed by Git, and never reach here (issue #183)
    raise OperationError(f"unsupported graph operation: {op_type}")


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
    files, cannot hold a file in the generated worktree either (issue #175);
    nor can one that differs from a path of the snapshot only in letter case or
    Unicode normalization, on macOS (issue #153; ``paths.file_path_conflict``).
    """
    conflict = file_path_conflict(path, snapshot)
    if conflict is not None:
        raise OperationError(f"{op_type} {conflict}")
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
