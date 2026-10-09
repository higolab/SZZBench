"""A merge parent that Git would not record is an error (issue #173).

``git merge`` records each head once and drops a head that is already
reachable from another one.  A commit that listed the same parent twice, or an
extra parent that was already an ancestor of another parent, passed
``validate-graph`` and ``validate-graph --simulate`` -- the simulation
generated it without verification -- and then failed ``generate-graph`` with
a parent mismatch (GE627/GE628) that named hashes, or with "commit would be
empty".  Validation now reports such a parent list as GE049, and the
generator names the dropped parent when ``git merge`` leaves it out.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import szzbench.graph_generator as graph_generator
from szzbench.findings import ValidationResult
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static

ROOT = Path(__file__).resolve().parents[1]


def _commit(cid, parents, operations=None, branch="main", **extra):
    commit = {"id": cid, "branch": branch, "parents": parents, "message": f"{cid}: msg",
              "role": "merge" if len(parents) > 1 else "intermediate", **extra}
    if operations is not None:
        commit["operations"] = operations
    return commit


def _write(path, content):
    return {"type": "write_file", "path": path, "content": content}


def _scenario(commits: list[dict]) -> dict:
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
        "repository": {"name": "probe", "default_branch": "main"},
        "graph": {"model": "commit_dag"},
        "commits": commits,
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "m1", "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }


# The two scenarios of the issue's reproduction, the `[c0, c0]` variant, and an
# octopus whose extra parent is an ancestor of a *later* parent: Git drops that
# one too.
CASES = {
    "duplicate-parent": _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("f1", ["c0"], [_write("f.txt", "f\n")], branch="feature"),
        _commit("m1", ["c0", "f1", "f1"]),
    ]),
    "ancestor-parent": _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("c1", ["c0"], [{"type": "replace", "path": "a.txt", "old": "a", "new": "b"}]),
        _commit("m1", ["c1", "c0"], allow_empty=True),
    ]),
    "self-parent": _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("m1", ["c0", "c0"]),
    ]),
    "octopus-ancestor": _scenario([
        _commit("c0", [], [_write("a.txt", "a\n")]),
        _commit("f1", ["c0"], [_write("f.txt", "1\n")], branch="feature"),
        _commit("f2", ["f1"], [_write("f.txt", "2\n")], branch="feature"),
        _commit("g1", ["c0"], [_write("g.txt", "g\n")]),
        _commit("m1", ["g1", "f1", "f2"]),
    ]),
}
EXPECTED = {   # (location, the words the GE049 message uses, the generator's message)
    "duplicate-parent": ("commits[2].parents", "lists parent 'f1' twice",
                         "merge of c0, f1, f1 for commit 'm1' recorded 2 parents, not 3: f1 is listed twice (GE049)."),
    "ancestor-parent": ("commits[2].parents", "lists parent 'c0', which is already an ancestor of its parent 'c1'",
                        "merge of c1, c0 for commit 'm1' recorded no second parent: c0 is already merged (GE049)."),
    "self-parent": ("commits[1].parents", "lists parent 'c0' twice",
                    "merge of c0, c0 for commit 'm1' recorded no second parent: c0 is listed twice (GE049)."),
    "octopus-ancestor": ("commits[4].parents", "lists parent 'f1', which is already an ancestor of its parent 'f2'",
                         "merge of g1, f1, f2 for commit 'm1' recorded 2 parents, not 3: f1 is already merged (GE049)."),
}


def _path(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "scenario" / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _errors(result: ValidationResult) -> list[tuple[str, str | None]]:
    return [(f.code, f.location) for f in result.findings if f.severity == "ERROR"]


# --- validation ---------------------------------------------------------------

@pytest.mark.parametrize("simulate", [False, True], ids=["static", "simulate"])
@pytest.mark.parametrize("case", sorted(CASES))
def test_a_parent_git_would_not_record_is_ge049(tmp_path, case, simulate):
    location, words, _ = EXPECTED[case]
    _, result = validate_graph_scenario_file(_path(tmp_path, CASES[case]), simulate=simulate)
    assert _errors(result) == [("GE049", location)]
    [finding] = [f for f in result.findings if f.code == "GE049"]
    assert words in finding.message and "would not record this merge as declared" in finding.message


@pytest.mark.parametrize("parents", [["g1", "f2"], ["c0", "f2", "g1"], ["f2", "g1"]],
                         ids=["merge", "octopus-from-the-common-ancestor", "branch-tip-first"])
def test_merges_git_records_as_declared_are_not_flagged(parents):
    """The first parent may be an ancestor of an extra parent: the generator merges with --no-ff."""
    data = CASES["octopus-ancestor"]
    data = dict(data, commits=[*data["commits"][:4], _commit("m1", parents)])
    assert _errors(validate_graph_static(data)) == []


def test_no_shipped_graph_scenario_has_a_duplicate_or_redundant_parent():
    paths = sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml"))
    assert len(paths) >= 146
    merges = 0
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        merges += sum(1 for commit in data["commits"] if len(commit.get("parents") or []) >= 2)
        assert "GE049" not in [code for code, _ in _errors(validate_graph_static(data))], path
    assert merges > 0   # the check has merges to look at


# --- generation ---------------------------------------------------------------

@pytest.mark.parametrize("case", sorted(CASES))
def test_generate_graph_refuses_it_at_validation(tmp_path, case):
    with pytest.raises(GraphGenerationError, match="validation failed"):
        generate_graph_repository(_path(tmp_path, CASES[case]), tmp_path / "out", force=True)


@pytest.mark.parametrize("case", sorted(CASES))
def test_the_generator_names_the_parent_git_dropped(tmp_path, monkeypatch, case):
    """With validation bypassed it stopped at "commit would be empty" or at verification."""
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))
    with pytest.raises(GraphGenerationError) as excinfo:
        generate_graph_repository(_path(tmp_path, CASES[case]), tmp_path / "out", force=True)
    assert str(excinfo.value) == EXPECTED[case][2]
    assert not (tmp_path / "out" / "metadata" / "verify-result.json").exists()
