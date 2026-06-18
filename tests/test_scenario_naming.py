from pathlib import Path
import re

import pytest
import yaml


SCENARIO_NAME_RE = re.compile(r"Scenario(\d{4})")
SCENARIO_ID_RE = re.compile(r"(?:SZZ|SZZG)-(\d{4})$")


def _scenario_files() -> list[Path]:
    return [
        *sorted(Path("scenarios").glob("SZZ-*/scenario.yml")),
        *sorted(Path("advanced-scenarios").glob("SZZG-*/scenario.graph.yml")),
    ]


@pytest.mark.parametrize("scenario_path", _scenario_files(), ids=str)
def test_scenario_java_names_match_scenario_id(scenario_path: Path):
    text = scenario_path.read_text(encoding="utf-8")
    scenario_numbers = set(SCENARIO_NAME_RE.findall(text))
    if not scenario_numbers:
        return

    data = yaml.safe_load(text)
    scenario_id = data["meta"]["id"]
    match = SCENARIO_ID_RE.fullmatch(scenario_id)

    assert match is not None
    assert scenario_numbers == {match.group(1)}
