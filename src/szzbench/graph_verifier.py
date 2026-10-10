from __future__ import annotations

from collections.abc import Callable, Container
from pathlib import Path
from typing import Any, NamedTuple
import json
import re

from .findings import ValidationResult
from .gitutils import (
    GitError,
    canonical_author,
    commit_branch,
    git_blame_line,
    git_hash_exists,
    git_message,
    git_parent,
    git_show,
    planned_generated_commits,
    run_git,
    run_git_with_input,
    scenario_default_branch,
    timestamp_to_git_raw,
)
from .graph_scenario import graph_bfc_entries, graph_bic_entries, graph_faults, graph_fixes, load_graph_scenario
from .operations import find_all_occurrences
from .validator import FAULT_REWRITE_FACTOR_RE, classic_scenario_guard, factor_matches

#: A full object name (SHA-1 or SHA-256), the only form a commit-map hash is fed to Git in.
_OBJECT_NAME_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


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
    # The graph checks would compare the repository with a graph a classic
    # scenario does not have, and never name `verify` (issue #155).
    guard = classic_scenario_guard(scenario, scenario_path, "verify-graph")
    if guard.has_errors():
        return ValidationResult([f for f in result.findings if f.code != "GE001"] + guard.findings)
    if not (repo_dir / ".git").exists():
        # one finding instead of a FileNotFoundError from the first Git call (issue #166)
        result.error("GE603", f"{repo_dir} is not a Git repository; generate it first, or check the path.", str(repo_dir))
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
    _verify_generated_commits(repo_dir, scenario, commit_map, result)
    _verify_commit_dates(repo_dir, result, commit_map)
    # verify-graph answers whether the repository is still the one generation
    # left (issue #176): its refs, HEAD, index and working tree too.  The
    # staleness check of the manifest stays tolerant of moved refs (#93).
    if not gm_result.has_errors():
        _verify_refs(repo_dir, graph_map, result)
    _verify_head(repo_dir, scenario, commit_map, result)
    _verify_worktree(repo_dir, result)
    _verify_bugs(repo_dir, scenario, commit_map, result)
    _verify_expected_szz(scenario, commit_map, result)
    return result


def _verify_commit_dates(repo_dir: Path, result: ValidationResult, commit_map: dict[str, Any] | None = None) -> None:
    """Every commit must be committed no earlier than its parents (issue #9).

    A scenario that pins some timestamps and leaves others to the generator can
    otherwise end up with a child committed before its parent, which silently
    changes what date-based candidate filters and recency heuristics see.  An
    author date *before* the committer date is the normal signature of a rebase
    and is not flagged; the other way round is an anomaly.

    Ordering is decided on the epoch seconds (``%ct`` / ``%at``), never on the
    ISO strings: Git keeps each timestamp's UTC offset in ``%cI`` / ``%aI``, so
    comparing those as text makes ``2024-01-01T10:00:00+09:00`` look later than
    ``2024-01-01T02:00:00Z`` although it is an hour earlier.  The ISO forms are
    kept for the message.

    The commits checked are those ``git log --all`` reaches and every commit of
    ``commit_map`` with its ancestors: the commits of a branch that
    ``graph.ref_lifecycle.delete_branches`` removed are in the commit map but
    no longer reachable from a ref (issue #176).  A commit-map hash that is not
    a commit of the repository is skipped here (``--ignore-missing``); GE622
    reports it.
    """
    log_args = ["log", "--all", "--format=%H|%P|%ct|%cI|%at|%aI"]
    hashes = _commit_map_hashes(commit_map) if commit_map else []
    try:
        if hashes:
            data = "".join(f"{commit_hash}^{{commit}}\n" for commit_hash in hashes).encode("ascii")
            raw = run_git_with_input(repo_dir, [*log_args, "--ignore-missing", "--stdin"], data).stdout.decode("utf-8", errors="replace")
        else:
            raw = run_git(repo_dir, log_args).stdout
    except GitError as exc:
        result.warning("GW632", f"Commit date check skipped: {exc}", "commits")
        return
    commits: dict[str, dict[str, Any]] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        commit_hash, parents, committed_at, committed_iso, authored_at, authored_iso = line.split("|")
        try:
            committed, authored = int(committed_at), int(authored_at)
        except ValueError:
            result.warning("GW632", f"Commit {commit_hash[:8]} has an unreadable timestamp.", "commits")
            continue
        commits[commit_hash] = {
            "parents": parents.split(),
            "committed": committed,
            "committed_iso": committed_iso,
            "authored": authored,
            "authored_iso": authored_iso,
        }
    # the logical ids beside the hashes, which were all the message named (issue #241)
    ids_by_hash: dict[str, list[str]] = {}
    for cid, map_entry in (commit_map or {}).items():
        if isinstance(map_entry, dict) and isinstance(map_entry.get("hash"), str):
            ids_by_hash.setdefault(map_entry["hash"], []).append(str(cid))

    def name(commit_hash: str) -> str:
        ids = ids_by_hash.get(commit_hash)
        return f"{commit_hash[:8]} ({', '.join(ids)})" if ids else commit_hash[:8]

    for commit_hash, entry in commits.items():
        for parent in entry["parents"]:
            parent_entry = commits.get(parent)
            if parent_entry is not None and parent_entry["committed"] > entry["committed"]:
                result.error(
                    "GE630",
                    f"Commit {name(commit_hash)} was committed at {entry['committed_iso']}, before its parent "
                    f"{name(parent)} at {parent_entry['committed_iso']}.",
                    "commits",
                )
        if entry["authored"] > entry["committed"]:
            result.warning(
                "GW631",
                f"Commit {name(commit_hash)} was authored at {entry['authored_iso']}, "
                f"after it was committed at {entry['committed_iso']}.",
                "commits",
            )


def _commit_map_hashes(commit_map: dict[str, Any]) -> list[str]:
    """The distinct hashes of ``commit_map`` that are full object names, sorted."""
    return sorted({
        entry["hash"] for entry in commit_map.values()
        if isinstance(entry, dict) and isinstance(entry.get("hash"), str) and _OBJECT_NAME_RE.fullmatch(entry["hash"])
    })


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
        # graph-map and commit-map are written from the same commit; they must
        # name the same hash.  (GE625 used to compare graph-map's branch with the
        # scenario's, which the generator copies, so it could not fire; #176.)
        graph_entry = (graph_map.get("commits", {}) or {}).get(cid) if isinstance(graph_map, dict) else None
        if isinstance(graph_entry, dict) and graph_entry.get("hash") != actual_hash:
            result.error(
                "GE625",
                f"graph-map.json records hash {graph_entry.get('hash')} for '{cid}', commit-map.json {actual_hash}.",
                loc,
            )


def _verify_parents(repo_dir: Path, commit_spec: dict[str, Any], commit_map: dict[str, Any], actual_hash: str, result: ValidationResult, loc: str) -> None:
    expected_parent_ids = [p for p in commit_spec.get("parents", []) or [] if isinstance(p, str)]
    expected_parent_hashes = [commit_map[p]["hash"] for p in expected_parent_ids if p in commit_map and isinstance(commit_map[p], dict)]
    # Compared whenever every declared parent resolves -- an empty list included:
    # a commit declared without parents must have none in the repository (issue #134).
    resolvable = len(expected_parent_hashes) == len(expected_parent_ids)
    # A commit that owns commit_generator operations sits on top of its
    # generated commits: its first parent is the last generated commit, not the
    # declared logical parent.  Later commits still point at the owner's own
    # hash, so only the owner's expectation changes.  The generated commits
    # the scenario plans are the expectation; one missing from the commit map
    # is GE629, reported with the rest of the chain by
    # _verify_generated_commits (issue #176).
    generated_ids = planned_generated_commits(str(commit_spec.get("id")), commit_spec)
    if generated_ids:
        last_generated = commit_map.get(generated_ids[-1])
        if isinstance(last_generated, dict) and isinstance(last_generated.get("hash"), str):
            expected_parent_hashes = [last_generated["hash"], *expected_parent_hashes[1:]]
        else:
            resolvable = False
    try:
        raw = run_git(repo_dir, ["rev-list", "--parents", "-n", "1", actual_hash]).stdout.strip()
    except GitError as exc:
        result.error("GE626", f"Cannot inspect parent list: {exc}", loc)
        return
    actual_parent_hashes = raw.split()[1:]
    if resolvable and actual_parent_hashes != expected_parent_hashes:
        result.error(
            "GE627",
            f"Parent mismatch. Expected {expected_parent_hashes}, got {actual_parent_hashes}.",
            f"{loc}.parents",
        )
    if len(expected_parent_ids) >= 2 and len(actual_parent_hashes) < 2:
        result.error("GE628", "Expected a merge commit but generated commit has fewer than two parents.", f"{loc}.parents")


def _verify_generated_commits(repo_dir: Path, scenario: dict[str, Any], commit_map: dict[str, Any], result: ValidationResult) -> None:
    """The ``<owner>.g<N>`` commits of every ``commit_generator`` owner (issue #176).

    ``_verify_commits`` walks the scenario's commits only.  The generator
    writes an owner's generated commits as a linear chain between the owner's
    declared first parent and the owner (``parent <- g1 <- ... <- gN <-
    owner``, ``gitutils.history_graph``); the owner's end of it -- its first
    parent is ``gN`` -- is GE627's.  Here the owner's ``generated_commits``
    must list the commits the scenario's operations plan (GE633), and every
    planned commit must be in the commit map (GE629) and in the repository
    (GE634), have the previous one as its only parent -- ``g1`` the owner's
    declared first parent, or none for a root owner -- (GE635), and carry the
    author, dates and subject the commit map records (GE636).  A count
    generation refuses, such as ``.inf``, plans no commits
    (``gitutils.commit_generator_count``): the scenario of an output whose
    count was changed so is reported here and at GE627 (issue #230).
    """
    owners: list[tuple[str, str, dict[str, Any], list[str]]] = []
    for i, commit_spec in enumerate(scenario.get("commits", []) or []):
        if not isinstance(commit_spec, dict) or not isinstance(commit_spec.get("id"), str):
            continue
        cid = commit_spec["id"]
        planned = planned_generated_commits(cid, commit_spec)
        own_entry = commit_map.get(cid)
        recorded = own_entry.get("generated_commits") if isinstance(own_entry, dict) else None
        if not planned and recorded is None:
            continue
        loc = f"commits[{i}]"
        if isinstance(own_entry, dict) and recorded != planned:
            result.error(
                "GE633",
                f"commit-map.json lists {_describe_ids(recorded)} as the generated commits of '{cid}'; "
                f"its commit_generator operations plan {_describe_ids(planned)}.",
                loc,
            )
        if planned:
            owners.append((cid, loc, commit_spec, planned))
    if not owners:
        return

    hashes = [
        commit_map[gid]["hash"] for _, _, _, planned in owners for gid in planned
        if isinstance(commit_map.get(gid), dict) and isinstance(commit_map[gid].get("hash"), str)
    ]
    try:
        records = _commit_records(repo_dir, hashes)
    except GitError as exc:
        result.error("GE637", f"Cannot inspect the generated commits: {exc}", "commits")
        return

    for cid, loc, commit_spec, planned in owners:
        declared = [p for p in commit_spec.get("parents", []) or [] if isinstance(p, str)]
        if declared:
            first = commit_map.get(declared[0])
            # None: the declared parent is not resolvable, GE627 territory
            previous: str | None = first.get("hash") if isinstance(first, dict) and isinstance(first.get("hash"), str) else None
        else:
            previous = ""
        for gid in planned:
            entry = commit_map.get(gid)
            if not isinstance(entry, dict) or not isinstance(entry.get("hash"), str):
                result.error("GE629", f"Generated commit '{gid}' is missing from commit-map.json.", loc)
                previous = None
                continue
            generated_hash = entry["hash"]
            record = records.get(generated_hash)
            if record is None:
                result.error("GE634", f"Git hash for generated commit '{gid}' does not exist: {generated_hash}", loc)
            else:
                expected_parents = [previous] if previous else []
                if previous is not None and record["parents"] != expected_parents:
                    result.error(
                        "GE635",
                        f"Generated commit '{gid}' has parents {record['parents']}, expected {expected_parents}.",
                        loc,
                    )
                differing = [field for field, recorded_value in _recorded_identity(entry).items() if record[field] != recorded_value]
                if differing:
                    result.error(
                        "GE636",
                        f"Generated commit '{gid}' does not carry the {', '.join(differing)} commit-map.json records.",
                        loc,
                    )
            previous = generated_hash


def _describe_ids(ids: Any) -> str:
    if not isinstance(ids, list):
        return "nothing" if ids is None else repr(ids)
    if not ids:
        return "no commits"
    if len(ids) <= 3:
        return ", ".join(str(i) for i in ids)
    return f"{len(ids)} commits ({ids[0]} .. {ids[-1]})"


def _recorded_identity(entry: dict[str, Any]) -> dict[str, str | None]:
    """What a generated commit's commit-map entry says Git recorded, in ``_commit_records``' form."""
    def raw(value: Any) -> str | None:
        try:
            return timestamp_to_git_raw(value)
        except (GitError, ValueError, OverflowError):
            return None
    return {
        "author": canonical_author(entry.get("author")) if isinstance(entry.get("author"), str) else None,
        "author date": raw(entry.get("author_date")),
        "committer date": raw(entry.get("committer_date")),
        "subject": entry.get("message") if isinstance(entry.get("message"), str) else None,
    }


def _commit_records(repo_dir: Path, hashes: list[str]) -> dict[str, dict[str, Any]]:
    """Parents, author, raw dates and subject of each of ``hashes``, from one ``git log --no-walk``.

    A hash that is not a commit of the repository is absent from the result
    (``--ignore-missing`` with ``^{commit}``).  Dates are Git's raw
    ``<epoch> <+hhmm>``, the form the generator writes them in.
    """
    names = sorted({h for h in hashes if _OBJECT_NAME_RE.fullmatch(h)})
    if not names:
        return {}
    data = "".join(f"{name}^{{commit}}\n" for name in names).encode("ascii")
    raw = run_git_with_input(
        repo_dir,
        ["log", "--no-walk", "--ignore-missing", "--stdin", "--date=raw", "--format=%H%x1f%P%x1f%an%x1f%ae%x1f%ad%x1f%cd%x1f%s"],
        data,
    ).stdout.decode("utf-8", errors="replace")
    records: dict[str, dict[str, Any]] = {}
    for line in raw.splitlines():
        fields = line.split("\x1f")
        if len(fields) != 7:
            continue
        commit_hash, parents, name, email, authored, committed, subject = fields
        records[commit_hash] = {
            "parents": parents.split(),
            "author": f"{name} <{email}>",
            "author date": authored,
            "committer date": committed,
            "subject": subject,
        }
    return records


# ---------------------------------------------------------------------------
# The repository as generation left it (issue #176)
# ---------------------------------------------------------------------------


def _verify_refs(repo_dir: Path, graph_map: dict[str, Any], result: ValidationResult) -> None:
    """Every ref is the one generation left.

    ``graph-map.json``'s ``refs`` records the branches and tags once
    ``graph.ref_lifecycle`` has been applied.  A recorded ref that is missing
    (GE641) or points at another object (GE642) is an error, and so is a ref
    generation did not leave (GE643): a new branch or tag, and any other name
    under ``refs/`` (remotes, notes, replace refs, a stash) -- the generator
    creates none, and some of them change what ``git log`` shows.
    """
    recorded = graph_map.get("refs")
    expected: dict[str, str] = {}
    readable = isinstance(recorded, dict)
    for kind, prefix in (("branches", "refs/heads/"), ("tags", "refs/tags/")):
        names = recorded.get(kind) if readable else None
        if not isinstance(names, dict) or not all(isinstance(h, str) for h in names.values()):
            readable = False
            break
        expected.update({prefix + str(name): h for name, h in names.items()})
    if not readable:
        result.error(
            "GE640",
            "graph-map.json does not record the refs generation left (refs.branches and refs.tags, name -> hash); "
            "regenerate the output.",
            "refs",
        )
        return
    try:
        out = run_git(repo_dir, ["for-each-ref", "--format=%(refname) %(objectname)"]).stdout
    except GitError as exc:
        result.error("GE646", f"Cannot list the refs: {exc}", "refs")
        return
    actual: dict[str, str] = {}
    for line in out.splitlines():
        refname, _, object_name = line.partition(" ")
        if refname:
            actual[refname] = object_name.strip()
    for refname in sorted(expected):
        if refname not in actual:
            result.error("GE641", f"{refname} is missing; generation left it at {expected[refname]}.", refname)
        elif actual[refname] != expected[refname]:
            result.error(
                "GE642",
                f"{refname} points at {actual[refname]}; generation left it at {expected[refname]}.",
                refname,
            )
    for refname in sorted(set(actual) - set(expected)):
        result.error("GE643", f"{refname} ({actual[refname]}) was not there when the repository was generated.", refname)


def _expected_head(scenario: dict[str, Any], commit_map: dict[str, Any]) -> tuple[str, str] | None:
    """Where generation leaves HEAD: ``("branch", name)`` or ``("detached", hash)``.

    HEAD stays on the branch of the scenario's last commit.  When
    ``graph.ref_lifecycle.delete_branches`` deletes that branch, the generator
    checks out the default branch if it has commits and survives, and
    otherwise detaches HEAD at the last commit (``_apply_ref_lifecycle``; the
    rule ``gitutils.reachable_commit_ids`` mirrors).  ``None`` when the
    scenario has no commits, or the detached commit is not in the commit map.
    """
    commits = [c for c in scenario.get("commits") or [] if isinstance(c, dict) and isinstance(c.get("id"), str)]
    if not commits:
        return None
    default_branch = str(scenario_default_branch(scenario))

    def branch_of(commit: dict[str, Any]) -> str:
        return str(commit_branch(commit, default_branch))

    graph = scenario.get("graph") if isinstance(scenario.get("graph"), dict) else {}
    lifecycle = graph.get("ref_lifecycle") if isinstance(graph.get("ref_lifecycle"), dict) else {}
    delete_branches = lifecycle.get("delete_branches")
    deleted = {n for n in delete_branches if isinstance(n, str)} if isinstance(delete_branches, list) else set()
    last = commits[-1]
    if branch_of(last) not in deleted:
        return "branch", branch_of(last)
    if default_branch not in deleted and any(branch_of(c) == default_branch for c in commits):
        return "branch", default_branch
    entry = commit_map.get(last["id"])
    if isinstance(entry, dict) and isinstance(entry.get("hash"), str):
        return "detached", entry["hash"]
    return None


def _verify_head(repo_dir: Path, scenario: dict[str, Any], commit_map: dict[str, Any], result: ValidationResult) -> None:
    """HEAD is where generation left it (GE644); the branch's own position is GE642's."""
    expected = _expected_head(scenario, commit_map)
    if expected is None:
        return
    kind, value = expected
    wanted = f"on branch {value}" if kind == "branch" else f"detached at {value}"
    try:
        symbolic = run_git(repo_dir, ["symbolic-ref", "-q", "HEAD"]).stdout.strip()
    except GitError:
        symbolic = ""  # exit status 1: HEAD is detached
    if symbolic:
        actual = f"on branch {symbolic[len('refs/heads/'):]}" if symbolic.startswith("refs/heads/") else f"on {symbolic}"
    else:
        try:
            head = run_git(repo_dir, ["rev-parse", "--verify", "-q", "HEAD"]).stdout.strip()
        except GitError:
            head = ""
        actual = f"detached at {head}" if head else "unreadable"
    if actual != wanted:
        result.error("GE644", f"HEAD is {actual}; generation left it {wanted}.", "HEAD")


def _verify_worktree(repo_dir: Path, result: ValidationResult) -> None:
    """The index and the working tree are clean, as generation left them (GE645).

    ``--no-optional-locks`` keeps ``git status`` from refreshing the index
    file: verification writes nothing into the repository it checks.
    """
    try:
        out = run_git(repo_dir, ["--no-optional-locks", "status", "--porcelain"]).stdout
    except GitError as exc:
        result.error("GE646", f"Cannot read the status of the index and the working tree: {exc}", "worktree")
        return
    entries = [line for line in out.splitlines() if line.strip()]
    if entries:
        shown = "; ".join(entries[:5]) + (f"; ... ({len(entries)} entries)" if len(entries) > 5 else "")
        result.error("GE645", f"The index or the working tree is not clean (git status: {shown}).", "worktree")


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
        _verify_basic_blame(repo_dir, commit_map, bug, result, loc, str(bid), factors=(scenario.get("meta") or {}).get("factors"))


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
    found = look_up_location(entry, commit_map, repository_file_reader(repo_dir, commit_map), kind=kind)
    if found is None:
        return
    commit_id = entry.get("commit")
    if found.outcome == LOOKUP_ENTITY:
        result.info("GI660", f"bug {bug_id} {kind} uses entity-level oracle; file content check skipped.", loc)
    elif found.outcome == LOOKUP_DELETED:
        result.info("GI661", f"bug {bug_id} fix is file deletion; file is absent at fix commit as expected.", loc)
    elif found.outcome == LOOKUP_NO_FILE:
        result.error("GE662", f"Cannot read {kind}.file for bug {bug_id}: {found.reason}", loc)
    elif found.outcome == LOOKUP_NOT_FOUND:
        result.error("GE663", f"bug {bug_id} {kind} statement not found at commit '{commit_id}'.", loc)
    elif found.outcome == LOOKUP_REPEATED:
        result.warning("GW664", f"bug {bug_id} {kind} statement appears {found.count} times at commit '{commit_id}'.", loc)


# --- looking a fault or fix up in its file (issue #238) -----------------------------------------

#: What :func:`look_up_location` finds.
LOOKUP_ENTITY = "entity"            # no file: an entity oracle, whose content is not checked (GI660)
LOOKUP_DELETED = "deleted"          # a ``file_deletion`` fix whose file is gone, as it says (GI661)
LOOKUP_NO_FILE = "no file"          # the file cannot be read at the commit (GE662)
LOOKUP_NOT_FOUND = "not found"      # the statement is not in the file (GE663)
LOOKUP_REPEATED = "repeated"        # the statement is in the file more than once (GW664)


class UnreadableFile(Exception):
    """Raised by a ``read_file`` of :func:`look_up_location`: the commit has no such file, or it cannot be read."""


class LocationLookup(NamedTuple):
    """What :func:`look_up_location` found, one of the ``LOOKUP_*`` outcomes."""
    outcome: str
    reason: str = ""        # why the file cannot be read (LOOKUP_NO_FILE)
    count: int = 0          # how often the statement occurs (LOOKUP_REPEATED)


def look_up_location(entry: dict[str, Any], commits: Container[str], read_file: Callable[[str, str], str], *,
                     kind: str) -> LocationLookup | None:
    """Look a fault or fix up in the file of its commit, by the rule of GE662, GE663 and GW664.

    ``read_file(commit, path)`` returns the file at the commit as the verifier
    reads a blob -- UTF-8 with replacement characters, every line ending
    ``\\n`` (issue #170) -- and raises :class:`UnreadableFile` with the reason
    when it cannot.  The verifier reads the generated repository
    (:func:`repository_file_reader`), ``validate-graph --simulate`` the
    snapshots of its replay (``graph_simulator.snapshot_file_reader``): one
    rule keeps the two from drifting apart (issue #238).  The statement is
    ``statement``, else ``added_statement``.  ``kind`` is ``fault`` or ``fix``;
    only a fix with ``fix_type: file_deletion`` may miss its file.  None when
    there is nothing to say: the commit is not one of ``commits``, the entry
    names neither a file nor an entity, or it has a file but no statement, or
    the statement is there once.
    """
    commit_id = entry.get("commit")
    file_path = entry.get("file")
    if not isinstance(commit_id, str) or commit_id not in commits:
        return None
    if not isinstance(file_path, str):
        return LocationLookup(LOOKUP_ENTITY) if entry.get("entity") is not None else None
    try:
        content = read_file(commit_id, file_path)
    except UnreadableFile as exc:
        if entry.get("fix_type") == "file_deletion" and kind == "fix":
            return LocationLookup(LOOKUP_DELETED)
        return LocationLookup(LOOKUP_NO_FILE, reason=str(exc))
    statement = entry.get("statement") or entry.get("added_statement")
    if not isinstance(statement, str) or not statement:
        return None
    count = len(find_all_occurrences(content, statement))
    if count == 0:
        return LocationLookup(LOOKUP_NOT_FOUND)
    if count > 1:
        return LocationLookup(LOOKUP_REPEATED, count=count)
    return None


def repository_file_reader(repo_dir: Path, commit_map: dict[str, Any]) -> Callable[[str, str], str]:
    """The ``read_file`` of :func:`look_up_location` for a generated repository: ``git show`` of the blob."""
    def read(commit_id: str, path: str) -> str:
        revision = commit_map[commit_id]["hash"]
        try:
            return git_show(repo_dir, revision, path)
        except GitError as exc:
            raise UnreadableFile(str(exc)) from exc
    return read


def _verify_basic_blame(repo_dir: Path, commit_map: dict[str, Any], bug: dict[str, Any], result: ValidationResult, loc: str, bug_id: str, factors: Any = None) -> None:
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
        # A fault line that is gone by the BFC is what a scenario declaring a
        # rewrite after the BIC exists to show (W320 makes the same exception).
        if factor_matches(factors, FAULT_REWRITE_FACTOR_RE):
            result.info("GI701", f"bug {bug_id}: fault.statement not present in final BFC parent, as the declared rewrite factor predicts; basic blame unavailable by design.", loc)
        else:
            result.warning("GW701", f"bug {bug_id}: fault.statement not present in final BFC parent; basic blame unavailable.", loc)
        return
    try:
        blamed_hash = git_blame_line(repo_dir, parent_hash, ffile, line_number)
    except GitError as exc:
        result.warning("GW702", f"bug {bug_id}: basic blame check failed: {exc}", loc)
        return
    expected_hashes = {
        commit_map[entry["commit"]]["hash"]
        for entry in graph_bic_entries(bug, roles={"direct", "reintroducing", "contributing"})
        if entry.get("commit") in commit_map
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
