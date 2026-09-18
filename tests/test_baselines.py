"""Cheap-baseline family (#14, #35).

The baselines exist to publish the floor a real SZZ variant has to beat, so
the tests check two things: that each predictor reads only what its family is
allowed to read, and that the runner scores them through the ordinary
evaluator rather than with its own notion of a correct answer.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from szzbench.baselines import (
    FAMILIES,
    Scenario,
    _all_non_bfc,
    _at_index,
    _before_bfc,
    _by_author,
    _message_admits_fault,
    build_predictors,
    format_report,
    run_baselines,
)
from szzbench.graph_generator import generate_graph_repository

REPO_ROOT = Path(__file__).resolve().parents[1]


def _scenario(**overrides) -> Scenario:
    base = dict(
        scenario_id="SZZG-9000",
        suite="graph",
        category="G1",
        commit_ids=["c0", "c1", "c2", "c3"],
        bfc_ids=["c3"],
        authors={"c0": "A <a@x>", "c1": "B <b@x>", "c2": "A <a@x>", "c3": "C <c@x>"},
        messages={"c0": "add the range check", "c1": "make the range check exclusive",
                  "c2": "document the range check", "c3": "accept the bounds again"},
        hash_of={}, id_of={}, repo_dir=Path("/nonexistent"),
    )
    base.update(overrides)
    return Scenario(**base)


def test_position_predictors_read_only_the_order():
    scenario = _scenario()
    assert _at_index(0)(scenario) == ["c0"]
    assert _at_index(1)(scenario) == ["c1"]
    assert _at_index(9)(scenario) == []
    assert _before_bfc(scenario) == ["c2"]
    assert _all_non_bfc(scenario) == ["c0", "c1", "c2"]

    # a fix in first position has no predecessor
    assert _before_bfc(_scenario(commit_ids=["c3", "c1"], bfc_ids=["c3"])) == []


def test_author_predictor_returns_every_commit_of_that_author():
    scenario = _scenario()
    assert _by_author("A <a@x>")(scenario) == ["c0", "c2"]
    assert _by_author("B <b@x>")(scenario) == ["c1"]
    assert _by_author("nobody")(scenario) == []


def test_message_predictor_uses_its_own_vocabulary_and_skips_the_fix():
    scenario = _scenario(messages={
        "c0": "add the range check",
        "c1": "introduce context-sensitive bug",     # hyphenated: the lint pattern misses it
        "c2": "keep the faulty line for now",        # no "bug" at all
        "c3": "fix the bug",                          # the fix may say so
    })
    assert _message_admits_fault(scenario) == ["c1", "c2"]


def test_every_predictor_declares_a_known_family():
    predictors = build_predictors([_scenario()])
    names = [name for name, _, _, _ in predictors]
    assert len(names) == len(set(names)), "baseline names must be unique"
    assert {family for _, family, _, _ in predictors} <= set(FAMILIES)
    # one rule per author, plus the fixed rules
    assert sum(1 for name in names if name.startswith("author:")) == 3
    for fixed in ("message-admits-fault", "position-second", "position-before-fix",
                  "shape-last-toucher", "blame-deleted-lines"):
        assert fixed in names


def _generate(tmp_path: Path, scenario_id: str, commits, bugs) -> None:
    data = {
        "schema_version": "graph-0.1-draft",
        "meta": {"id": scenario_id, "title": "baseline fixture", "category": "test",
                 "category_code": "G1", "factors": []},
        "repository": {"name": scenario_id.lower(), "default_branch": "main",
                       "language": "java", "source_root": "src/main/java"},
        "graph": {"model": "commit_dag"},
        "commits": commits,
        "bugs": bugs,
    }
    directory = tmp_path / "advanced-scenarios" / scenario_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "scenario.graph.yml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    generate_graph_repository(path, tmp_path / "repos" / scenario_id / "default", force=True)


def test_runner_scores_through_the_evaluator(tmp_path):
    """A history whose BIC is the second commit must be solved by position-second."""
    java = "package example;\npublic class Range {\n  public boolean contains(int v, int lo, int hi) {\n    return v %s lo;\n  }\n}\n"
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the range check", "role": "initial",
         "operations": [{"type": "write_file", "path": "src/main/java/example/Range.java", "content": java % ">="}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "require values above the minimum",
         "role": "bug_introducing",
         "operations": [{"type": "replace", "path": "src/main/java/example/Range.java",
                         "old": "return v >= lo;", "new": "return v > lo;"}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "accept the lower bound again",
         "role": "bug_fixing",
         "operations": [{"type": "replace", "path": "src/main/java/example/Range.java",
                         "old": "return v > lo;", "new": "return v >= lo;"}]},
    ]
    bugs = [{"id": "B001",
             "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
             "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
             "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}}}]
    _generate(tmp_path, "SZZG-9000", commits, bugs)

    report = run_baselines(
        generated_root=tmp_path / "repos",
        scenarios_root=tmp_path,
        advanced_scenarios_root=tmp_path / "advanced-scenarios",
    )
    assert report["scenario_count"] == 1
    assert report["errors"] == []
    by_name = {item["name"]: item for item in report["baselines"]}
    assert by_name["position-second"]["passed"] == 1
    assert by_name["blame-deleted-lines"]["passed"] == 1
    assert by_name["position-first"]["passed"] == 0
    assert by_name["message-admits-fault"]["passed"] == 0
    assert report["solved_by_any_baseline"] == 1
    assert report["unsolved"] == []
    assert report["per_category"]["G1"] == {"total": 1, "solved": 1}

    # families can be restricted, and the text report mentions every baseline run
    only_position = run_baselines(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                                  advanced_scenarios_root=tmp_path / "advanced-scenarios",
                                  families=["position"])
    assert only_position["scenario_count"] == 1
    assert {item["family"] for item in only_position["baselines"]} == {"position"}
    # in a three-commit history the BIC is both the second commit and the one before the fix
    assert {item["name"] for item in only_position["baselines"] if item["passed"]} == {
        "position-second", "position-before-fix"}
    text = format_report(report)
    assert "position-second" in text and "solved by none" in text
    assert json.dumps(report)  # the report is JSON-serialisable for --json / --out
