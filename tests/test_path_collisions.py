"""Two spellings of one file, and a file below a file, agree between ``--simulate`` and generation (issue #153).

The classic ``validate --simulate`` kept the simulated repository as a flat
dict keyed by the path as written, and the graph simulator did not know more
about letter case.  Generation writes to a file system.  So a classic scenario
that wrote ``src/A.java/B.java`` beside the file ``src/A.java`` passed
``--simulate`` and failed ``generate`` with ``File exists``, and in both
suites ``src/a.java`` beside ``src/A.java`` passed: on macOS generation
overwrote ``A.java`` (``replace.old not found`` later, or a tree without the
file the scenario names), on Linux it wrote a second file.  The two spellings
``./src/A.java`` and ``src/A.java`` have been E050 / GE054 since issue #136.

Both simulators now refuse a file below a file, a file at a directory, and a
path that differs from one of the snapshot only in letter case or Unicode
normalization, name by name (``paths.file_path_conflict``, with the key
``paths.file_system_key`` that ref names use since issue #229).  The graph
generator, which ``generate-graph`` runs without the simulation and which
``--simulate`` itself runs for a scenario with commits Git computes, refuses
a path that reaches an entry of the worktree spelt otherwise.
"""
from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import szzbench.paths as paths
from szzbench.findings import ValidationResult
from szzbench.generator import GenerationError, generate_repository
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_simulator import simulated_snapshots
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.validator import simulate_commits, validate_scenario_file

from support import git_stdout

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = yaml.safe_load((ROOT / "scenarios/SZZ-0005/scenario.yml").read_text(encoding="utf-8"))
CLASSIC_FILE = "SZZ-0005/scenario.yml"
GRAPH_FILE = "SZZG-9900/scenario.graph.yml"
REQUEST = "src/main/java/example/UserRequest.java"          # SZZ-0005's c0.operations[1]
NFC, NFD = "src/café.txt", "src/café.txt"            # one name on macOS, two on Linux
PLATFORM = "macOS (and Windows, for letter case) reads both as one name, so generation would depend on the platform"


def _write_file(path: str, content: str) -> dict:
    return {"type": "write_file", "path": path, "content": content}


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True)


def _json_errors(completed: subprocess.CompletedProcess) -> list[tuple[str, str]]:
    return [(f["code"], f["location"]) for f in json.loads(completed.stdout)["findings"] if f["severity"] == "ERROR"]


def _errors(result: ValidationResult) -> list[tuple[str, str, str]]:
    return [(f.code, f.location, f.message) for f in result.findings if f.severity == "ERROR"]


# --- classic: the issue's four rows -----------------------------------------------------

def _dot_slash(data: dict) -> None:
    data["commits"][0]["operations"][1]["path"] = f"./{REQUEST}"


def _resave_as(path: str):
    def mutate(data: dict) -> None:
        content = data["commits"][0]["operations"][1]["content"]
        # dated between c0 and c1: undated, it took the schedule's date, after c1's (E016, issue #241)
        data["commits"].insert(1, {"id": "c0b", "message": "Re-save the request class", "role": "refactoring",
                                   "date": "2023-10-17T10:00:00Z", "operations": [_write_file(path, content)]})
    return mutate


def _also_write(path: str):
    def mutate(data: dict) -> None:
        data["commits"][0]["operations"].append(_write_file(path, "class Extra {}\n"))
    return mutate


#: row: (change to SZZ-0005, the errors of validate --simulate, a part of the first one's message)
ROWS = {
    # (a) and (b): the grammar of issue #136 leaves one spelling per path
    "dot-slash": (_dot_slash, [("E050", "commits[0].operations[1].path")], "current directory '.' is not allowed"),
    "two-spellings": (_resave_as(f"./{REQUEST}"), [("E050", "commits[1].operations[0].path")],
                      "current directory '.' is not allowed"),
    # (b) in the spellings the grammar allows: on macOS the commit would be empty, on Linux a new file
    "two-spellings-by-case": (_resave_as(REQUEST.lower()), [("E2XX", "commits[1].operations[0]")],
                              f"write_file target {REQUEST.lower()} differs only in letter case or Unicode "
                              f"normalization from the file {REQUEST}: {PLATFORM}"),
    # (c): on macOS the write replaced UserRequest.java, and c1's replace found no @Required(true)
    "case": (_also_write("src/main/java/example/userrequest.java"), [("E2XX", "commits[0].operations[2]")],
             "write_file target src/main/java/example/userrequest.java differs only in letter case or Unicode "
             f"normalization from the file {REQUEST}: {PLATFORM}"),
    # (d): generation stopped with [Errno 17] File exists
    "parent-is-file": (_also_write("src/main/java/example/Required.java/Extra.java"), [("E2XX", "commits[0].operations[2]")],
                       "write_file target lies below the file src/main/java/example/Required.java: "
                       "src/main/java/example/Required.java/Extra.java"),
}


def _classic(root: Path, row: str) -> Path:
    data = deepcopy(CLASSIC)
    ROWS[row][0](data)
    path = root / CLASSIC_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


@pytest.mark.parametrize("row", list(ROWS))
def test_validate_simulate_and_generate_give_one_verdict(tmp_path, row):
    """Through the CLI, on paths relative to the working directory."""
    _classic(tmp_path, row)
    _, expected, says = ROWS[row]
    completed = _szzbench(tmp_path, "validate", "--simulate", "--json", CLASSIC_FILE)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert _json_errors(completed) == expected
    assert says in json.loads(completed.stdout)["findings"][0]["message"]
    completed = _szzbench(tmp_path, "generate", CLASSIC_FILE, "--out", "out")
    assert completed.returncode == 1
    assert completed.stderr.startswith("[ERROR] GENERATION_FAILED: Scenario validation failed."), completed.stderr
    assert not (tmp_path / "out").exists()


def test_generate_refuses_the_rows_through_the_api(tmp_path):
    for row in ("case", "parent-is-file"):
        with pytest.raises(GenerationError, match="Scenario validation failed"):
            generate_repository(_classic(tmp_path / row, row), tmp_path / row / "out")


def test_the_unchanged_scenario_still_validates_and_generates(tmp_path):
    path = tmp_path / CLASSIC_FILE
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(CLASSIC, sort_keys=False), encoding="utf-8")
    _, result, _ = validate_scenario_file(path, simulate=True)
    assert _errors(result) == []
    generate_repository(path, tmp_path / "out")


# --- both simulators: which pairs conflict ----------------------------------------------

#: (a file of the snapshot, the path written next, a part of the message or None)
PAIRS = [
    ("src/A.java", "src/a.java", f"target src/a.java differs only in letter case or Unicode normalization from the "
                                 f"file src/A.java: {PLATFORM}"),
    ("src/Foo/A.java", "src/foo/B.java", "target src/foo/B.java: its directory src/foo differs only in letter case or "
                                         "Unicode normalization from the directory src/Foo:"),
    ("src/A.java", "src/a.java/B.java", "target src/a.java/B.java: its directory src/a.java differs only in letter "
                                        "case or Unicode normalization from the file src/A.java:"),
    ("src/Foo/A.java", "src/foo", "target src/foo differs only in letter case or Unicode normalization from the "
                                  "directory src/Foo:"),
    ("SRC/A.java", "src/B.java", "its directory src differs only in letter case or Unicode normalization from the "
                                 "directory SRC:"),
    # Unicode normalization: the two are told apart in the message
    (NFC, NFD, f"target {NFD} differs only in letter case or Unicode normalization from the file {NFC} "
               "(spelt 'src/cafe\\u0301.txt' and 'src/caf\\xe9.txt'):"),
    (NFD, NFC.upper(), "differs only in letter case or Unicode normalization"),
    # a code point HFS+ ignores, as for E050 and the ref names of issue #229
    ("src/A.java", "src/A‌.java", "from the file src/A.java (spelt 'src/A\\u200c.java' and 'src/A.java')"),
    # full case folding: APFS takes straße.txt and STRASSE.txt for one name
    ("src/straße.txt", "src/STRASSE.txt", "differs only in letter case or Unicode normalization"),
    # the two of issue #175, which the classic simulator did not know
    ("src/A.java", "src/A.java/B.java", "target lies below the file src/A.java: src/A.java/B.java"),
    ("src/lib/a.txt", "src/lib", "target is a directory: src/lib"),
    # no conflict
    ("src/A.java", "src/A.java", None),
    ("src/A.java", "src/B.java", None),
    ("src/A.java", "src/A.javax", None),
    ("src/Ab/x.txt", "src/A/x.txt", None),
    ("src/A.java", "srcA.java", None),
    ("src/a.txt", "src/a.txt.bak/b.txt", None),
]
PAIR_IDS = ["case", "directory-case", "directory-case-of-a-file", "file-case-of-a-directory", "top-directory-case",
            "nfc-nfd", "nfd-nfc-upper", "hfs-ignored", "full-case-folding", "below-a-file", "a-directory",
            "same-file", "other-file", "longer-name", "longer-directory", "no-directory", "prefix-of-a-name"]


def _classic_snapshots(first: str, second: str) -> ValidationResult:
    data = {"commits": [{"id": "c0", "message": "Add a file", "operations": [_write_file(first, "one\n")]},
                        {"id": "c1", "message": "Add another", "operations": [_write_file(second, "two\n")]}]}
    return simulate_commits(data)[1]


def _graph_data(*commits: dict) -> dict:
    return {"schema_version": "graph-1.0",
            "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
            "repository": {"name": "probe", "default_branch": "main"}, "graph": {"model": "commit_dag"},
            "commits": list(commits),
            "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                      "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}]}],
            "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}}


def _graph_commit(cid: str, parents: list[str], *operations: dict) -> dict:
    return {"id": cid, "branch": "main", "parents": parents, "message": f"Update the sources ({cid})",
            "role": "intermediate", "operations": list(operations)}


def _graph_snapshots(first: str, second: str) -> ValidationResult:
    result = ValidationResult()
    simulated_snapshots(_graph_data(_graph_commit("c0", [], _write_file(first, "one\n")),
                                    _graph_commit("c1", ["c0"], _write_file(second, "two\n"))), result)
    return result


@pytest.mark.parametrize("first, second, says", PAIRS, ids=PAIR_IDS)
def test_the_classic_simulation_refuses_what_a_file_system_cannot_hold(first, second, says):
    errors = _errors(_classic_snapshots(first, second))
    if says is None:
        assert errors == []
    else:
        [(code, location, message)] = errors
        assert (code, location) == ("E2XX", "commits[1].operations[0]")
        assert message.startswith("Operation failed in commit 'c1': write_file target ") and says in message, message


@pytest.mark.parametrize("first, second, says", PAIRS, ids=PAIR_IDS)
def test_the_graph_simulation_refuses_what_a_file_system_cannot_hold(first, second, says):
    errors = _errors(_graph_snapshots(first, second))
    if says is None:
        assert errors == []
    else:
        [(code, location, message)] = errors
        assert (code, location) == ("GE201", "commits[1].operations[0]")
        assert message.startswith("Graph simulation failed for commit 'c1': write_file target ") and says in message, message


@pytest.mark.parametrize("first, second, says", PAIRS, ids=PAIR_IDS)
def test_the_worktree_check_finds_the_same_spellings(tmp_path, first, second, says):
    """``paths.another_spelling_on_disk`` reads the worktree the graph generator writes.

    A file below a file and a file at a directory are left to the operation,
    which fails with the OS's reason on every platform (issue #175).
    """
    (tmp_path / first).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / first).write_text("one\n", encoding="utf-8")
    found = paths.another_spelling_on_disk(tmp_path, second)
    if says is None or says.startswith(("target lies below", "target is a directory")):
        assert found is None
    else:
        mine, theirs = found
        assert mine == "/".join(second.split("/")[:mine.count("/") + 1])
        assert theirs == "/".join(first.split("/")[:theirs.count("/") + 1]) and mine != theirs
        assert paths.file_system_key(mine) == paths.file_system_key(theirs)


def test_a_file_written_again_in_its_own_spelling_is_no_conflict():
    data = {"commits": [{"id": "c0", "message": "Add", "operations": [_write_file("src/A.java", "one\n")]},
                        {"id": "c1", "message": "Change", "operations": [_write_file("src/A.java", "two\n"),
                                                                          _write_file("src/A.java", "three\n")]}]}
    snapshots, result = simulate_commits(data)
    assert _errors(result) == [] and snapshots["c1"] == {"src/A.java": "three\n"}


def test_the_key_is_taken_name_by_name():
    """``file_path_conflict`` compares names one by one with the key of a whole path in mind."""
    for path in ("src/Café/A‌.java", "SRC/STRASSE/K.txt", "a/b/c"):
        assert paths.file_system_key(path) == "/".join(paths.file_system_key(name) for name in path.split("/"))


# --- graph: simulation and generation, for each operation that writes a file -------------

RANGE = _write_file("src/Range.java", "class Range {}\n")
OTHER = _write_file("src/Other.java", "class Other {}\n")
GENERATOR = {"type": "commit_generator", "generator": "noise", "count": 2, "path": "generated"}


def _two_commits(*operations: dict) -> dict:
    return _graph_data(_graph_commit("c0", [], RANGE, OTHER), _graph_commit("c1", ["c0"], *operations))


#: name: (scenario, the errors of validate-graph --simulate as (code, location, message part),
#:        the error generate-graph stops with)
GRAPH_SHAPES = {
    "write_file": (
        _two_commits(_write_file("src/range.java", "class range {}\n")),
        [("GE201", "commits[1].operations[0]", "write_file target src/range.java differs only in letter case")],
        "write_file 'src/range.java': 'src/range.java' differs only in letter case or Unicode normalization from "
        f"'src/Range.java', which the worktree has: {PLATFORM}"),
    "write_file-directory": (
        _two_commits(_write_file("SRC/Next.java", "class Next {}\n")),
        [("GE201", "commits[1].operations[0]", "write_file target SRC/Next.java: its directory SRC differs only")],
        "write_file 'SRC/Next.java': 'SRC' differs only in letter case or Unicode normalization from 'src'"),
    "write_file-nfd": (
        _graph_data(_graph_commit("c0", [], _write_file(NFC, "one\n")), _graph_commit("c1", ["c0"], _write_file(NFD, "two\n"))),
        [("GE201", "commits[1].operations[0]", "(spelt 'src/cafe\\u0301.txt' and 'src/caf\\xe9.txt')")],
        "'src/cafe\\u0301.txt' differs only in letter case or Unicode normalization from 'src/caf\\xe9.txt'"),
    "copy_file": (
        _two_commits({"type": "copy_file", "from": "src/Other.java", "to": "src/range.java"}),
        [("GE201", "commits[1].operations[0]", "copy_file target src/range.java differs only in letter case")],
        "copy_file 'src/Other.java' -> 'src/range.java': 'src/range.java' differs only in letter case"),
    "move_file": (
        _two_commits({"type": "move_file", "from": "src/Other.java", "to": "Src/Moved.java"}),
        [("GE201", "commits[1].operations[0]", "move_file target Src/Moved.java: its directory Src differs only")],
        "move_file 'src/Other.java' -> 'Src/Moved.java': 'Src' differs only in letter case"),
    "copy_entity": (
        _two_commits({"type": "copy_entity", "entity": {"name": "Other"}, "from_file": "src/Other.java",
                      "to_file": "src/RANGE.java"}),
        [("GE201", "commits[1].operations[0]", "copy_entity target src/RANGE.java differs only in letter case")],
        "copy_entity 'src/Other.java' -> 'src/RANGE.java': 'src/RANGE.java' differs only in letter case"),
    "write_binary_file": (
        _two_commits({"type": "write_binary_file", "path": "src/range.java", "content_base64": "/wD/AA=="}),
        [("GE201", "commits[1].operations[0]", "write_binary_file target src/range.java differs only in letter case")],
        "write_binary_file 'src/range.java': 'src/range.java' differs only in letter case"),
    "write_generated_text_file": (
        _two_commits({"type": "write_generated_text_file", "path": "src/range.java", "lines": 2, "template": "row {line}"}),
        [("GE201", "commits[1].operations[0]", "write_generated_text_file target src/range.java differs only")],
        "write_generated_text_file 'src/range.java': 'src/range.java' differs only in letter case"),
    "commit_generator": (
        _graph_data(_graph_commit("c0", [], _write_file("Generated/x.txt", "x\n")), _graph_commit("c1", ["c0"], GENERATOR),
                    _graph_commit("c2", ["c1"], _write_file("a.txt", "a\n"))),
        [("GE201", "commits[1].operations[0]", "commit_generator target generated/noise-01.txt: its directory "
                                               "generated differs only in letter case")],
        "commit_generator of commit 'c1' cannot write 'generated/noise-01.txt': 'generated' differs only in letter "
        "case or Unicode normalization from 'Generated', which the worktree has"),
    # two commit_generators of one import whose files differ only in spelling: macOS kept one file, fast-import
    # wrote both entries, and verification passed (PR #234 review)
    "commit_generator-directories-of-one-import": (
        _graph_data(_graph_commit("c0", [], _write_file("a.txt", "a\n")),
                    _graph_commit("c1", ["c0"], dict(GENERATOR, count=1),
                                  dict(GENERATOR, count=1, path="Generated")),
                    _graph_commit("c2", ["c1"], _write_file("b.txt", "b\n"))),
        [("GE201", "commits[1].operations[1]", "commit_generator target Generated/noise-01.txt: its directory "
                                               "Generated differs only in letter case")],
        "commit_generator of commit 'c1' cannot write 'Generated/noise-01.txt' beside the files it generates: target "
        "Generated/noise-01.txt: its directory Generated differs only in letter case"),
    "commit_generator-names-of-one-import": (
        _graph_data(_graph_commit("c0", [], _write_file("a.txt", "a\n")),
                    _graph_commit("c1", ["c0"], dict(GENERATOR, count=1),
                                  dict(GENERATOR, count=1, generator="Noise")),
                    _graph_commit("c2", ["c1"], _write_file("b.txt", "b\n"))),
        [("GE201", "commits[1].operations[1]", "commit_generator target generated/Noise-01.txt differs only in letter case")],
        "commit_generator of commit 'c1' cannot write 'generated/Noise-01.txt' beside the files it generates: target "
        "generated/Noise-01.txt differs only in letter case"),
    # format_file reads and rewrites its file: on macOS it formatted src/Range.java (PR #234 review)
    "format_file": (
        _graph_data(_graph_commit("c0", [], _write_file("src/Range.java", "class Range {}   \n")),
                    _graph_commit("c1", ["c0"], {"type": "format_file", "path": "src/range.java"})),
        [("GE201", "commits[1].operations[0]", "format_file target does not exist: src/range.java")],
        "format_file 'src/range.java': 'src/range.java' differs only in letter case"),
    "format_file-directory": (
        _graph_data(_graph_commit("c0", [], _write_file("src/Range.java", "class Range {}   \n")),
                    _graph_commit("c1", ["c0"], {"type": "format_file", "path": "SRC/Range.java"})),
        [("GE201", "commits[1].operations[0]", "format_file target does not exist: SRC/Range.java")],
        "format_file 'SRC/Range.java': 'SRC' differs only in letter case"),
    # a path an operation reads: the simulation has no such file, and generation on macOS changed Range.java
    "replace": (
        _two_commits({"type": "replace", "path": "src/range.java", "old": "Range", "new": "Span"}),
        [("GE201", "commits[1].operations[0]", "replace target does not exist: src/range.java")],
        "replace 'src/range.java': 'src/range.java' differs only in letter case"),
    # a scenario with a merge is simulated by generating it (issue #94)
    "write_file-with-a-merge": (
        _graph_data(_graph_commit("c0", [], RANGE),
                    dict(_graph_commit("b1", ["c0"], OTHER), branch="side"),
                    _graph_commit("c1", ["c0"], _write_file("src/range.java", "class range {}\n")),
                    _graph_commit("m1", ["c1", "b1"])),
        [("GE203", "commits[2]", "Generating the scenario with Git failed at commit 'c1': write_file 'src/range.java': "
                                 "'src/range.java' differs only in letter case")],
        "write_file 'src/range.java': 'src/range.java' differs only in letter case"),
    # the review's merge variants: --simulate generates them, and generation refuses them now
    "commit_generator-of-one-import-with-a-merge": (
        _graph_data(_graph_commit("c0", [], RANGE),
                    dict(_graph_commit("b1", ["c0"], OTHER), branch="side"),
                    _graph_commit("c1", ["c0"], dict(GENERATOR, count=1), dict(GENERATOR, count=1, path="Generated")),
                    _graph_commit("m1", ["c1", "b1"])),
        [("GE203", "commits[2]", "Generating the scenario with Git failed at commit 'c1': commit_generator of commit "
                                 "'c1' cannot write 'Generated/noise-01.txt' beside the files it generates")],
        "commit_generator of commit 'c1' cannot write 'Generated/noise-01.txt' beside the files it generates"),
    "format_file-with-a-merge": (
        _graph_data(_graph_commit("c0", [], _write_file("src/Range.java", "class Range {}   \n")),
                    dict(_graph_commit("b1", ["c0"], OTHER), branch="side"),
                    _graph_commit("c1", ["c0"], {"type": "format_file", "path": "src/range.java"}),
                    _graph_commit("m1", ["c1", "b1"])),
        [("GE203", "commits[2]", "Generating the scenario with Git failed at commit 'c1': format_file 'src/range.java': "
                                 "'src/range.java' differs only in letter case")],
        "format_file 'src/range.java': 'src/range.java' differs only in letter case"),
}


def _write_graph(root: Path, data: dict) -> Path:
    path = root / GRAPH_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


@pytest.mark.parametrize("name", GRAPH_SHAPES)
def test_validate_graph_simulate_and_generate_graph_give_one_verdict(tmp_path, name):
    data, simulated, generation_error = GRAPH_SHAPES[name]
    scenario = _write_graph(tmp_path, data)
    _, result = validate_graph_scenario_file(scenario, simulate=True, strict_paths=True)
    errors = _errors(result)
    assert [(code, location) for code, location, _ in errors] == [(code, location) for code, location, _ in simulated], errors
    for (_, _, message), (_, _, part) in zip(errors, simulated):
        assert part in message, message
    with pytest.raises(GraphGenerationError) as raised:
        generate_graph_repository(scenario, tmp_path / "out", force=True)
    assert generation_error in str(raised.value)


def test_a_format_file_path_is_checked_like_the_other_paths():
    """format_file was missing from PATH_FIELDS_BY_OPERATION: its path had no GE054 either (PR #234 review)."""
    data = _graph_data(_graph_commit("c0", [], RANGE), _graph_commit("c1", ["c0"], {"type": "format_file", "path": "../Range.java"}))
    assert [(code, location) for code, location, _ in _errors(validate_graph_static(data))] == \
        [("GE054", "commits[1].operations[0].path")]


def test_validate_graph_and_generate_graph_through_the_cli(tmp_path):
    """On paths relative to the working directory."""
    _write_graph(tmp_path, GRAPH_SHAPES["write_file"][0])
    completed = _szzbench(tmp_path, "validate-graph", "--simulate", "--json", GRAPH_FILE)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert _json_errors(completed) == [("GE201", "commits[1].operations[0]")]
    completed = _szzbench(tmp_path, "generate-graph", GRAPH_FILE, "--out", "out")
    assert completed.returncode == 1
    assert completed.stderr.startswith("[ERROR] GRAPH_GENERATION_FAILED: write_file 'src/range.java': "
                                       "'src/range.java' differs only in letter case"), completed.stderr


def test_a_file_renamed_in_its_letter_case_over_two_commits_generates(tmp_path):
    """Deleting ``Range.java`` and writing ``range.java`` in a later commit is no conflict anywhere."""
    data = _graph_data(_graph_commit("c0", [], RANGE, OTHER),
                       _graph_commit("c1", ["c0"], {"type": "delete_file", "path": "src/Range.java"}),
                       _graph_commit("c2", ["c1"], _write_file("src/range.java", "class range {}\n")))
    scenario = _write_graph(tmp_path, data)
    _, result = validate_graph_scenario_file(scenario, simulate=True, strict_paths=True)
    assert _errors(result) == []
    commit_map, _ = generate_graph_repository(scenario, tmp_path / "out", force=True)
    assert git_stdout(tmp_path / "out/repo", "ls-tree", "-r", "--name-only", commit_map["c2"]["hash"]).split() == \
        ["src/Other.java", "src/range.java"]


def test_a_file_written_again_in_its_own_spelling_generates(tmp_path):
    data = _two_commits(_write_file("src/Range.java", "class Range { int x; }\n"))
    scenario = _write_graph(tmp_path, data)
    _, result = validate_graph_scenario_file(scenario, simulate=True, strict_paths=True)
    assert _errors(result) == []
    generate_graph_repository(scenario, tmp_path / "out", force=True)


# --- GE060 compares the paths with the same key -----------------------------------------

@pytest.mark.parametrize("source, target", [
    ("src/Range.java", "src/range.java"),
    (NFC, NFD),
    ("src/Range.java", "src/Range‌.java"),
], ids=["case", "nfc-nfd", "hfs-ignored"])
def test_a_rename_within_one_name_is_ge060(source, target):
    data = _graph_data(_graph_commit("c0", [], _write_file(source, "x\n")),
                       _graph_commit("c1", ["c0"], {"type": "rename_file", "from": source, "to": target}))
    [(code, location, message)] = _errors(validate_graph_static(data))
    assert (code, location) == ("GE060", "commits[1].operations[0].to")
    assert "changes only the letter case or the Unicode normalization" in message
