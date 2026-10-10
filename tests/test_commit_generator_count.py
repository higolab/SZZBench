"""A ``commit_generator``'s ``count`` is read one way (issue #230).

``graph_operations.commit_generator_plan`` (generation, ``--simulate``)
refused a count ``int()`` cannot read, ``OverflowError`` included, while
``gitutils.planned_generated_commits`` (the reachability model, the author
lint, GW151, ``verify-graph``) caught ``TypeError`` and ``ValueError`` only.
``count: .inf`` ended ``verify-graph`` in a traceback, and the author lint
swallowed the exception and checked nothing.  Now the planned ids skip exactly
the counts generation refuses (``gitutils.commit_generator_count``).
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from szzbench import gitutils
from szzbench.findings import ValidationResult
from szzbench.gitutils import planned_generated_commits
from szzbench.graph_generator import generate_graph_repository
from szzbench.graph_operations import commit_generator_plan
from szzbench.graph_verifier import verify_graph_generated_repo
from szzbench.validator import lint_author_coincidence

ANN = "Ann Example <ann@example.com>"
BOB = "Bob Example <bob@example.com>"


def _generator(count) -> dict:
    return {"type": "commit_generator", "generator": "catalog_sync", "count": count, "files": 1, "path": "generated"}


def _scenario(count) -> dict:
    """Ann writes c0 and c1, the required commits; Bob's c2 expands ``count`` generated commits."""
    def commit(cid: str, parents: list[str], author: str, operations: list[dict]) -> dict:
        return {"id": cid, "branch": "main", "parents": parents, "author": author, "message": f"Edit the notes ({cid})",
                "role": "intermediate", "operations": operations}
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "Generator count", "category": "fixture", "factors": ["single-bic"]},
        "repository": {"name": "generator-count", "default_branch": "main"},
        "graph": {"model": "commit_dag"},
        "commits": [commit("c0", [], ANN, [{"type": "write_file", "path": "a.txt", "content": "a\n"}]),
                    commit("c1", ["c0"], ANN, [{"type": "write_file", "path": "b.txt", "content": "b\n"}]),
                    commit("c2", ["c1"], BOB, [_generator(count), {"type": "write_file", "path": "c.txt", "content": "c\n"}])],
        "bugs": [{"id": "B001",
                  "bug_introducing_commits": [{"commit": "c0", "role": "direct"}, {"commit": "c1", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0", "c1"]}},
    }


@pytest.mark.parametrize("count", [math.inf, -math.inf, math.nan, -1, "many", 3, 2500],
                         ids=["inf", "-inf", "nan", "negative", "many", "3", "capped"])
def test_planned_generated_commits_skips_exactly_the_counts_generation_refuses(count):
    """An infinite count raised OverflowError out of planned_generated_commits; generation refused it."""
    planned = planned_generated_commits("c2", {"id": "c2", "operations": [_generator(count)]})
    try:
        plan = commit_generator_plan(_generator(count), "c2")
    except ValueError:
        assert planned == []
    else:
        assert planned == [f"c2.g{n}" for n in range(1, plan.count + 1)]


def test_the_shared_reading_names_the_field_as_generation_does():
    for count in (math.inf, math.nan, -1, "many"):
        with pytest.raises(ValueError) as refused:
            commit_generator_plan(_generator(count), "c2")
        with pytest.raises(ValueError) as read:
            gitutils.commit_generator_count(_generator(count), "c2")
        assert str(read.value) == str(refused.value), count


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    """The repository of ``_scenario(3)``: c1 <- c2.g1 <- c2.g2 <- c2.g3 <- c2."""
    tmp = tmp_path_factory.mktemp("generated")
    scenario = tmp / "scenario.graph.yml"
    scenario.write_text(yaml.safe_dump(_scenario(3), sort_keys=False), encoding="utf-8")
    _, result = generate_graph_repository(scenario, tmp / "out", force=True)
    assert not result.has_errors(), result.to_dict()
    return tmp / "out"


@pytest.mark.parametrize("count", [math.inf, -math.inf], ids=["inf", "-inf"])
def test_verify_graph_reports_an_infinite_count_instead_of_a_traceback(tmp_path, generated, count):
    """The issue's reproduction: the scenario of an existing output with its count changed to .inf.
    The count plans no generated commits, so c2's first parent and its generated_commits disagree."""
    scenario = tmp_path / "scenario.graph.yml"
    scenario.write_text(yaml.safe_dump(_scenario(count), sort_keys=False), encoding="utf-8")     # count: .inf
    result = verify_graph_generated_repo(generated / "repo", scenario)
    assert [(f.code, f.location) for f in result.findings if f.severity == "ERROR"] == [
        ("GE627", "commits[2].parents"), ("GE633", "commits[2]")]


def test_the_author_lint_still_runs_with_an_infinite_count():
    """Ann wrote exactly the required commits {c0, c1}: GW413.  With count: .inf the lint caught the
    OverflowError and returned without a word."""
    result = ValidationResult()
    lint_author_coincidence(_scenario(math.inf), "advanced-scenarios", result, prefix="GW")
    assert [f.code for f in result.findings] == ["GW413"]
