"""A scenario that writes a file Git reads: ``.gitignore``, ``.gitattributes``, ``.gitmodules`` (issue #164).

Both simulators take a file an operation writes to be committed as written.
The generators stage with ``git add -A``, and Git reads the ``.gitignore`` and
``.gitattributes`` the scenario itself wrote.  So a ``.gitignore`` with
``*.log`` followed by ``logs/app.log`` validated and generated with 0 errors
while ``app.log`` was in no tree; a commit whose only change was that file
failed generation with "commit would be empty"; and ``* text=auto`` stored a
``line_ending: crlf`` file as an LF blob.  Neither ``validate --simulate`` nor
the verification said anything.

``validate`` and ``validate-graph`` now refuse an operation that writes one of
these files, in any directory and in any spelling macOS reads as one (E051 /
GE063); ``.gitattributes`` is allowed when ``meta.factors`` declares
``gitattributes-bic``, as SZZG-0134 does.  Behind that check both generators
stop when ``git add -A`` leaves out a file the commit's operations wrote, and
name the file and the ignore rule.
"""
from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from support import git_bytes, git_stdout
from szzbench import graph_validator, validator
from szzbench.generator import GenerationError, generate_repository
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_operations import (REQUIRED_FIELDS_BY_OPERATION, SUPPORTED_GRAPH_OPERATIONS,
                                       WRITTEN_PATH_FIELDS_BY_OPERATION, commit_generator_changes,
                                       commit_generator_plan)
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.validator import git_control_file, validate_scenario_file, validate_static

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = yaml.safe_load((ROOT / "scenarios/SZZ-0005/scenario.yml").read_text(encoding="utf-8"))
CLASSIC_FILE = "SZZ-0005/scenario.yml"
GRAPH_FILE = "SZZG-9900/scenario.graph.yml"
REQUEST = "src/main/java/example/UserRequest.java"          # SZZ-0005's c0.operations[1]
FACTOR = "gitattributes-bic"


def _write_file(path: str, content: str) -> dict:
    return {"type": "write_file", "path": path, "content": content}


# --- the issue's three variants of SZZ-0005 ---------------------------------------------

def _ignored(data: dict) -> None:
    """A: c0 writes .gitignore, c1 writes an ignored file next to its real change."""
    data["commits"][0]["operations"].insert(0, _write_file(".gitignore", "*.log\n"))
    data["commits"][1]["operations"].append(_write_file("logs/app.log", "started\n"))


def _ignored_only(data: dict) -> None:
    """B: a commit whose only change is the ignored file."""
    data["commits"][0]["operations"].insert(0, _write_file(".gitignore", "*.log\n"))
    data["commits"].insert(1, {"id": "c0b", "message": "Add the application log", "author": "Aiko Mori <aiko.mori@example.com>",
                               "date": "2023-10-17T10:00:00Z", "role": "distractor",
                               "operations": [_write_file("logs/app.log", "started\n")]})


def _attributes(data: dict) -> None:
    """C: c0 writes .gitattributes with text=auto, and UserRequest.java with line_ending: crlf."""
    data["commits"][0]["operations"].insert(0, _write_file(".gitattributes", "* text=auto\n"))
    data["commits"][0]["operations"][2]["line_ending"] = "crlf"


VARIANTS = {"ignored": _ignored, "ignored-only": _ignored_only, "attributes": _attributes}
#: the file each variant writes as c0.operations[0]
CONTROL_FILE = {"ignored": ".gitignore", "ignored-only": ".gitignore", "attributes": ".gitattributes"}


def _classic(variant: str | None = None, *, factors: tuple[str, ...] = ()) -> dict:
    data = deepcopy(CLASSIC)
    if variant is not None:
        VARIANTS[variant](data)
    data["meta"]["factors"] = [*data["meta"]["factors"], *factors]
    return data


def _as_graph(data: dict) -> dict:
    """The classic scenario as a linear graph scenario."""
    commits = deepcopy(data["commits"])
    for i, commit in enumerate(commits):
        commit.update(branch="main", parents=[commits[i - 1]["id"]] if i else [])
    bug = data["bugs"][0]
    fault, fix = bug["fault"], bug["fix"]
    return {
        "schema_version": "graph-1.0",
        "meta": {**deepcopy(data["meta"]), "id": "SZZG-9900"},
        "repository": deepcopy(data["repository"]),
        "commits": commits,
        "bugs": [{"id": bug["id"],
                  "bug_introducing_commits": [{"commit": cid, "role": "direct"} for cid in bug["bug_introducing_commits"]],
                  "bug_fixing_commits": [{"commit": bug["bug_fixing_commit"], "role": "complete_fix"}],
                  "faults": [{"commit": fault["commit"], "file": fault["file"], "statement": fault["statement"]}],
                  "fixes": [{"commit": fix["commit"], "file": fix["file"], "statement": fix["statement"]}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": list(bug["bug_introducing_commits"])}},
    }


def _graph(variant: str | None = None, *, factors: tuple[str, ...] = ()) -> dict:
    return _as_graph(_classic(variant, factors=factors))


def _save(root: Path, relative: str, data: dict) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _errors(result) -> list[tuple[str, str]]:
    return [(f.code, f.location) for f in result.findings if f.severity == "ERROR"]


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True)


def _json_errors(completed: subprocess.CompletedProcess) -> list[tuple[str, str, str]]:
    return [(f["code"], f["location"], f["message"]) for f in json.loads(completed.stdout)["findings"]
            if f["severity"] == "ERROR"]


# --- validation refuses the three variants ----------------------------------------------

# Static errors stop before simulation. The CLI checks both modes on one
# representative input per suite; the API keeps all three variants.
@pytest.mark.parametrize("variant", VARIANTS)
def test_validate_refuses_each_variant(tmp_path, variant):
    path = _save(tmp_path, CLASSIC_FILE, _classic(variant))
    _, result, _ = validate_scenario_file(path)
    assert _errors(result) == [("E051", "commits[0].operations[0].path")]
    [finding] = [f for f in result.findings if f.code == "E051"]
    assert f"writes '{CONTROL_FILE[variant]}', a file Git reads: " in finding.message


@pytest.mark.parametrize("variant", VARIANTS)
def test_validate_graph_refuses_each_variant(tmp_path, variant):
    path = _save(tmp_path, GRAPH_FILE, _graph(variant))
    _, result = validate_graph_scenario_file(path)
    assert _errors(result) == [("GE063", "commits[0].operations[0].path")]
    [finding] = [f for f in result.findings if f.code == "GE063"]
    assert f"writes '{CONTROL_FILE[variant]}', a file Git reads: " in finding.message


def test_the_classic_commands_refuse_a_control_file(tmp_path):
    """Through the CLI, on paths relative to the working directory."""
    _save(tmp_path, CLASSIC_FILE, _classic("ignored"))
    for flags in ([], ["--simulate"]):
        completed = _szzbench(tmp_path, "validate", *flags, "--json", CLASSIC_FILE)
        assert completed.returncode == 1, completed.stdout + completed.stderr
        [(code, location, message)] = _json_errors(completed)
        assert (code, location) == ("E051", "commits[0].operations[0].path")
    completed = _szzbench(tmp_path, "generate", CLASSIC_FILE, "--out", "out")
    assert completed.returncode == 1
    assert completed.stderr.startswith("[ERROR] GENERATION_FAILED: Scenario validation failed."), completed.stderr
    assert not (tmp_path / "out").exists()


def test_the_graph_commands_refuse_a_control_file(tmp_path):
    _save(tmp_path, GRAPH_FILE, _graph("ignored"))
    for flags in ([], ["--simulate"]):
        completed = _szzbench(tmp_path, "validate-graph", *flags, "--json", GRAPH_FILE)
        assert completed.returncode == 1, completed.stdout + completed.stderr
        [(code, location, message)] = _json_errors(completed)
        assert (code, location) == ("GE063", "commits[0].operations[0].path")
    completed = _szzbench(tmp_path, "generate-graph", GRAPH_FILE, "--out", "out")
    assert completed.returncode == 1
    assert completed.stderr.startswith("[ERROR] GRAPH_GENERATION_FAILED: Graph scenario validation failed."), completed.stderr
    assert not (tmp_path / "out").exists()


def test_the_messages_say_why_and_how_gitattributes_is_allowed():
    data = _classic("attributes")
    data["commits"][0]["operations"][1:1] = [_write_file(".gitignore", "*.log\n"), _write_file(".gitmodules", "")]
    messages = {f.location: f.message for f in validate_static(data).findings if f.code == "E051"}
    assert messages == {
        "commits[0].operations[0].path":
            "Operation 'write_file' writes '.gitattributes', a file Git reads: its attributes (text, eol, ident, "
            "working-tree-encoding, ...) decide the bytes Git stores, so a blob would differ from what the scenario "
            "writes. Declare the factor 'gitattributes-bic' in meta.factors to write one on purpose.",
        "commits[0].operations[1].path":
            "Operation 'write_file' writes '.gitignore', a file Git reads: its rules decide which files `git add -A` "
            "stages, so a file they match would be left out of the commit the scenario describes. A scenario cannot "
            "write .gitignore.",
        "commits[0].operations[2].path":
            "Operation 'write_file' writes '.gitmodules', a file Git reads: it declares submodules, which `git "
            "submodule` and `git clone --recurse-submodules` act on and neither the generators nor the simulators "
            "model. A scenario cannot write .gitmodules.",
    }


# --- the factor allows .gitattributes, and only it --------------------------------------

def test_a_declared_gitattributes_rule_validates_generates_and_verifies(tmp_path):
    """What the issue's variant C does once declared: the blob is LF, the worktree file CRLF."""
    path = _save(tmp_path, CLASSIC_FILE, _classic("attributes", factors=(FACTOR,)))
    _, result, _ = validate_scenario_file(path, simulate=True)
    assert _errors(result) == []
    commit_map, verify = generate_repository(path, tmp_path / "out")
    assert not verify.has_errors(), verify.to_dict()
    repo = tmp_path / "out/repo"
    blob = git_bytes(repo, "show", f"{commit_map['c0']['hash']}:{REQUEST}")
    assert b"\n" in blob and b"\r" not in blob
    assert b"\r\n" in (repo / REQUEST).read_bytes()


def test_a_declared_gitattributes_rule_validates_and_generates_in_the_graph_suite(tmp_path):
    path = _save(tmp_path, GRAPH_FILE, _graph("attributes", factors=(FACTOR,)))
    _, result = validate_graph_scenario_file(path, simulate=True)
    assert _errors(result) == []
    commit_map, verify = generate_graph_repository(path, tmp_path / "out")
    assert not verify.has_errors(), verify.to_dict()
    assert b"\r" not in git_bytes(tmp_path / "out/repo", "show", f"{commit_map['c0']['hash']}:{REQUEST}")


@pytest.mark.parametrize("name", [".gitignore", ".gitmodules"])
def test_the_factor_does_not_allow_the_other_files(name):
    data = _classic(factors=(FACTOR,))
    data["commits"][0]["operations"].append(_write_file(name, "x\n"))
    assert _errors(validate_static(data)) == [("E051", "commits[0].operations[2].path")]
    assert _errors(validate_graph_static(_as_graph(data))) == [("GE063", "commits[0].operations[2].path")]


def test_szzg_0134_validates_and_generates_its_published_hashes(tmp_path):
    """The one shipped scenario that writes .gitattributes, on purpose (factor gitattributes-bic)."""
    path = ROOT / "advanced-scenarios/SZZG-0134/scenario.graph.yml"
    _, result = validate_graph_scenario_file(path, simulate=True, lint=True)
    assert [f for f in result.findings if f.severity != "INFO"] == []
    commit_map, verify = generate_graph_repository(path, tmp_path / "out")
    assert not verify.has_errors(), verify.to_dict()
    assert {cid: entry["hash"] for cid, entry in commit_map.items()} == {
        "c0": "1d7867ec6515dd65fe42eda22d02d3d1e0234fc9",
        "c1": "50e87cc8f8c39533156ad3038bed6a6b141ce363",       # the README's commit structure
        "c2": "12fa71087806e95627090ba8607040de3aab01ee",
    }


# --- which paths are a file Git reads ---------------------------------------------------

#: (path, the file Git reads it as)
CONTROL_SPELLINGS = [
    (".gitignore", ".gitignore"),
    ("src/main/.gitignore", ".gitignore"),              # Git reads one in every directory
    (".GITIGNORE", ".gitignore"),                       # Git on macOS reads it; Git on Linux does not
    ("logs/.GitIgnore", ".gitignore"),
    (".git‌ignore", ".gitignore"),                 # a code point HFS+ ignores, as for E050
    (".gitattributes", ".gitattributes"),
    ("src/.GITATTRIBUTES", ".gitattributes"),
    (".gitmodules", ".gitmodules"),
    ("vendor/.GitModules", ".gitmodules"),
]
#: names next to them that Git does not read
ORDINARY_NAMES = [".gitignore/notes.txt", ".gitignore.bak", "x.gitignore", "gitignore", ".gitkeep",
                  ".git-blame-ignore-revs", ".github/workflows/ci.yml", ".gitattributes~", "docs/.gitmodules.md"]


@pytest.mark.parametrize("path, name", CONTROL_SPELLINGS)
def test_every_spelling_of_a_control_file_is_refused(path, name):
    assert git_control_file(path) == name
    data = _classic(factors=(FACTOR,) if name != ".gitattributes" else ())
    data["commits"][0]["operations"].append(_write_file(path, "x\n"))
    [finding] = [f for f in validate_static(data).findings if f.severity == "ERROR"]
    assert (finding.code, finding.location) == ("E051", "commits[0].operations[2].path")
    if path.rsplit("/", 1)[-1] != name:
        assert f"which Git on macOS can read as {name}: " in finding.message
    assert _errors(validate_graph_static(_as_graph(data))) == [("GE063", "commits[0].operations[2].path")]


@pytest.mark.parametrize("path", ORDINARY_NAMES)
def test_names_that_only_resemble_a_control_file_are_accepted(path):
    assert git_control_file(path) is None
    data = _classic()
    data["commits"][0]["operations"].append(_write_file(path, "x\n"))
    assert _errors(validate_static(data)) == []
    assert _errors(validate_graph_static(_as_graph(data))) == []


#: An operation of each type that writes a file, with the field that names it set to ``.gitignore``.
WRITING_OPERATIONS = {
    "write_file": {"type": "write_file", "path": ".gitignore", "content": "*.log\n"},
    "replace": {"type": "replace", "path": ".gitignore", "old": "a", "new": "b"},
    "insert_after": {"type": "insert_after", "path": ".gitignore", "anchor": "a", "content": "b\n"},
    "write_binary_file": {"type": "write_binary_file", "path": ".gitignore", "content_base64": "KgoK"},
    "write_generated_text_file": {"type": "write_generated_text_file", "path": ".gitignore", "lines": 1,
                                  "template": "*.log"},
    "format_file": {"type": "format_file", "path": ".gitignore"},
    "rename_file": {"type": "rename_file", "from": "ignore.txt", "to": ".gitignore"},
    "move_file": {"type": "move_file", "from": "ignore.txt", "to": ".gitignore"},
    "copy_file": {"type": "copy_file", "from": "ignore.txt", "to": ".gitignore"},
    "move_entity": {"type": "move_entity", "entity": {"name": "rules"}, "from_file": "ignore.txt", "to_file": ".gitignore"},
    "copy_entity": {"type": "copy_entity", "entity": {"name": "rules"}, "from_file": "ignore.txt", "to_file": ".gitignore"},
}
#: The operations that write no file at a path of their own: Git computes what the
#: patch ones write (apply_patch is not implemented), and commit_generator writes
#: ``<generator>-NN.txt``.
NOT_WRITING = {"delete_file", "chmod", "commit_generator", "apply_squash", "apply_patch_from", "apply_patch"}


def test_every_graph_operation_is_known_to_write_a_file_or_not():
    assert set(WRITTEN_PATH_FIELDS_BY_OPERATION) == set(WRITING_OPERATIONS) == SUPPORTED_GRAPH_OPERATIONS - NOT_WRITING


@pytest.mark.parametrize("op_type", WRITING_OPERATIONS)
def test_validate_graph_checks_the_file_each_operation_writes(op_type):
    op = WRITING_OPERATIONS[op_type]
    assert set(REQUIRED_FIELDS_BY_OPERATION[op_type]) <= set(op)
    data = _graph()
    data["commits"][1]["operations"].append(deepcopy(op))
    [field] = WRITTEN_PATH_FIELDS_BY_OPERATION[op_type]
    assert _errors(validate_graph_static(data)) == [("GE063", f"commits[1].operations[1].{field}")]


def test_the_source_of_a_move_and_a_deletion_are_not_writes():
    data = _graph()
    data["commits"][1]["operations"] += [
        {"type": "rename_file", "from": ".gitignore", "to": "ignore.txt"},
        {"type": "copy_entity", "entity": {"name": "rules"}, "from_file": ".gitattributes", "to_file": "rules.txt"},
        {"type": "delete_file", "path": ".gitmodules"},
        {"type": "chmod", "path": ".gitignore", "mode": "644"},
    ]
    assert [f for f in validate_graph_static(data).findings if f.code == "GE063"] == []


def test_commit_generator_files_are_never_a_control_file():
    op = {"type": "commit_generator", "generator": ".gitignore", "count": 3, "files": 2, "path": "logs"}
    paths = [path for _, path, _ in commit_generator_changes([commit_generator_plan(op, "c1")], lambda path: "")]
    assert paths == ["logs/.gitignore-01.txt", "logs/.gitignore-02.txt", "logs/.gitignore-01.txt"]
    assert [git_control_file(path) for path in paths] == [None, None, None]
    data = _graph()
    data["commits"][1]["operations"].append(op)
    assert [f for f in validate_graph_static(data).findings if f.code == "GE063"] == []


# --- generation names a file Git did not stage, when validation is passed by -------------

@pytest.fixture
def unchecked(monkeypatch):
    """Validation without E051 / GE063, so that a scenario that writes .gitignore reaches the generators."""
    monkeypatch.setattr(validator, "check_git_control_files", lambda *args, **kwargs: None)
    monkeypatch.setattr(graph_validator, "check_git_control_files", lambda *args, **kwargs: None)


def _generate(tmp_path: Path, suite: str, data: dict):
    if suite == "classic":
        return generate_repository(_save(tmp_path, CLASSIC_FILE, data), tmp_path / "out")
    return generate_graph_repository(_save(tmp_path, GRAPH_FILE, _as_graph(data)), tmp_path / "out")


GENERATION_ERRORS = {"classic": GenerationError, "graph": GraphGenerationError}
#: variant -> the commit that writes logs/app.log
LOG_COMMIT = {"ignored": "c1", "ignored-only": "c0b"}


@pytest.mark.parametrize("variant", LOG_COMMIT)
@pytest.mark.parametrize("suite", GENERATION_ERRORS)
def test_generation_names_the_ignored_file_and_its_rule(tmp_path, unchecked, suite, variant):
    """Variant A committed c1 without app.log; variant B failed with "commit would be empty"."""
    with pytest.raises(GENERATION_ERRORS[suite]) as raised:
        _generate(tmp_path, suite, _classic(variant))
    message = str(raised.value)
    assert message.startswith(f"Commit '{LOG_COMMIT[variant]}' writes a file Git ignores: "
                              "logs/app.log ('*.log' in .gitignore, line 1). `git add -A` leaves it out of the commit"), message
    assert "would be empty" not in message
    error = json.loads((tmp_path / "out/metadata/generation-error.json").read_text(encoding="utf-8"))
    assert error["error"] == message


@pytest.mark.parametrize("suite", GENERATION_ERRORS)
def test_generation_names_every_ignored_file_with_its_own_rule(tmp_path, unchecked, suite):
    """A rule of a .gitignore in a subdirectory, a directory pattern, and a name Git could read as pathspec magic."""
    data = _classic()
    data["commits"][0]["operations"] += [_write_file("build/.gitignore", "# generated\nout/\n"),
                                         _write_file(".gitignore", "*.tmp\n")]
    data["commits"][1]["operations"] += [_write_file("build/out/Main.class", "x\n"), _write_file(":(top)x.tmp", "y\n")]
    with pytest.raises(GENERATION_ERRORS[suite], match="^" + "".join(
            ["Commit 'c1' writes files Git ignores: ",
             r":\(top\)x\.tmp \('\*\.tmp' in \.gitignore, line 1\), ",
             r"build/out/Main\.class \('out/' in build/\.gitignore, line 2\)\. ",
             "`git add -A` leaves them out of the commit"])):
        _generate(tmp_path, suite, data)


@pytest.mark.parametrize("suite", GENERATION_ERRORS)
def test_a_tracked_file_an_ignore_rule_matches_later_is_still_committed(tmp_path, unchecked, suite):
    """Git ignores untracked files only: no false alarm for a file the repository already has."""
    data = _classic()
    data["commits"][0]["operations"].append(_write_file("logs/app.log", "started\n"))
    data["commits"][1]["operations"] += [_write_file(".gitignore", "*.log\n"), _write_file("logs/app.log", "stopped\n")]
    commit_map, verify = _generate(tmp_path, suite, data)
    assert not verify.has_errors(), verify.to_dict()
    assert git_stdout(tmp_path / "out/repo", "show", f"{commit_map['c1']['hash']}:logs/app.log") == "stopped\n"
