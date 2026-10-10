"""The classic verifier's basic blame check gives each outcome the graph verifier's number (issue #275).

``verify`` reported a fault statement absent from the BFC parent, blame that
reaches another commit than the BIC, and a check that could not run, all as
W700, where ``verify-graph`` has GW701, GW703 and GW702 (and GW700 for a fault
file it cannot read at the BFC parent).  A script reading ``verify --json``
had to parse the message to tell a property of the scenario from a failure of
the environment.  The absent statement (W701) is in test_verifier_declarations.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from szzbench import verifier
from szzbench.generator import generate_repository
from szzbench.gitutils import GitError
from szzbench.verifier import verify_generated_repo

ROOT = Path(__file__).resolve().parent.parent
#: blame at c2^ reaches c0, which wrote the line, not the BIC c1 that deleted the guard above it
SCENARIO = ROOT / "scenarios" / "SZZ-0078" / "scenario.yml"
#: the outcomes of the basic blame check
BLAME = {"I700", "I701", "W700", "W701", "W702", "W703"}


@pytest.fixture(scope="module")
def repo(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("szz0078") / "SZZ-0078"
    _, verify = generate_repository(SCENARIO, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    return out / "repo"


def _blame_findings(result) -> list[tuple[str, str]]:
    return [(f.code, f.message) for f in result.findings if f.code in BLAME]


def test_blame_that_reaches_another_commit_than_the_bic_is_w703(repo):
    [(code, message)] = _blame_findings(verify_generated_repo(repo, SCENARIO))
    assert code == "W703" and message.startswith("bug B001: basic git blame reaches "), message


def test_a_git_blame_that_fails_is_w702(repo, monkeypatch):
    def fails(*args):
        raise GitError("git blame exited with 128")
    monkeypatch.setattr(verifier, "git_blame_line", fails)
    result = verify_generated_repo(repo, SCENARIO)
    assert _blame_findings(result) == [("W702", "bug B001: basic blame check failed: git blame exited with 128")]


def test_a_fault_file_the_bfc_parent_does_not_have_skips_the_check_with_w700(repo, tmp_path):
    data = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    data["bugs"][0]["fault"]["file"] = "src/main/java/example/Missing.java"
    scenario = tmp_path / "scenario.yml"
    scenario.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = verify_generated_repo(repo, scenario)
    assert "E300" in {f.code for f in result.findings}             # not at fault.commit either
    [(code, message)] = _blame_findings(result)
    assert code == "W700" and message.startswith("bug B001: basic blame check skipped: "), message
