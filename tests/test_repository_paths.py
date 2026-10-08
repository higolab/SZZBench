"""A scenario path may not reach the generated repository's own ``.git`` (issue #135).

The check compared each path component with ``.git`` as a string.  On the
case-insensitive file systems macOS and Windows use by default, ``.GIT/config``
passed it, and generation wrote into the repository's own metadata:
``.GIT/config`` replaced the configuration ``init_repo`` writes,
``.GIT/info/exclude`` kept later files out of every commit, and a graph
scenario could install an executable hook with ``chmod``.  Validation and
verification reported nothing.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from szzbench.generator import GenerationError, generate_repository
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_static
from szzbench.paths import PathValidationError, safe_join, validate_repo_relative_path
from szzbench.validator import validate_static

import yaml

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
    "git~1/config",            # the NTFS 8.3 short name of .git
    "GIT~1/config",
    ".g‌it/config",       # HFS+ ignores U+200C ...
    "﻿.git/config",       # ... and U+FEFF
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


def test_no_shipped_scenario_names_such_a_path():
    """The rule changes no shipped scenario's outcome: none of them writes such a path."""
    root = Path(__file__).resolve().parents[1]
    for scenario in [*root.glob("scenarios/SZZ-*/scenario.yml"), *root.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")]:
        data = yaml.safe_load(scenario.read_text(encoding="utf-8"))
        validate = validate_graph_static if scenario.name == "scenario.graph.yml" else validate_static
        codes = {f.code for f in validate(data).findings if f.severity == "ERROR"}
        assert not codes & {"E050", "GE054", "GE102"}, scenario
