"""A commit ``role`` that is not a string (issue #150).

The classic validator tested ``role not in ALLOWED_ROLES`` before anything
checked the type: ``role: 5`` was E030, and a list or a mapping (``role:
[bug_introducing]``, a plausible slip for a one-word field) raised
``TypeError: cannot use 'list' as a set element`` out of ``validate``,
``--json`` included.  The graph validator read ``role`` only for its
merge-like test (GW040 / GW041): the same value passed without a finding on a
commit with one parent, and raised the same ``TypeError`` on a merge.

A role that is not a string is now E030 in the classic suite and GE041 in the
graph suite.  The graph suite's static checks accept any string; whether it is
one of the roles both suites share is the `--lint` check GE405 (issue #195,
`tests/test_metadata_lints.py`).
"""
from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from szzbench.graph_validator import validate_graph_static
from szzbench.validator import validate_static

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = yaml.safe_load((ROOT / "scenarios/SZZ-0005/scenario.yml").read_text(encoding="utf-8"))
GRAPH = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml").read_text(encoding="utf-8"))
#: SZZG-0060's c3 is a merge (two parents, role: merge)
MERGE = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0060/scenario.graph.yml").read_text(encoding="utf-8"))

NOT_STRINGS = {"list": ["bug_introducing"], "mapping": {"bug": "introducing"}, "int": 5}


def _with_role(base: dict, index: int, role) -> dict:
    data = deepcopy(base)
    data["commits"][index]["role"] = role
    return data


def _errors(result) -> list[tuple[str, str | None]]:
    return [(f.code, f.location) for f in result.findings if f.severity == "ERROR"]


def _write(tmp_path: Path, relative: str, data: dict) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True)


@pytest.mark.parametrize("kind", list(NOT_STRINGS))
def test_a_classic_role_that_is_not_a_string_is_e030(kind):
    assert _errors(validate_static(_with_role(CLASSIC, 1, NOT_STRINGS[kind]))) == [("E030", "commits[1].role")]


@pytest.mark.parametrize("kind", list(NOT_STRINGS))
def test_validate_json_reports_it_instead_of_a_traceback(tmp_path, kind):
    """The issue's reproduction: validate --json on a copy, from a path relative to the working directory."""
    _write(tmp_path, "classic/SZZ-0005/scenario.yml", _with_role(CLASSIC, 1, NOT_STRINGS[kind]))
    completed = _szzbench(tmp_path, "validate", "--json", "classic/SZZ-0005/scenario.yml")
    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr, completed.stderr
    findings = json.loads(completed.stdout)["findings"]
    assert [(f["code"], f["location"]) for f in findings if f["severity"] == "ERROR"] == [("E030", "commits[1].role")]


def test_an_unknown_classic_role_is_still_e030_with_its_name():
    [finding] = [f for f in validate_static(_with_role(CLASSIC, 1, "bug_intro")).findings if f.code == "E030"]
    assert finding.message == "Unknown commit role 'bug_intro'."


@pytest.mark.parametrize("kind", list(NOT_STRINGS))
def test_a_graph_role_that_is_not_a_string_is_ge041(kind):
    assert _errors(validate_graph_static(_with_role(GRAPH, 1, NOT_STRINGS[kind]))) == [("GE041", "commits[1].role")]


@pytest.mark.parametrize("kind", list(NOT_STRINGS))
def test_a_merge_whose_role_is_not_a_string_is_ge041_not_a_traceback(kind):
    """The merge-like test (GW041) raised TypeError for an unhashable role."""
    result = validate_graph_static(_with_role(MERGE, 3, NOT_STRINGS[kind]))
    assert _errors(result) == [("GE041", "commits[3].role")]
    assert not [f for f in result.findings if f.code in ("GW040", "GW041")]


@pytest.mark.parametrize("kind", list(NOT_STRINGS))
def test_validate_graph_json_reports_it(tmp_path, kind):
    _write(tmp_path, "graph/SZZG-0060/scenario.graph.yml", _with_role(MERGE, 3, NOT_STRINGS[kind]))
    completed = _szzbench(tmp_path, "validate-graph", "--simulate", "--strict", "--strict-paths", "--lint", "--json",
                          "graph/SZZG-0060/scenario.graph.yml")
    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr, completed.stderr
    findings = json.loads(completed.stdout)["findings"]
    assert [(f["code"], f["location"]) for f in findings if f["severity"] == "ERROR"] == [("GE041", "commits[3].role")]


def test_the_graph_static_checks_accept_any_role_string():
    """Any string passes them; only the merge-like test reads it.  The vocabulary is a lint (GE405)."""
    assert _errors(validate_graph_static(_with_role(GRAPH, 1, "a_role_nobody_listed"))) == []
    assert _errors(validate_graph_static(_with_role(GRAPH, 1, None))) == []      # a blank role is no role
    result = validate_graph_static(_with_role(MERGE, 3, "a_role_nobody_listed"))
    assert _errors(result) == [] and [f.code for f in result.findings if f.code == "GW041"] == ["GW041"]


def test_every_shipped_role_is_a_string():
    for path in [*ROOT.glob("scenarios/SZZ-*/scenario.yml"), *ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")]:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for commit in data.get("commits") or []:
            assert commit.get("role") is None or isinstance(commit["role"], str), (path, commit.get("id"))
