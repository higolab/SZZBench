"""verify and verify-graph report a missing repository instead of raising (issue #166).

With ``--commit-map`` naming an existing map, ``verify`` reached its first Git
call with a repository path that did not exist; ``subprocess.run`` raised
FileNotFoundError for the missing working directory, which nothing caught.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from szzbench.generator import generate_repository
from szzbench.gitutils import GitError, git_hash_exists, run_git, run_git_with_input
from szzbench.graph_generator import generate_graph_repository

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "scenarios/SZZ-0005/scenario.yml"
GRAPH = ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml"


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(ROOT / "src")})


@pytest.fixture(scope="module")
def outputs(tmp_path_factory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("outputs")
    generate_repository(CLASSIC, root / "classic", force=True)
    generate_graph_repository(GRAPH, root / "graph", force=True)
    return root / "classic", root / "graph"


@pytest.mark.parametrize("with_map", [True, False], ids=["commit-map", "default-map"])
@pytest.mark.parametrize("repo_kind", ["missing", "not-a-repository"])
def test_verify_reports_a_path_that_is_not_a_repository(tmp_path, outputs, with_map, repo_kind):
    repo = tmp_path / "nonexistent/repo"
    if repo_kind == "not-a-repository":
        repo.mkdir(parents=True)
    args = ["verify", str(repo), "--scenario", str(CLASSIC), "--json"]
    if with_map:
        args += ["--commit-map", str(outputs[0] / "metadata/commit-map.json")]
    completed = _cli(*args)
    assert completed.returncode == 1 and "Traceback" not in completed.stderr
    findings = json.loads(completed.stdout)["findings"]
    assert [(f["code"], f["location"]) for f in findings] == [("E603", str(repo))]


@pytest.mark.parametrize("with_maps", [True, False], ids=["maps", "default-maps"])
def test_verify_graph_reports_a_missing_repository(tmp_path, outputs, with_maps):
    repo = tmp_path / "nonexistent/repo"
    args = ["verify-graph", str(repo), "--scenario", str(GRAPH), "--json"]
    if with_maps:
        args += ["--commit-map", str(outputs[1] / "metadata/commit-map.json"),
                 "--graph-map", str(outputs[1] / "metadata/graph-map.json")]
    completed = _cli(*args)
    assert completed.returncode == 1 and "Traceback" not in completed.stderr
    assert [f["code"] for f in json.loads(completed.stdout)["findings"]] == ["GE603"]


def test_an_existing_repository_still_verifies(outputs):
    classic, graph = outputs
    assert _cli("verify", str(classic / "repo"), "--scenario", str(CLASSIC)).returncode == 0
    assert _cli("verify-graph", str(graph / "repo"), "--scenario", str(GRAPH)).returncode == 0


def test_git_that_cannot_start_is_a_git_error(tmp_path):
    missing = tmp_path / "no-such-directory"
    with pytest.raises(GitError, match=r"git status could not run: the directory .*no-such-directory does not exist"):
        run_git(missing, ["status"])
    with pytest.raises(GitError, match="could not run"):
        run_git_with_input(missing, ["hash-object", "--stdin"], b"x")
    assert git_hash_exists(missing, "HEAD") is False
