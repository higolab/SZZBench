"""generate-graph reports an operation value it cannot use instead of raising (issue #172).

Three values reached generation and ended in a Python traceback, with no
generation.log and no generation-error.json: a ``chmod`` ``mode`` written as an
unquoted ``0755`` (which YAML reads as the integer 493), a ``content_base64``
that does not decode, and a text operation on a file that is not UTF-8.  The
validator now checks the values it can (GE057-GE059), and the generator turns
any such failure into an error that names the operation and its path.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import szzbench.graph_generator as graph_generator
from szzbench.findings import ValidationResult
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_static

ROOT = Path(__file__).resolve().parents[1]
BASE = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml").read_text(encoding="utf-8"))


def _with_ops(*ops: dict) -> dict:
    data = deepcopy(BASE)
    data["commits"][0]["operations"] = [*data["commits"][0]["operations"], *ops]
    return data


def _write(tmp_path: Path, data: dict, text: str | None = None) -> Path:
    path = tmp_path / "SZZG-0001" / "scenario.graph.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text is not None else yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _errors(data: dict) -> list[tuple[str, str]]:
    return [(f.code, f.location) for f in validate_graph_static(data).findings if f.severity == "ERROR"]


SCRIPT = {"type": "write_file", "path": "scripts/run.sh", "content": "#!/bin/sh\n"}
BINARY = {"type": "write_binary_file", "path": "assets/logo.bin", "content_base64": "/wD/AA=="}


# --- the static checks ----------------------------------------------------------

def test_an_unquoted_0755_is_ge057_with_the_reason(tmp_path):
    text = yaml.safe_dump(_with_ops(SCRIPT, {"type": "chmod", "path": "scripts/run.sh", "mode": "MODE"}), sort_keys=False)
    data = yaml.safe_load(text.replace("mode: MODE", "mode: 0755"))
    assert data["commits"][0]["operations"][-1]["mode"] == 493
    result = validate_graph_static(data)
    [finding] = [f for f in result.findings if f.severity == "ERROR"]
    assert (finding.code, finding.location) == ("GE057", "commits[0].operations[2].mode")
    assert "YAML reads an unquoted 0755 as the integer 493" in finding.message


@pytest.mark.parametrize("mode", ["755", "0755", "644"])
def test_a_quoted_octal_mode_is_accepted(mode):
    assert _errors(_with_ops(SCRIPT, {"type": "chmod", "path": "scripts/run.sh", "mode": mode})) == []


@pytest.mark.parametrize("mode", [755, "rwx", "8", "75", "07555", True])
def test_any_other_mode_is_ge057(mode):
    assert _errors(_with_ops(SCRIPT, {"type": "chmod", "path": "scripts/run.sh", "mode": mode})) == \
        [("GE057", "commits[0].operations[2].mode")]


@pytest.mark.parametrize("value", ["@@@not-base64@@@", "!!!", "/wD/A", 42])
def test_base64_that_does_not_decode_is_ge058(value):
    assert _errors(_with_ops({**BINARY, "content_base64": value})) == [("GE058", "commits[0].operations[1].content_base64")]


@pytest.mark.parametrize("value", ["/wD/AA==", "/wD/\n AA==\n", ""])
def test_base64_that_decodes_is_accepted(value):
    assert _errors(_with_ops({**BINARY, "content_base64": value})) == []


@pytest.mark.parametrize("lines", [-5, "many", 2.5, True, None])
def test_lines_that_are_not_a_non_negative_integer_are_ge059(lines):
    op = {"type": "write_generated_text_file", "path": "gen/data.txt", "lines": lines, "template": "row {line}"}
    assert _errors(_with_ops(op)) == [("GE059", "commits[0].operations[1].lines")]


def test_no_shipped_scenario_has_such_a_value():
    for path in sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")):
        codes = {code for code, _ in _errors(yaml.safe_load(path.read_text(encoding="utf-8")))}
        assert not codes & {"GE057", "GE058", "GE059"}, path


# --- generation -----------------------------------------------------------------

def test_generate_graph_refuses_the_values_the_validator_reports(tmp_path):
    scenario = _write(tmp_path, _with_ops({**BINARY, "content_base64": "@@@not-base64@@@"}))
    with pytest.raises(GraphGenerationError, match="validation failed"):
        generate_graph_repository(scenario, tmp_path / "out", force=True)


@pytest.mark.parametrize("op, message", [
    ({"type": "chmod", "path": "scripts/run.sh", "mode": 493},
     "chmod 'scripts/run.sh': mode must be octal digits, got 493; YAML reads an unquoted 0755"),
    ({**BINARY, "content_base64": "@@@not-base64@@@"},
     "write_binary_file 'assets/logo.bin': content_base64 does not decode"),
    ({"type": "write_file", "path": "notes.txt", "content": "x", "encoding": "no-such-codec"},
     "write_file 'notes.txt': unknown encoding: no-such-codec"),
], ids=["mode", "base64", "encoding"])
def test_a_value_that_slips_past_validation_is_a_reported_failure(tmp_path, monkeypatch, op, message):
    """The generator does not rely on the validator: the operation itself reports the value."""
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))
    scenario = _write(tmp_path, _with_ops(SCRIPT, op))
    with pytest.raises(GraphGenerationError, match=message.replace("(", r"\(").replace(")", r"\)")):
        generate_graph_repository(scenario, tmp_path / "out", force=True)
    metadata = tmp_path / "out" / "metadata"
    assert message in json.loads((metadata / "generation-error.json").read_text(encoding="utf-8"))["error"]
    assert "ERROR: " + message.split(":")[0] in (metadata / "generation.log").read_text(encoding="utf-8")


def test_format_file_on_a_binary_file_is_a_reported_failure_without_a_traceback(tmp_path):
    scenario = _write(tmp_path, _with_ops(BINARY, {"type": "format_file", "path": "assets/logo.bin"}))
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", "generate-graph", str(scenario), "--out", str(tmp_path / "out")],
                               capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert completed.returncode == 1 and "Traceback" not in completed.stderr
    assert completed.stderr.strip() == ("[ERROR] GRAPH_GENERATION_FAILED: format_file 'assets/logo.bin': "
                                        "the file is not text in utf-8 (byte 0xff at position 0)")
    assert (tmp_path / "out/metadata/generation-error.json").is_file()
    assert (tmp_path / "out/metadata/generation.log").is_file()
