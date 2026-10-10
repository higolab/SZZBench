"""What `szzbench readme <target>` checks (issue #188, `docs/scenario-readme.md`).

A suite root named on the command line resolved to no scenario file, so the
command reported zero scenarios and exited 0 having checked nothing; a missing
file was reported under the name of the directory above it, or under no name.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from szzbench.cli import main

REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("suite, ids", [("scenarios", ["SZZ-0005", "SZZ-0006"]),
                                        ("advanced-scenarios", ["SZZG-0001", "SZZG-0002"])])
def test_a_suite_root_is_checked_as_the_no_argument_form_checks_that_suite(tmp_path, monkeypatch, capsys, suite, ids):
    for sid in ids:
        shutil.copytree(REPO / suite / sid, tmp_path / suite / sid)
    stale = tmp_path / suite / ids[1] / "README.md"
    title, rest = stale.read_text(encoding="utf-8").split("\n", 1)
    stale.write_text(f"{title} (edited)\n{rest}", encoding="utf-8")
    (tmp_path / "empty").mkdir()
    monkeypatch.chdir(tmp_path)
    roots = {"scenarios": "empty", "advanced-scenarios": "empty", suite: suite}

    assert main(["readme", "--json", "--scenarios-root", roots["scenarios"],
                 "--advanced-scenarios-root", roots["advanced-scenarios"]]) == 1
    expected = json.loads(capsys.readouterr().out)
    assert main(["readme", "--json", suite]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report == expected
    assert report["scenario_count"] == 2 and [item["scenario_id"] for item in report["stale"]] == [ids[1]]


def test_a_directory_without_a_scenario_is_an_error_naming_it(tmp_path, capsys):
    scenario = tmp_path / "SZZ-0005"
    shutil.copytree(REPO / "scenarios" / "SZZ-0005", scenario)
    notes = tmp_path / "notes"
    (notes / "drafts").mkdir(parents=True)
    (notes / "drafts" / "README.md").write_text("# Draft\n", encoding="utf-8")

    assert main(["readme", str(scenario), str(notes)]) == 1
    out = capsys.readouterr().out
    assert f"error: {notes}: no scenario file found" in out
    assert "2 scenario(s): 1 README header(s) current, 0 stale or missing, 1 unreadable" in out


def test_a_missing_file_is_named_by_the_path_given(tmp_path, monkeypatch, capsys):
    (tmp_path / "scenarios").mkdir()
    monkeypatch.chdir(tmp_path)

    assert main(["readme", "nope", "scenarios/SZZ-9999"]) == 1
    out = capsys.readouterr().out
    assert "error: nope: Cannot read scenario file" in out
    assert "error: scenarios/SZZ-9999: Cannot read scenario file" in out
