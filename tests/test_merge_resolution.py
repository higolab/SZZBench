"""What ``resolution`` does with an octopus merge and with a path that did not conflict.

Issue #177: the docs and the generator said that Git's octopus strategy does
not resolve conflicts, so an octopus with a conflict always failed.  Git 2.39
and 2.50 both stop at the first conflict instead: a conflict with the last
parent stays in the index and ``resolution`` resolves it, while a conflict
with an earlier parent makes Git give up, leaving nothing to resolve, which
the generator reported as a failure "without reporting conflicts".

Issue #182: every ``resolution`` entry was written into the commit, also one
for a path Git had merged cleanly, so the merge carried a change the scenario
did not declare and ``resolved_conflicts`` did not list.  Such an entry is now
a generation error, the mirror of the check for a conflicted path without one.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from support import git_stdout


def _commit(cid, parents, operations=None, branch="main", **extra):
    commit = {"id": cid, "branch": branch, "parents": parents, "message": f"{cid}: msg",
              "role": "merge" if len(parents) > 1 else "intermediate", **extra}
    if operations is not None:
        commit["operations"] = operations
    return commit


def _write(path, content):
    return {"type": "write_file", "path": path, "content": content}


def _replace(path, old, new):
    return {"type": "replace", "path": path, "old": old, "new": new}


def _path(tmp_path: Path, commits: list[dict]) -> Path:
    data = {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
        "repository": {"name": "probe", "default_branch": "main"},
        "graph": {"model": "commit_dag"},
        "commits": commits,
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "m1", "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }
    path = tmp_path / "scenario" / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


C0 = _commit("c0", [], [_write("a.txt", "a\n"), _write("b.txt", "b\n")])


def test_a_conflict_with_the_last_parent_of_an_octopus_is_resolved(tmp_path):
    """The scenario of issue #177: f2, the last parent, conflicts with f1 in a.txt."""
    scenario = _path(tmp_path, [
        C0,
        _commit("f1", ["c0"], [_replace("a.txt", "a", "f1")], branch="f1"),
        _commit("f2", ["c0"], [_replace("a.txt", "a", "f2")], branch="f2"),
        _commit("m1", ["c0", "f1", "f2"], resolution={"a.txt": "resolved\n"}),
    ])
    commit_map, verify = generate_graph_repository(scenario, tmp_path / "out", force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = tmp_path / "out" / "repo"
    m1 = commit_map["m1"]["hash"]
    assert git_stdout(repo, "log", "-1", "--format=%P", m1).split() == [
        commit_map[cid]["hash"] for cid in ("c0", "f1", "f2")]
    assert git_stdout(repo, "show", f"{m1}:a.txt") == "resolved\n"
    assert commit_map["m1"]["resolved_conflicts"] == ["a.txt"]


def test_a_conflict_before_the_last_parent_stops_generation_and_says_why(tmp_path):
    """f1 and f2 conflict in a.txt, and f3 is still to be merged: Git gives up, whatever resolution holds."""
    scenario = _path(tmp_path, [
        C0,
        _commit("f1", ["c0"], [_replace("a.txt", "a", "f1")], branch="f1"),
        _commit("f2", ["c0"], [_replace("a.txt", "a", "f2")], branch="f2"),
        _commit("f3", ["c0"], [_replace("b.txt", "b", "f3")], branch="f3"),
        _commit("m1", ["c0", "f1", "f2", "f3"], resolution={"a.txt": "resolved\n"}),
    ])
    with pytest.raises(GraphGenerationError) as excinfo:
        generate_graph_repository(scenario, tmp_path / "out", force=True)
    message = str(excinfo.value)
    assert message.startswith("Octopus merge of parents ['f1', 'f2', 'f3'] failed for commit 'm1' "
                              "and left no conflict to resolve:"), message
    assert "gives up at a conflict with any parent but the last ('f3')" in message
    assert "content conflict in a.txt" in message   # Git's own words are kept


def test_a_resolution_entry_for_a_path_without_conflict_is_refused(tmp_path):
    """The scenario of issue #182: a.txt conflicts, b.txt does not."""
    scenario = _path(tmp_path, [
        C0,
        _commit("c1", ["c0"], [_replace("a.txt", "a", "left")]),
        _commit("f1", ["c0"], [_replace("a.txt", "a", "right")], branch="feature"),
        _commit("m1", ["c1", "f1"], resolution={"a.txt": "resolved\n", "b.txt": "sneaky\n"}),
    ])
    with pytest.raises(GraphGenerationError) as excinfo:
        generate_graph_repository(scenario, tmp_path / "out", force=True)
    assert str(excinfo.value) == (
        "resolution of commit 'm1' names ['b.txt'], which Git did not report as conflicted "
        "(conflicted: ['a.txt']); a change to a path without a conflict belongs in 'operations'.")
