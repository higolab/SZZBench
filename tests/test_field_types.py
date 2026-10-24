"""Values ``validate`` accepted and ``generate`` refused or misread (issue #152).

``docs/validation.md`` said E010 covered "a required field that is missing or
has the wrong type", but most fields were checked for presence only, and
several values only the generators read were checked by nothing: a ``path``
that is a number, a numeric ``commit.id`` or ``default_branch``, a ``date`` Git
cannot read, a ``line_ending`` the simulator never looks at, an unknown graph
``encoding``, a ``commit_generator.count`` that is not an integer.  They passed
``validate --simulate`` (or ``validate-graph --simulate --lint``) and failed in
``generate``, ``default_branch: 1`` with a traceback.  Four more passed both
and meant something else: a ``fault`` written as a list skipped every fault
check, an empty ``fix.statement`` is in every text, a numeric ``author`` was
replaced by a default author, and ``schema_version: 1.0`` was compared with
nothing.

The validators now report each value at its field, and what they accept the
generators build: the sweep below sets the commit, operation, repository and
meta fields of both suites to values of the wrong type (an error at the field,
no exception, and generation refused before Git runs), and the values next to
them that are spelt otherwise but valid validate and generate. The non-string
text and message regressions of issue #151 use the same case table; an identical
input is checked once, with all of its API and CLI assertions.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
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
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.operations import OperationError, normalize_newlines, text_field
from szzbench.validator import simulate_commits, validate_scenario_file, validate_static

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = yaml.safe_load((ROOT / "scenarios/SZZ-0005/scenario.yml").read_text(encoding="utf-8"))
GRAPH = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml").read_text(encoding="utf-8"))
#: SZZG-0001 with two generated commits before c1, so that commit_generator's fields can be swept.
GRAPH_WITH_GENERATOR = deepcopy(GRAPH)
GRAPH_WITH_GENERATOR["commits"][1]["operations"].append(
    {"type": "commit_generator", "generator": "unrelated_changes", "count": 2, "files": 1, "path": "generated"})
CLASSIC_FILE = "SZZ-0005/scenario.yml"
GRAPH_FILE = "SZZG-0001/scenario.graph.yml"
OLD_RANGE = "src/main/java/example/OldRange.java"


def _location(path: tuple) -> str:
    return "".join(f"[{key}]" if isinstance(key, int) else f".{key}" for key in path).lstrip(".")


def _set(data: dict, path: tuple, value) -> dict:
    data = deepcopy(data)
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = deepcopy(value)
    return data


def _write(tmp_path: Path, relative: str, data: dict) -> Path:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _errors(result: ValidationResult) -> list[tuple[str, str]]:
    return [(f.code, f.location) for f in result.error_findings()]


def _validate(path: Path, graph: bool) -> ValidationResult:
    if graph:
        return validate_graph_scenario_file(path, strict_paths=True, simulate=True, lint=True)[1]
    return validate_scenario_file(path, simulate=True, lint=True)[1]


# --- the issue's table: one change to SZZ-0005 or SZZG-0001 per row ------------------

def _append_op(commit: int, op: dict):
    def mutate(data: dict) -> None:
        data["commits"][commit]["operations"].append(op)
    return mutate


def _at(path: tuple, value):
    def mutate(data: dict) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    return mutate


def _fault_as_list(data: dict) -> None:
    data["bugs"][0]["fault"] = [data["bugs"][0]["fault"]]


#: row -> (mutation, code, location).  ``message-null`` (#151, PR #227) and the
#: two graph rows ``message-null`` (#151) and ``lifecycle`` (#229, PR #231) were
#: fixed before this issue; they stay here as the table's rows.
CLASSIC_ROWS = {
    "path-int": (_append_op(0, {"type": "write_file", "path": 123, "content": "x\n"}), "E041", "commits[0].operations[2].path"),
    "message-null": (_at(("commits", 1, "message"), None), "E010", "commits[1].message"),
    "commit-id-int": (_at(("commits", 0, "id"), 0), "E010", "commits[0].id"),
    "branch-int": (_at(("repository", "default_branch"), 1), "E010", "repository.default_branch"),
    "date-bogus": (_at(("commits", 0, "date"), "yesterday"), "E013", "commits[0].date"),
    "line-ending-cr": (_at(("commits", 0, "operations", 0, "line_ending"), "cr"), "E042", "commits[0].operations[0].line_ending"),
    "fault-list": (_fault_as_list, "E010", "bugs[0].fault"),
    "fix-statement-empty": (_at(("bugs", 0, "fix", "statement"), ""), "E311", "bugs[0].fix.statement"),
    "author-int": (_at(("commits", 1, "author"), 5), "E014", "commits[1].author"),
    "schema-float": (_at(("schema_version",), 1.0), "E010", "schema_version"),
}
GRAPH_ROWS = {
    "message-null": (_at(("commits", 1, "message"), None), "GE040", "commits[1].message"),
    "encoding": (_at(("commits", 0, "operations", 0, "encoding"), "bogus"), "GE061", "commits[0].operations[0].encoding"),
    "count": (_append_op(1, {"type": "commit_generator", "generator": "unrelated", "count": "many"}), "GE062",
              "commits[1].operations[1].count"),
    "lifecycle": (_at(("graph", "ref_lifecycle"), {"delete_branches": ["nope"]}), "GE154",
                  "graph.ref_lifecycle.delete_branches[0]"),
}


def _op(commit: int, op: int, key: str, value):
    return _at(("commits", commit, "operations", op, key), value)


def _message(commit: int, value):
    return _at(("commits", commit, "message"), value)


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


# Non-string text and message regressions (issue #151).
CLASSIC_TEXT_ROWS = {
    "content-int": (_op(0, 0, "content", 42), "E041", "commits[0].operations[0].content"),
    "content-null": (_op(0, 0, "content", None), "E041", "commits[0].operations[0].content"),
    "old-int": (_op(1, 0, "old", 42), "E041", "commits[1].operations[0].old"),
    "new-null": (_op(1, 0, "new", None), "E041", "commits[1].operations[0].new"),
    "message-int": (_message(1, 123), "E010", "commits[1].message"),
    "message-null": (_message(1, None), "E010", "commits[1].message"),   # issue #152: TypeError in generate
}
GRAPH_TEXT_ROWS = {
    "content-null": (_op(0, 0, "content", None), "GE053", "commits[0].operations[0].content"),
    "content-int": (_op(0, 0, "content", 42), "GE053", "commits[0].operations[0].content"),
    "old-int": (_op(1, 0, "old", 42), "GE053", "commits[1].operations[0].old"),
    "new-null": (_op(2, 2, "new", None), "GE053", "commits[2].operations[2].new"),
    "anchor-int": (_insert_after("anchor", 7), "GE053", "commits[1].operations[1].anchor"),
    "inserted-content-null": (_insert_after("content", None), "GE053", "commits[1].operations[1].content"),
    "message-int": (_message(1, 123), "GE040", "commits[1].message"),
    "message-null": (_message(1, None), "GE040", "commits[1].message"),  # issue #152: subject 'c1'
}


# --- the sweep: wrong types for the commit, operation, repository and meta fields -----

STRINGS = [42, 1.5, True, None, ["x"], {"x": 1}]
TIMESTAMPS = [*STRINGS, "", "yesterday", "2024-13-01T10:00:00Z", date(2024, 1, 2),
              # instants Git refuses or records as another date (Git 2.39 and 2.50)
              "1969-12-31T23:59:59Z", "1970-01-01T08:59:59+09:00", "2100-01-01T00:00:00Z",
              "2099-12-31T23:59:59-12:00", "0001-01-01T00:00:00Z", datetime(1969, 7, 20, 20, 17, tzinfo=timezone.utc)]
AUTHORS = [*STRINGS, "", "   ", "Alice", "alice@example.com", "<alice@example.com>", "Alice <>", "Alice <  >",
           ". <alice@example.com>", "Alice <alice@example.com", "Alice alice@example.com>"]
LINE_ENDINGS = [42, True, ["lf"], {"x": 1}, "", "cr", "\r\n", "unix"]
CLASSIC_ENCODINGS = [42, True, ["utf-8"], {"x": 1}, "", "latin-1", "bogus", "base64"]
GRAPH_ENCODINGS = [42, True, ["utf-8"], {"x": 1}, "", "bogus", "base64", "rot13", "utf\x00", "latin-1", "utf-16"]

#: (path, code, values): each value at the path is an error with that code at that field.
CLASSIC_SWEEP = [
    (("schema_version",), "E010", [1.0, 1, True, None, ["1.0"], {"v": 1}]),
    (("schema_version",), "E004", ["2.0", "1", "1.0 ", "v1.0"]),
    *[(("meta", key), "E010", STRINGS) for key in ("id", "title", "category")],
    *[(("repository", key), "E010", STRINGS) for key in ("name", "default_branch", "language")],
    (("repository", "base_date"), "E013", TIMESTAMPS),
    (("commits", 1, "id"), "E010", STRINGS),
    (("commits", 1, "message"), "E010", STRINGS),
    (("commits", 1, "author"), "E014", AUTHORS),
    *[(("commits", 1, key), "E013", TIMESTAMPS) for key in ("date", "author_date", "committer_date")],
    (("commits", 1, "role"), "E030", [42, 1.5, True, ["bug_introducing"], {"x": 1}, "bogus"]),
    (("commits", 1, "operations"), "E010", [42, "x", None, {"x": 1}]),
    (("commits", 0, "operations", 0, "type"), "E041", [42, True, None, ["write_file"], {"x": 1}]),
    *[(("commits", 0, "operations", 0, key), "E041", STRINGS) for key in ("path", "content")],
    *[(("commits", 1, "operations", 0, key), "E041", STRINGS) for key in ("path", "old", "new")],
    (("commits", 0, "operations", 0, "line_ending"), "E042", LINE_ENDINGS),
    (("commits", 1, "operations", 0, "line_ending"), "E042", LINE_ENDINGS),
    (("commits", 0, "operations", 0, "encoding"), "E042", CLASSIC_ENCODINGS),
    (("commits", 1, "operations", 0, "encoding"), "E042", CLASSIC_ENCODINGS),
    *[(("bugs", 0, key), "E010", [42, "x", None, [{"commit": "c1"}]]) for key in ("fault", "fix")],
    (("bugs", 0, "fault", "statement"), "E301", ["", "   ", "\n"]),
    *[(("bugs", 0, "fix", key), "E311", ["", " \t"]) for key in ("statement", "added_statement", "removed_statement")],
]
GRAPH_SWEEP = [
    (("schema_version",), "GE001", [1.0, None, ["graph-1.0"], "1.0"]),
    (("schema_version",), "GE002", ["graph-0.1-draft", "graph-2.0", "my-graph", "graph-1.0 "]),
    (("meta", "id"), "GE012", STRINGS),
    *[(("meta", key), "GE017", STRINGS) for key in ("title", "category")],
    *[(("repository", key), "GE022", STRINGS) for key in ("name", "default_branch", "language")],
    (("repository", "base_date"), "GE071", TIMESTAMPS),
    (("commits", 1, "id"), "GE033", [*STRINGS, ""]),
    (("commits", 1, "message"), "GE040", STRINGS),
    (("commits", 1, "author"), "GE072", AUTHORS),
    *[(("commits", 1, key), "GE071", TIMESTAMPS) for key in ("date", "author_date", "committer_date")],
    (("commits", 1, "branch"), "GE035", [42, 1.5, True, ["main"], {"x": 1}]),
    (("commits", 1, "parents"), "GE036", [42, "c0", None, {"x": 1}]),
    (("commits", 1, "role"), "GE041", [42, 1.5, True, ["x"], {"x": 1}]),
    (("commits", 1, "operations"), "GE044", [42, "x", {"x": 1}]),
    (("commits", 0, "operations", 0, "type"), "GE051", [42, True, None, ["write_file"], {"x": 1}]),
    (("commits", 0, "operations", 0, "path"), "GE055", STRINGS),
    (("commits", 0, "operations", 0, "content"), "GE053", STRINGS),
    *[(("commits", 1, "operations", 0, key), "GE053", STRINGS) for key in ("old", "new")],
    (("commits", 0, "operations", 0, "line_ending"), "GE061", LINE_ENDINGS),
    (("commits", 1, "operations", 0, "line_ending"), "GE061", LINE_ENDINGS),
    (("commits", 0, "operations", 0, "encoding"), "GE061", GRAPH_ENCODINGS),
    (("commits", 1, "operations", 0, "encoding"), "GE061", GRAPH_ENCODINGS),
    (("commits", 1, "operations", 1, "count"), "GE062",
     ["many", "3", 1.5, float("inf"), float("-inf"), float("nan"), True, None, -1, [2], {"n": 2}]),
    (("commits", 1, "operations", 1, "files"), "GE062", [0, -1, 1.5, "2", True, None, [1], float("inf")]),
]


def _sweep_cases(sweep: list) -> list:
    return [(path, code, value) for path, code, values in sweep for value in values]


def _sweep_id(case) -> str:
    path, code, value = case
    return f"{_location(path)}={value!r}"


@dataclass
class InvalidFieldCase:
    graph: bool
    name: str
    data: dict
    code: str
    location: str
    cli_modes: set[bool] = field(default_factory=set)  # validate with and/or without --lint
    generate_cli: bool = False


def _invalid_cases() -> list[InvalidFieldCase]:
    """One input per case, retaining every CLI mode attached to duplicate rows.

    YAML distinguishes bools from ints, nulls from strings, and all the other
    wrong types in the sweep. Graph cases with generated commits remain distinct
    from the plain graph fixture even when the changed field is the same.
    """
    cases = {}

    def add(graph, name, data, code, location, *, lint=None, generate_cli=False):
        key = graph, yaml.safe_dump(data, sort_keys=True)
        if key not in cases:
            cases[key] = InvalidFieldCase(graph, f"{'graph' if graph else 'classic'}-{name}", data, code, location)
        case = cases[key]
        assert (case.code, case.location) == (code, location), name
        if lint is not None:
            case.cli_modes.add(lint)
        case.generate_cli |= generate_cli

    for graph, sweep in ((False, CLASSIC_SWEEP), (True, GRAPH_SWEEP)):
        base = GRAPH_WITH_GENERATOR if graph else CLASSIC
        for path, code, value in _sweep_cases(sweep):
            add(graph, _sweep_id((path, code, value)), _set(base, path, value), code, _location(path))
    for graph, rows, text_rows in ((False, CLASSIC_ROWS, CLASSIC_TEXT_ROWS), (True, GRAPH_ROWS, GRAPH_TEXT_ROWS)):
        base = GRAPH if graph else CLASSIC
        for name, (mutate, code, location) in rows.items():
            add(graph, name, _mutated(base, mutate), code, location, lint=True,
                generate_cli=not graph and name == "branch-int")
        for name, (mutate, code, location) in text_rows.items():
            add(graph, name, _mutated(base, mutate), code, location, lint=False, generate_cli=True)
    return list(cases.values())


INVALID_CASES = _invalid_cases()


@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda case: case.name)
def test_an_invalid_value_is_reported_and_stops_generation(tmp_path, case):
    relative = GRAPH_FILE if case.graph else CLASSIC_FILE
    scenario = _write(tmp_path, relative, case.data)
    result = _validate(scenario, case.graph)
    assert (case.code, case.location) in _errors(result), result.to_dict()
    generate, error = (generate_graph_repository, GraphGenerationError) if case.graph else (generate_repository, GenerationError)
    with pytest.raises(error, match="validation failed"):
        generate(scenario, tmp_path / "out")
    assert not (tmp_path / "out").exists()

    # Keep the original relative-path CLI checks, including both lint modes where
    # two issue reproductions shared the input but used different command options.
    for lint in sorted(case.cli_modes):
        command = ["validate-graph" if case.graph else "validate", "--simulate"]
        if lint:
            command += ["--strict-paths", "--lint"] if case.graph else ["--lint"]
        completed = subprocess.run([sys.executable, "-m", "szzbench.cli", *command, "--json", relative], cwd=tmp_path,
                                   capture_output=True, text=True)
        assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
        errors = [(f["code"], f["location"]) for f in json.loads(completed.stdout)["findings"] if f["severity"] == "ERROR"]
        assert errors == [(case.code, case.location)]
        if case.graph and case.generate_cli:
            assert "not found" not in completed.stdout
    if case.generate_cli:
        command = "generate-graph" if case.graph else "generate"
        completed = subprocess.run([sys.executable, "-m", "szzbench.cli", command, relative, "--out", "cli-out"],
                                   cwd=tmp_path, capture_output=True, text=True)
        assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
        prefix = ("[ERROR] GRAPH_GENERATION_FAILED: Graph scenario validation failed." if case.graph else
                  "[ERROR] GENERATION_FAILED: Scenario validation failed.")
        assert completed.stderr.startswith(prefix), completed.stderr
        assert not (tmp_path / "cli-out").exists()


# --- what the checks accept, the generators build ----------------------------------

def _without_dates(data: dict) -> None:
    for commit in data["commits"]:
        commit.pop("date", None)


#: (path, value): spellings the checks accept; each one must validate and generate a verified repository.
CLASSIC_ACCEPTED = [
    (("commits", 1, "author"), "Alice<alice@example.com>"),
    (("commits", 1, "author"), "  Alice Example   <alice@example.com>  "),
    (("commits", 1, "author"), "Tolkien Jr. <jrrt@example.com>"),      # Git 2.39 drops the '.', verify does not mind
    (("commits", 1, "date"), "2023-10-19T20:36:00+0900"),
    (("commits", 1, "date"), "2023-10-19T11:36:00"),                   # no zone: UTC
    (("commits", 1, "date"), datetime(2023, 10, 19, 11, 36, tzinfo=timezone(timedelta(hours=-5)))),
    (("commits", 0, "date"), "1970-01-01T00:00:00Z"),                  # the first commit: nothing before it (E016)
    (("commits", 2, "date"), "2099-12-31T23:59:59Z"),                  # the last commit: nothing after it
    (("commits", 1, "author_date"), "2023-10-18T09:00:00Z"),
    (("commits", 1, "committer_date"), "2023-10-20T09:00:00.250Z"),
    (("repository", "base_date"), "2024-06-01T10:00:00Z"),
    (("commits", 0, "operations", 0, "line_ending"), "CRLF"),
    (("commits", 1, "operations", 0, "line_ending"), "LF"),
    (("commits", 0, "operations", 0, "line_ending"), None),            # blank: the default
    (("commits", 0, "operations", 0, "encoding"), "UTF8"),
    (("commits", 0, "operations", 0, "encoding"), "UTF_8_SIG"),
    (("commits", 0, "operations", 0, "encoding"), None),
]
GRAPH_ACCEPTED = [
    (("commits", 1, "author"), "Bob<bob@example.com>"),
    (("commits", 1, "date"), "2024-01-02T10:00:00+09:00"),             # between c0 and c2 of the plain schedule
    (("repository", "base_date"), "2024-06-03T10:00:00Z"),
    (("commits", 0, "operations", 0, "line_ending"), "crlf"),
    (("commits", 0, "operations", 0, "encoding"), "UTF_8_SIG"),        # a byte order mark (issue #240)
    (("commits", 0, "operations", 0, "encoding"), "UTF-8"),
    (("commits", 1, "operations", 1, "count"), 0),
    (("commits", 1, "operations", 1, "count"), 3),
    (("commits", 1, "operations", 1, "files"), 3),
]


@pytest.mark.parametrize("path, value", CLASSIC_ACCEPTED, ids=[f"{_location(p)}={v!r}" for p, v in CLASSIC_ACCEPTED])
def test_an_accepted_classic_value_generates_a_verified_repository(tmp_path, path, value):
    data = _set(CLASSIC, path, value)
    if path == ("repository", "base_date"):
        _without_dates(data)                                             # so that the base date is used
    scenario = _write(tmp_path, CLASSIC_FILE, data)
    assert _errors(_validate(scenario, False)) == []
    _, verify = generate_repository(scenario, tmp_path / "out")
    assert verify is not None and not verify.has_errors(), verify.to_dict()


@pytest.mark.parametrize("path, value", GRAPH_ACCEPTED, ids=[f"{_location(p)}={v!r}" for p, v in GRAPH_ACCEPTED])
def test_an_accepted_graph_value_generates_a_verified_repository(tmp_path, path, value):
    scenario = _write(tmp_path, GRAPH_FILE, _set(GRAPH_WITH_GENERATOR, path, value))
    assert _errors(_validate(scenario, True)) == []
    _, verify = generate_graph_repository(scenario, tmp_path / "out")
    assert verify is not None and not verify.has_errors(), verify.to_dict()


def test_the_bases_validate_and_generate(tmp_path):
    for graph, base in ((False, CLASSIC), (True, GRAPH_WITH_GENERATOR)):
        scenario = _write(tmp_path / str(graph), GRAPH_FILE if graph else CLASSIC_FILE, base)
        assert _errors(_validate(scenario, graph)) == []
        generate = generate_graph_repository if graph else generate_repository
        _, verify = generate(scenario, tmp_path / str(graph) / "out")
        assert verify is not None and not verify.has_errors()


def test_a_blank_date_is_refused_rather_than_replaced_by_the_default(tmp_path):
    """A blank ``date:`` (YAML null) used to get the generated date without a word."""
    scenario = _write(tmp_path, CLASSIC_FILE, _set(CLASSIC, ("commits", 1, "date"), None))
    result = _validate(scenario, False)
    assert _errors(result) == [("E013", "commits[1].date")]
    assert "without the key the generator picks a date" in result.error_findings()[0].message


def test_an_author_without_an_email_is_refused_rather_than_given_the_benchmarks_address(tmp_path):
    scenario = _write(tmp_path, CLASSIC_FILE, _set(CLASSIC, ("commits", 1, "author"), "Aiko Mori"))
    result = _validate(scenario, False)
    assert _errors(result) == [("E014", "commits[1].author")]
    assert "'Aiko Mori' is not 'Name <email>'" in result.error_findings()[0].message


def test_the_shipped_suites_use_the_values_the_checks_require():
    """The values the two schema_version checks require are the ones every shipped scenario declares."""
    classic = {yaml.safe_load(p.read_text(encoding="utf-8"))["schema_version"]
               for p in ROOT.glob("scenarios/SZZ-*/scenario.yml")}
    graph = {yaml.safe_load(p.read_text(encoding="utf-8"))["schema_version"]
             for p in ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")}
    assert (classic, graph) == ({"1.0"}, {"graph-1.0"})


# --- what still reaches the generators is GENERATION_FAILED, not a traceback --------

def _no_validation(monkeypatch) -> None:
    monkeypatch.setattr(generator, "validate_scenario_file", lambda path, simulate: (None, ValidationResult(), None))
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))


@pytest.mark.parametrize("graph", [False, True], ids=["classic", "graph"])
def test_a_default_branch_git_cannot_take_is_a_reported_failure(tmp_path, monkeypatch, graph):
    """``default_branch: 1`` reached ``subprocess`` and ended ``generate`` in a TypeError traceback."""
    _no_validation(monkeypatch)
    data = _set(GRAPH if graph else CLASSIC, ("repository", "default_branch"), 1)
    scenario = _write(tmp_path, GRAPH_FILE if graph else CLASSIC_FILE, data)
    generate, error = (generate_graph_repository, GraphGenerationError) if graph else (generate_repository, GenerationError)
    with pytest.raises(error, match="expected str, bytes or os.PathLike object, not int"):
        generate(scenario, tmp_path / "out")
    assert (tmp_path / "out" / "metadata" / "generation-error.json").is_file()


@pytest.mark.parametrize("graph", [False, True], ids=["classic", "graph"])
def test_a_lookup_error_from_an_operation_is_a_reported_failure(tmp_path, monkeypatch, graph):
    def unknown_codec(*args, **kwargs):
        raise LookupError("unknown encoding: bogus")
    _no_validation(monkeypatch)
    if graph:
        monkeypatch.setattr(graph_generator, "apply_graph_operation_to_filesystem", unknown_codec)
    else:
        monkeypatch.setattr(generator, "apply_operation_to_filesystem", unknown_codec)
    scenario = _write(tmp_path, GRAPH_FILE if graph else CLASSIC_FILE, GRAPH if graph else CLASSIC)
    generate, error = (generate_graph_repository, GraphGenerationError) if graph else (generate_repository, GenerationError)
    with pytest.raises(error, match="unknown encoding: bogus"):
        generate(scenario, tmp_path / "out")
    assert "unknown encoding: bogus" in (tmp_path / "out" / "metadata" / "generation.log").read_text(encoding="utf-8")


# --- PR #236 review: values the first checks passed, and Git still could not record --------------

def _without_dates(data: dict) -> dict:
    data = deepcopy(data)
    for commit in data["commits"]:
        for key in ("date", "author_date", "committer_date"):
            commit.pop(key, None)
    return data


#: name -> (classic scenario, graph scenario, classic code, graph code, location)
REVIEW_CASES = {
    # Git keeps an offset as +hhmm: the instant moved by 30 seconds (E605 in the classic suite, nothing in the graph one)
    "an offset with seconds": (_set(CLASSIC, ("commits", 1, "date"), "2023-10-19T11:36:00+00:00:30"),
                               _set(GRAPH, ("commits", 1, "date"), "2024-01-02T10:00:00+00:00:30"),
                               "E013", "GE071", "commits[1].date"),
    # the generators pass the author to Git in its environment
    "a NUL in the name": (_set(CLASSIC, ("commits", 1, "author"), "Alice\0 Example <alice@example.com>"),
                          _set(GRAPH, ("commits", 1, "author"), "Alice\0 Example <alice@example.com>"),
                          "E014", "GE072", "commits[1].author"),
    "a NUL in the e-mail": (_set(CLASSIC, ("commits", 1, "author"), "Alice <alice\0@example.com>"),
                            _set(GRAPH, ("commits", 1, "author"), "Alice <alice\0@example.com>"),
                            "E014", "GE072", "commits[1].author"),
    "a lone surrogate in the name": (_set(CLASSIC, ("commits", 1, "author"), "Alice\ud800 <alice@example.com>"),
                                     _set(GRAPH, ("commits", 1, "author"), "Alice\ud800 <alice@example.com>"),
                                     "E014", "GE072", "commits[1].author"),
    "a lone surrogate in the e-mail": (_set(CLASSIC, ("commits", 1, "author"), "Alice <alice\ud800@example.com>"),
                                       _set(GRAPH, ("commits", 1, "author"), "Alice <alice\ud800@example.com>"),
                                       "E014", "GE072", "commits[1].author"),
    # the schedule from the base date gives the later commits dates past 2099
    "a base date at the end of the range": (
        _set(_without_dates(CLASSIC), ("repository", "base_date"), "2099-12-31T23:59:59Z"),
        _set(_without_dates(GRAPH), ("repository", "base_date"), "2099-12-31T23:59:59Z"),
        "E013", "GE071", "repository.base_date"),
}


@pytest.mark.parametrize("graph", [False, True], ids=["classic", "graph"])
@pytest.mark.parametrize("case", list(REVIEW_CASES))
def test_a_value_git_would_record_otherwise_or_refuse_is_an_error_before_generation(tmp_path, graph, case):
    classic, graph_data, classic_code, graph_code, location = REVIEW_CASES[case]
    data, code = (graph_data, graph_code) if graph else (classic, classic_code)
    scenario = _write(tmp_path, GRAPH_FILE if graph else CLASSIC_FILE, data)
    assert _errors(_validate(scenario, graph)) == [(code, location)]
    generate, error = (generate_graph_repository, GraphGenerationError) if graph else (generate_repository, GenerationError)
    with pytest.raises(error, match="validation failed"):
        generate(scenario, tmp_path / "out")
    assert not (tmp_path / "out" / "repo").exists()


@pytest.mark.parametrize("graph", [False, True], ids=["classic", "graph"])
def test_a_base_date_whose_schedule_stays_in_range_generates(tmp_path, graph):
    """The schedule check refuses only dates past the range: early January 2099 leaves room for every commit."""
    base = GRAPH if graph else CLASSIC
    data = _set(_without_dates(base), ("repository", "base_date"), "2099-01-05T10:00:00Z")
    scenario = _write(tmp_path, GRAPH_FILE if graph else CLASSIC_FILE, data)
    assert _errors(_validate(scenario, graph)) == []
    generate = generate_graph_repository if graph else generate_repository
    commit_map, verify_result = generate(scenario, tmp_path / "out")
    assert not verify_result.has_errors()
    assert all(entry["author_date"].startswith("2099-") for entry in commit_map.values())


def test_an_offset_in_whole_minutes_is_accepted():
    from szzbench.validator import timestamp_problem
    assert timestamp_problem("2024-01-02T10:00:00+05:30") is None
    assert timestamp_problem("2024-01-02T10:00:00-00:45") is None
    assert "whole minutes" in timestamp_problem("2024-01-02T10:00:00+05:30:15")


def _inheriting(*, inherit: bool = True, committer_date: str | None = "2024-01-03T10:00:00Z") -> dict:
    """The review's derivation of SZZG-0001: a base date at the end of the range, c0 and c1 dated, and c2 a rebase
    of c1 that inherits its author date and names only its committer date."""
    data = _set(_without_dates(GRAPH), ("repository", "base_date"), "2099-12-31T23:59:59Z")
    data["commits"][0]["date"] = "2024-01-01T10:00:00Z"
    data["commits"][1]["date"] = "2024-01-02T10:00:00Z"
    c2 = data["commits"][2]
    c2["rebase_of"] = "c1"
    if inherit:
        c2["inherit_author_date"] = True
    if committer_date is not None:
        c2["committer_date"] = committer_date
    return data


def test_an_inherited_author_date_is_not_checked_on_the_schedule(tmp_path):
    """inherit_author_date replaces the scheduled author date by the rewrite source's (PR #236 review): the
    scheduled one, 2100-01-02, is never used, and the scenario generates."""
    scenario = _write(tmp_path, GRAPH_FILE, _inheriting())
    assert _errors(_validate(scenario, True)) == []
    commit_map, verify_result = generate_graph_repository(scenario, tmp_path / "out")
    assert not verify_result.has_errors()
    assert commit_map["c2"]["author_date"].startswith("2024-01-02T10:00:00")
    assert commit_map["c2"]["committer_date"].startswith("2024-01-03T10:00:00")


@pytest.mark.parametrize("variant", ["without inherit_author_date", "without a committer_date"])
def test_the_dates_the_schedule_still_gives_are_checked(tmp_path, variant):
    """Without the inheritance the author date comes from the schedule; without a committer_date, so does the
    committer date, inheritance or not."""
    data = _inheriting(inherit=False) if variant == "without inherit_author_date" else _inheriting(committer_date=None)
    scenario = _write(tmp_path, GRAPH_FILE, data)
    assert _errors(_validate(scenario, True)) == [("GE071", "repository.base_date")]


# --- non-string text, replay, and generation without validation (issue #151) ---

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
def test_the_classic_simulation_reports_an_unvalidated_value_as_e201(row):
    """``simulate_commits`` without ``validate_static`` first: an error, not an AttributeError."""
    mutate, _, location = CLASSIC_TEXT_ROWS[row]
    snapshots, result = simulate_commits(_mutated(CLASSIC, mutate))
    assert snapshots is None
    [finding] = result.findings
    field = location.rsplit(".", 1)[1]
    assert (finding.code, finding.location) == ("E201", location.rsplit(".", 1)[0])
    assert f".{field} must be a string" in finding.message


def test_classic_generation_fails_on_an_unvalidated_value(tmp_path, monkeypatch):
    _no_validation(monkeypatch)
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
    result = simulate_graph_scenario(_mutated(GRAPH, GRAPH_TEXT_ROWS[row][0]))
    first = next(f for f in result.findings if f.severity == "ERROR")
    assert (first.code, first.location) == ("GE201", location)
    assert first.message.endswith(message)


def test_graph_generation_writes_no_none_for_an_unvalidated_null(tmp_path, monkeypatch):
    _no_validation(monkeypatch)
    scenario = _write(tmp_path, GRAPH_FILE, _mutated(GRAPH, _op(0, 0, "content", None)))
    with pytest.raises(GraphGenerationError, match=r"write_file\.content must be a string, not null"):
        generate_graph_repository(scenario, tmp_path / "out")
    assert not (tmp_path / "out/repo" / OLD_RANGE).exists()


def test_graph_generation_commits_no_subject_for_an_unvalidated_message(tmp_path, monkeypatch):
    _no_validation(monkeypatch)
    scenario = _write(tmp_path, GRAPH_FILE, _mutated(GRAPH, _message(1, 123)))
    with pytest.raises(GraphGenerationError, match=r"^message of commit 'c1' must be a string, not int\.$"):
        generate_graph_repository(scenario, tmp_path / "out")
    assert git(tmp_path / "out/repo", "log", "--format=%s") == "Add the range check"
