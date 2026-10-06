"""The classic commands refuse a graph scenario instead of misreading it (issue #119).

`validate`, `generate` and `verify` take a scenario path, and nothing checked
that the file was a classic scenario.  Given a graph scenario, `validate` and
`generate` stopped with a traceback (`set()` over the BIC mappings of
`validate_static`), and `verify` skipped the blame check and printed a clean
summary.  Each now stops with E003, which names the matching graph command; a
classic scenario with a malformed BIC entry gets E010 instead of a traceback.
"""
from __future__ import annotations

from copy import deepcopy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from szzbench.validator import validate_scenario_file, validate_static

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "advanced-scenarios/SZZG-0115/scenario.graph.yml"
CLASSIC = ROOT / "scenarios/SZZ-0006/scenario.yml"


def _szzbench(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, text=True, capture_output=True)


def _refused(completed: subprocess.CompletedProcess, graph_command: str) -> None:
    output = completed.stdout + completed.stderr
    assert completed.returncode == 1, output
    assert "Traceback" not in output
    assert "E003" in output and f"szzbench {graph_command}" in output, output


@pytest.mark.parametrize("flags", [[], ["--lint"], ["--simulate"], ["--json"]])
def test_validate_refuses_a_graph_scenario(flags):
    completed = _szzbench("validate", *flags, str(GRAPH))
    _refused(completed, "validate-graph")
    if flags == ["--json"]:
        assert [f["code"] for f in json.loads(completed.stdout)["findings"]] == ["E003"]


def test_the_refusal_comes_before_any_other_check():
    _, result, _ = validate_scenario_file(GRAPH, lint=True)
    assert [f.code for f in result.findings] == ["E003"]


def test_generate_refuses_a_graph_scenario_and_writes_nothing(tmp_path):
    out = tmp_path / "out"
    _refused(_szzbench("generate", "--out", str(out), str(GRAPH)), "generate-graph")
    assert not out.exists()


def test_verify_refuses_a_graph_scenario_even_on_its_own_repository(tmp_path):
    out = tmp_path / "SZZG-0115"
    generated = _szzbench("generate-graph", str(GRAPH), "--out", str(out))
    assert generated.returncode == 0, generated.stdout + generated.stderr
    # verify-graph is the command for it; classic verify printed a clean summary
    assert _szzbench("verify-graph", "--scenario", str(GRAPH), str(out / "repo")).returncode == 0
    _refused(_szzbench("verify", "--scenario", str(GRAPH), str(out / "repo")), "verify-graph")


def test_a_file_named_like_a_graph_scenario_without_a_schema_version_is_refused(tmp_path):
    data = yaml.safe_load(GRAPH.read_text(encoding="utf-8"))
    del data["schema_version"]
    path = tmp_path / "scenario.graph.yml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _refused(_szzbench("validate", str(path)), "validate-graph")


@pytest.mark.parametrize("schema_version", ["graph-0.1-draft", "graph-1.0", "my-graph", "1.0", "Graph-1.0", 1.0, ["graph"]])
def test_e003_recognises_a_graph_scenario_as_ge001_does(tmp_path, schema_version):
    # graph_scenario.py, which decides GE001, is fingerprinted generation code, so
    # the classic side has its own copy of the rule; this keeps the two in step.
    from szzbench.graph_scenario import load_graph_scenario

    path = tmp_path / "scenario.yml"
    path.write_text(yaml.safe_dump({"schema_version": schema_version}), encoding="utf-8")
    _, graph = load_graph_scenario(path)
    _, classic, _ = validate_scenario_file(path)
    assert ("E003" in [f.code for f in classic.findings]) == ("GE001" not in [f.code for f in graph.findings])


def test_a_classic_scenario_is_validated_whatever_its_file_is_called(tmp_path):
    # the schema_version decides, as GE001 does on the graph side; the name is only a hint
    path = tmp_path / "scenario.graph.yml"
    path.write_text(CLASSIC.read_text(encoding="utf-8"), encoding="utf-8")
    _, result, _ = validate_scenario_file(path)
    assert "E003" not in [f.code for f in result.findings] and not result.has_errors()


def test_a_classic_bic_entry_that_is_not_a_string_is_an_error_not_a_traceback():
    data = yaml.safe_load(CLASSIC.read_text(encoding="utf-8"))
    malformed = deepcopy(data)
    malformed["bugs"][0]["bug_introducing_commits"] = [{"commit": "c1", "role": "direct"}]
    result = validate_static(malformed)
    assert [(f.code, f.location) for f in result.findings if f.code == "E010"] == [
        ("E010", "bugs[0].bug_introducing_commits")]
    # a duplicate string entry is still caught next to a malformed one
    malformed["bugs"][0]["bug_introducing_commits"] = ["c1", "c1", {"commit": "c1"}]
    assert {"E010", "E083"} <= {f.code for f in validate_static(malformed).findings}
