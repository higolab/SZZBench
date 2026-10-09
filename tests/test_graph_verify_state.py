"""verify-graph checks the repository as generation left it (issue #176).

It compared each scenario commit with ``commit-map.json`` and the chronology of
what ``git log --all`` reaches, and nothing else.  A repository whose branch
had been moved, whose tag was deleted, whose HEAD was detached and whose index
was emptied verified with no finding; a child committed before its parent on a
branch that ``graph.ref_lifecycle`` deletes escaped GE630; and the
``<owner>.g<N>`` commits of ``commit_generator`` were never looked at.  Now
the refs are compared with ``graph-map.json``'s ``refs`` (GE641-GE643), HEAD
with where the generator leaves it (GE644), the index and the working tree
must be clean (GE645), the date check covers every commit of the commit map,
and the generated chain is verified commit by commit (GE629, GE633-GE636).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from support import git
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_verifier import verify_graph_generated_repo

ROOT = Path(__file__).resolve().parents[1]
HUGE_HISTORY = ROOT / "advanced-scenarios/SZZG-0114/scenario.graph.yml"


def _commit(cid: str, parents: list[str], operations: list[dict], *, branch: str = "main", **extra) -> dict:
    return {"id": cid, "branch": branch, "parents": parents, "message": f"Edit the notes ({cid[-1]})",
            "role": "intermediate", "operations": operations, **extra}


def _write(path: Path) -> dict:
    return {"type": "write_file", "path": path, "content": f"{path}\n"}


def _scenario(commits: list[dict], ref_lifecycle: dict | None = None) -> dict:
    graph: dict = {"model": "commit_dag"}
    if ref_lifecycle is not None:
        graph["ref_lifecycle"] = ref_lifecycle
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "Verified state", "category": "fixture", "factors": ["single-bic"]},
        "repository": {"name": "verified-state", "default_branch": "main"},
        "graph": graph,
        "commits": commits,
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c1", "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }


def _branches_and_a_tag() -> dict:
    """main (c0 <- c1), feature (c0 <- f1), and the tag v1 at c0; HEAD is on main."""
    return _scenario(
        [_commit("c0", [], [_write("a.txt")]),
         _commit("f1", ["c0"], [_write("f.txt")], branch="feature"),
         _commit("c1", ["c0"], [_write("b.txt")])],
        ref_lifecycle={"tags": [{"name": "v1", "commit": "c0"}]},
    )


def _generate(tmp_path: Path, data: dict, *, verify: bool = True) -> tuple[Path, Path, dict]:
    scenario = tmp_path / "scenario.graph.yml"
    scenario.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    out = tmp_path / "out"
    commit_map, result = generate_graph_repository(scenario, out, force=True, verify=verify)
    if verify:
        assert not result.has_errors(), result.to_dict()
    return out, scenario, commit_map


@pytest.fixture(scope="module")
def pristine(tmp_path_factory) -> Path:
    out, _, _ = _generate(tmp_path_factory.mktemp("pristine"), _branches_and_a_tag())
    return out


@pytest.fixture
def generated(tmp_path, pristine) -> tuple[Path, Path, dict]:
    """A copy of the generated output, for a test to change: ``(out, scenario, commit map)``."""
    out = shutil.copytree(pristine, tmp_path / "out", symlinks=True)
    commit_map = json.loads((out / "metadata/commit-map.json").read_text(encoding="utf-8"))
    return out, out / "metadata/scenario.graph.yml", commit_map


def _errors(out: Path, scenario: Path, *, commit_map: Path | None = None, graph_map: Path | None = None) -> list[tuple[str, str]]:
    result = verify_graph_generated_repo(out / "repo", scenario, commit_map, graph_map)
    return [(f.code, f.location) for f in result.findings if f.severity == "ERROR"]


# --- refs, HEAD, index and working tree -------------------------------------------------------

TAMPERING = {
    # the four operations of the issue's reproduction, one at a time
    "branch moved": (lambda repo, root: git(repo, "branch", "-f", "feature", root), [("GE642", "refs/heads/feature")]),
    "tag deleted": (lambda repo, root: git(repo, "tag", "-d", "v1"), [("GE641", "refs/tags/v1")]),
    "head detached": (lambda repo, root: git(repo, "checkout", "-q", "--detach"), [("GE644", "HEAD")]),
    "index emptied": (lambda repo, root: git(repo, "rm", "-q", "-r", "--cached", "."), [("GE645", "worktree")]),
    # and their neighbours
    "branch deleted": (lambda repo, root: git(repo, "branch", "-D", "feature"), [("GE641", "refs/heads/feature")]),
    "branch added": (lambda repo, root: git(repo, "branch", "extra", root), [("GE643", "refs/heads/extra")]),
    "tag added": (lambda repo, root: git(repo, "tag", "v2"), [("GE643", "refs/tags/v2")]),
    "tag moved": (lambda repo, root: git(repo, "tag", "-f", "v1", "HEAD"), [("GE642", "refs/tags/v1")]),
    "other ref added": (lambda repo, root: git(repo, "update-ref", "refs/remotes/origin/main", "HEAD"),
                        [("GE643", "refs/remotes/origin/main")]),
    "other branch checked out": (lambda repo, root: git(repo, "checkout", "-q", "feature"), [("GE644", "HEAD")]),
    "checked-out branch reset": (lambda repo, root: git(repo, "reset", "-q", "--hard", root), [("GE642", "refs/heads/main")]),
    "file edited": (lambda repo, root: (repo / "a.txt").write_text("edited\n", encoding="utf-8"), [("GE645", "worktree")]),
    "file staged": (lambda repo, root: ((repo / "a.txt").write_text("edited\n", encoding="utf-8"), git(repo, "add", "a.txt")),
                    [("GE645", "worktree")]),
    "untracked file": (lambda repo, root: (repo / "new.txt").write_text("new\n", encoding="utf-8"), [("GE645", "worktree")]),
}


@pytest.mark.parametrize("name", list(TAMPERING))
def test_verify_graph_reports_a_repository_changed_after_generation(generated, name):
    out, scenario, commit_map = generated
    tamper, expected = TAMPERING[name]
    tamper(out / "repo", commit_map["c0"]["hash"])
    assert _errors(out, scenario) == expected


def test_the_issue_reproduction_fails_verify_graph(generated):
    """All four operations together, through the CLI, with paths relative to the output."""
    out, _, commit_map = generated
    repo = out / "repo"
    git(repo, "checkout", "-q", "--detach")
    git(repo, "branch", "-f", "main", commit_map["c0"]["hash"])
    git(repo, "tag", "-d", "v1")
    git(repo, "rm", "-q", "-r", "--cached", ".")
    completed = subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "verify-graph", "repo", "--scenario", "metadata/scenario.graph.yml", "--json"],
        cwd=out, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    assert completed.returncode == 1, completed.stderr
    findings = json.loads(completed.stdout)["findings"]
    assert sorted(f["code"] for f in findings if f["severity"] == "ERROR") == ["GE641", "GE642", "GE644", "GE645"]


def test_a_fresh_output_verifies_with_no_error_and_verification_writes_nothing(generated):
    out, scenario, _ = generated
    repo = out / "repo"
    # A tracked file whose timestamp changed but whose content did not: plain
    # `git status` refreshes the index for it and rewrites .git/index.
    later = (repo / "a.txt").stat().st_mtime + 100
    os.utime(repo / "a.txt", (later, later))

    def snapshot() -> dict[str, tuple[int, bytes]]:
        return {str(p.relative_to(repo)): (p.stat().st_mtime_ns, p.read_bytes())
                for p in sorted(repo.rglob("*")) if p.is_file()}

    before = snapshot()
    assert _errors(out, scenario) == []
    assert snapshot() == before
    git(repo, "status", "--porcelain")      # the check above would have seen this write
    assert snapshot()[".git/index"] != before[".git/index"]


# --- where generation leaves HEAD -------------------------------------------------------------

HEAD_CASES = {
    # the last commit's branch survives: HEAD stays on it
    "last branch kept": ({"tags": [{"name": "v1", "commit": "c0"}]}, "feature"),
    # the last commit's branch is deleted: the default branch is checked out
    "last branch deleted": ({"delete_branches": ["feature"]}, "main"),
    # the default branch is deleted too: HEAD detaches at the last commit
    "every branch deleted": ({"delete_branches": ["feature", "main"]}, None),
}


@pytest.mark.parametrize("name", list(HEAD_CASES))
def test_head_is_expected_where_the_generator_leaves_it(tmp_path, name):
    lifecycle, branch = HEAD_CASES[name]
    data = _scenario([_commit("c0", [], [_write("a.txt")]),
                      _commit("c1", ["c0"], [_write("b.txt")]),
                      _commit("f1", ["c1"], [_write("f.txt")], branch="feature")], ref_lifecycle=lifecycle)
    out, scenario, commit_map = _generate(tmp_path, data)
    repo = out / "repo"
    if branch is None:
        assert git(repo, "rev-parse", "HEAD") == commit_map["f1"]["hash"]
        assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"
    else:
        assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == branch
    git(repo, "checkout", "-q", "--detach", commit_map["c0"]["hash"])
    assert _errors(out, scenario) == [("GE644", "HEAD")]


# --- commit dates over the whole commit map ---------------------------------------------------

def test_a_child_older_than_its_parent_on_a_deleted_branch_is_ge630(tmp_path):
    data = _scenario(
        [_commit("c0", [], [_write("a.txt")], date="2024-01-01T10:00:00Z"),
         _commit("f1", ["c0"], [_write("f.txt")], branch="feature", date="2024-01-10T10:00:00Z"),
         _commit("f2", ["f1"], [_write("g.txt")], branch="feature", date="2024-01-05T10:00:00Z"),  # before its parent
         _commit("c1", ["c0"], [_write("b.txt")], date="2024-01-20T10:00:00Z")],
        ref_lifecycle={"delete_branches": ["feature"]},
    )
    out, scenario, commit_map = _generate(tmp_path, data, verify=False)
    f1, f2 = commit_map["f1"]["hash"], commit_map["f2"]["hash"]
    assert f2 not in git(out / "repo", "log", "--all", "--format=%H").split()
    result = verify_graph_generated_repo(out / "repo", scenario)
    inversions = [f.message for f in result.findings if f.code == "GE630"]
    assert len(inversions) == 1 and f2[:8] in inversions[0] and f1[:8] in inversions[0]
    with pytest.raises(GraphGenerationError, match="failed verification"):
        generate_graph_repository(scenario, tmp_path / "verified", force=True)


# --- generated commits (SZZG-0114: c2 and c3 own 500 each) ------------------------------------

@pytest.fixture(scope="module")
def huge_history(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("szzg-0114") / "out"
    _, result = generate_graph_repository(HUGE_HISTORY, out, force=True)
    assert not result.has_errors(), result.to_dict()
    return out


def _with_commit_map(tmp_path: Path, out: Path, edit) -> Path:
    commit_map = json.loads((out / "metadata/commit-map.json").read_text(encoding="utf-8"))
    edit(commit_map)
    path = tmp_path / "commit-map.json"
    path.write_text(json.dumps(commit_map), encoding="utf-8")
    return path


def _swap_hash(cm: dict) -> None:
    cm["c2.g250"]["hash"] = cm["c2.g251"]["hash"]


def _unknown_hash(cm: dict) -> None:
    cm["c2.g250"]["hash"] = "0" * 40


def _other_author(cm: dict) -> None:
    cm["c3.g10"]["author"] = "Someone Else <someone@example.com>"


def _other_date(cm: dict) -> None:
    cm["c3.g10"]["committer_date"] = "2001-01-01T00:00:00Z"


def _dropped(cm: dict) -> None:
    del cm["c3.g20"]


def _shortened_list(cm: dict) -> None:
    cm["c2"]["generated_commits"] = cm["c2"]["generated_commits"][:-1]


GENERATED_CASES = {
    # a generated commit re-parented: g250 names g251's commit, whose parent is the real g250
    "hash of another commit": (_swap_hash, [("GE635", "commits[2]"), ("GE636", "commits[2]"), ("GE635", "commits[2]")]),
    "hash not in the repository": (_unknown_hash, [("GE634", "commits[2]"), ("GE635", "commits[2]")]),
    "author": (_other_author, [("GE636", "commits[3]")]),
    "committer date": (_other_date, [("GE636", "commits[3]")]),
    "missing from the commit map": (_dropped, [("GE629", "commits[3]")]),
    "owner's list": (_shortened_list, [("GE633", "commits[2]")]),
}


def test_the_generated_chain_of_szzg_0114_verifies(huge_history):
    assert _errors(huge_history, HUGE_HISTORY) == []


@pytest.mark.parametrize("name", list(GENERATED_CASES))
def test_a_generated_commit_that_disagrees_with_the_commit_map_is_an_error(tmp_path, huge_history, name):
    edit, expected = GENERATED_CASES[name]
    commit_map = _with_commit_map(tmp_path, huge_history, edit)
    assert _errors(huge_history, HUGE_HISTORY, commit_map=commit_map,
                   graph_map=huge_history / "metadata/graph-map.json") == expected


# --- graph-map ---------------------------------------------------------------------------------

def test_graph_map_and_commit_map_must_name_the_same_hash(tmp_path, generated):
    out, scenario, commit_map = generated
    graph_map = json.loads((out / "metadata/graph-map.json").read_text(encoding="utf-8"))
    graph_map["commits"]["c1"]["hash"] = commit_map["c0"]["hash"]
    edited = tmp_path / "graph-map.json"
    edited.write_text(json.dumps(graph_map), encoding="utf-8")
    assert _errors(out, scenario, graph_map=edited) == [("GE625", "commits[2]")]


def test_a_graph_map_without_refs_is_an_error(tmp_path, generated):
    out, scenario, _ = generated
    graph_map = json.loads((out / "metadata/graph-map.json").read_text(encoding="utf-8"))
    del graph_map["refs"]
    edited = tmp_path / "graph-map.json"
    edited.write_text(json.dumps(graph_map), encoding="utf-8")
    assert _errors(out, scenario, graph_map=edited) == [("GE640", "refs")]
