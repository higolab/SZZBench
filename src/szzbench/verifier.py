from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

from .findings import ValidationResult
from .gitutils import (GitError, git_blame_line, git_hash_exists, git_message, git_parent, git_refs, git_show,
                       parse_author, parse_timestamp, run_git, scenario_default_branch)
from .operations import find_all_occurrences
from .scenario import load_yaml
from .validator import DUPLICATE_STATEMENT_FACTOR_RE, FAULT_REWRITE_FACTOR_RE, factor_matches, graph_scenario_guard

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

@dataclass
class _Commit:
    """What Git records for a commit, as the verifier compares it with the commit map (issue #167)."""
    hash: str
    parents: list[str]
    author_name: str
    author_email: str
    author_epoch: int
    author_iso: str
    committer_epoch: int
    committer_iso: str

def _read_commit(repo_dir: Path, revision: str) -> _Commit:
    # %an / %ae: the identity as recorded (a .mailmap changes only %aN / %aE)
    out = run_git(repo_dir, ["log", "-1", "--format=%H%x00%P%x00%an%x00%ae%x00%at%x00%aI%x00%ct%x00%cI",
                             revision]).stdout
    fields = out.rstrip("\n").split("\0")
    try:
        full, parents, name, email, author_epoch, author_iso, committer_epoch, committer_iso = fields
        return _Commit(full, parents.split(), name, email, int(author_epoch), author_iso, int(committer_epoch),
                       committer_iso)
    except ValueError as exc:
        raise GitError(f"git log -1 {revision} printed {out!r}") from exc

#: What Git drops from either end of an author's name and e-mail: control
#: characters, white space and some punctuation, which differs between
#: versions (Git 2.39 drops ``.``, ``,``, ``:`` and ``;`` as well, Git 2.50
#: keeps them: ``Tolkien Jr.``).  The comparison drops all of them on both
#: sides, and ``<``, ``>`` and newlines anywhere, as every version does.
_IDENT_END_CRUD = "".join(chr(code) for code in range(33)) + ".,:;<>\"\\'"

def _ident_part(text: str) -> str:
    return "".join(ch for ch in text.strip(_IDENT_END_CRUD) if ch not in "\n<>")

def _same_instant(recorded, epoch: int) -> bool:
    """``recorded``, a timestamp of the commit map, is the second ``epoch`` Git recorded.

    Compared as instants, so ``Z``, ``+00:00`` and any other offset of the
    same instant are equal; Git keeps whole seconds and drops a fraction.
    """
    try:
        return math.floor(parse_timestamp(recorded).timestamp()) == epoch
    except (GitError, ArithmeticError, OSError, ValueError):
        return False

def _verify_recorded_metadata(cid: str, entry: dict, commit: _Commit, result: ValidationResult) -> None:
    """commit-map.json records the commit's own author and dates (issue #167).

    ``role`` and ``date`` record what the scenario says, not what Git
    records, and are not compared.
    """
    recorded = entry.get("author")
    if isinstance(recorded, str):
        name, email = parse_author(recorded)
        same = ((_ident_part(name), _ident_part(email))
                == (_ident_part(commit.author_name), _ident_part(commit.author_email)))
    else:
        same = False
    if not same:
        result.error("E605", f"commit-map.json records author {recorded!r} for '{cid}', but the commit's author is "
                     f"'{commit.author_name} <{commit.author_email}>'.", f"commits.{cid}")
    for field, epoch, actual in (("author_date", commit.author_epoch, commit.author_iso),
                                 ("committer_date", commit.committer_epoch, commit.committer_iso)):
        if not _same_instant(entry.get(field), epoch):
            result.error("E605", f"commit-map.json records {field} {entry.get(field)!r} for '{cid}', but the commit "
                         f"has {actual}.", f"commits.{cid}")

def _verify_date_order(cid: str, commit: _Commit, read: dict[str, tuple[str, _Commit]], result: ValidationResult) -> None:
    """The commit is committed no earlier than its parents, as GE630 checks a graph repository (issue #241).

    The classic verifier had no such check, and a scenario whose written
    dates put a child before its parent generated and verified.  Validation
    now refuses that scenario (E016); this finds a repository generated
    before that, or changed afterwards.  Compared on the seconds Git records
    (``%ct``), not the ISO text, whose offsets differ.  A parent that is not
    a commit of the scenario is E606's.
    """
    for parent_hash in commit.parents:
        if parent_hash not in read:
            continue
        pid, parent = read[parent_hash]
        if parent.committer_epoch > commit.committer_epoch:
            result.error("E610", f"Commit {commit.hash[:8]} ({cid}) was committed at {commit.committer_iso}, before its "
                         f"parent {parent.hash[:8]} ({pid}) at {parent.committer_iso}.", f"commits.{cid}")

def _verify_as_generated(repo_dir: Path, scenario: dict, resolved: dict[str, str], result: ValidationResult) -> None:
    """The repository is still as the generator left it (issue #167).

    Every commit of the scenario is reachable from a ref, the default branch
    points at the last commit and is checked out, and neither the index nor
    the working tree has a change.  An SZZ tool that checks out, commits or
    leaves files in the repository fails this; the output still counts as
    fresh for ``evaluate``, which asks only that every commit is there and
    reachable (``manifest.staleness``).
    """
    try:
        reachable = set(run_git(repo_dir, ["rev-list", "--all"]).stdout.split())
    except GitError as exc:
        result.error("E604", f"Cannot list the commits reachable from the refs: {exc}", str(repo_dir))
        reachable = set(resolved.values())
    for cid, full in resolved.items():
        if full not in reachable:
            result.error("E604", f"Logical commit '{cid}' ({full}) is not reachable from any branch, tag or HEAD; "
                         "`git log --all` does not show it.", f"commits.{cid}")
    branch = str(scenario_default_branch(scenario))                  # the branch init_repo creates
    commits = scenario.get("commits") or []
    last = commits[-1].get("id") if commits and isinstance(commits[-1], dict) else None
    try:
        tip = git_refs(repo_dir)["branches"].get(branch)
    except GitError as exc:
        result.error("E607", f"Cannot read the branches: {exc}", "repository.default_branch")
    else:
        if tip is None:
            result.error("E607", f"The default branch '{branch}' does not exist.", "repository.default_branch")
        elif last in resolved and tip != resolved[last]:
            result.error("E607", f"The default branch '{branch}' points at {tip}, not at the last commit '{last}' "
                         f"({resolved[last]}).", "repository.default_branch")
    try:
        head = run_git(repo_dir, ["symbolic-ref", "-q", "HEAD"]).stdout.strip()
    except GitError:                                                   # exit 1: a detached HEAD
        head = ""
    if head != f"refs/heads/{branch}":
        where = f"on {head}" if head else "detached"
        result.error("E608", f"HEAD is {where}; the generator leaves the default branch '{branch}' checked out.",
                     "repository.default_branch")
    try:
        # --no-optional-locks: a plain status refreshes the index on disk, and
        # verify writes nothing into the repository
        changes = run_git(repo_dir, ["--no-optional-locks", "status", "--porcelain"]).stdout.splitlines()
    except GitError as exc:
        result.error("E609", f"Cannot read the status of the working tree: {exc}", str(repo_dir))
        return
    if changes:
        shown = "; ".join(line.strip() for line in changes[:3]) + ("; ..." if len(changes) > 3 else "")
        result.error("E609", f"The index or the working tree has {len(changes)} change(s) ({shown}); the generator "
                     "leaves both clean.", str(repo_dir))

def verify_generated_repo(repo_dir: Path, scenario_path: Path, commit_map_path: Path | None = None) -> ValidationResult:
    result = ValidationResult()
    scenario, load_result = load_yaml(scenario_path)
    result.extend(load_result)
    if scenario is None:
        return result
    # The classic checks find nothing to blame in a graph scenario and would
    # report a clean repository (issue #119).
    result.extend(graph_scenario_guard(scenario, scenario_path, "verify"))
    if result.has_errors():
        return result
    if not (repo_dir / ".git").exists():
        # one finding instead of a FileNotFoundError from the first Git call (issue #166)
        result.error("E603", f"{repo_dir} is not a Git repository; generate it first, or check the path.", str(repo_dir))
        return result
    # The same declarations the simulated checks honour, so a scenario that is
    # clean under `validate --lint` is clean under `verify --strict` as well.
    meta = scenario.get("meta") if isinstance(scenario.get("meta"), dict) else {}
    duplicate_declared = factor_matches(meta.get("factors"), DUPLICATE_STATEMENT_FACTOR_RE)
    rewrite_declared = factor_matches(meta.get("factors"), FAULT_REWRITE_FACTOR_RE)
    if commit_map_path is None:
        commit_map_path = repo_dir.parent / "metadata" / "commit-map.json"
    commit_map, cm_result = _load_commit_map(commit_map_path)
    result.extend(cm_result)
    if cm_result.has_errors():
        return result
    # the full hash of every commit that exists, by logical id, for the checks of
    # the repository as a whole (issue #167)
    resolved: dict[str, str] = {}
    read: dict[str, tuple[str, _Commit]] = {}        # hash -> (logical id, commit), for the date order
    previous: str | None = ""        # the parent the next commit must have: "" for none, None when unknown
    for commit_spec in scenario.get("commits", []):
        cid = commit_spec.get("id")
        parent, previous = previous, None
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
            commit = _read_commit(repo_dir, actual_hash)
        except GitError as exc:
            result.error("E601", f"Cannot inspect commit '{cid}': {exc}", f"commits.{cid}")
            continue
        resolved[cid] = previous = commit.hash
        _verify_recorded_metadata(cid, commit_map[cid], commit, result)
        if parent is not None and commit.parents != ([parent] if parent else []):
            wanted = f"the previous commit ({parent})" if parent else "none, as the first commit"
            result.error("E606", f"Commit '{cid}' has parent(s) {', '.join(commit.parents) or 'none'}; the generator "
                         f"gives it {wanted}.", f"commits.{cid}")
        _verify_date_order(cid, commit, read, result)
        read.setdefault(commit.hash, (cid, commit))
    _verify_as_generated(repo_dir, scenario, resolved, result)
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
                        elif count > 1 and not duplicate_declared:
                            result.warning("W301", f"bug {bid} fault.statement appears {count} times at fault.commit '{fcommit}'; declare the duplication with a factor if intended.", f"{loc}.fault.statement")
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
                    if isinstance(removed_text, str):
                        if removed_text in content:
                            result.error("E312", f"bug {bid} fix.removed_statement is still present at fix.commit '{fix_commit}'.", f"{loc}.fix.removed_statement")
                        before_hash = git_parent(repo_dir, fix_hash)
                        if before_hash:
                            before = git_show(repo_dir, before_hash, fix_file)
                            if removed_text not in before:
                                result.error("E313", f"bug {bid} fix.removed_statement is not present in '{fix_file}' immediately before fix.commit '{fix_commit}'; the fix removed nothing.", f"{loc}.fix.removed_statement")
                except GitError as exc:
                    result.error("E310", f"Cannot read fix.file for bug {bid}: {exc}", f"{loc}.fix.file")
        if isinstance(fault, dict) and fault.get("change_type") != "omission" and bfc in commit_map:
            bfc_hash = commit_map[bfc]["hash"]
            parent_hash = git_parent(repo_dir, bfc_hash)
            ffile = fault.get("file")
            stmt = fault.get("statement")
            if parent_hash and isinstance(ffile, str) and isinstance(stmt, str):
                _verify_basic_blame(repo_dir, commit_map, parent_hash, ffile, stmt, bics, rewrite_declared, result,
                                    loc, bid)
    return result


def _verify_basic_blame(repo_dir: Path, commit_map: dict, parent_hash: str, ffile: str, stmt: str, bics: list,
                        rewrite_declared: bool, result: ValidationResult, loc: str, bid: str) -> None:
    """Blame the fault statement at the BFC's parent, with the graph verifier's codes (issue #275).

    W700 used to stand for every outcome but I700 and I701: a statement absent
    from the parent, blame that reaches another commit, and a check that could
    not run.  A script reading ``verify --json`` could not tell a property of
    the scenario from a failure of the environment without parsing the message.
    Each outcome now has the number ``graph_verifier._verify_basic_blame``
    gives it: W700 / GW700 when the file cannot be read, W701 / GW701,
    W702 / GW702 when ``git blame`` fails, W703 / GW703.
    """
    try:
        parent_content = git_show(repo_dir, parent_hash, ffile)
    except GitError as exc:
        result.warning("W700", f"bug {bid}: basic blame check skipped: {exc}", loc)
        return
    line_number = None
    for line_index, line in enumerate(parent_content.splitlines(), start=1):
        if stmt in line:
            line_number = line_index
            break
    if line_number is None:
        if rewrite_declared:
            result.info("I701", f"bug {bid}: fault.statement not present in BFC parent, as the declared rewrite factor predicts; basic blame unavailable by design.", loc)
        else:
            result.warning("W701", f"bug {bid}: fault.statement not present in BFC parent; basic blame unavailable.", loc)
        return
    try:
        blamed_hash = git_blame_line(repo_dir, parent_hash, ffile, line_number)
    except GitError as exc:
        result.warning("W702", f"bug {bid}: basic blame check failed: {exc}", loc)
        return
    expected_hashes = {commit_map[bic]["hash"] for bic in bics if bic in commit_map}
    if blamed_hash in expected_hashes:
        result.info("I700", f"bug {bid}: basic git blame reaches expected BIC.", loc)
    else:
        result.warning("W703", f"bug {bid}: basic git blame reaches {blamed_hash}, not expected BIC(s) {sorted(bics)}.", loc)
