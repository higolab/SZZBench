"""Check each shipped scenario's README, description and Java names together.

These checks share one YAML parse per scenario and report every problem under
its scenario id. Java names matter only when the source contains ScenarioNNNN;
there is no separate passing test for a scenario without such a name.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from szzbench.readme import check_readme, render_header, scenario_files, suite_of
from szzbench.scenario import load_yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_NAME_RE = re.compile(r"Scenario(\d{4})")
SCENARIO_ID_RE = re.compile(r"(?:SZZ|SZZG)-(\d{4})$")
GENERIC_DESCRIPTION_RE = re.compile(
    r"^Evaluates .* and checks whether SZZ identifies the expected bug-introducing commit set\.$"
)
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


@pytest.mark.parametrize("scenario_path", scenario_files(ROOT / "scenarios", ROOT / "advanced-scenarios"),
                         ids=lambda p: p.parent.name)
def test_shipped_metadata(scenario_path: Path):
    """Regenerate stale headers with ``szzbench readme --write``."""
    data, result = load_yaml(scenario_path)
    assert data is not None, result.findings
    text = scenario_path.with_name("README.md").read_text(encoding="utf-8")
    problems = check_readme(text, render_header(data, suite_of(scenario_path)))
    problems.extend(f"README still carries {phrase!r}" for phrase in README_BOILERPLATE if phrase in text)

    description = " ".join(str(data["meta"].get("description", "")).split())
    if GENERIC_DESCRIPTION_RE.search(description):
        problems.append("description restates the title with the template sentence")
    if "intermediate intermediate" in description:
        problems.append("description contains 'intermediate intermediate'")

    if suite_of(scenario_path) == "advanced-scenarios":
        design = data.get("scenario_design") or {}
        if "required_extensions_from_source" in design:
            problems.append("scenario_design repeats the header's factors and graph features")
        if "requires graph-aware scenario semantics" in str(design.get("current_schema_limitation", "")):
            problems.append("scenario_design carries the graph-semantics template sentence")
        if design.get("evaluation_points") == GENERIC_EVALUATION_POINTS:
            problems.append("scenario_design carries the generic evaluation points")
        title = data["meta"]["title"].lower()
        purpose = " ".join(str(design.get("purpose", "")).split()).lower()
        if purpose.startswith(f"evaluate {title} and whether"):
            problems.append("scenario_design purpose restates the title")

    numbers = set(SCENARIO_NAME_RE.findall(scenario_path.read_text(encoding="utf-8")))
    if numbers:
        match = SCENARIO_ID_RE.fullmatch(data["meta"]["id"])
        if match is None or numbers != {match.group(1)}:
            problems.append(f"Java ScenarioNNNN names {sorted(numbers)} do not match {data['meta']['id']}")

    assert problems == [], "\n".join(problems)
