"""A commit message Git does not store as written, and a generation that fails verification (issue #163).

A classic commit whose ``message`` ended with a newline (``message: |``) or
had a body after a blank line passed ``validate --simulate --lint``, and its
generation ended with ``GENERATION_FAILED: Generated repository failed
verification.`` and nothing else.  ``git commit -m`` drops the trailing
newline, and the subject it gives back (``%s``) is the first line only, while
the verifier compares it with the whole message: E602.  The finding was
written to ``verify-result.json`` only; ``generate`` and
``generate-all-repos`` did not print it, and the classic output was left
without ``generation.log`` and ``generation-error.json``.

``validate`` (E012) and ``validate-graph`` (GE070) now reject a message that
does not come back from Git as written: a line break, leading or trailing
whitespace, an empty message, a sign-off line on its own, a NUL or a lone
surrogate.  A generation that fails verification prints the findings and
records the failure like any other.
"""
from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

import szzbench.graph_validator as graph_validator
import szzbench.validator as validator
from support import git
from szzbench.bulk_generator import generate_all_repositories
from szzbench.generator import GenerationError, generate_repository
from szzbench.gitutils import GitError, git_message, init_repo
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_validator import validate_graph_static
from szzbench.validator import validate_static

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = yaml.safe_load((ROOT / "scenarios/SZZ-0005/scenario.yml").read_text(encoding="utf-8"))
GRAPH = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml").read_text(encoding="utf-8"))
CLASSIC_FILE = "scenarios/SZZ-0005/scenario.yml"
GRAPH_FILE = "advanced-scenarios/SZZG-0001/scenario.graph.yml"
CLASSIC_SUBJECT = "Initial required field annotation"      # SZZ-0005's c0
GRAPH_SUBJECT = "Make the range check exclusive"           # SZZG-0001's c1

#: The two messages of the issue, for the commit of each suite.
SHAPES = {
    "trailing-newline": "{}\n",
    "body": "{}\n\nSee the design note.",
}

#: The CLI with the new rule switched off, so that such a message reaches generation
#: and its verification, as it did before.
WITHOUT_THE_RULE = (
    "import sys\n"
    "import szzbench.graph_validator as graph_validator\n"
    "import szzbench.validator as validator\n"
    "validator.commit_message_problem = graph_validator.commit_message_problem = lambda message: None\n"
    "from szzbench.cli import main\n"
    "sys.exit(main(sys.argv[1:]))\n"
)


def _with_message(base: dict, index: int, message: str) -> dict:
    data = deepcopy(base)
    data["commits"][index]["message"] = message
    return data


def _write(root: Path, relative: str, data: dict) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _classic(root: Path, shape: str) -> Path:
    return _write(root, CLASSIC_FILE, _with_message(CLASSIC, 0, SHAPES[shape].format(CLASSIC_SUBJECT)))


def _graph(root: Path, shape: str) -> Path:
    return _write(root, GRAPH_FILE, _with_message(GRAPH, 1, SHAPES[shape].format(GRAPH_SUBJECT)))


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True)


def _szzbench_without_the_rule(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", WITHOUT_THE_RULE, *args], cwd=cwd, capture_output=True, text=True)


def _json_errors(completed: subprocess.CompletedProcess) -> list[tuple[str, str]]:
    return [(f["code"], f["location"]) for f in json.loads(completed.stdout)["findings"] if f["severity"] == "ERROR"]


@pytest.fixture
def without_the_rule(monkeypatch):
    for module in (validator, graph_validator):
        monkeypatch.setattr(module, "commit_message_problem", lambda message: None, raising=False)


# --- validation, through the CLI ------------------------------------------------------

def test_the_issues_block_scalar_is_rejected_by_validate(tmp_path):
    """The issue's reproduction: ``message: |`` keeps a trailing newline."""
    path = tmp_path / CLASSIC_FILE
    path.parent.mkdir(parents=True)
    text = (ROOT / CLASSIC_FILE).read_text(encoding="utf-8")
    path.write_text(text.replace(f'message: "{CLASSIC_SUBJECT}"', f"message: |\n      {CLASSIC_SUBJECT}", 1),
                    encoding="utf-8")
    completed = _szzbench(tmp_path, "validate", "--json", CLASSIC_FILE)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert _json_errors(completed) == [("E012", "commits[0].message")]


@pytest.mark.parametrize("shape", list(SHAPES))
def test_validate_rejects_the_message_without_simulate(tmp_path, shape):
    """Run on a path relative to the working directory."""
    _classic(tmp_path, shape)
    completed = _szzbench(tmp_path, "validate", "--json", CLASSIC_FILE)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert _json_errors(completed) == [("E012", "commits[0].message")]


@pytest.mark.parametrize("shape", list(SHAPES))
def test_validate_graph_rejects_the_message_without_simulate(tmp_path, shape):
    _graph(tmp_path, shape)
    completed = _szzbench(tmp_path, "validate-graph", "--json", GRAPH_FILE)
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert _json_errors(completed) == [("GE070", "commits[1].message")]


@pytest.mark.parametrize("command, path_of, failed", [
    ("generate", _classic, "[ERROR] GENERATION_FAILED: Scenario validation failed."),
    ("generate-graph", _graph, "[ERROR] GRAPH_GENERATION_FAILED: Graph scenario validation failed."),
], ids=["classic", "graph"])
def test_generation_refuses_the_message_before_writing(tmp_path, command, path_of, failed):
    path = path_of(tmp_path, "trailing-newline")
    completed = _szzbench(tmp_path, command, str(path.relative_to(tmp_path)), "--out", "out")
    assert completed.returncode == 1 and completed.stderr.startswith(failed), completed.stderr
    assert not (tmp_path / "out").exists()


# --- what the finding says --------------------------------------------------------------

@pytest.mark.parametrize("message, says", [
    (f"{CLASSIC_SUBJECT}\n", "ends with a line break (a `message: |` block scalar keeps one), which Git drops: "
                             f"the subject read back would be '{CLASSIC_SUBJECT}', so verification would fail."),
    (f"{CLASSIC_SUBJECT}\n\nSee the design note.", "has a body after a blank line, which Git stores apart from the "
                                                   f"subject: the subject read back would be '{CLASSIC_SUBJECT}'"),
    ("Initial required\nfield annotation", "spans 2 lines, which Git joins into one subject: "
                                           "the subject read back would be 'Initial required field annotation'"),
    (f"\n{CLASSIC_SUBJECT}", "starts with a line break, which Git drops"),
    (f"{CLASSIC_SUBJECT} ", "ends with whitespace (' '), which Git drops"),
    (f"{CLASSIC_SUBJECT}　", "ends with whitespace ('\\u3000'), which verification strips from the subject"),
    (f"\t{CLASSIC_SUBJECT}", "starts with whitespace ('\\t'), which verification strips from the subject"),
    ("Initial\rrequired field annotation", "contains a carriage return, which verification reads back as a line break"),
    ("", "is empty, and Git refuses a commit with an empty message"),
    ("  ", "is only whitespace, which Git removes, and Git refuses a commit with an empty message"),
    ("Signed-off-by: A U Thor <author@example.com>", "starts with 'Signed-off-by:': Git does not count a sign-off line"),
    ("Initial\0required", "contains a NUL character"),
    ("Initial\udc80required", "contains a lone surrogate (U+DC80)"),
], ids=["trailing-newline", "body", "two-lines", "leading-newline", "trailing-space", "trailing-ideographic-space",
        "leading-tab", "carriage-return", "empty", "whitespace", "sign-off", "nul", "surrogate"])
def test_the_finding_says_what_is_wrong_and_what_git_stores(message, says):
    [finding] = [f for f in validate_static(_with_message(CLASSIC, 0, message)).findings if f.severity == "ERROR"]
    assert (finding.code, finding.location) == ("E012", "commits[0].message")
    assert finding.message.startswith(f"Commit 'c0' message {says}"), finding.message
    assert finding.message.endswith("Write it on one line, without leading or trailing whitespace; "
                                    "a message body is not supported.")
    [finding] = [f for f in validate_graph_static(_with_message(GRAPH, 1, message)).findings if f.severity == "ERROR"]
    assert (finding.code, finding.location) == ("GE070", "commits[1].message")
    assert finding.message.startswith(f"Commit 'c1' message {says}"), finding.message


def test_a_graph_commit_without_a_message_is_not_checked():
    """``inherit_message`` and ``revert_of`` supply the subject from Git; there is nothing to check."""
    data = deepcopy(GRAPH)
    del data["commits"][1]["message"]
    assert [f for f in validate_graph_static(data).findings if f.code == "GE070"] == []


def test_no_shipped_scenario_has_such_a_message():
    for path in sorted(ROOT.glob("scenarios/SZZ-*/scenario.yml")):
        findings = validate_static(yaml.safe_load(path.read_text(encoding="utf-8"))).findings
        assert [f for f in findings if f.code == "E012"] == [], path
    for path in sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")):
        findings = validate_graph_static(yaml.safe_load(path.read_text(encoding="utf-8"))).findings
        assert [f for f in findings if f.code == "GE070"] == [], path


# --- the rule is what Git does ------------------------------------------------------------

#: name -> (message, whether Git gives it back as written)
MESSAGES = {
    "plain": ("Fix the range check", True),
    "inner-tab": ("Fix\tthe range check", True),
    "inner-double-space": ("Fix  the range check", True),
    "inner-ideographic-space": ("範囲　チェックを直す", True),
    "inner-no-break-space": ("Fix the range check", True),
    "inner-vertical-tab": ("Fix\vthe range check", True),
    "inner-form-feed": ("Fix\fthe range check", True),
    "inner-next-line": ("Fix\u0085the range check", True),
    "inner-line-separator": ("Fix the range check", True),
    "inner-escape": ("Fix\x1bthe range check", True),
    "trailing-zero-width-space": ("Fix the range check​", True),
    "hash-first": ("# Fix the range check", True),
    "dash-first": ("--amend the range check", True),
    "non-ascii": ("Corrige la vérification — 範囲チェック 🐛", True),
    "co-author-trailer": ("Co-authored-by: A U Thor <author@example.com>", True),
    "sign-off-without-space": ("Signed-off-by:A U Thor", True),
    "backslash-n": ("Fix the range check\\n", True),
    "long": ("x" * 2000, True),
    "empty": ("", False),
    "space-only": (" ", False),
    "tab-only": ("\t", False),
    "newline-only": ("\n", False),
    "trailing-newline": ("Fix the range check\n", False),
    "trailing-newlines": ("Fix the range check\n\n", False),
    "body": ("Fix the range check\n\nSee the design note.", False),
    "body-after-a-whitespace-line": ("Fix the range check\n \t\nSee the design note.", False),
    "two-lines": ("Fix the range check\nand the bounds", False),
    "leading-newline": ("\nFix the range check", False),
    "trailing-space": ("Fix the range check ", False),
    "trailing-tab": ("Fix the range check\t", False),
    "leading-space": (" Fix the range check", False),
    "leading-tab": ("\tFix the range check", False),
    "trailing-carriage-return": ("Fix the range check\r", False),
    "crlf": ("Fix the range check\r\n", False),
    "inner-carriage-return": ("Fix\rthe range check", False),
    "trailing-vertical-tab": ("Fix the range check\v", False),
    "trailing-form-feed": ("Fix the range check\f", False),
    "trailing-ideographic-space": ("Fix the range check　", False),
    "leading-ideographic-space": ("　Fix the range check", False),
    "trailing-no-break-space": ("Fix the range check ", False),
    "trailing-next-line": ("Fix the range check\u0085", False),
    "trailing-line-separator": ("Fix the range check ", False),
    "trailing-file-separator": ("Fix the range check\x1c", False),
    "sign-off": ("Signed-off-by: A U Thor <author@example.com>", False),
    "nul": ("Fix\0the range check", False),
    "lone-low-surrogate": ("Fix\udc80the range check", False),
    "lone-high-surrogate": ("Fix\ud800the range check", False),
}


@pytest.fixture(scope="module")
def message_repo(tmp_path_factory) -> Path:
    repo = tmp_path_factory.mktemp("messages") / "repo"
    init_repo(repo, "main")
    return repo


@pytest.mark.parametrize("name", list(MESSAGES))
def test_the_rule_is_what_git_commit_stores(message_repo, name):
    """``git commit -m`` and the verifiers' reading of ``%s``, against the rule and its model of them."""
    message, kept = MESSAGES[name]
    try:
        git(message_repo, "commit", "--allow-empty", "-m", message)
    except (GitError, ValueError):     # refused by Git, or not passed to it at all (a NUL, a lone surrogate)
        stored = None
    else:
        stored = git_message(message_repo, "HEAD")
    assert (stored == message) == kept, repr(stored)
    assert (validator.commit_message_problem(message) is None) == kept
    if stored is not None and _is_utf8(message):     # Git rewrites a surrogate's bytes; the model does not
        assert validator.subject_read_back(message) == stored


def _is_utf8(text: str) -> bool:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


# --- a generation that fails verification -------------------------------------------------

@pytest.mark.parametrize("shape", list(SHAPES))
def test_classic_generation_records_the_failed_verification(tmp_path, without_the_rule, shape):
    with pytest.raises(GenerationError, match=r"^Generated repository failed verification\.$") as raised:
        generate_repository(_classic(tmp_path, shape), tmp_path / "out")
    errors = [(f.code, f.location) for f in raised.value.verify_result.findings if f.severity == "ERROR"]
    assert errors == [("E602", "commits.c0.message")]
    metadata = tmp_path / "out/metadata"
    error = json.loads((metadata / "generation-error.json").read_text(encoding="utf-8"))
    assert error["error"] == "Generated repository failed verification."
    log = (metadata / "generation.log").read_text(encoding="utf-8").splitlines()
    assert log[-2:] == ["Verification: [ERROR] E602: Commit message mismatch for 'c0'. (commits.c0.message)",
                        "ERROR: Generated repository failed verification."]
    assert (metadata / "verify-result.json").is_file()
    assert not (metadata / "manifest.json").exists()


@pytest.mark.parametrize("shape", list(SHAPES))
def test_graph_generation_records_the_failed_verification(tmp_path, without_the_rule, shape):
    with pytest.raises(GraphGenerationError, match=r"^Generated graph repository failed verification\.$") as raised:
        generate_graph_repository(_graph(tmp_path, shape), tmp_path / "out")
    errors = [(f.code, f.location) for f in raised.value.verify_result.findings if f.severity == "ERROR"]
    assert errors == [("GE623", "commits[1].message")]
    metadata = tmp_path / "out/metadata"
    error = json.loads((metadata / "generation-error.json").read_text(encoding="utf-8"))
    assert error["error"] == "Generated graph repository failed verification."
    log = (metadata / "generation.log").read_text(encoding="utf-8").splitlines()
    assert log[-2:] == ["Verification: [ERROR] GE623: Commit message mismatch for 'c1'. (commits[1].message)",
                        "ERROR: Generated graph repository failed verification."]
    assert not (metadata / "manifest.json").exists()


def test_generate_prints_the_findings_and_records_the_failure(tmp_path):
    _classic(tmp_path, "trailing-newline")
    completed = _szzbench_without_the_rule(tmp_path, "generate", CLASSIC_FILE, "--out", "out")
    assert completed.returncode == 1
    lines = completed.stderr.splitlines()
    assert lines[0] == "[ERROR] GENERATION_FAILED: Generated repository failed verification.", completed.stderr
    assert "[ERROR] E602: Commit message mismatch for 'c0'. (commits.c0.message)" in lines
    assert lines[-1].startswith("Summary: 1 error(s), ")
    metadata = tmp_path / "out/metadata"
    assert (metadata / "generation.log").is_file() and (metadata / "generation-error.json").is_file()
    assert not (metadata / "manifest.json").exists()


def test_generate_graph_prints_the_findings_and_records_the_failure(tmp_path):
    _graph(tmp_path, "body")
    completed = _szzbench_without_the_rule(tmp_path, "generate-graph", GRAPH_FILE, "--out", "out")
    assert completed.returncode == 1
    lines = completed.stderr.splitlines()
    assert lines[0] == "[ERROR] GRAPH_GENERATION_FAILED: Generated graph repository failed verification.", completed.stderr
    assert "[ERROR] GE623: Commit message mismatch for 'c1'. (commits[1].message)" in lines
    assert lines[-1].startswith("Summary: 1 error(s), ")
    metadata = tmp_path / "out/metadata"
    assert (metadata / "generation.log").is_file() and (metadata / "generation-error.json").is_file()
    assert not (metadata / "manifest.json").exists()


def test_generate_all_repos_keeps_the_verification_errors_of_a_failed_item(tmp_path, without_the_rule):
    _classic(tmp_path, "body")
    _graph(tmp_path, "trailing-newline")
    result = generate_all_repositories(scenarios_root=tmp_path / "scenarios",
                                       advanced_scenarios_root=tmp_path / "advanced-scenarios",
                                       output_root=tmp_path / "repos")
    by_id = {item.scenario_id: item for item in result.items}
    assert [(f.code, f.location) for f in by_id["SZZ-0005"].verification_errors] == [("E602", "commits.c0.message")]
    assert [(f.code, f.location) for f in by_id["SZZG-0001"].verification_errors] == [("GE623", "commits[1].message")]
    assert result.failed_count == 2


def test_generate_all_repos_prints_the_verification_errors_under_the_failed_item(tmp_path):
    _classic(tmp_path, "trailing-newline")
    _graph(tmp_path, "body")
    completed = _szzbench_without_the_rule(tmp_path, "generate-all-repos", "--scenarios-root", "scenarios",
                                           "--advanced-scenarios-root", "advanced-scenarios", "--out-root", "repos")
    assert completed.returncode == 1 and "  Failed:      2" in completed.stdout
    lines = completed.stderr.splitlines()
    # generate-all-repos generates into <id>/default.tmp, and names it (issue #168)
    repos = tmp_path.resolve() / "repos"
    classic = lines.index("Failed [classic] SZZ-0005: repos/SZZ-0005/default: Generated repository failed verification; "
                          f"the files of this attempt are in {repos / 'SZZ-0005/default.tmp'}")
    assert lines[classic + 1] == "  [ERROR] E602: Commit message mismatch for 'c0'. (commits.c0.message)"
    graph = lines.index("Failed [graph] SZZG-0001: repos/SZZG-0001/default: Generated graph repository failed "
                        f"verification; the files of this attempt are in {repos / 'SZZG-0001/default.tmp'}")
    assert lines[graph + 1] == "  [ERROR] GE623: Commit message mismatch for 'c1'. (commits[1].message)"
    for sid in ("SZZ-0005", "SZZG-0001"):
        assert not (tmp_path / "repos" / sid / "default").exists()
        metadata = tmp_path / "repos" / sid / "default.tmp/metadata"
        assert (metadata / "generation.log").is_file() and (metadata / "generation-error.json").is_file()
        assert not (metadata / "manifest.json").exists()
