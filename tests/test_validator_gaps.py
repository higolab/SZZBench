"""Three gaps in the validators: the graph commands on a classic scenario (issue #155), the
index checks (issue #158), and graph commit options generation needs a source for (issue #179).

* #155, the mirror of #119's E003: ``validate-graph`` on a classic scenario reported GE001
  and went on with the graph checks (GE013, GW014, GE048, GW120), ``generate-graph`` said
  "Run 'szzbench validate-graph'", and ``verify-graph`` compared the repository with a graph
  the scenario does not have.  None named the classic command.  Each now stops with GE003.
* #158: an empty or missing ``index.yml`` was reported in ``load_yaml``'s words for a
  scenario file ("The root of scenario.yml ..."), a string ``scenario_count`` as
  ``IE010: scenario_count is 146, but the index lists 146 entries.``, and nothing looked at
  an entry's ``readme`` or at the order of the entries.
* #179: ``inherit_message`` / ``inherit_author_date`` without a single source commit (a
  ``rebase_of`` list included), ``cherry_pick_trailer`` without a source, and a default
  branch no commit is on passed ``validate-graph``; generation then stopped on the first
  three, with a false message for the ``rebase_of`` list, and left the default branch unborn.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from support import scenario_file
from szzbench.generator import generate_repository
from szzbench.graph_validator import validate_graph_scenario_file
from szzbench.graph_verifier import verify_graph_generated_repo
from szzbench.scenario_builder import NewScenarioError, create_new_scenario
from szzbench.validator import validate_index_file

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = scenario_file("SZZ-0005")


def _szzbench(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=ROOT, text=True, capture_output=True)


def _codes(result) -> list[str]:
    return [finding.code for finding in result.findings]


# --- #155: a classic scenario given to a graph command -------------------------------------

def test_validate_graph_stops_at_ge003_on_a_classic_scenario():
    completed = _szzbench("validate-graph", "--simulate", "--lint", "--json", "scenarios/SZZ-0005/scenario.yml")
    assert completed.returncode == 1, completed.stdout + completed.stderr
    findings = json.loads(completed.stdout)["findings"]
    assert [f["code"] for f in findings] == ["GE003"]
    assert "is a classic scenario (its schema_version is '1.0')" in findings[0]["message"]
    assert "Run `szzbench validate` instead." in findings[0]["message"]


def test_generate_graph_refuses_a_classic_scenario_and_writes_nothing(tmp_path):
    out = tmp_path / "out"
    completed = _szzbench("generate-graph", str(CLASSIC), "--out", str(out))
    assert completed.returncode == 1
    assert "GE003" in completed.stderr and "Run `szzbench generate` instead." in completed.stderr, completed.stderr
    assert "Traceback" not in completed.stderr
    assert not out.exists()


def test_verify_graph_refuses_a_classic_scenario_on_its_own_repository(tmp_path):
    generate_repository(CLASSIC, tmp_path / "out")
    result = verify_graph_generated_repo(tmp_path / "out" / "repo", CLASSIC)
    assert _codes(result) == ["GE003"]
    assert "Run `szzbench verify` instead." in result.findings[0].message


@pytest.mark.parametrize("name, schema_version", [
    ("scenario.graph.yml", "1.0"),       # a graph scenario's own file name: a wrong version, not a classic scenario
    ("probe.yml", None),                 # no schema_version, and no name to go by
    ("scenario.yml", 1.0),               # not a string
])
def test_a_file_that_is_not_recognisably_classic_keeps_ge001_and_the_graph_checks(tmp_path, name, schema_version):
    data = yaml.safe_load(CLASSIC.read_text(encoding="utf-8"))
    if schema_version is None:
        del data["schema_version"]
    else:
        data["schema_version"] = schema_version
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _, result = validate_graph_scenario_file(path)
    assert "GE003" not in _codes(result)
    assert {"GE001", "GE013"} <= set(_codes(result)), _codes(result)


# --- #158: validate-index and the builders' index reading ----------------------------------

def _index_root(tmp_path: Path, entries: list[dict], *, count=None) -> Path:
    """advanced-scenarios/ with a scenario and a README for each entry, and the index."""
    root = tmp_path / "advanced-scenarios"
    for entry in entries:
        (root / entry["id"]).mkdir(parents=True)
        (root / entry["id"] / "scenario.graph.yml").write_text(
            yaml.safe_dump({"meta": {"id": entry["id"], "title": entry["title"]}}), encoding="utf-8")
        (root / entry["id"] / "README.md").write_text("# README\n", encoding="utf-8")
    index = {"scenario_count": len(entries) if count is None else count, "scenarios": entries}
    (root / "index.yml").write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")
    return root


def _entry(sid: str, readme: str | None = None) -> dict:
    return {"id": sid, "title": sid, "path": f"advanced-scenarios/{sid}/scenario.graph.yml",
            "readme": readme or f"advanced-scenarios/{sid}/README.md"}


def test_an_empty_or_missing_index_is_named_in_the_message(tmp_path):
    root = tmp_path / "scenarios"
    root.mkdir()
    result = validate_index_file(root / "index.yml", root, "scenario.yml")
    assert [(f.code, f.message) for f in result.findings] == [("IE001", "Cannot load index: index.yml does not exist.")]
    (root / "index.yml").write_text("", encoding="utf-8")
    result = validate_index_file(root / "index.yml", root, "scenario.yml")
    assert [(f.code, f.message) for f in result.findings] == [("IE001", "Cannot load index: index.yml is empty.")]
    with pytest.raises(NewScenarioError, match=r"index\.yml: index\.yml is empty\.$"):
        create_new_scenario(title="Probe", category="Basic semantic line changes", root=root)
    assert sorted(p.name for p in root.iterdir()) == ["index.yml"]


def test_a_string_scenario_count_is_a_type_error_not_a_count_mismatch(tmp_path):
    root = _index_root(tmp_path, [_entry("SZZG-0001")], count="1")
    result = validate_index_file(root / "index.yml", root, "scenario.graph.yml")
    assert [(f.code, f.message) for f in result.findings] == [
        ("IE011", "scenario_count must be an integer, not str '1'.")]


def test_a_dangling_readme_is_an_error_and_entries_out_of_id_order_a_warning(tmp_path):
    root = _index_root(tmp_path, [_entry("SZZG-0002", readme="advanced-scenarios/SZZG-0002/NO-SUCH-README.md"),
                                  _entry("SZZG-0001")])
    result = validate_index_file(root / "index.yml", root, "scenario.graph.yml")
    prefix = (root / "index.yml").as_posix()
    assert [(f.severity, f.code, f.location) for f in result.findings] == [
        ("ERROR", "IE024", f"{prefix}:scenarios[0].readme"),
        ("WARNING", "IW048", f"{prefix}:scenarios[1].id"),
    ]
    assert "'SZZG-0001' comes after 'SZZG-0002'" in result.findings[1].message


def test_a_readme_that_cannot_be_checked_is_ie024_not_a_traceback(tmp_path, monkeypatch):
    """On Python 3.10-3.13 ``Path.is_file`` raises for a path inside a directory without search
    permission (3.14 returns False), and validate-index ended in a traceback (PR #261 review).  The
    error is raised here on every version, so that the test does not depend on the runtime or on
    file permissions, which a root container ignores."""
    root = _index_root(tmp_path, [_entry("SZZG-0001", readme="locked/README.md")])
    real_is_file = Path.is_file

    def is_file(self):
        if "locked" in self.parts:
            raise PermissionError(13, "Permission denied", str(self))
        return real_is_file(self)

    monkeypatch.setattr(Path, "is_file", is_file)
    result = validate_index_file(root / "index.yml", root, "scenario.graph.yml")
    assert [(f.code, f.location) for f in result.findings] == [
        ("IE024", f"{(root / 'index.yml').as_posix()}:scenarios[0].readme")]
    assert "readme 'locked/README.md' cannot be checked (Permission denied)" in result.findings[0].message


# --- #179: commit options generation needs a source for, and the default branch -----------

def _graph_scenario(tmp_path: Path, commits: list[dict]) -> Path:
    data = {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
        "repository": {"name": "probe", "default_branch": "main"},
        "commits": commits,
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }
    path = tmp_path / "scenario.graph.yml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _commit(cid: str, parents: list[str], branch: str = "main", **keys) -> dict:
    operations = ([{"type": "write_file", "path": "a.txt", "content": "a\n"}] if not parents
                  else [{"type": "write_file", "path": f"{cid}.txt", "content": f"{cid}\n"}])
    return {"id": cid, "branch": branch, "parents": parents, "message": f"Change {cid}", "operations": operations, **keys}


def _features() -> list[dict]:
    return [_commit("c0", []), _commit("f1", ["c0"], branch="feature"), _commit("f2", ["f1"], branch="feature")]


@pytest.mark.parametrize("rewritten, location, words", [
    # a squash-rebase: the generator said "has no rebase_of, cherry_pick_of or backport_of"
    ({"rebase_of": ["f1", "f2"], "inherit_message": True}, "inherit_message", "its rebase_of is a list"),
    ({"inherit_author_date": True}, "inherit_author_date", "has no rebase_of, cherry_pick_of or backport_of"),
])
def test_an_inherit_option_without_a_single_source_commit_is_ge074(tmp_path, rewritten, location, words):
    commit = _commit("r1", ["c0"], **rewritten)
    if "inherit_message" in rewritten:
        del commit["message"]
    _, result = validate_graph_scenario_file(_graph_scenario(tmp_path, [*_features(), commit]))
    assert [(f.code, f.location) for f in result.findings] == [("GE074", f"commits[3].{location}")]
    assert words in result.findings[0].message


def test_cherry_pick_trailer_needs_a_source_to_name(tmp_path):
    _, result = validate_graph_scenario_file(_graph_scenario(tmp_path, [_commit("c0", []),
                                                                        _commit("c1", ["c0"], cherry_pick_trailer=True)]))
    assert [(f.code, f.location) for f in result.findings] == [("GE075", "commits[1].cherry_pick_trailer")]
    # an apply_patch_from operation is a source, as generation reads it
    picked = _commit("r1", ["c0"], cherry_pick_trailer=True)
    picked["operations"] = [{"type": "apply_patch_from", "commit": "f2"}]
    _, result = validate_graph_scenario_file(_graph_scenario(tmp_path, [*_features(), picked]))
    assert "GE075" not in _codes(result) and not result.has_errors(), result.to_dict()


def test_a_default_branch_no_commit_is_on_is_gw022(tmp_path):
    commits = [_commit("c0", [], branch="develop"), _commit("c1", ["c0"], branch="develop")]
    _, result = validate_graph_scenario_file(_graph_scenario(tmp_path, commits))
    assert [(f.severity, f.code, f.location) for f in result.findings] == [
        ("WARNING", "GW022", "repository.default_branch")]
    assert "'main'" in result.findings[0].message
