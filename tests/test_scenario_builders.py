"""The scenario skeletons grade a new scenario like any other (PR #75 review).

``advanced`` was the graph suite's placeholder difficulty until 2026-09-22
(``decisions/vocabulary.md`` section 4).  The authoring path must not keep
producing the value the migration retired: both skeleton builders default to a
graded value and refuse a value outside the vocabulary.
"""
from __future__ import annotations

import pytest

from szzbench.cli import main
from szzbench.graph_scenario_builder import NewGraphScenarioError, create_new_graph_scenario
from szzbench.graph_validator import validate_graph_scenario_file
from szzbench.scenario import load_yaml
from szzbench.scenario_builder import NewScenarioError, create_new_scenario
from szzbench.validator import validate_scenario_file


def _codes(result) -> set[str]:
    return {finding.code for finding in result.findings}


def test_the_graph_skeleton_default_difficulty_passes_gw461(tmp_path):
    root = tmp_path / "advanced-scenarios"
    assert main(["new-graph-scenario", "--title", "Difficulty default probe", "--category", "G4",
                 "--root", str(root)]) == 0
    path = root / "SZZG-0001" / "scenario.graph.yml"
    data, _ = load_yaml(path)
    assert data["meta"]["difficulty"] == "medium"
    _, result = validate_graph_scenario_file(path, lint=True)
    assert "GW461" not in _codes(result)
    assert "advanced" not in path.read_text()
    assert "advanced" not in (root / "index.yml").read_text().replace("advanced-scenarios", "")


def test_the_graph_builder_api_default_matches_the_cli(tmp_path):
    result = create_new_graph_scenario(title="API default probe", category="G4", root=tmp_path / "advanced-scenarios")
    data, _ = load_yaml(result.scenario_path)
    assert data["meta"]["difficulty"] == "medium"


def test_the_classic_skeleton_default_difficulty_passes_w461(tmp_path):
    root = tmp_path / "scenarios"
    assert main(["new-scenario", "--title", "Difficulty default probe", "--category", "S1", "--root", str(root)]) == 0
    path = root / "SZZ-0001" / "scenario.yml"
    _, result, _ = validate_scenario_file(path, lint=True)
    assert "W461" not in _codes(result)


def test_a_retired_or_unknown_difficulty_is_refused_by_both_builders(tmp_path):
    with pytest.raises(NewGraphScenarioError, match="easy, medium, hard"):
        create_new_graph_scenario(title="t", category="G4", root=tmp_path / "g", difficulty="advanced")
    with pytest.raises(NewScenarioError, match="easy, medium, hard"):
        create_new_scenario(title="t", category="S1", root=tmp_path / "s", difficulty="expert")
    with pytest.raises(SystemExit):        # argparse refuses it before the builder runs
        main(["new-graph-scenario", "--title", "t", "--category", "G4", "--root", str(tmp_path / "g2"),
              "--difficulty", "advanced"])
    assert not (tmp_path / "g").exists() and not (tmp_path / "g2").exists()
