"""The in-memory replay of ``validate-graph --simulate`` and what it does not model.

Issue #183: since issue #94 ``validate-graph --simulate`` generates every
scenario with a commit Git computes (a merge, a real revert or cherry-pick,
``apply_patch_from``, ``apply_squash``, a ``resolution``) with Git, so the
replay's file-level model of merges and patches was reached by no command.
Called directly, it still answered for a merge with an approximation of its
own (``GE200 ... merge conflict for path: a.txt`` where the command says
GE203).  The model is gone, and such a commit is refused instead.
"""
from __future__ import annotations

import pytest

from szzbench.graph_simulator import SimFile, simulate_graph_scenario, simulated_snapshots


def _write_file(path: str, content: str, **keys) -> dict:
    return {"type": "write_file", "path": path, "content": content, **keys}


def _replace(path: str, old: str, new: str, **keys) -> dict:
    return {"type": "replace", "path": path, "old": old, "new": new, **keys}


def _commit(cid: str, parents: list[str], *operations: dict, branch: str = "main") -> dict:
    commit = {"id": cid, "branch": branch, "parents": parents, "message": f"Update the sources ({cid})",
              "role": "merge" if len(parents) > 1 else "intermediate"}
    if operations:
        commit["operations"] = list(operations)
    return commit


def _scenario(*commits: dict, bug: dict | None = None) -> dict:
    return {"schema_version": "graph-1.0",
            "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
            "repository": {"name": "probe", "default_branch": "main"}, "graph": {"model": "commit_dag"},
            "commits": list(commits),
            "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                      "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}], **(bug or {})}],
            "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}}


def _findings(result) -> list[tuple[str, str]]:
    return [(f.code, f.location) for f in result.findings]


# --- issue #183: no file-level model of what Git computes ----------------------------------

#: The issue's two scenarios: a merge that conflicts, and an apply_patch_from of a merge.
CONFLICT = _scenario(_commit("c0", [], _write_file("a.txt", "a\n")), _commit("c1", ["c0"], _replace("a.txt", "a", "left")),
                     _commit("f1", ["c0"], _replace("a.txt", "a", "right"), branch="feature"),
                     _commit("m1", ["c1", "f1"]))
PATCH = _scenario(_commit("c0", [], _write_file("a.txt", "a\n")),
                  _commit("f1", ["c0"], _write_file("f.txt", "f\n"), branch="feature"), _commit("m1", ["c0", "f1"]),
                  _commit("rel", ["c0"], _write_file("r.txt", "r\n"), branch="release"),
                  _commit("a1", ["rel"], {"type": "apply_patch_from", "commit": "m1", "mainline": 1}, branch="release"))


@pytest.mark.parametrize("data, refused", [
    (CONFLICT, [("GE200", "commits[3]")]),
    (PATCH, [("GE200", "commits[2]"), ("GE200", "commits[4]")]),
], ids=["conflicting-merge", "patch-of-a-merge"])
def test_the_replay_refuses_a_commit_git_computes_instead_of_approximating_it(data, refused):
    result = simulate_graph_scenario(data)
    assert _findings(result) == refused
    assert all("validate-graph --simulate generates such a scenario with Git" in f.message for f in result.findings)


def test_the_snapshots_of_a_commit_git_computes_must_be_given():
    with pytest.raises(ValueError, match="does not model commit 'm1', whose content Git computes \\(merge\\)"):
        simulated_snapshots(CONFLICT)
    merged = {"a.txt": SimFile("resolved\n")}
    assert simulated_snapshots(CONFLICT, given={"m1": merged})["m1"] == merged
