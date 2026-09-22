"""No scenario carries the 2026-09-17 template's boilerplate any more (issue #19).

The template wrote the same sentences into every graph README and scenario
file it produced -- a purpose that restated the title, a "graph-aware
semantics" sentence on linear histories, a features list that duplicated the
metadata, three generic evaluation bullets, a directory tree -- and the same
`Evaluates <title> and checks whether ...` description into classic
scenarios.  The generated header (`docs/scenario-readme.md`) now states the
facts those sections copied; this test keeps the sentences from coming back.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
GRAPH = sorted(ROOT.glob("advanced-scenarios/SZZG-*/scenario.graph.yml"))
CLASSIC = sorted(ROOT.glob("scenarios/SZZ-*/scenario.yml"))

GENERIC_EVALUATION_POINTS = [
    "Whether SZZ identifies the expected BIC set.",
    "Whether structural or contextual history is handled according to the scenario factors.",
    "Whether the expected_szz evaluation policy is applied correctly.",
]
README_BOILERPLATE = (
    "## Required graph-schema features",
    "## Files\n",
    "requires graph-aware scenario semantics",
    "and whether SZZ identifies the expected bug-introducing commit set.",
    "and checks whether SZZ identifies the expected bug-introducing commit set.",
    "\n".join(f"- {bullet}" for bullet in GENERIC_EVALUATION_POINTS),
)


def _ids(paths):
    return [p.parent.name for p in paths]


@pytest.mark.parametrize("scenario_path", GRAPH + CLASSIC, ids=_ids(GRAPH + CLASSIC))
def test_readme_carries_no_template_boilerplate(scenario_path: Path):
    text = scenario_path.with_name("README.md").read_text(encoding="utf-8")
    for phrase in README_BOILERPLATE:
        assert phrase not in text, f"{scenario_path.parent.name}: README still carries {phrase!r}"


@pytest.mark.parametrize("scenario_path", GRAPH, ids=_ids(GRAPH))
def test_graph_scenario_design_carries_no_template_boilerplate(scenario_path: Path):
    data = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    design = data.get("scenario_design") or {}
    assert "required_extensions_from_source" not in design, "the header's factors and graph-features rows say this"
    assert "requires graph-aware scenario semantics" not in str(design.get("current_schema_limitation", ""))
    assert design.get("evaluation_points") != GENERIC_EVALUATION_POINTS
    title = data["meta"]["title"].lower()
    purpose = " ".join(str(design.get("purpose", "")).split()).lower()
    assert not purpose.startswith(f"evaluate {title} and whether"), "the purpose restates the title"


@pytest.mark.parametrize("scenario_path", GRAPH + CLASSIC, ids=_ids(GRAPH + CLASSIC))
def test_description_is_not_the_template_sentence(scenario_path: Path):
    data = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
    description = " ".join(str(data["meta"].get("description", "")).split())
    assert not re.search(r"^Evaluates .* and checks whether SZZ identifies the expected bug-introducing commit set\.$",
                         description), f"{scenario_path.parent.name}: description restates the title"
    assert "intermediate intermediate" not in description
