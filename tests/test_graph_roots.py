"""Only the first commit of a graph scenario is a root (issue #134).

A later commit declared with ``parents: []`` -- an intended second root, or a
commit whose ``parents`` key was misspelt -- was generated as a child of
whatever the generator had last checked out.  ``commit-map.json`` recorded no
parents, ``validate-graph --simulate`` passed it, and ``verify-graph`` did not
look, because it compared parent lists only when the scenario declared at
least one parent.  Such a commit is now GE048, and the verifier compares an
empty parent list too.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import szzbench.graph_generator as graph_generator
from support import git
from szzbench.findings import ValidationResult
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.graph_verifier import verify_graph_generated_repo

ROOT = Path(__file__).resolve().parents[1]


def _scenario() -> dict:
    def commit(cid, parents, operations, **extra):
        return {"id": cid, "branch": "main", "parents": parents, "message": f"Change {cid}", "role": "intermediate",
                "operations": operations, **extra}
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "Roots", "category": "fixture", "factors": ["single-bic"]},
        "repository": {"name": "roots", "default_branch": "main"},
        "graph": {"model": "commit_dag"},
        "commits": [
            commit("c0", [], [{"type": "write_file", "path": "a.txt", "content": "a\n"}]),
            commit("c1", ["c0"], [{"type": "replace", "path": "a.txt", "old": "a", "new": "b"}]),
            commit("c2", ["c1"], [{"type": "write_file", "path": "other.txt", "content": "x\n"}]),
            commit("c3", ["c2"], [{"type": "replace", "path": "other.txt", "old": "x", "new": "y"}]),
        ],
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c3", "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}},
    }


def _second_root(branch: str = "main") -> dict:
    data = _scenario()
    data["commits"][2].update(parents=[], branch=branch)
    return data


def _misspelt(key: str = "parent") -> dict:
    data = _scenario()
    data["commits"][2][key] = data["commits"][2].pop("parents")
    return data


def _findings(data: dict) -> list[tuple[str, str | None]]:
    return [(f.code, f.location) for f in validate_graph_static(data).findings if f.severity == "ERROR"]


def _write(tmp_path: Path, name: str, data: dict) -> Path:
    path = tmp_path / name / "SZZG-9900" / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


# --- validation ---------------------------------------------------------------

@pytest.mark.parametrize("branch", ["main", "orphan"])
def test_a_second_root_is_ge048(branch):
    assert _findings(_second_root(branch)) == [("GE048", "commits[2].parents")]


@pytest.mark.parametrize("key", ["parent", "Parents"])
def test_a_misspelt_parents_key_is_ge048_and_the_message_names_the_key(key):
    result = validate_graph_static(_misspelt(key))
    [finding] = [f for f in result.findings if f.severity == "ERROR"]
    assert (finding.code, finding.location) == ("GE048", "commits[2].parents")
    assert f"it has a '{key}' key, and the key is 'parents'" in finding.message


def test_the_first_commit_is_a_root_with_or_without_the_key():
    assert _findings(_scenario()) == []
    data = _scenario()
    del data["commits"][0]["parents"]
    assert _findings(data) == []


def test_parents_that_are_not_a_list_stay_ge036_only():
    data = _scenario()
    data["commits"][2]["parents"] = "c1"
    assert _findings(data) == [("GE036", "commits[2].parents")]


def test_validate_graph_simulate_reports_ge048_for_the_scenario_file(tmp_path):
    _, result = validate_graph_scenario_file(_write(tmp_path, "root", _second_root()), simulate=True)
    assert "GE048" in [f.code for f in result.findings]


def test_no_shipped_graph_scenario_has_a_second_root():
    for path in sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "GE048" not in [code for code, _ in _findings(data)], path


# --- generation ---------------------------------------------------------------

@pytest.mark.parametrize("data", [_second_root(), _second_root("orphan"), _misspelt()], ids=["root", "orphan", "misspelt"])
def test_generate_graph_refuses_a_second_root(tmp_path, data):
    with pytest.raises(GraphGenerationError, match="validation failed"):
        generate_graph_repository(_write(tmp_path, "s", data), tmp_path / "out", force=True)


def test_the_generator_refuses_it_even_when_validation_is_bypassed(tmp_path, monkeypatch):
    """The generator does not rely on the validator: it used to commit the root on top of HEAD."""
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))
    with pytest.raises(GraphGenerationError, match=r"Commit 'c2' declares no parents.*\(GE048\)"):
        generate_graph_repository(_write(tmp_path, "s", _second_root()), tmp_path / "out", force=True, verify=False)


# --- verification -------------------------------------------------------------

@pytest.fixture
def generated(tmp_path) -> Path:
    out = tmp_path / "out"
    _, verify = generate_graph_repository(_write(tmp_path, "s", _scenario()), out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    return out


def test_verify_graph_reports_a_commit_declared_as_a_root_that_has_a_parent(tmp_path, generated):
    out = generated
    declared_root = _write(tmp_path, "declared", _second_root())
    result = verify_graph_generated_repo(out / "repo", declared_root, out / "metadata/commit-map.json",
                                         out / "metadata/graph-map.json")
    assert ("GE627", "commits[2].parents") in [(f.code, f.location) for f in result.findings]


def test_verify_graph_accepts_the_first_commit_as_a_root(tmp_path, generated):
    out = generated
    commit_map = json.loads((out / "metadata/commit-map.json").read_text(encoding="utf-8"))
    assert git(out / "repo", "rev-list", "--parents", "-n", "1", commit_map["c0"]["hash"]) == commit_map["c0"]["hash"]
    scenario = _write(tmp_path, "same", _scenario())
    result = verify_graph_generated_repo(out / "repo", scenario, out / "metadata/commit-map.json",
                                         out / "metadata/graph-map.json")
    assert not result.has_errors(), result.to_dict()
