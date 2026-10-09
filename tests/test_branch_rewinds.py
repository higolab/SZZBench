"""A first parent off the branch that leaves commits unreachable is a warning (issue #174).

A branch's tip is the last commit declared on it.  When a commit's branch
already exists and its first parent is not that tip, the generator checks the
branch out and resets it to the parent.  SZZG-0052's and SZZG-0128's ``c4``
rely on that as a fast-forward.  When the tip is not an ancestor of the
parent, the reset left the old tip unreachable from every ref, and nothing
said so: ``validate-graph`` (``--lint`` included) passed, ``generation.log``
did not mention the reset, and ``verify-graph`` checks commits by hash.
Validation now warns (GW151) and names the commits no ref reaches once
generation has finished, and the log records every reset.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from support import git, scenario_file
from szzbench.cli import main
from szzbench.findings import ValidationResult
from szzbench.graph_generator import generate_graph_repository
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static

ROOT = Path(__file__).resolve().parents[1]


def _commit(cid, parents, operations, branch="main", **extra):
    return {"id": cid, "branch": branch, "parents": parents, "message": f"Change {cid}", "role": "intermediate",
            "operations": operations, **extra}


def _write(path, content):
    return {"type": "write_file", "path": path, "content": content}


def _replace(path, old, new):
    return {"type": "replace", "path": path, "old": old, "new": new}


def _scenario(commits: list[dict], **ref_lifecycle) -> dict:
    graph: dict = {"model": "commit_dag"}
    if ref_lifecycle:
        graph["ref_lifecycle"] = ref_lifecycle
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
        "repository": {"name": "probe", "default_branch": "main"},
        "graph": graph,
        "commits": commits,
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }


def _rewind(**ref_lifecycle) -> dict:
    """The issue's reproduction: ``c2`` is on ``main``, whose tip is ``c1``, and its first parent is ``f1``."""
    return _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("c1", ["c0"], [_replace("a.txt", "a", "c1")]),
        _commit("f1", ["c0"], [_write("f.txt", "f\n")], branch="feature"),
        _commit("c2", ["f1"], [_replace("f.txt", "f", "g")]),
    ], **ref_lifecycle)


def _path(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "scenario" / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _gw151(result: ValidationResult) -> list[tuple[str | None, str]]:
    assert {f.severity for f in result.findings if f.code == "GW151"} <= {"WARNING"}
    return [(f.location, f.message) for f in result.findings if f.code == "GW151"]


def _named(data: dict) -> list[tuple[str | None, list[str]]]:
    """Where GW151 is reported, and the commits it says no ref reaches."""
    named = []
    for location, message in _gw151(validate_graph_static(data)):
        unreachable = message.split("no ref reaches ", 1)[1].split(", so git log --all", 1)[0]
        named.append((location, [name.strip("'") for name in unreachable.split(", ")]))
    return named


# --- validation ---------------------------------------------------------------

@pytest.mark.parametrize("simulate, lint", [(False, False), (True, False), (True, True)],
                         ids=["static", "simulate", "simulate-lint"])
def test_a_reset_that_leaves_the_old_tip_unreachable_is_gw151(tmp_path, simulate, lint):
    _, result = validate_graph_scenario_file(_path(tmp_path, _rewind()), simulate=simulate, lint=lint)
    assert not result.has_errors()
    [(location, message)] = _gw151(result)
    assert location == "commits[3].parents"
    assert message.startswith("Commit 'c2' resets branch 'main' from its tip 'c1' to its first parent 'f1', "
                              "which is not a fast-forward: after generation no ref reaches 'c1', "
                              "so git log --all does not show it.")
    assert [f.severity for f in result.findings if f.code == "GW151"] == ["WARNING"]


def test_validate_graph_strict_fails_on_it(tmp_path, capsys):
    path = _path(tmp_path, _rewind())
    assert main(["validate-graph", "--simulate", str(path)]) == 0
    assert main(["validate-graph", "--simulate", "--strict", str(path)]) == 1
    assert "GW151" in capsys.readouterr().out


def test_a_fast_forward_is_not_reported():
    data = _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("c1", ["c0"], [_replace("a.txt", "a", "c1")]),
        _commit("f1", ["c1"], [_write("f.txt", "f\n")], branch="feature"),
        _commit("c2", ["f1"], [_replace("f.txt", "f", "g")]),      # main: c1 -> f1, a descendant of c1
    ])
    assert validate_graph_static(data).findings == []


def _two_branch_rewrite(rewrite: dict[str, dict]) -> dict:
    """``feature`` (f1, f2) is rewritten on itself: r1 and r2 on top of ``main``'s c1."""
    return _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("f1", ["c0"], [_write("f.txt", "1\n")], branch="feature"),
        _commit("f2", ["f1"], [_replace("f.txt", "1", "2")], branch="feature"),
        _commit("c1", ["c0"], [_replace("a.txt", "a", "b")]),
        _commit("r1", ["c1"], [_write("f.txt", "1\n")], branch="feature", **rewrite.get("r1", {})),
        _commit("r2", ["r1"], [_replace("f.txt", "1", "2")], branch="feature", **rewrite.get("r2", {})),
    ])


def _squashed(squashes: list[str] | None) -> dict:
    """``feature`` (f1, f2) is squashed on itself into s1."""
    return _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("f1", ["c0"], [_write("f.txt", "1\n")], branch="feature"),
        _commit("f2", ["f1"], [_replace("f.txt", "1", "2")], branch="feature"),
        _commit("s1", ["c0"], [_write("f.txt", "2\n")], branch="feature",
                **({"squashes": squashes} if squashes is not None else {})),
    ])


def _deleted(delete: bool) -> dict:
    """``feature`` is reset from f1 to c0 by f2; the lifecycle may then delete ``feature``."""
    return _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("f1", ["c0"], [_write("f.txt", "1\n")], branch="feature"),
        _commit("f2", ["c0"], [_write("g.txt", "2\n")], branch="feature"),
        _commit("c1", ["c0"], [_replace("a.txt", "a", "b")]),
    ], **({"delete_branches": ["feature"]} if delete else {}))


def _kept_by_a_branch(keep: bool) -> dict:
    data = _rewind()
    if keep:
        data["commits"].insert(2, _commit("k1", ["c1"], [_write("k.txt", "k\n")], branch="keep"))
    return data


def _merged_back(merge: bool) -> dict:
    data = _rewind()
    if merge:
        data["commits"][3].update(parents=["f1", "c1"], role="merge", operations=[])
    return data


# Each case without the declaration that keeps it silent, and with it.
EXEMPTIONS = {
    "tag": (_rewind(), _rewind(tags=[{"name": "keep", "commit": "c1"}]),
            [("commits[3].parents", ["c1"])]),
    "another-branch": (_kept_by_a_branch(False), _kept_by_a_branch(True),
                       [("commits[3].parents", ["c1"])]),
    "merged-back": (_merged_back(False), _merged_back(True),
                    [("commits[3].parents", ["c1"])]),
    "deleted-branch": (_deleted(False), _deleted(True),
                       [("commits[2].parents", ["f1"])]),
    "rebase_of": (_two_branch_rewrite({}), _two_branch_rewrite({"r1": {"rebase_of": "f1"}, "r2": {"rebase_of": "f2"}}),
                  [("commits[4].parents", ["f1", "f2"])]),
    "rebase_of-list": (_two_branch_rewrite({}), _two_branch_rewrite({"r1": {"rebase_of": ["f1", "f2"]}}),
                       [("commits[4].parents", ["f1", "f2"])]),
    "squashes": (_squashed(None), _squashed(["f1", "f2"]),
                 [("commits[3].parents", ["f1", "f2"])]),
}


@pytest.mark.parametrize("case", sorted(EXEMPTIONS))
def test_a_commit_the_scenario_keeps_or_gives_up_on_purpose_is_not_reported(case):
    without, with_it, reported = EXEMPTIONS[case]
    assert _named(without) == reported
    assert _gw151(validate_graph_static(with_it)) == []
    assert not validate_graph_static(with_it).has_errors()


def test_only_the_commits_a_rewrite_does_not_name_are_reported():
    data = _two_branch_rewrite({"r1": {"rebase_of": "f1"}})
    assert _named(data) == [("commits[4].parents", ["f2"])]


def test_a_commit_two_resets_leave_behind_is_named_at_the_later_one():
    """main leaves c1 behind, but topic still reaches it until topic is reset too."""
    data = _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("c1", ["c0"], [_replace("a.txt", "a", "b")]),
        _commit("t1", ["c1"], [_write("t.txt", "t\n")], branch="topic"),
        _commit("f1", ["c0"], [_write("f.txt", "f\n")], branch="feature"),
        _commit("c2", ["f1"], [_replace("f.txt", "f", "g")]),                   # main: c1 -> f1
        _commit("t2", ["f1"], [_write("u.txt", "u\n")], branch="topic"),         # topic: t1 -> f1
    ])
    assert _named(data) == [("commits[5].parents", ["c1", "t1"])]


def test_malformed_input_does_not_reach_the_history_model(tmp_path):
    """reachable_commit_ids raises on these; the generator refuses them, so there is nothing to report."""
    assert _gw151(validate_graph_static(_rewind(tags=5))) == []
    assert _gw151(validate_graph_static(_rewind(delete_branches="feature"))) == []
    data = _rewind()
    data["commits"][1]["operations"] = 5
    result = validate_graph_static(data)
    assert [f.code for f in result.findings if f.severity == "ERROR"] == ["GE044"]
    assert _gw151(result) == []
    # passes the static checks; planned_generated_commits raises OverflowError on it
    data = _rewind()
    data["commits"][1]["operations"] = [{"type": "commit_generator", "generator": "churn", "count": float("inf")}]
    assert validate_graph_static(data).findings == []
    _, result = validate_graph_scenario_file(_path(tmp_path, data), simulate=True)
    assert [(f.code, f.location) for f in result.findings] == [("GE201", "commits[1].operations[0]")]


def test_no_shipped_graph_scenario_leaves_a_commit_behind():
    paths = sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml"))
    assert len(paths) >= 146
    rewrites = 0
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        rewrites += sum(1 for commit in data["commits"] if "rebase_of" in commit or "squashes" in commit)
        assert _gw151(validate_graph_static(data)) == [], path
    assert rewrites > 0   # the rewrite scenarios are among those checked


# --- generation ---------------------------------------------------------------

def test_the_warning_is_true_and_the_log_records_the_reset(tmp_path):
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(_path(tmp_path, _rewind()), out)
    assert verify is not None and not verify.has_errors()
    c1, f1 = commit_map["c1"]["hash"], commit_map["f1"]["hash"]
    assert git(out / "repo", "for-each-ref", "--contains", c1) == ""        # no ref reaches c1
    log = (out / "metadata" / "generation.log").read_text(encoding="utf-8").splitlines()
    assert [line for line in log if line.startswith("Reset branch ")] == [
        f"Reset branch main from c1 ({c1}) to f1 ({f1}), the first parent of c2 "
        "(fast-forward: no; the branch no longer contains 1 commit(s))"
    ]
    recorded = json.loads((out / "metadata" / "validation-result.json").read_text(encoding="utf-8"))
    assert [f["code"] for f in recorded["findings"]] == ["GW151"]


def test_the_log_counts_the_generated_commits_left_behind(tmp_path):
    data = _rewind()
    data["commits"][1]["operations"] = [{"type": "commit_generator", "generator": "churn", "count": 2, "files": 1,
                                         "path": "gen"}]
    assert _named(data) == [("commits[3].parents", ["c1"])]                 # the owner, not c1.g1 / c1.g2
    out = tmp_path / "out"
    generate_graph_repository(_path(tmp_path, data), out)
    log = (out / "metadata" / "generation.log").read_text(encoding="utf-8")
    assert "the first parent of c2 (fast-forward: no; the branch no longer contains 3 commit(s))" in log


@pytest.mark.parametrize("sid, old_tip, first_parent", [("SZZG-0052", "c0", "a3"), ("SZZG-0128", "c0", "c2")])
def test_the_shipped_fast_forwards_are_logged_and_not_reported(tmp_path, sid, old_tip, first_parent):
    _, result = validate_graph_scenario_file(scenario_file(sid))
    assert _gw151(result) == []
    out = tmp_path / sid
    commit_map, _ = generate_graph_repository(scenario_file(sid), out)
    log = (out / "metadata" / "generation.log").read_text(encoding="utf-8").splitlines()
    assert [line for line in log if line.startswith("Reset branch ")] == [
        f"Reset branch main from {old_tip} ({commit_map[old_tip]['hash']}) to {first_parent} "
        f"({commit_map[first_parent]['hash']}), the first parent of c4 (fast-forward: yes)"
    ]
