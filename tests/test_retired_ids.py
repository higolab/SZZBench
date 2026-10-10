"""A retired scenario id is never issued or accepted again (issue #112).

`docs/retired-ids.md` records the id of every withdrawn scenario and says ids
are never renumbered, but nothing that assigned or accepted an id read it.
The skeleton builders numbered after the highest id in the index and the
scenario directories, so retiring the highest id of a suite issued it again,
and a retired id brought back by hand passed `validate-index`.  The builders,
the Scenario Editor (`tests/test_scenario_editor.py`) and `validate-index` now
read the first column of that table.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from szzbench.graph_scenario_builder import create_new_graph_scenario
from szzbench.scenario_builder import create_new_scenario
from szzbench.validator import validate_scenario_indexes

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs/retired-ids.md"


@pytest.fixture
def work(tmp_path):
    """Copies of both suites and of docs/retired-ids.md, laid out as in a checkout."""
    for suite in ("scenarios", "advanced-scenarios"):
        shutil.copytree(REPO / suite, tmp_path / suite)
    (tmp_path / "docs").mkdir()
    shutil.copy(DOC, tmp_path / "docs/retired-ids.md")
    return tmp_path


def _ids(index: Path) -> list[str]:
    return [entry["id"] for entry in yaml.safe_load(index.read_text(encoding="utf-8"))["scenarios"]]


def _retire(work: Path, suite: str, sid: str) -> None:
    """Withdraw ``sid`` as docs/retired-ids.md prescribes: its directory and
    index entry go, and a row naming it joins the table."""
    shutil.rmtree(work / suite / sid)
    index = work / suite / "index.yml"
    lines = index.read_text(encoding="utf-8").splitlines(keepends=True)
    start = lines.index(f"- id: {sid}\n")
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith(" ")), len(lines))
    text = "".join(lines[:start] + lines[end:])
    index.write_text(re.sub(r"^scenario_count: (\d+)$", lambda m: f"scenario_count: {int(m.group(1)) - 1}", text,
                            flags=re.MULTILINE), encoding="utf-8")
    doc = work / "docs/retired-ids.md"
    rows = doc.read_text(encoding="utf-8").splitlines(keepends=True)
    last = max(i for i, row in enumerate(rows) if row.startswith("|"))
    rows.insert(last + 1, f"| {sid} | Probe | Withdrawn by a test. | None. |\n")
    doc.write_text("".join(rows), encoding="utf-8")


def _bring_back(work: Path, sid: str, *, entry: bool = True) -> None:
    """The issue's reproduction: a copy of SZZ-0005 saved as ``sid``."""
    target = work / "scenarios" / sid
    target.mkdir()
    for name in ("scenario.yml", "README.md"):
        text = (work / "scenarios/SZZ-0005" / name).read_text(encoding="utf-8")
        (target / name).write_text(text.replace("SZZ-0005", sid), encoding="utf-8")
    if entry:
        index = work / "scenarios/index.yml"
        text = index.read_text(encoding="utf-8")
        start = text.index("- id: SZZ-0005\n")
        end = text.index("- id: ", start + 1)
        # in id order, as new-scenario and the Scenario Editor keep the entries (IW048, issue #158)
        at = next((m.start() for m in re.finditer(r"^- id: (\S+)$", text, flags=re.MULTILINE) if m.group(1) > sid),
                  len(text))
        index.write_text(text[:at] + text[start:end].replace("SZZ-0005", sid) + text[at:], encoding="utf-8")


def _findings(work: Path) -> list[tuple[str, str]]:
    result = validate_scenario_indexes(work / "scenarios", work / "advanced-scenarios")
    return [(finding.code, finding.message) for finding in result.findings]


def test_every_row_of_the_table_is_read():
    from szzbench.retired_ids import read_retired_ids

    rows = [line for line in DOC.read_text(encoding="utf-8").splitlines() if line.startswith("|")][2:]
    retired = read_retired_ids(REPO / "scenarios")
    assert rows and len(retired) == len(rows)
    assert {"SZZ-0058", "SZZ-0082", "SZZ-0120", "SZZ-0167"} <= retired


@pytest.mark.parametrize("suite", ["scenarios", "advanced-scenarios"])
def test_the_builders_skip_the_highest_id_once_it_is_retired(work, suite):
    index = work / suite / "index.yml"
    highest = _ids(index)[-1]
    _retire(work, suite, highest)
    assert _findings(work) == []                    # a clean retirement, as validate-index sees it
    build = create_new_scenario if suite == "scenarios" else create_new_graph_scenario
    result = build(title="Probe", category="Probe", root=work / suite)
    prefix, number = highest.split("-")
    assert result.scenario_id == f"{prefix}-{int(number) + 1:04d}"


def test_validate_index_reports_a_retired_id_brought_back(work):
    _bring_back(work, "SZZ-0058")
    findings = _findings(work)
    assert [code for code, _ in findings] == ["IE047"]
    assert "SZZ-0058" in findings[0][1] and "docs/retired-ids.md" in findings[0][1]


def test_validate_index_reports_a_retired_id_used_by_a_directory_alone(work):
    _bring_back(work, "SZZ-0082", entry=False)
    assert sorted(code for code, _ in _findings(work)) == ["IE030", "IE047"]


def test_the_table_is_read_beside_the_suite_roots(work):
    """A copy of the suites without docs/retired-ids.md has no retired ids."""
    _bring_back(work, "SZZ-0058")
    (work / "docs/retired-ids.md").unlink()
    assert _findings(work) == []


def test_the_shipped_suites_use_no_retired_id():
    assert validate_scenario_indexes(REPO / "scenarios", REPO / "advanced-scenarios").findings == []
