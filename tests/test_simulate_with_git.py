"""``validate-graph --simulate`` checks with Git what generation lets Git compute (issue #94).

The in-memory simulator models file operations.  Merges, ``git revert``,
``git cherry-pick``, ``apply_patch_from`` / ``apply_squash`` and conflict
``resolution`` are computed by Git during generation; the simulator
approximated merges and patches file by file and did not model the rest.
Until 2026-09-29 nine shipped scenarios that generate and verify therefore
failed ``--simulate`` with 17 errors (10 GE202, 2 GE200, 5 GE201): a real
revert looked empty, a declared resolution looked like an unresolved conflict,
and a cherry-picked change was missing when the next operation needed it.

A scenario that uses any of those features is now generated with Git in a
temporary directory: GE203 reports a failure there, at the commit that failed,
and GI203 records that the check was made with Git.  Every other scenario
keeps the in-memory check and its operation-level locations.

The generated repository was not verified, so a scenario could pass
``--simulate`` and fail ``generate-graph`` at verification -- a merge parent
Git did not record, a fault statement that is not in the file (issue #173).
It is now verified as ``generate-graph`` verifies it, and each verification
error is GE203 too, with the verifier's code and location.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_simulator import git_performed_features
from szzbench.graph_validator import validate_graph_scenario_file

ROOT = Path(__file__).resolve().parents[1]

GRAPH_SCENARIOS = sorted((ROOT / "advanced-scenarios").glob("SZZG-*/scenario.graph.yml"))
FORMERLY_REJECTED = ["SZZG-0089", "SZZG-0123", "SZZG-0124", "SZZG-0125", "SZZG-0126", "SZZG-0127",
                     "SZZG-0147", "SZZG-0150", "SZZG-0151"]


def _codes(result, severity: str) -> list[str]:
    assert severity in ("ERROR", "WARNING", "INFO")     # findings spell severities in capitals
    return [finding["code"] for finding in result.to_dict()["findings"] if finding["severity"] == severity]


def _findings(result, code: str) -> list[dict]:
    return [finding for finding in result.to_dict()["findings"] if finding["code"] == code]


@pytest.mark.parametrize("path", GRAPH_SCENARIOS, ids=lambda p: p.parent.name)
def test_every_shipped_graph_scenario_passes_the_simulation(path):
    _, result = validate_graph_scenario_file(path, simulate=True, strict_paths=True, lint=True)
    assert _codes(result, "ERROR") == [], result.to_dict()


@pytest.mark.parametrize("scenario_id", FORMERLY_REJECTED)
def test_the_nine_formerly_rejected_scenarios_are_checked_with_git(scenario_id):
    path = ROOT / "advanced-scenarios" / scenario_id / "scenario.graph.yml"
    _, result = validate_graph_scenario_file(path, simulate=True, strict_paths=True)
    assert _codes(result, "ERROR") == []
    assert len(_findings(result, "GI203")) == 1


def test_a_scenario_without_git_computed_commits_keeps_the_in_memory_check():
    _, result = validate_graph_scenario_file(ROOT / "advanced-scenarios/SZZG-0030/scenario.graph.yml",
                                             simulate=True, strict_paths=True)
    assert _findings(result, "GI203") == [] and _codes(result, "ERROR") == []


def test_the_features_that_send_a_scenario_to_git_mirror_the_generator():
    replace = [{"type": "replace", "path": "a.txt", "old": "x", "new": "y"}]
    data = {"commits": [
        {"id": "c0", "parents": [], "operations": [{"type": "write_file", "path": "a.txt", "content": "x\n"}]},
        {"id": "h1", "parents": ["c0"], "revert_of": "c0", "operations": replace},            # hand-written revert
        {"id": "r1", "parents": ["h1"], "revert_of": "c0", "apply_revert": True, "operations": replace},
        {"id": "r2", "parents": ["r1"], "revert_of": "c0"},
        {"id": "h2", "parents": ["r2"], "cherry_pick_of": "c0", "operations": replace},       # hand-written pick
        {"id": "p1", "parents": ["h2"], "backport_of": "c0"},
        {"id": "m1", "parents": ["p1", "c0"]},
        {"id": "a1", "parents": ["m1"], "operations": [{"type": "apply_patch_from", "commit": "c0"},
                                                       {"type": "apply_patch_from", "commit": "c0"}]},
        {"id": "s1", "parents": ["a1"], "operations": [{"type": "apply_squash", "from_commits": ["c0"]}]},
        {"id": "x1", "parents": ["s1"], "cherry_pick_of": "c0", "resolution": {"a.txt": "z\n"}},
    ]}
    assert git_performed_features(data) == [
        "r1: git revert", "r2: git revert", "p1: git cherry-pick", "m1: merge", "a1: apply_patch_from",
        "s1: apply_squash", "x1: git cherry-pick", "x1: resolution"]


def _variant(tmp_path: Path, scenario_id: str, edit) -> Path:
    data = yaml.safe_load((ROOT / "advanced-scenarios" / scenario_id / "scenario.graph.yml").read_text())
    edit(data)
    path = tmp_path / scenario_id / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _commit(data: dict, cid: str) -> dict:
    return next(commit for commit in data["commits"] if commit["id"] == cid)


def test_an_unresolved_conflict_is_still_an_error(tmp_path):
    def drop_resolution(data):
        del _commit(data, "c3")["resolution"]
    _, result = validate_graph_scenario_file(_variant(tmp_path, "SZZG-0123", drop_resolution), simulate=True)
    [finding] = _findings(result, "GE203")
    assert "at commit 'c3'" in finding["message"] and "reported conflicts" in finding["message"]
    assert finding["location"] == "commits[5]"


def test_a_revert_that_changes_nothing_is_still_an_error(tmp_path):
    def revert_an_undone_change(data):   # c7 undoes c6 by hand, so reverting c6 changes nothing
        notes = "docs/NOTES.md"
        data["commits"] += [
            {"id": "c5", "branch": "main", "parents": ["c4"], "message": "Add the notes", "role": "intermediate",
             "operations": [{"type": "write_file", "path": notes, "content": "alpha\n"}]},
            {"id": "c6", "branch": "main", "parents": ["c5"], "message": "Rename the note", "role": "intermediate",
             "operations": [{"type": "replace", "path": notes, "old": "alpha", "new": "beta"}]},
            {"id": "c7", "branch": "main", "parents": ["c6"], "message": "Restore the note", "role": "intermediate",
             "operations": [{"type": "replace", "path": notes, "old": "beta", "new": "alpha"}]},
            {"id": "c8", "branch": "main", "parents": ["c7"], "message": "Revert the rename", "role": "intermediate",
             "revert_of": "c6"},
        ]
    _, result = validate_graph_scenario_file(_variant(tmp_path, "SZZG-0126", revert_an_undone_change), simulate=True)
    [finding] = _findings(result, "GE203")
    assert finding["location"] == "commits[8]"
    assert "at commit 'c8'" in finding["message"] and "commit would be empty" in finding["message"]


def _misquote_the_fault(data):
    data["bugs"][0]["faults"][0]["statement"] = "return attempts <= budget;"


def _date_the_fix_after_the_merge(data):
    # The merge c3 is then committed before its parent f2.  A trailing space in c3's
    # message (GE623) was this case until validation rejected such a message itself
    # (GE070, issue #163).
    _commit(data, "f2")["date"] = "2030-01-01T00:00:00Z"


@pytest.mark.parametrize("edit, code, location", [
    (_misquote_the_fault, "GE663", "bugs[0].faults[0]"),
    (_date_the_fix_after_the_merge, "GE630", "commits"),
], ids=["fault-statement", "commit-date"])
def test_a_verification_error_is_ge203_with_the_verifiers_code_and_location(tmp_path, edit, code, location):
    path = _variant(tmp_path, "SZZG-0123", edit)
    _, static = validate_graph_scenario_file(path, strict_paths=True, lint=True)
    assert not static.has_errors(), static.to_dict()     # only verification finds it
    _, result = validate_graph_scenario_file(path, simulate=True)
    [finding] = _findings(result, "GE203")
    assert finding["location"] == location
    assert finding["message"].startswith(f"The scenario generated with Git fails verification: {code} ")
    assert _findings(result, "GI203") == []
    with pytest.raises(GraphGenerationError, match="failed verification"):   # what --simulate now predicts
        generate_graph_repository(path, tmp_path / "out", force=True)


def test_a_broken_operation_after_a_cherry_pick_is_still_an_error(tmp_path):
    def break_r2(data):
        _commit(data, "r2")["operations"][0]["old"] = "this text is not in the file"
    _, result = validate_graph_scenario_file(_variant(tmp_path, "SZZG-0124", break_r2), simulate=True)
    [finding] = _findings(result, "GE203")
    assert "at commit 'r2'" in finding["message"] and "replace.old not found" in finding["message"]


def test_a_broken_operation_in_a_plain_scenario_keeps_its_operation_location(tmp_path):
    def break_c3(data):
        _commit(data, "c3")["operations"][0]["old"] = "this text is not in the file"
    _, result = validate_graph_scenario_file(_variant(tmp_path, "SZZG-0030", break_c3), simulate=True)
    [finding] = _findings(result, "GE201")
    assert finding["location"] == "commits[3].operations[0]"
    assert _findings(result, "GE203") == [] and _findings(result, "GI203") == []


def test_gi203_names_what_git_computed():
    _, result = validate_graph_scenario_file(ROOT / "advanced-scenarios/SZZG-0126/scenario.graph.yml", simulate=True)
    [finding] = _findings(result, "GI203")
    assert "c3: git revert" in finding["message"] and "c4: git revert" in finding["message"]
