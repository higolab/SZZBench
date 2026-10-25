"""Branch names follow Git's rules and are compared as macOS compares them (issue #239).

``repository.default_branch`` (both suites) and a graph commit's ``branch``
were checked for their type only, and ``validate --simulate --strict --lint``
and ``validate-graph --simulate --strict --strict-paths --lint`` passed every
value of the issue's table.  A name Git refuses then stopped generation with
Git's own message (``unknown switch 'x'`` for ``default_branch: -x``),
``branch: ""`` put the commits on the default branch without a word, and on
macOS two names that differ only in letter case (``Feature`` beside
``feature``, ``Main`` beside ``main``) became one branch while verification
passed.  Validation now reports each at the field (E015, GE023, GE024) with
the rule of the tag names of ``graph.ref_lifecycle`` (``paths.ref_name_problem``,
``paths.ref_names_clash``), and the generators check the same rules before
``git init``.  An empty name is an error; without the key (or with a blank
value) a commit is on the default branch, the one reading of the validators,
the generators and the verifiers (``gitutils.commit_branch``).  The PR #243
review added two rules for names Git accepts: a whitespace character of
Unicode (``my\u00a0topic``), which SZZBench cannot read back from Git's list
of refs, and a component longer than a file name may be (``"a" * 251``, whose
lock file ``.lock`` makes it 256 bytes long).
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import szzbench.generator as generator
import szzbench.gitutils as gitutils
import szzbench.graph_generator as graph_generator
import szzbench.graph_scenario as graph_scenario
import szzbench.paths as paths
import szzbench.validator as validator
from support import git, git_env, scenario_file
from szzbench.findings import ValidationResult
from szzbench.generator import GenerationError, generate_repository
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.validator import validate_scenario_file

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = yaml.safe_load(scenario_file("SZZ-0005").read_text(encoding="utf-8"))
F = "src/main/java/example/Range.java"
#: café with a precomposed é (NFC), and with e and a combining acute accent (NFD): two names to Git, one ref
#: file to the file systems of macOS.
CAFE_NFC, CAFE_NFD = "caf\u00e9", "cafe\u0301"


def _graph(default_branch="main", side="feature", fix_branch=None) -> dict:
    """The issue's scenario: c0 on the default branch; c1 (the BIC) and c2 (the fix) on ``side``, or c2 on
    ``fix_branch``.  ``side=None`` leaves c1 and c2 without ``branch``; ``default_branch=None`` leaves the key out."""
    messages = {"c0": "Add the range check", "c1": "Reject zero in the range check", "c2": "Accept zero again"}

    def commit(cid, branch, parents, operations):
        entry = {"id": cid, "parents": parents, "message": messages[cid], "operations": operations}
        if branch is not None:
            entry["branch"] = branch
        return entry

    repository = {"name": "probe"}
    if default_branch is not None:
        repository["default_branch"] = default_branch
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"],
                 "tier": "control", "difficulty": "easy"},
        "repository": repository,
        "graph": {"model": "commit_dag"},
        "commits": [
            commit("c0", None, [], [{"type": "write_file", "path": F,
                                     "content": "class Range { boolean ok(int v) { return v >= 0; } }\n"}]),
            commit("c1", side, ["c0"], [{"type": "replace", "path": F, "old": "v >= 0", "new": "v > 0"}]),
            commit("c2", side if fix_branch is None else fix_branch, ["c1"],
                   [{"type": "replace", "path": F, "old": "v > 0", "new": "v >= 0"}]),
        ],
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
                  "faults": [{"id": "F001", "commit": "c1", "file": F, "statement": "return v > 0;"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}},
    }


def _classic(default_branch) -> dict:
    data = copy.deepcopy(CLASSIC)
    data["repository"]["default_branch"] = default_branch
    return data


#: The names of the issue's table that Git refuses (and ``""``), by the key its script gives them.
BAD = {"space": "a b", "dash": "-x", "HEAD": "HEAD", "dotdot": "a..b", "lock": "x.lock", "slash": "feature/", "empty": ""}

#: The rows of the issue's table: (suite, scenario, code, location).  Each is one error, at that field.
ROWS = {
    **{f"g-branch-{key}": ("graph", _graph(side=name), "GE023", "commits[1].branch") for key, name in BAD.items()},
    **{f"g-default-{key}": ("graph", _graph(default_branch=name, side=None), "GE023", "repository.default_branch")
       for key, name in BAD.items()},
    **{f"c-default-{key}": ("classic", _classic(name), "E015", "repository.default_branch") for key, name in BAD.items()},
    "g-dir-file": ("graph", _graph(fix_branch="feature/x"), "GE024", "commits[2].branch"),
    "g-case-two-branches": ("graph", _graph(fix_branch="Feature"), "GE024", "commits[2].branch"),
    "g-case-default": ("graph", _graph(side="Main"), "GE024", "commits[1].branch"),
}


def _write(directory: Path, suite: str, data: dict) -> Path:
    """The scenario where the issue's script writes it: SZZG-9900/scenario.graph.yml or SZZ-0005/scenario.yml."""
    path = directory / ("SZZG-9900/scenario.graph.yml" if suite == "graph" else "SZZ-0005/scenario.yml")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _errors(result: ValidationResult) -> list[tuple[str, str | None]]:
    return [(f.code, f.location) for f in result.findings if f.severity == "ERROR"]


def _validate(path: Path, suite: str) -> ValidationResult:
    if suite == "graph":
        return validate_graph_scenario_file(path)[1]                    # no --simulate
    return validate_scenario_file(path)[1]


# --- the issue's table ----------------------------------------------------------------------

@pytest.mark.parametrize("row", list(ROWS))
def test_each_row_is_one_error_at_its_field(tmp_path, row):
    suite, data, code, location = ROWS[row]
    assert _errors(_validate(_write(tmp_path, suite, data), suite)) == [(code, location)]


@pytest.mark.parametrize("row", ["g-branch-dash", "g-default-dash", "c-default-dash", "g-case-default"])
def test_each_row_fails_the_issues_command_with_a_relative_path(tmp_path, row):
    """API tests cover every name; the CLI covers both suites, both fields and a clash on relative paths."""
    suite, data, code, location = ROWS[row]
    relative = _write(tmp_path, suite, data).relative_to(tmp_path)
    command = (["validate-graph", "--simulate", "--strict", "--strict-paths", "--lint"] if suite == "graph"
               else ["validate", "--simulate", "--strict", "--lint"])
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", *command, "--json", str(relative)],
                               cwd=tmp_path, capture_output=True, text=True)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    findings = json.loads(completed.stdout)["findings"]
    assert [(f["code"], f["location"]) for f in findings if f["severity"] == "ERROR"] == [(code, location)]
    assert not [f for f in findings if f["severity"] == "WARNING"]


@pytest.mark.parametrize("row", ["g-branch-dash", "g-default-dash", "c-default-dash", "g-case-default"])
def test_generation_stops_at_validation(tmp_path, row):
    suite, data, _, _ = ROWS[row]
    relative = _write(tmp_path, suite, data).relative_to(tmp_path)
    command = "generate-graph" if suite == "graph" else "generate"
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", command, str(relative), "--out", "out"],
                               cwd=tmp_path, capture_output=True, text=True)
    assert completed.returncode == 1 and "validation failed" in completed.stderr, completed.stderr
    assert "unknown switch" not in completed.stderr and "fatal:" not in completed.stderr
    assert not (tmp_path / "out").exists()


# The messages of some rows, as validation and generation give them.
MESSAGES = {
    "g-branch-dash": "commits[1].branch '-x' is not a valid branch name: it starts with '-', which git branch reads "
                     "as an option.",
    "g-branch-empty": "commits[1].branch '' is not a valid branch name: it is empty; without the key the commit is "
                      "on the default branch.",
    "c-default-empty": "repository.default_branch '' is not a valid branch name: it is empty.",
    "g-dir-file": "commits[2].branch 'feature/x' and the branch 'feature' (commits[1].branch) cannot both be "
                  "branches: Git stores a ref as a file, and the one would be a directory of the other.",
    "g-case-two-branches": "commits[2].branch 'Feature' differs only in letter case or Unicode normalization from "
                           "the branch 'feature' (commits[1].branch): macOS (and Windows, for letter case) stores "
                           "both as one ref, so generation would depend on the platform.",
    "g-case-default": "commits[1].branch 'Main' differs only in letter case or Unicode normalization from the "
                      "default branch 'main': macOS (and Windows, for letter case) stores both as one ref, so "
                      "generation would depend on the platform.",
}


@pytest.mark.parametrize("row", list(MESSAGES))
def test_the_messages_name_the_field_and_the_rule(tmp_path, row):
    suite, data, _, _ = ROWS[row]
    assert [f.message for f in _validate(_write(tmp_path, suite, data), suite).error_findings()] == [MESSAGES[row]]


# --- the generators check the same rules before git init ---------------------------------

def _bypass_validation(monkeypatch) -> None:
    monkeypatch.setattr(generator, "validate_scenario_file", lambda path, simulate: (None, ValidationResult(), None))
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))


#: Names Git accepts that a generated repository cannot keep (see PORTABLE below), as rows of their own.
MORE_ROWS = {
    "g-branch-head": ("graph", _graph(side="head"), "GE023", "commits[1].branch"),
    "g-branch-at": ("graph", _graph(side="@"), "GE023", "commits[1].branch"),
    "g-default-LOCK": ("graph", _graph(default_branch="main.LOCK", side=None), "GE023", "repository.default_branch"),
    "c-default-head": ("classic", _classic("Head"), "E015", "repository.default_branch"),
    "g-nfd": ("graph", _graph(side=CAFE_NFD), "GE023", "commits[1].branch"),
    "g-case-hfs": ("graph", _graph(side="feature", fix_branch="fea\u200cture"), "GE024", "commits[2].branch"),
}


@pytest.mark.parametrize("row", [*ROWS, *MORE_ROWS])
def test_the_generators_refuse_them_before_git_init(tmp_path, monkeypatch, row):
    """With validation bypassed, generation stops with SZZBench's message, before ``git init``: no Git
    message, no ``unknown switch``, no repository."""
    suite, data, code, location = {**ROWS, **MORE_ROWS}[row]
    _bypass_validation(monkeypatch)
    out = tmp_path / "out"
    generate, error = (generate_graph_repository, GraphGenerationError) if suite == "graph" else \
        (generate_repository, GenerationError)
    with pytest.raises(error) as excinfo:
        generate(_write(tmp_path, suite, data), out)
    message = str(excinfo.value)
    assert message.startswith(location + " ") and message.endswith(f" ({code}). Generation stopped before git init.")
    if row in MESSAGES:
        assert message == f"{MESSAGES[row].rstrip('.')} ({code}). Generation stopped before git init."
    assert "fatal:" not in message and "error:" not in message and "unknown switch" not in message
    assert not (out / "repo" / ".git").exists()
    assert json.loads((out / "metadata" / "generation-error.json").read_text(encoding="utf-8"))["error"] == message


def test_the_graph_generator_counts_the_other_problems(tmp_path, monkeypatch):
    _bypass_validation(monkeypatch)
    with pytest.raises(GraphGenerationError) as excinfo:
        generate_graph_repository(_write(tmp_path, "graph", _graph(default_branch="-x", side="a b", fix_branch="A B")),
                                  tmp_path / "out")
    assert str(excinfo.value).endswith(" (GE023). Generation stopped before git init. 2 more problem(s) with branch "
                                       "names; 'szzbench validate-graph' lists them.")


@pytest.mark.parametrize("row", ["g-case-two-branches", "g-case-default", "g-branch-empty"])
def test_the_rows_that_generated_now_stop_on_every_platform(tmp_path, monkeypatch, row):
    """On main these generated and verified: on macOS with one branch where the scenario has two, and
    ``branch: ""`` with the commits on the default branch."""
    _bypass_validation(monkeypatch)
    with pytest.raises(GraphGenerationError, match=r"Generation stopped before git init\.$"):
        generate_graph_repository(_write(tmp_path, "graph", ROWS[row][1]), tmp_path / "out")
    assert not (tmp_path / "out" / "metadata" / "graph-map.json").exists()


# --- the rule is Git's ------------------------------------------------------------------------

#: Names Git accepts and names it refuses as a branch (git check-ref-format --branch); each refused one
#: breaks one rule.
BRANCH_NAMES = [
    # accepted
    "main", "feature", "feature-x", "release/2024.1", "user/alice/topic", "v1.0", "a.b", "a./b", "a/b.c", "a@b", "@a",
    "a@", "@@", "{@", "@/x", "a{b", "a}b", "a]b", "a#b", "a$b", "a%b", "a&b", "a'b", 'a"b', "a(b)", "a+b", "a,b", "a;b",
    "a<b>", "a=b", "a|b", "a`b", "a!b", "a_b", "1", "a-", "a/-b", "x.lock.y", "lock", "a.lockx", "a-.lock-b", "x/lock",
    "FETCH_HEAD", "ORIG_HEAD", "HEAD/x", "x/HEAD", "x/head", "heads", "refs/heads/main",
    "0123456789abcdef0123456789abcdef01234567", "héllo", "日本語", "ä/ö", "emoji😀", CAFE_NFC, "x\u200by", "x\x80y",
    "a" * 250, "d" * 255 + "/x", "x/" + "a" * 250, "\u00e9" * 125, "\u01d5" * 83, "\U0001f642" * 62,
    # refused
    "", " ", "a b", "trailing ", " leading", "v\t1", "v\n1", "v\x01", "v\x1f", "v\x7f", "v~1", "v^1", "v:1", "v?1",
    "v*1", "v[1", "v\\1", "a..b", "..", ".", "...", ".v", "x/.y", "x/..", "a/./b", "a/../b", "x.lock", "a/b.lock",
    "a.lock/b", ".lock", "v1.", "a.", "a/b.", "/a", "a/", "feature/", "a//b", "a@{b", "@{", "@{u}", "@{-1}", "a/@{b}",
    "-", "-x", "--list", "HEAD",
]

#: Names Git accepts as a branch that SZZBench refuses, and why: a component ending in ``.lock`` in another
#: letter case is another branch's lock file on macOS; Git on macOS converts a name to NFC; ``HEAD`` in another
#: letter case is stored as ``refs/heads/HEAD`` there, which makes ``HEAD`` ambiguous (``git checkout -b``
#: fails); Git 2.50 reads ``git checkout @`` as ``HEAD`` and stays on the current branch (Git 2.39 switches
#: to the branch); a whitespace character of Unicode is accepted by Git and cannot be read back from its list of
#: refs; a component longer than a file name may be is accepted by Git, which cannot lock it (PR #243 review).
PORTABLE = {
    "main.LOCK": "ends with '.lock' in another spelling", "a/b.Lock": "ends with '.lock' in another spelling",
    CAFE_NFC + ".LoCk": "ends with '.lock' in another spelling",
    CAFE_NFD: "not in Unicode normalization form C (NFC): Git on macOS creates the branch 'caf\\xe9' instead",
    "x/" + CAFE_NFD + "/y": "not in Unicode normalization form C", "\u212b": "not in Unicode normalization form C",
    "head": "it is HEAD in another letter case", "Head": "it is HEAD in another letter case",
    "hEAD": "it is HEAD in another letter case",
    "@": "it is '@', which recent versions of git checkout read as HEAD",
    "\u00a0nbsp": "it contains the whitespace character U+00A0 NO-BREAK SPACE",
    "my\u00a0topic": "it contains the whitespace character U+00A0 NO-BREAK SPACE",
    "a\u2028b": "it contains the whitespace character U+2028 LINE SEPARATOR",
    "a" * 251: "it is too long for a file name: 251 bytes in UTF-8",
    "x/" + "a" * 251: "its last component is too long for a file name: 251 bytes in UTF-8",
    "d" * 256 + "/x": "its component 1 is too long for a file name: 256 bytes in UTF-8, and Git stores it as a directory",
    "\u00e9" * 126: "it is too long for a file name: 252 bytes in UTF-8",
    "\u01d5" * 84: "it is too long for a file name: 252 UTF-16 code units in its decomposed form, as HFS+ counts them",
    "\U0001f642" * 63: "it is too long for a file name: 252 bytes in UTF-8",
}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, env=git_env(), capture_output=True, text=True)


def test_branch_names_are_refused_exactly_where_git_check_ref_format_refuses_them(tmp_path):
    assert len(BRANCH_NAMES) >= 100
    mismatches = []
    for name in BRANCH_NAMES:
        git_accepts = _git(tmp_path, "check-ref-format", "--branch", name).returncode == 0
        if git_accepts != (paths.ref_name_problem(name, "branch") is None):
            mismatches.append((name, "git accepts" if git_accepts else "git refuses", paths.ref_name_problem(name, "branch")))
    assert mismatches == []
    assert sum(paths.ref_name_problem(name, "branch") is None for name in BRANCH_NAMES) >= 50   # both kinds are compared


def test_the_names_git_accepts_and_a_generated_repository_cannot_keep_are_refused(tmp_path):
    for name, reason in PORTABLE.items():
        assert _git(tmp_path, "check-ref-format", "--branch", name).returncode == 0, name
        assert reason in paths.ref_name_problem(name, "branch"), name


def test_the_generators_commands_create_and_check_out_every_name_szzbench_accepts(tmp_path):
    """As the generators run them: ``git branch -M`` on the unborn default branch, ``git checkout -B`` without a
    start point (a first commit off the default branch) and with one (a new branch, or one moved to its first
    parent), and ``git checkout`` back to the branch.  ``git checkout -b`` afterwards: ``HEAD`` is not ambiguous."""
    def commit(repo: Path, message: str) -> str:
        assert _git(repo, "-c", "user.name=a", "-c", "user.email=a@example.com",
                    "commit", "-q", "--allow-empty", "-m", message).returncode == 0
        return _git(repo, "rev-parse", "HEAD").stdout.strip()

    accepted = [n for n in BRANCH_NAMES if paths.ref_name_problem(n, "branch") is None]
    for i, name in enumerate(accepted):
        unborn = tmp_path / f"{i}-unborn"
        unborn.mkdir()
        assert _git(unborn, "init", "-q", "--template=").returncode == 0
        assert _git(unborn, "checkout", "-q", "-B", name).returncode == 0, name
        commit(unborn, "c0")
        assert _git(unborn, "symbolic-ref", "HEAD").stdout.strip() == f"refs/heads/{name}", name

        repo = tmp_path / str(i)
        repo.mkdir()
        assert _git(repo, "init", "-q", "--template=").returncode == 0
        assert _git(repo, "branch", "-M", name).returncode == 0, name
        c0 = commit(repo, "c0")
        assert _git(repo, "checkout", "-q", "-B", "elsewhere", c0).returncode == 0
        c1 = commit(repo, "c1")
        assert _git(repo, "checkout", "-q", "-B", name, c1).returncode == 0, name
        assert _git(repo, "rev-parse", f"refs/heads/{name}").stdout.strip() == c1, name
        assert _git(repo, "checkout", "-q", "elsewhere").returncode == 0
        assert _git(repo, "checkout", "-q", name).returncode == 0, name
        assert _git(repo, "symbolic-ref", "HEAD").stdout.strip() == f"refs/heads/{name}", name
        assert _git(repo, "checkout", "-q", "-b", "new").returncode == 0, name


def test_the_tag_names_follow_the_same_rule_except_at(tmp_path):
    """Tags (GE157) and branches share the rule.  ``HEAD`` in another letter case is refused for a tag too:
    a tag ``head`` made ``git checkout -b`` fail with ``ambiguous object name: 'HEAD'`` on macOS.  ``@`` stays
    a valid tag: the generator never checks a tag out."""
    for name in BRANCH_NAMES + list(PORTABLE):
        if name != "@":
            assert (paths.ref_name_problem(name, "tag") is None) == (paths.ref_name_problem(name, "branch") is None), name
    assert paths.ref_name_problem("@", "tag") is None
    assert "it is HEAD in another letter case" in paths.ref_name_problem("head", "tag")
    assert "git tag reads as an option" in paths.ref_name_problem("-x", "tag")
    with pytest.raises(ValueError):
        paths.ref_name_problem("main", "remote")
    data = copy.deepcopy(_graph())
    data["graph"]["ref_lifecycle"] = {"tags": [{"name": "head", "commit": "c0"}]}
    assert _errors(validate_graph_static(data)) == [("GE157", "graph.ref_lifecycle.tags[0].name")]


# --- whitespace, and the longest names (PR #243 review) -----------------------------------------

#: Every whitespace character of Unicode that ``str.split()`` and ``str.strip()`` take, besides the control
#: characters and the space Git refuses.
UNICODE_WHITESPACE = [chr(c) for c in range(0x80, 0x110000) if chr(c).isspace()]


def test_every_unicode_whitespace_is_refused_where_git_accepts_it(tmp_path):
    """Git created ``my\u00a0topic`` and ``topic\u00a0``; ``gitutils.git_refs`` splits Git's list of refs at
    whitespace and the verifiers strip ``HEAD``, so generation failed verification (E607, GE641-GE644)."""
    assert len(UNICODE_WHITESPACE) == 19            # U+0085, U+00A0, U+1680, U+2000-U+200A, U+2028, U+2029, ...
    for char in UNICODE_WHITESPACE:
        for name in (f"my{char}topic", f"topic{char}", f"{char}topic"):
            assert _git(tmp_path, "check-ref-format", "--branch", name).returncode == 0, ascii(name)
            for kind in paths.REF_KINDS:
                assert f"it contains the whitespace character U+{ord(char):04X}" in paths.ref_name_problem(name, kind)


def test_git_cannot_lock_a_name_one_byte_longer_than_the_rule_allows(tmp_path):
    """Git accepts these (``git check-ref-format``) and cannot create them: its lock file ``<name>.lock``, or a
    directory, is longer than a file name may be (255 bytes on Linux, 255 UTF-16 code units on macOS).  One
    byte shorter, each is created."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(repo, "init", "-q", "--template=").returncode == 0
    assert _git(repo, "-c", "user.name=a", "-c", "user.email=a@example.com",
                "commit", "-q", "--allow-empty", "-m", "c0").returncode == 0
    for too_long, longest in (("a" * 251, "a" * 250), ("x/" + "b" * 251, "x/" + "b" * 250),
                              ("d" * 256 + "/x", "e" * 255 + "/x")):
        assert _git(tmp_path, "check-ref-format", "--branch", too_long).returncode == 0
        for command in ("branch", "tag"):
            failed = _git(repo, command, too_long)
            assert failed.returncode != 0 and "fatal:" in failed.stderr, (command, len(too_long))
            assert _git(repo, command, longest).returncode == 0, (command, len(longest))
        assert paths.ref_name_problem(too_long, "branch") is not None and paths.ref_name_problem(longest, "branch") is None


def _four_fields(name: str) -> dict[str, tuple[str, dict, str, str]]:
    """``name`` in each field that names a ref: ``(suite, scenario, code, location)``, the code and location
    of the error a name the rule refuses is."""
    tagged = _graph()
    tagged["graph"]["ref_lifecycle"] = {"tags": [{"name": name, "commit": "c1"}]}
    return {
        "classic default branch": ("classic", _classic(name), "E015", "repository.default_branch"),
        "graph default branch": ("graph", _graph(default_branch=name, side="feature"), "GE023",
                                 "repository.default_branch"),
        "graph commit branch": ("graph", _graph(side=name), "GE023", "commits[1].branch"),
        "graph tag": ("graph", tagged, "GE157", "graph.ref_lifecycle.tags[0].name"),
    }


#: The review's names, and one name past each limit of the rule: (name, the reason the message gives).
REFUSED_IN_EVERY_FIELD = {
    "a no-break space": ("my\u00a0topic", "it contains the whitespace character U+00A0 NO-BREAK SPACE"),
    "a trailing no-break space": ("topic\u00a0", "it contains the whitespace character U+00A0 NO-BREAK SPACE"),
    "an ideographic space": ("a\u3000b", "it contains the whitespace character U+3000 IDEOGRAPHIC SPACE"),
    "251 bytes": ("a" * 251, "it is too long for a file name: 251 bytes in UTF-8, and Git writes the"),
    "a last component of 251 bytes": ("x/" + "a" * 251, "its last component is too long for a file name: 251 bytes"),
    "a directory of 256 bytes": ("d" * 256 + "/x", "its component 1 is too long for a file name: 256 bytes"),
    "252 bytes of a two-byte letter": ("\u00e9" * 126, "it is too long for a file name: 252 bytes in UTF-8"),
    "252 code units on HFS+": ("\u01d5" * 84, "252 UTF-16 code units in its decomposed form, as HFS+ counts them"),
    "252 bytes of an emoji": ("\U0001f642" * 63, "it is too long for a file name: 252 bytes in UTF-8"),
}


@pytest.mark.parametrize("label", list(REFUSED_IN_EVERY_FIELD))
def test_they_are_one_error_in_every_field_that_names_a_ref(tmp_path, label):
    name, reason = REFUSED_IN_EVERY_FIELD[label]
    for field, (suite, data, code, location) in _four_fields(name).items():
        result = _validate(_write(tmp_path / field.replace(" ", "-"), suite, data), suite)
        assert _errors(result) == [(code, location)], field
        assert reason in result.error_findings()[0].message, field


@pytest.mark.parametrize("label", ["a trailing no-break space", "251 bytes"])
def test_the_reviews_commands_refuse_them_and_create_nothing(tmp_path, label):
    """The unmodified CLI, as the review ran it: strict simulated validation with ``--lint`` is that one error
    and no warning, and ``generate`` / ``generate-graph`` stop at validation, before ``git init``."""
    name, _ = REFUSED_IN_EVERY_FIELD[label]
    for field, (suite, data, code, location) in _four_fields(name).items():
        directory = tmp_path / field.replace(" ", "-")
        relative = _write(directory, suite, data).relative_to(directory)
        command = (["validate-graph", "--simulate", "--strict", "--strict-paths", "--lint"] if suite == "graph"
                   else ["validate", "--simulate", "--strict", "--lint"])
        completed = subprocess.run([sys.executable, "-m", "szzbench.cli", *command, "--json", str(relative)],
                                   cwd=directory, capture_output=True, text=True)
        assert completed.returncode == 1, completed.stdout + completed.stderr
        findings = json.loads(completed.stdout)["findings"]
        assert [(f["code"], f["location"]) for f in findings if f["severity"] != "INFO"] == [(code, location)], field
        completed = subprocess.run([sys.executable, "-m", "szzbench.cli", "generate-graph" if suite == "graph"
                                    else "generate", str(relative), "--out", "out"],
                                   cwd=directory, capture_output=True, text=True)
        assert completed.returncode == 1 and "validation failed" in completed.stderr, (field, completed.stderr)
        assert "cannot lock ref" not in completed.stderr and not (directory / "out").exists(), field


@pytest.mark.parametrize("label", list(REFUSED_IN_EVERY_FIELD))
def test_the_generators_refuse_them_before_git_creates_the_ref(tmp_path, monkeypatch, label):
    """With validation bypassed, a branch name stops generation before ``git init``, and a tag name before the
    first ref changes (GE157, issue #229): Git never sees the name, and ``cannot lock ref`` never shows."""
    _bypass_validation(monkeypatch)
    name, reason = REFUSED_IN_EVERY_FIELD[label]
    for field, (suite, data, code, location) in _four_fields(name).items():
        directory = tmp_path / field.replace(" ", "-")
        out = directory / "out"
        generate, error = (generate_graph_repository, GraphGenerationError) if suite == "graph" else \
            (generate_repository, GenerationError)
        with pytest.raises(error) as excinfo:
            generate(_write(directory, suite, data), out)
        message = str(excinfo.value)
        assert message.startswith(location + " ") and reason in message, (field, message)
        assert "fatal:" not in message and "cannot lock ref" not in message, field
        if field == "graph tag":
            assert message.endswith(f" ({code}). No ref was changed."), message
            assert git(out / "repo", "tag", "--list") == ""
        else:
            assert message.endswith(f" ({code}). Generation stopped before git init."), message
            assert not (out / "repo" / ".git").exists(), field


#: Names at the limits of the rule, and characters a reader may take for whitespace or a control character,
#: which Git keeps as written and SZZBench reads back.
ROUND_TRIP = {
    "250 bytes": "a" * 250,
    "a directory of 255 bytes": "d" * 255 + "/x",
    "250 bytes of a two-byte letter": "\u00e9" * 125,
    "249 code units on HFS+": "\u01d5" * 83,
    "248 bytes of an emoji": "\U0001f642" * 62,
    "NFC": CAFE_NFC,
    "a zero-width space": "x\u200by",
    "a C1 control character": "x\x80y",
}


@pytest.mark.parametrize("label", list(ROUND_TRIP))
def test_the_names_the_rule_accepts_generate_and_verify_in_every_field(tmp_path, label):
    """Strict simulated validation passes without a warning, generation verifies, and the repository has the
    ref under the name as written."""
    name = ROUND_TRIP[label]
    for field, (suite, data, _, _) in _four_fields(name).items():
        directory = tmp_path / field.replace(" ", "-")
        path = _write(directory, suite, data)
        if suite == "graph":
            result = validate_graph_scenario_file(path, strict_paths=True, simulate=True)[1]
            _, verify = generate_graph_repository(path, directory / "out")
        else:
            result = validate_scenario_file(path, simulate=True)[1]
            _, verify = generate_repository(path, directory / "out")
        assert [f.code for f in result.findings if f.severity in ("ERROR", "WARNING")] == [], field
        assert verify is not None and not verify.has_errors(), (field, verify.to_dict())
        refs = git(directory / "out" / "repo", "for-each-ref", "--format=%(refname)").split("\n")
        assert ("refs/tags/" if field == "graph tag" else "refs/heads/") + name in refs, field


# --- two names of one scenario ------------------------------------------------------------------

def _two(first: str, second: str, default_branch="main") -> dict:
    return _graph(default_branch=default_branch, side=first, fix_branch=second)


CLASHES = {
    "letter case": (_two("feature", "Feature"), "commits[2].branch"),
    "letter case of the default branch": (_graph(side="MAIN"), "commits[1].branch"),
    "letter case of an implied default branch": (_graph(default_branch=None, side="Main"), "commits[1].branch"),
    "an invisible code point HFS+ ignores": (_two("feature", "fea\u200cture"), "commits[2].branch"),
    "a directory of an earlier branch": (_two("feature", "feature/x"), "commits[2].branch"),
    "an earlier branch's directory": (_two("feature/x", "feature"), "commits[2].branch"),
    "a directory in another letter case": (_two("feature", "Feature/x"), "commits[2].branch"),
    "a directory of the default branch": (_graph(side="main/x"), "commits[1].branch"),
    "the default branch's directory": (_graph(default_branch="release/main", side="release"), "commits[1].branch"),
}


@pytest.mark.parametrize("case", list(CLASHES))
def test_two_names_one_file_system_reads_as_one_ref_are_an_error(case):
    data, location = CLASHES[case]
    assert [e for e in _errors(validate_graph_static(data)) if e[0] == "GE024"] == [("GE024", location)]


def test_two_names_that_look_alike_are_spelt_out():
    message = validate_graph_static(_two("feature", "fea\u200cture")).error_findings()[0].message
    assert "(spelt 'fea\\u200cture' and 'feature')" in message


@pytest.mark.parametrize("first, second, location", [(CAFE_NFC, CAFE_NFD, "commits[2].branch"),
                                                     (CAFE_NFD, CAFE_NFC, "commits[1].branch")])
def test_a_name_in_another_normalization_than_nfc_is_an_error_in_either_order(first, second, location):
    """Git on macOS converts the name it is given to NFC, so there the NFD one is the NFC one: one branch where
    the scenario has two (on Linux, two)."""
    assert _errors(validate_graph_static(_two(first, second))) == [("GE023", location)]


@pytest.mark.skipif(sys.platform != "darwin", reason="Git converts names to NFC on macOS only")
def test_git_on_macos_creates_a_branch_named_in_nfd_in_nfc(tmp_path):
    """Why NFC is required: ``git init`` sets core.precomposeUnicode on macOS, and Git then converts the names
    in its arguments, so the generators' ``git checkout -B cafe<U+0301>`` created ``caf<U+00E9>``."""
    assert _git(tmp_path, "init", "-q", "--template=").returncode == 0
    assert _git(tmp_path, "checkout", "-q", "-B", CAFE_NFD).returncode == 0
    assert _git(tmp_path, "-c", "user.name=a", "-c", "user.email=a@example.com",
                "commit", "-q", "--allow-empty", "-m", "c0").returncode == 0
    assert _git(tmp_path, "for-each-ref", "--format=%(refname)").stdout.strip() == f"refs/heads/{CAFE_NFC}"


NO_CLASH = {
    "two names": ("feature", "fix"),
    "a common prefix that is no directory": ("feature", "feature-x"),
    "siblings": ("release/1", "release/2"),
    "a longer directory name": ("feature", "features/x"),
    "one name": ("feature", "feature"),
}


@pytest.mark.parametrize("case", list(NO_CLASH))
def test_names_that_do_not_clash_pass(case):
    assert validate_graph_static(_two(*NO_CLASH[case])).findings == []


def test_a_name_is_checked_once_where_the_scenario_first_names_it():
    data = _graph(side="a b")
    data["commits"].append({"id": "c3", "branch": "a b", "parents": ["c2"], "message": "Note", "allow_empty": True,
                            "operations": []})
    assert _errors(validate_graph_static(data)) == [("GE023", "commits[1].branch")]


def test_a_tag_and_a_branch_are_compared_by_ge158_alone():
    """GE158 (issue #229) compares the tags with the branches; GE024 compares the branches with each other."""
    data = _graph()
    data["graph"]["ref_lifecycle"] = {"tags": [{"name": "Feature", "commit": "c0"}]}
    assert _errors(validate_graph_static(data)) == [("GE158", "graph.ref_lifecycle.tags[0].name")]


# --- an empty name, a blank one, and none --------------------------------------------------------

def test_an_empty_or_blank_branch_name_is_an_error():
    for name, problem in [("", "it is empty"), ("  ", "it contains a space"), ("\t", "the control character")]:
        result = validate_graph_static(_graph(side=name))
        assert _errors(result) == [("GE023", "commits[1].branch")], name
        assert problem in result.error_findings()[0].message


@pytest.mark.parametrize("suite", ["graph", "classic"])
def test_an_empty_default_branch_is_an_error_and_null_is_one_of_type(tmp_path, suite):
    data = _graph(default_branch="") if suite == "graph" else _classic("")
    code, type_code = ("GE023", "GE022") if suite == "graph" else ("E015", "E010")
    assert _errors(_validate(_write(tmp_path / "empty", suite, data), suite)) == [(code, "repository.default_branch")]
    data["repository"]["default_branch"] = None
    assert _errors(_validate(_write(tmp_path / "null", suite, data), suite)) == [(type_code, "repository.default_branch")]


def test_one_reading_of_an_absent_a_blank_and_an_empty_name():
    """Absent or null: the default branch (``main`` for ``default_branch``); an empty string is a name, which
    validation refuses.  The generators handed ``default_branch: ""`` to Git, and everyone else read ``""``
    as ``main`` and ``branch: ""`` as the default branch."""
    assert gitutils.scenario_default_branch({}) == "main"
    assert gitutils.scenario_default_branch({"repository": {"default_branch": None}}) == "main"
    assert gitutils.scenario_default_branch({"repository": {"default_branch": "trunk"}}) == "trunk"
    assert gitutils.scenario_default_branch({"repository": {"default_branch": ""}}) == ""
    assert gitutils.commit_branch({}, "trunk") == "trunk"
    assert gitutils.commit_branch({"branch": None}, "trunk") == "trunk"
    assert gitutils.commit_branch({"branch": ""}, "trunk") == ""
    assert gitutils.commit_branch({"branch": "topic"}, "trunk") == "topic"


@pytest.mark.parametrize("blank", [True, False], ids=["null", "absent"])
def test_a_commit_without_a_branch_is_on_the_default_branch(tmp_path, blank):
    data = _graph(default_branch="trunk", side=None)
    if blank:
        data["commits"][1]["branch"] = None
    path = _write(tmp_path, "graph", data)
    assert _errors(validate_graph_scenario_file(path, simulate=True)[1]) == []
    commit_map, verify = generate_graph_repository(path, tmp_path / "out")
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    assert {cid: entry["branch"] for cid, entry in commit_map.items()} == {"c0": "trunk", "c1": "trunk", "c2": "trunk"}
    assert git(tmp_path / "out" / "repo", "for-each-ref", "--format=%(refname)") == "refs/heads/trunk"


# --- what stays valid -----------------------------------------------------------------------------

def test_valid_names_generate_the_branches_the_scenario_names(tmp_path):
    data = _graph(default_branch="develop", side="release/2024.1", fix_branch="feature-x")
    path = _write(tmp_path, "graph", data)
    assert _errors(validate_graph_scenario_file(path, strict_paths=True, simulate=True)[1]) == []
    commit_map, verify = generate_graph_repository(path, tmp_path / "out")
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    refs = git(tmp_path / "out" / "repo", "for-each-ref", "--format=%(refname) %(objectname)").splitlines()
    assert refs == [f"refs/heads/develop {commit_map['c0']['hash']}", f"refs/heads/feature-x {commit_map['c2']['hash']}",
                    f"refs/heads/release/2024.1 {commit_map['c1']['hash']}"]


@pytest.mark.parametrize("name", ["release/2024.1", "feature-x", "user/alice/topic", "v1.0", CAFE_NFC, "FETCH_HEAD",
                                  "heads", "x/HEAD"])
def test_valid_names_pass_in_both_fields(tmp_path, name):
    assert validate_graph_static(_graph(side=name)).findings == []
    assert validate_graph_static(_graph(default_branch=name, side=None)).findings == []
    assert validator.default_branch_problem({"default_branch": name}) is None


def test_the_shipped_scenarios_name_branches_the_rule_accepts():
    graph = sorted((ROOT / "advanced-scenarios").glob("SZZG-*/scenario.graph.yml"))
    classic = sorted((ROOT / "scenarios").glob("SZZ-*/scenario.yml"))
    assert len(graph) >= 140 and len(classic) >= 130
    names = set()
    for path in graph:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert graph_scenario.branch_name_problems(data) == [], path.parent.name
        names.add(gitutils.scenario_default_branch(data))
        names.update(c["branch"] for c in data["commits"] if c.get("branch") is not None)
    for path in classic:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert validator.default_branch_problem(data["repository"]) is None, path.parent.name
    assert "main" in names and len(names) >= 10
