"""The Markdown report keeps one row per scenario, whatever the tool wrote (issue #139).

Unknown references are listed as written, and a tool's run errors are copied
into the report.  A ``|`` in either ended a table cell, so later cells moved
left and a fake ``PASS`` could appear in the Status column, and a newline
split a table row or a list item.  The JSON report keeps the text unchanged.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from szzbench.evaluator import evaluate_predictions
from szzbench.generator import generate_repository

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = 18
PIPE_REF = "x | PASS | ok"
NEWLINE_REF = "line1\nline2"
ERROR = "Traceback (most recent call last):\n  File \"tool.py\", line 3\nValueError: bad | input\r\n"


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    root = tmp_path_factory.mktemp("generated")
    for sid in ("SZZ-0006", "SZZ-0005"):
        generate_repository(ROOT / f"scenarios/{sid}/scenario.yml", root / sid / "default", force=True)
    path = root / "predictions.jsonl"
    records = [
        {"scenario_id": "SZZ-0006", "predictions": [{"inducing_commit": "c1"}, {"inducing_commit": PIPE_REF},
                                                     {"inducing_commit": NEWLINE_REF}]},
        {"scenario_id": "SZZ-0005", "status": "error", "errors": [ERROR], "predictions": []},
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return evaluate_predictions(path, generated_root=root, scenarios_root=ROOT / "scenarios",
                                advanced_scenarios_root=ROOT / "advanced-scenarios")


def _cells(row: str) -> list[str]:
    """The cells of a GFM table row: split on the pipes that are not escaped."""
    assert row.startswith("| ") and row.endswith(" |"), row
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", row[1:-1])]


def _section(markdown: str, title: str) -> list[str]:
    lines = markdown.split("\n")
    start = lines.index(f"## {title}") + 2
    end = next((i for i in range(start, len(lines)) if lines[i] == ""), len(lines))
    return lines[start:end]


def test_every_row_has_one_physical_line_and_all_its_cells(report):
    rows = _section(report.to_markdown(), "Results")[2:]
    assert len(rows) == 2
    for row in rows:
        assert len(_cells(row)) == COLUMNS, row


def test_the_status_column_is_the_scenarios_own(report):
    rows = {(_cells(row)[0]): _cells(row) for row in _section(report.to_markdown(), "Results")[2:]}
    assert rows["SZZ-0006"][1:3] == ["FAIL", "ok"]
    assert rows["SZZ-0005"][1:3] == ["FAIL", "error"]
    unknown = rows["SZZ-0006"][11]
    assert unknown == r"line1 line2, x \| PASS \| ok"


def test_a_run_error_stays_one_list_item(report):
    notes = [line for line in _section(report.to_markdown(), "Scenario notes") if line.startswith("- SZZ-0005")]
    assert notes, report.to_markdown()
    for line in notes:
        assert "\n" not in line and "\r" not in line
    assert any("Traceback (most recent call last): File \"tool.py\", line 3 ValueError: bad | input" in line
               for line in notes)


def test_errors_warnings_and_information_stay_one_line_each():
    from szzbench.evaluator import _md_cell, _md_line
    assert _md_line("a\r\n  b\tc\n\nd") == "a b c d"
    assert _md_cell("a | b\nc") == r"a \| b c"


def test_the_json_keeps_the_tools_text(report):
    data = report.to_dict()
    scenario = next(item for item in data["scenarios"] if item["scenario_id"] == "SZZ-0006")
    assert sorted(scenario["unknown_predictions"]) == sorted([PIPE_REF, NEWLINE_REF])
    errored = next(item for item in data["scenarios"] if item["scenario_id"] == "SZZ-0005")
    assert errored["run_errors"] == [ERROR]
