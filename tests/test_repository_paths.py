"""What a scenario path may name (issues #135 and #136).

A scenario path may not reach the generated repository's own ``.git`` (issue
#135).  The check compared each path component with ``.git`` as a string.  On
the case-insensitive file systems macOS and Windows use by default,
``.GIT/config`` passed it, and generation wrote into the repository's own
metadata: ``.GIT/config`` replaced the configuration ``init_repo`` writes,
``.GIT/info/exclude`` kept later files out of every commit, and a graph
scenario could install an executable hook with ``chmod``.  Validation and
verification reported nothing.

A scenario path is a repository-relative POSIX path, whatever the host (issue
#136).  The check read the path with ``pathlib.Path``, so ``..\\escape.txt``
and ``C:\\x.txt`` were one file name each on macOS and Linux and ``..`` and an
absolute path on Windows; a NUL byte, a name of one space and a trailing
``/`` passed too.  ``validate --simulate`` reported nothing, ``generate``
ended in a ``ValueError`` traceback on the NUL byte and committed the others
under their literal names (``src/Dir/`` as the file ``src/Dir``).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest
import yaml

from support import git_env
from szzbench import paths
from szzbench.generator import GenerationError, generate_repository
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.paths import PathValidationError, safe_join, validate_repo_relative_path
from szzbench.validator import validate_static

JAVA = "src/main/java/example/Range.java"
RANGE = ("package example;\n\npublic class Range {\n"
         "    public boolean contains(int value, int min, int max) {\n"
         "        return value >= min && value <= max;\n    }\n}\n")
FAULTY, FIXED = "value > min && value < max", "value >= min && value <= max"


def classic_scenario() -> dict:
    return {
        "schema_version": "1.0",
        "meta": {"id": "SZZ-9900", "title": "Path fixture", "category": "fixture", "factors": ["line-modification"]},
        "repository": {"name": "path-fixture", "default_branch": "main", "language": "java"},
        "commits": [
            {"id": "c0", "message": "Add the range check", "role": "initial",
             "operations": [{"type": "write_file", "path": JAVA, "content": RANGE}]},
            {"id": "c1", "message": "Exclude the bounds", "role": "bug_introducing",
             "operations": [{"type": "replace", "path": JAVA, "old": FIXED, "new": FAULTY}]},
            {"id": "c2", "message": "Include the bounds again", "role": "bug_fixing",
             "operations": [{"type": "replace", "path": JAVA, "old": FAULTY, "new": FIXED}]},
        ],
        "bugs": [{"id": "B001", "bug_fixing_commit": "c2", "bug_introducing_commits": ["c1"],
                  "fault": {"commit": "c1", "file": JAVA, "statement": f"return {FAULTY};", "change_type": "line_modification"},
                  "fix": {"commit": "c2", "file": JAVA, "statement": f"return {FIXED};", "fix_type": "line_modification"}}],
    }


def graph_scenario() -> dict:
    data = classic_scenario()
    for i, commit in enumerate(data["commits"]):
        commit.update(branch="main", parents=[f"c{i - 1}"] if i else [])
    return {
        "schema_version": "graph-1.0",
        "meta": {**data["meta"], "id": "SZZG-9900"},
        "repository": data["repository"],
        "commits": data["commits"],
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
                  "faults": [{"commit": "c1", "file": JAVA, "statement": f"return {FAULTY};"}],
                  "fixes": [{"commit": "c2", "file": JAVA, "statement": f"return {FIXED};"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}},
    }


def write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path

# Each of these opens the repository's .git on some file system Git supports.
GIT_DIRECTORY_SPELLINGS = [
    ".GIT/config",
    ".Git/hooks/post-commit",
    ".gIt/info/exclude",
    "a/.GIT/b",
    ".git./config",            # Windows drops trailing dots ...
    ".git /config",            # ... and spaces
    ".git. . /config",
    "git~1/config",            # the NTFS 8.3 short name of .git ...
    "GIT~1/config",
    "git~1./config",           # ... which also answers with trailing dots or spaces
    "git~1 /config",
    "git~1. . /hooks/post-commit",
    ".git::$INDEX_ALLOCATION/config",      # an NTFS alternate data stream of the directory
    "git~1::$INDEX_ALLOCATION/config",
    ".GIT. ::$INDEX_ALLOCATION/hooks/post-commit",
    ".git:stream/config",      # Git refuses every stream, not only $INDEX_ALLOCATION
    ".git\\config",            # a backslash separates directories on Windows
    ".g\u200cit/config",       # HFS+ ignores U+200C ...
    "\ufeff.git/config",       # ... and U+FEFF
]

# Names that only look like .git, and that shipped scenarios or ordinary projects use.
ORDINARY_SPELLINGS = [
    ".gitignore",
    ".gitattributes",
    ".github/workflows/tests.yml",
    ".git-blame-ignore-revs",
    "src/.gitkeep",
    "git/notes.txt",
    ".gitx/config",
    "git~2/config",
    "git~10/config",
    "git~1x/config",
    "x.git/config",
    ".git-x:y/z",
]


@pytest.mark.parametrize("path", GIT_DIRECTORY_SPELLINGS)
def test_every_spelling_of_the_git_directory_is_refused(path, tmp_path):
    with pytest.raises(PathValidationError, match=r"\.git"):
        validate_repo_relative_path(path)
    with pytest.raises(PathValidationError):
        safe_join(tmp_path, path)


@pytest.mark.parametrize("path", ORDINARY_SPELLINGS)
def test_names_that_only_resemble_git_are_accepted(path, tmp_path):
    validate_repo_relative_path(path)
    assert safe_join(tmp_path, path) == (tmp_path / path).resolve()


def test_szzbench_refuses_exactly_what_git_refuses(tmp_path):
    """The rule is Git's (``verify_path`` with ``core.protectNTFS`` and ``core.protectHFS``).

    ``update-index --cacheinfo`` asks Git about a path in the index only, so the
    check creates nothing on disk and gives the same verdict on every platform
    (PR #208 review: the NTFS short name with trailing dots or spaces, and the
    ``::$INDEX_ALLOCATION`` stream, passed while Git refused them).
    """
    def run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=tmp_path, env=git_env(), capture_output=True, text=True)

    assert run("init", "-q", "--template=").returncode == 0
    blob = run("hash-object", "-w", "--stdin").stdout.strip()
    for path in [*GIT_DIRECTORY_SPELLINGS, *ORDINARY_SPELLINGS]:
        git_refuses = run("-c", "core.protectNTFS=true", "-c", "core.protectHFS=true",
                          "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}").returncode != 0
        try:
            validate_repo_relative_path(path)
            szzbench_refuses = False
        except PathValidationError:
            szzbench_refuses = True
        assert szzbench_refuses == git_refuses, (path, "git refuses" if git_refuses else "git accepts")


def _classic_writing(path: str) -> dict:
    data = deepcopy(classic_scenario())
    data["commits"][0]["operations"].append({"type": "write_file", "path": path, "content": "[core]\n"})
    return data


def _graph_writing(path: str) -> dict:
    data = deepcopy(graph_scenario())
    data["commits"][0]["operations"] += [
        {"type": "write_file", "path": path, "content": "#!/bin/sh\necho hook-ran\n"},
        {"type": "chmod", "path": path, "mode": "755"},
    ]
    return data


@pytest.mark.parametrize("path", [".GIT/config", ".git./config", "git~1/config"])
def test_validate_reports_e050_for_a_path_into_the_git_directory(path):
    findings = [(f.code, f.location) for f in validate_static(_classic_writing(path)).findings]
    assert ("E050", "commits[0].operations[1].path") in findings


@pytest.mark.parametrize("path", [".Git/hooks/post-commit", "a/.GIT/b"])
def test_validate_graph_reports_ge054_for_an_operation_path_into_the_git_directory(path):
    findings = [(f.code, f.location) for f in validate_graph_static(_graph_writing(path)).findings]
    assert ("GE054", "commits[0].operations[1].path") in findings
    assert ("GE054", "commits[0].operations[2].path") in findings


def test_validate_graph_reports_ge102_for_a_fault_file_in_the_git_directory():
    data = deepcopy(graph_scenario())
    data["bugs"][0]["faults"][0]["file"] = ".GIT/config"
    findings = [(f.code, f.location) for f in validate_graph_static(data).findings]
    assert ("GE102", "bugs[0].faults[0].file") in findings


def test_generate_refuses_a_classic_scenario_that_writes_into_the_git_directory(tmp_path):
    scenario = write_yaml(tmp_path / "SZZ-9900" / "scenario.yml", _classic_writing(".GIT/config"))
    with pytest.raises(GenerationError):
        generate_repository(scenario, tmp_path / "out", force=True)
    config = tmp_path / "out" / "repo" / ".git" / "config"
    assert not config.exists() or config.read_text() != "[core]\n"


def test_generate_graph_refuses_a_hook_written_through_another_spelling(tmp_path):
    scenario = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", _graph_writing(".GIT/hooks/post-commit"))
    with pytest.raises(GraphGenerationError):
        generate_graph_repository(scenario, tmp_path / "out", force=True)
    assert not (tmp_path / "out" / "repo" / ".git" / "hooks" / "post-commit").exists()


NTFS_ALIASES = ["git~1./config", "git~1 /config", ".git::$INDEX_ALLOCATION/config", "git~1::$INDEX_ALLOCATION/hooks/post-commit"]


@pytest.mark.parametrize("path", NTFS_ALIASES)
def test_both_generators_refuse_an_ntfs_alias_before_touching_the_file_system(tmp_path, path):
    """Refused at validation, before the output directory exists (PR #208 review)."""
    classic = write_yaml(tmp_path / "classic/SZZ-9900/scenario.yml", _classic_writing(path))
    with pytest.raises(GenerationError, match="validation failed"):
        generate_repository(classic, tmp_path / "classic-out", force=True)
    assert not (tmp_path / "classic-out").exists()
    graph = write_yaml(tmp_path / "graph/SZZG-9900/scenario.graph.yml", _graph_writing(path))
    with pytest.raises(GraphGenerationError, match="validation failed"):
        generate_graph_repository(graph, tmp_path / "graph-out", force=True)
    assert not (tmp_path / "graph-out").exists()


# --- the path grammar (issue #136) ----------------------------------------------------------

# Paths main accepted, with the part of the message that names the rule they break.
OUTSIDE_THE_GRAMMAR = [
    ("a\x00b.txt", "U+0000"),                 # ended generate in a ValueError traceback
    ("src/a\tb.java", "U+0009"),
    ("src/a\x7fb.java", "U+007F"),
    ("..\\escape.txt", "backslash"),          # '..' and 'escape.txt' on Windows, one name elsewhere
    ("src\\Win.java", "backslash"),
    ("C:\\x.txt", "drive prefix 'C:'"),       # absolute on Windows
    ("c:x.txt", "drive prefix 'c:'"),         # relative to the current directory of drive C:
    ("C:/x.txt", "drive prefix 'C:'"),
    (" ", "only whitespace"),                 # committed as a file named one space
    ("src/ /Win.java", "only whitespace"),
    ("src/\u3000/Win.java", "only whitespace"),
    ("src/Dir/", "trailing '/'"),             # written as the file src/Dir
    ("a//b.txt", "empty component"),
    ("./x.txt", "current directory '.'"),
    ("src/./Win.java", "current directory '.'"),
]

# The rows of the issue's table, in its order.
ISSUE_ROWS = ["a\x00b.txt", "..\\escape.txt", "src\\Win.java", "C:\\x.txt", " ", "src/Dir/"]

# Paths the grammar accepts: what the shipped scenarios write, and names next to a rule
# that break none (spaces inside a name, a colon that is not a drive prefix).
INSIDE_THE_GRAMMAR = [
    JAVA,
    "README.md",
    "docs/release notes.md",
    "src/Foo Bar.java",
    "docs/\u65e5\u672c\u8a9e.md",
    "x y/z ",
    "ab:c.txt",
    "src/C:x",
    *ORDINARY_SPELLINGS,
]


@pytest.mark.parametrize("path,rule", OUTSIDE_THE_GRAMMAR)
def test_a_path_outside_the_grammar_is_refused_with_the_rule_it_breaks(path, rule, tmp_path):
    with pytest.raises(PathValidationError, match=re.escape(rule)):
        validate_repo_relative_path(path)
    with pytest.raises(PathValidationError, match=re.escape(rule)):
        safe_join(tmp_path, path)


@pytest.mark.parametrize("path,rule", [("/etc/passwd", "absolute"), ("src/../../x.txt", "parent directory '..'"),
                                       ("..", "parent directory '..'"), ("", "non-empty")])
def test_the_earlier_rules_still_apply(path, rule):
    with pytest.raises(PathValidationError, match=re.escape(rule)):
        validate_repo_relative_path(path)


@pytest.mark.parametrize("path", INSIDE_THE_GRAMMAR)
def test_posix_and_windows_split_an_accepted_path_into_the_same_names(path, tmp_path):
    """Neither reads a drive or a root in an accepted path, nor a separator other than ``/``."""
    validate_repo_relative_path(path)
    assert PurePosixPath(path).parts == PureWindowsPath(path).parts == tuple(path.split("/"))
    assert not PureWindowsPath(path).anchor
    assert safe_join(tmp_path, path) == (tmp_path / path).resolve()


@pytest.mark.parametrize("host", [PurePosixPath, PureWindowsPath], ids=["posix", "windows"])
def test_the_verdict_does_not_depend_on_how_the_host_reads_paths(monkeypatch, host):
    """The check used ``pathlib.Path``: on Windows ``..\\escape.txt`` was ``..`` and ``C:\\x.txt``
    absolute, on macOS and Linux both were one file name.  Reading paths as either host gives
    the same verdicts now."""
    monkeypatch.setattr(paths, "Path", host)
    for path, rule in OUTSIDE_THE_GRAMMAR:
        with pytest.raises(PathValidationError, match=re.escape(rule)):
            validate_repo_relative_path(path)
    for path in INSIDE_THE_GRAMMAR:
        validate_repo_relative_path(path)


@pytest.mark.parametrize("path,rule", OUTSIDE_THE_GRAMMAR)
def test_validate_reports_e050_for_a_path_outside_the_grammar(path, rule):
    findings = [(f.code, f.location, f.message) for f in validate_static(_classic_writing(path)).findings]
    assert [(code, loc) for code, loc, message in findings if rule in message] == [("E050", "commits[0].operations[1].path")]


@pytest.mark.parametrize("path,rule", OUTSIDE_THE_GRAMMAR)
def test_validate_graph_reports_ge054_for_a_path_outside_the_grammar(path, rule):
    findings = [(f.code, f.location) for f in validate_graph_static(_graph_writing(path)).findings]
    assert ("GE054", "commits[0].operations[1].path") in findings
    assert ("GE054", "commits[0].operations[2].path") in findings


@pytest.mark.parametrize("path", ["src\\main\\java\\example\\Range.java", "src/main/java/example/Range.java/", "./" + JAVA])
def test_validate_graph_reports_ge102_for_a_fault_file_outside_the_grammar(path):
    data = deepcopy(graph_scenario())
    data["bugs"][0]["faults"][0]["file"] = path
    findings = [(f.code, f.location) for f in validate_graph_static(data).findings]
    assert ("GE102", "bugs[0].faults[0].file") in findings


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True)


def test_validate_simulate_reports_each_row_of_the_issue_as_e050(tmp_path):
    """Run on a path relative to the working directory, as the issue's reproduction does."""
    data = deepcopy(classic_scenario())
    data["commits"][0]["operations"] += [{"type": "write_file", "path": path, "content": "x\n"} for path in ISSUE_ROWS]
    write_yaml(tmp_path / "SZZ-9900" / "scenario.yml", data)
    completed = _szzbench(tmp_path, "validate", "--simulate", "--json", "SZZ-9900/scenario.yml")
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    errors = [(f["code"], f["location"]) for f in json.loads(completed.stdout)["findings"] if f["severity"] == "ERROR"]
    assert errors == [("E050", f"commits[0].operations[{i}].path") for i in range(1, len(ISSUE_ROWS) + 1)]


def test_validate_graph_simulate_strict_paths_reports_each_row_of_the_issue_as_ge054(tmp_path):
    data = deepcopy(graph_scenario())
    data["commits"][0]["operations"] += [{"type": "write_file", "path": path, "content": "x\n"} for path in ISSUE_ROWS]
    write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", data)
    completed = _szzbench(tmp_path, "validate-graph", "--simulate", "--strict-paths", "--json", "SZZG-9900/scenario.graph.yml")
    assert completed.returncode == 1 and "Traceback" not in completed.stderr, completed.stderr
    errors = [(f["code"], f["location"]) for f in json.loads(completed.stdout)["findings"] if f["severity"] == "ERROR"]
    assert errors == [("GE054", f"commits[0].operations[{i}].path") for i in range(1, len(ISSUE_ROWS) + 1)]


def _graph_generating_into(directory: str) -> dict:
    data = deepcopy(graph_scenario())
    data["commits"][1]["operations"].append(
        {"type": "commit_generator", "generator": "unrelated_changes", "count": 2, "path": directory})
    return data


@pytest.mark.parametrize("command,scenario,data,reason", [
    ("generate", "SZZ-9900/scenario.yml", _classic_writing("a\x00b.txt"), "validation failed"),
    ("generate-graph", "SZZG-9900/scenario.graph.yml", _graph_writing("a\x00b.txt"), "validation failed"),
    # commit_generator.path names a directory, which static validation does not read:
    # the NUL byte reaches safe_join during generation
    ("generate-graph", "SZZG-9900/scenario.graph.yml", _graph_generating_into("gen\x00dir"), "U+0000"),
], ids=["classic", "graph", "graph-commit-generator"])
def test_generation_refuses_a_nul_byte_without_a_traceback(tmp_path, command, scenario, data, reason):
    write_yaml(tmp_path / scenario, data)
    completed = _szzbench(tmp_path, command, scenario, "--out", "out")
    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr, completed.stderr
    assert "GENERATION_FAILED" in completed.stderr and reason in completed.stderr, completed.stderr


# commit_generator.path in spellings generation reads as a directory (commit_generator_directory)
COMMIT_GENERATOR_SPELLINGS = [
    "generated/telemetry/",            # a directory written with its trailing slash
    "generated\\telemetry",            # a backslash, read as '/'
    "./generated/telemetry",
    "generated//telemetry",
    "generated/telemetry/batch-1.txt",  # the old placeholder file: its parent directory
    "/",                               # the repository root
]


@pytest.mark.parametrize("directory", COMMIT_GENERATOR_SPELLINGS)
def test_the_simulation_accepts_the_commit_generator_paths_generation_accepts(tmp_path, directory):
    """The path rule refused ``generated/telemetry/`` in the simulator's placeholder, while
    generation reads the field as a directory and generated the scenario (PR #219 review)."""
    scenario = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", _graph_generating_into(directory))
    _, result = validate_graph_scenario_file(scenario, strict_paths=True, simulate=True)
    assert [(f.code, f.message) for f in result.findings if f.severity == "ERROR"] == []
    commit_map, verify_result = generate_graph_repository(scenario, tmp_path / "out", force=True)
    assert not verify_result.has_errors()
    assert len(commit_map) == len(graph_scenario()["commits"]) + 2


@pytest.mark.parametrize("directory", ["generated/../../escape", "gen\x00dir/"])
def test_the_simulation_and_generation_refuse_the_same_commit_generator_paths(tmp_path, directory):
    scenario = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", _graph_generating_into(directory))
    _, result = validate_graph_scenario_file(scenario, strict_paths=True, simulate=True)
    assert [f.code for f in result.findings if f.severity == "ERROR"] == ["GE201"]
    with pytest.raises(GraphGenerationError, match="invalid path"):
        generate_graph_repository(scenario, tmp_path / "out", force=True, verify=False)


@pytest.mark.parametrize("path", ISSUE_ROWS[1:])
def test_both_generators_refuse_the_other_rows_of_the_issue_before_writing(tmp_path, path):
    classic = write_yaml(tmp_path / "classic/SZZ-9900/scenario.yml", _classic_writing(path))
    with pytest.raises(GenerationError, match="validation failed"):
        generate_repository(classic, tmp_path / "classic-out", force=True)
    assert not (tmp_path / "classic-out").exists()
    graph = write_yaml(tmp_path / "graph/SZZG-9900/scenario.graph.yml", _graph_writing(path))
    with pytest.raises(GraphGenerationError, match="validation failed"):
        generate_graph_repository(graph, tmp_path / "graph-out", force=True)
    assert not (tmp_path / "graph-out").exists()


def _refused_by_the_file_system(*args, **kwargs):
    raise ValueError("lstat: embedded null character in path")


@pytest.mark.parametrize("kind", ["classic", "graph"])
def test_a_value_error_late_in_generation_is_a_generation_failure(tmp_path, monkeypatch, kind):
    """What still reaches the file system after validation fails like any other generation error."""
    if kind == "classic":
        monkeypatch.setattr("szzbench.generator.apply_operation_to_filesystem", _refused_by_the_file_system)
        scenario = write_yaml(tmp_path / "SZZ-9900" / "scenario.yml", classic_scenario())
        with pytest.raises(GenerationError, match="embedded null character"):
            generate_repository(scenario, tmp_path / "out")
    else:
        monkeypatch.setattr("szzbench.graph_generator.apply_graph_operation_to_filesystem", _refused_by_the_file_system)
        scenario = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", graph_scenario())
        with pytest.raises(GraphGenerationError, match="embedded null character"):
            generate_graph_repository(scenario, tmp_path / "out")
    error = json.loads((tmp_path / "out" / "metadata" / "generation-error.json").read_text(encoding="utf-8"))
    assert "embedded null character" in error["error"]
