"""Operation text and commit messages that are not strings (issue #151).

The classic validator checked that ``content``, ``old``, ``new`` and a
commit's ``message`` were there, not that they were strings.  ``content: 42``,
a blank ``content:`` (YAML null) and ``old: 42`` ended ``validate --simulate``
and ``generate`` in an ``AttributeError`` traceback from ``normalize_newlines``;
``message: 123`` validated, and ``generate`` ended in a ``TypeError`` from
``git commit -m``.  The graph suite read the values through ``str()``: a blank
``content:`` wrote the text ``None`` into the file, and the first error was a
``replace.old not found`` on a later operation; ``message: 123`` became the
subject ``123`` and failed only at verification.

The validators now report such a value at the field (E041 / E010, GE053 /
GE040), and what still reaches the operations or the commit is an error that
names the field, not a traceback and not ``"None"``.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import szzbench.generator as generator
import szzbench.graph_generator as graph_generator
from support import git
from szzbench.findings import ValidationResult
from szzbench.generator import GenerationError, generate_repository
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_simulator import simulate_graph_scenario
from szzbench.graph_validator import validate_graph_static
from szzbench.operations import OperationError, normalize_newlines, text_field
from szzbench.validator import simulate_commits, validate_static

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = yaml.safe_load((ROOT / "scenarios/SZZ-0005/scenario.yml").read_text(encoding="utf-8"))
GRAPH = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml").read_text(encoding="utf-8"))
OLD_RANGE = "src/main/java/example/OldRange.java"   # written by SZZG-0001's c0


def _op(commit: int, op: int, key: str, value):
    def mutate(data: dict) -> None:
        data["commits"][commit]["operations"][op][key] = value
    return mutate


def _message(commit: int, value):
    def mutate(data: dict) -> None:
        data["commits"][commit]["message"] = value
    return mutate


def _insert_after(key: str, value):
    """An ``insert_after`` appended to SZZG-0001's c1, with ``key`` set to ``value``."""
    def mutate(data: dict) -> None:
        op = {"type": "insert_after", "path": OLD_RANGE, "anchor": "package example;\n", "content": "// range checks\n"}
        data["commits"][1]["operations"].append({**op, key: value})
    return mutate


def _mutated(base: dict, mutate) -> dict:
    data = deepcopy(base)
    mutate(data)
    return data


def _write(tmp_path: Path, relative: str, data: dict) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True)


def _json_errors(completed: subprocess.CompletedProcess) -> list[tuple[str, str]]:
    return [(f["code"], f["location"]) for f in json.loads(completed.stdout)["findings"] if f["severity"] == "ERROR"]


# The rows of the issue's two tables, and the null message of issue #152, which the
# same check rejects: (mutation, code, location).
CLASSIC_ROWS = {
    "content-int": (_op(0, 0, "content", 42), "E041", "commits[0].operations[0].content"),
    "content-null": (_op(0, 0, "content", None), "E041", "commits[0].operations[0].content"),
    "old-int": (_op(1, 0, "old", 42), "E041", "commits[1].operations[0].old"),
    "new-null": (_op(1, 0, "new", None), "E041", "commits[1].operations[0].new"),
    "message-int": (_message(1, 123), "E010", "commits[1].message"),
    "message-null": (_message(1, None), "E010", "commits[1].message"),   # issue #152: TypeError in generate
}
GRAPH_ROWS = {
    "content-null": (_op(0, 0, "content", None), "GE053", "commits[0].operations[0].content"),
    "content-int": (_op(0, 0, "content", 42), "GE053", "commits[0].operations[0].content"),
    "old-int": (_op(1, 0, "old", 42), "GE053", "commits[1].operations[0].old"),
    "new-null": (_op(2, 2, "new", None), "GE053", "commits[2].operations[2].new"),
    "anchor-int": (_insert_after("anchor", 7), "GE053", "commits[1].operations[1].anchor"),
    "inserted-content-null": (_insert_after("content", None), "GE053", "commits[1].operations[1].content"),
    "message-int": (_message(1, 123), "GE040", "commits[1].message"),
    "message-null": (_message(1, None), "GE040", "commits[1].message"),  # issue #152: subject 'c1'
}
CLASSIC_FILE = "SZZ-0005/scenario.yml"
GRAPH_FILE = "SZZG-0001/scenario.graph.yml"


# --- the validators, through the CLI ----------------------------------------------

@pytest.mark.parametrize("row", list(CLASSIC_ROWS))
def test_validate_simulate_json_reports_the_field_without_a_traceback(tmp_path, row):
    """Run on a path relative to the working directory, as the issue's reproduction does."""
    mutate, code, location = CLASSIC_ROWS[row]
    _write(tmp_path, CLASSIC_FILE, _mutated(CLASSIC, mutate))
    completed = _szzbench(tmp_path, "validate", "--simulate", "--json", CLASSIC_FILE)
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    assert _json_errors(completed) == [(code, location)]


@pytest.mark.parametrize("row", list(CLASSIC_ROWS))
def test_generate_fails_without_a_traceback(tmp_path, row):
    mutate, _, _ = CLASSIC_ROWS[row]
    _write(tmp_path, CLASSIC_FILE, _mutated(CLASSIC, mutate))
    completed = _szzbench(tmp_path, "generate", CLASSIC_FILE, "--out", "out")
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    assert completed.stderr.startswith("[ERROR] GENERATION_FAILED: Scenario validation failed."), completed.stderr
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("row", list(GRAPH_ROWS))
def test_validate_graph_json_reports_the_field_itself(tmp_path, row):
    """Not a ``replace.old not found`` on a later operation, as the null content was."""
    mutate, code, location = GRAPH_ROWS[row]
    _write(tmp_path, GRAPH_FILE, _mutated(GRAPH, mutate))
    completed = _szzbench(tmp_path, "validate-graph", "--simulate", "--json", GRAPH_FILE)
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    assert _json_errors(completed) == [(code, location)]
    assert "not found" not in completed.stdout


@pytest.mark.parametrize("row", list(GRAPH_ROWS))
def test_generate_graph_fails_before_writing(tmp_path, row):
    """No file holding ``None``, no commit with the subject ``123`` or ``c1``."""
    mutate, _, _ = GRAPH_ROWS[row]
    _write(tmp_path, GRAPH_FILE, _mutated(GRAPH, mutate))
    completed = _szzbench(tmp_path, "generate-graph", GRAPH_FILE, "--out", "out")
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    assert completed.stderr.startswith("[ERROR] GRAPH_GENERATION_FAILED: Graph scenario validation failed."), completed.stderr
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("value, label", [(42, "int"), (None, "null (a blank value)"), (["x"], "list"), (1.5, "float")],
                         ids=["int", "null", "list", "float"])
def test_the_finding_names_the_type_it_got(value, label):
    findings = validate_static(_mutated(CLASSIC, _op(0, 0, "content", value))).findings
    assert [f.message for f in findings if f.severity == "ERROR"] == \
        [f"Operation 'write_file' field 'content' must be a string, not {label}."]
    findings = validate_graph_static(_mutated(GRAPH, _message(1, value))).findings
    assert [f.message for f in findings if f.severity == "ERROR"] == \
        [f"commit.message must be a string when present, not {label}."]


def test_an_empty_string_is_a_string():
    """The check is the type: an empty ``content`` or ``new`` is still text."""
    assert not validate_static(_mutated(CLASSIC, _op(1, 0, "new", ""))).has_errors()
    assert not validate_graph_static(_mutated(GRAPH, _op(0, 0, "content", ""))).has_errors()


def test_no_shipped_scenario_has_such_a_value():
    """The checks change no shipped scenario's outcome: none of them reports anything."""
    for path in sorted(ROOT.glob("scenarios/SZZ-*/scenario.yml")):
        findings = validate_static(yaml.safe_load(path.read_text(encoding="utf-8"))).findings
        assert [f for f in findings if f.code in {"E010", "E041"}] == [], path
    for path in sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")):
        findings = validate_graph_static(yaml.safe_load(path.read_text(encoding="utf-8"))).findings
        assert [f for f in findings if f.code in {"GE040", "GE053"}] == [], path


# --- what still reaches the operations (belt and braces) --------------------------

@pytest.mark.parametrize("value, label", [(42, "int"), (None, "null (a blank value)"), (True, "bool"), ({"a": 1}, "dict")],
                         ids=["int", "null", "bool", "dict"])
def test_normalize_newlines_refuses_what_is_not_text(value, label):
    with pytest.raises(OperationError, match=f"^{re.escape(f'expected text, not {label}')}$"):
        normalize_newlines(value)


def test_normalize_newlines_reads_text_as_before():
    assert normalize_newlines("a\r\nb\rc\n") == "a\nb\nc\n"


def test_text_field_names_the_operation_and_the_field():
    op = {"type": "replace", "path": "a.txt", "old": 42}
    with pytest.raises(OperationError, match=r"^replace\.old must be a string, not int$"):
        text_field(op, "old")
    with pytest.raises(OperationError, match=r"^replace\.new is missing$"):
        text_field(op, "new")
    assert text_field({"type": "write_file", "content": "x\r\n"}, "content") == "x\r\n"


@pytest.mark.parametrize("row", ["content-int", "content-null", "old-int", "new-null"])
def test_the_classic_simulation_reports_an_unvalidated_value_as_e2xx(row):
    """``simulate_commits`` without ``validate_static`` first: an error, not an AttributeError."""
    mutate, _, location = CLASSIC_ROWS[row]
    snapshots, result = simulate_commits(_mutated(CLASSIC, mutate))
    assert snapshots is None
    [finding] = result.findings
    field = location.rsplit(".", 1)[1]
    assert (finding.code, finding.location) == ("E2XX", location.rsplit(".", 1)[0])
    assert f".{field} must be a string" in finding.message


@pytest.fixture
def no_classic_validation(monkeypatch):
    monkeypatch.setattr(generator, "validate_scenario_file", lambda path, simulate: (None, ValidationResult(), None))


@pytest.fixture
def no_graph_validation(monkeypatch):
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))


def test_classic_generation_fails_on_an_unvalidated_value(tmp_path, no_classic_validation):
    scenario = _write(tmp_path, CLASSIC_FILE, _mutated(CLASSIC, _op(1, 0, "old", 42)))
    with pytest.raises(GenerationError, match=r"replace\.old must be a string, not int"):
        generate_repository(scenario, tmp_path / "out")
    error = json.loads((tmp_path / "out/metadata/generation-error.json").read_text(encoding="utf-8"))
    assert error["error"] == "replace.old must be a string, not int"


@pytest.mark.parametrize("row, location, message", [
    ("content-null", "commits[0].operations[0]", "write_file.content must be a string, not null (a blank value)"),
    ("old-int", "commits[1].operations[0]", "replace.old must be a string, not int"),
    ("anchor-int", "commits[1].operations[1]", "insert_after.anchor must be a string, not int"),
], ids=["content-null", "old-int", "anchor-int"])
def test_the_graph_simulation_reports_the_operation_with_the_value(row, location, message):
    """``simulate_graph_scenario`` without the static checks: the first error is the operation itself."""
    result = simulate_graph_scenario(_mutated(GRAPH, GRAPH_ROWS[row][0]))
    first = next(f for f in result.findings if f.severity == "ERROR")
    assert (first.code, first.location) == ("GE201", location)
    assert first.message.endswith(message)


def test_graph_generation_writes_no_none_for_an_unvalidated_null(tmp_path, no_graph_validation):
    scenario = _write(tmp_path, GRAPH_FILE, _mutated(GRAPH, _op(0, 0, "content", None)))
    with pytest.raises(GraphGenerationError, match=r"write_file\.content must be a string, not null"):
        generate_graph_repository(scenario, tmp_path / "out")
    assert not (tmp_path / "out/repo" / OLD_RANGE).exists()


def test_graph_generation_commits_no_subject_for_an_unvalidated_message(tmp_path, no_graph_validation):
    scenario = _write(tmp_path, GRAPH_FILE, _mutated(GRAPH, _message(1, 123)))
    with pytest.raises(GraphGenerationError, match=r"^message of commit 'c1' must be a string, not int\.$"):
        generate_graph_repository(scenario, tmp_path / "out")
    assert git(tmp_path / "out/repo", "log", "--format=%s") == "Add the range check"
