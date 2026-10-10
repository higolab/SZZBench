"""A scenario or index file that is not UTF-8 is reported, not raised (issue #149).

``load_yaml`` handed a UTF-8 text stream to PyYAML, and a file in UTF-16 or
Latin-1 raised UnicodeDecodeError from inside it.  Nothing caught it, so
validate, validate-graph, validate-index, generate, readme and the skeleton
builders all ended in a traceback -- and one such scenario file took
validate-index down for its whole suite.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from szzbench.scenario import load_yaml

ROOT = Path(__file__).resolve().parents[1]


def _cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], capture_output=True, text=True, cwd=cwd,
                          env={**os.environ, "PYTHONPATH": str(ROOT / "src")})


def _reencode(path: Path, encoding: str, *, replace: tuple[str, str] | None = None) -> bytes:
    text = path.read_text(encoding="utf-8")
    if replace:
        text = text.replace(*replace, 1)
    raw = text.encode(encoding)
    path.write_bytes(raw)
    return raw


def _findings(completed: subprocess.CompletedProcess) -> list[tuple[str, str]]:
    assert "Traceback" not in completed.stderr, completed.stderr
    return [(f["code"], f["message"]) for f in json.loads(completed.stdout)["findings"]]


@pytest.fixture
def layout(tmp_path) -> Path:
    for suite, sid in (("scenarios", "SZZ-0005"), ("scenarios", "SZZ-0006"), ("advanced-scenarios", "SZZG-0001")):
        shutil.copytree(ROOT / suite / sid, tmp_path / suite / sid)
    index = (ROOT / "scenarios/index.yml").read_text(encoding="utf-8")
    entries = index.split("\n- id: ")
    kept = [entries[0]] + [e for e in entries[1:] if e.startswith(("SZZ-0005\n", "SZZ-0006\n"))]
    (tmp_path / "scenarios/index.yml").write_text("\n- id: ".join(kept).rstrip("\n") + "\n", encoding="utf-8")
    graph_index = (ROOT / "advanced-scenarios/index.yml").read_text(encoding="utf-8")
    head, _, rest = graph_index.partition("scenarios:\n")
    first = rest.split("\n- id: ")[0]
    (tmp_path / "advanced-scenarios/index.yml").write_text(
        head.replace("scenario_count: 146", "scenario_count: 1") + "scenarios:\n" + first + "\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    shutil.copy(ROOT / "docs/retired-ids.md", tmp_path / "docs/retired-ids.md")
    assert _cli("validate-index", cwd=tmp_path).returncode == 0
    return tmp_path


@pytest.mark.parametrize("encoding, replace, byte", [
    ("utf-16", None, 0xFF),
    ("latin-1", ("Aiko Mori", "Aiko Moré"), 0xE9),
], ids=["utf-16", "latin-1"])
def test_validate_reports_a_scenario_file_that_is_not_utf8(layout, encoding, replace, byte):
    path = layout / "scenarios/SZZ-0005/scenario.yml"
    raw = _reencode(path, encoding, replace=replace)
    completed = _cli("validate", str(path), "--json")
    assert completed.returncode == 1
    position = raw.index(bytes([byte]))
    assert _findings(completed) == [
        ("E000", f"Cannot read scenario.yml: it is not UTF-8 (byte 0x{byte:02x} at position {position}); save it as UTF-8.")]


def test_validate_graph_reports_a_scenario_file_that_is_not_utf8(layout):
    path = layout / "advanced-scenarios/SZZG-0001/scenario.graph.yml"
    _reencode(path, "utf-16")
    completed = _cli("validate-graph", str(path), "--json")
    assert completed.returncode == 1
    assert [code for code, _ in _findings(completed)] == ["E000"]


def test_validate_index_reports_an_index_that_is_not_utf8_and_checks_the_other_suite(layout):
    _reencode(layout / "scenarios/index.yml", "utf-16")
    completed = _cli("validate-index", "--json", cwd=layout)
    assert completed.returncode == 1
    findings = _findings(completed)
    assert [code for code, _ in findings] == ["IE001"]
    assert "it is not UTF-8 (byte 0xff at position 0)" in findings[0][1]


def test_validate_index_reports_one_scenario_file_and_goes_on(layout):
    _reencode(layout / "scenarios/SZZ-0005/scenario.yml", "utf-16")
    other = layout / "scenarios/SZZ-0006/scenario.yml"
    text = other.read_text(encoding="utf-8")
    assert "  title: Arithmetic sign error\n" in text
    other.write_text(text.replace("  title: Arithmetic sign error\n", "  title: Arithmetic sign errors\n", 1), encoding="utf-8")
    completed = _cli("validate-index", "--json", cwd=layout)
    codes = [code for code, _ in _findings(completed)]
    assert completed.returncode == 1 and "IE042" in codes
    assert "IE041" in codes                         # the next entry was still compared


def test_new_scenario_reports_an_index_that_is_not_utf8(layout):
    _reencode(layout / "scenarios/index.yml", "utf-16")
    completed = _cli("new-scenario", "--title", "Probe", "--category", "Basic semantic line changes",
                     "--factor", "line-modification", "--tier", "control", "--root", str(layout / "scenarios"))
    assert completed.returncode == 1 and "Traceback" not in completed.stderr
    assert completed.stderr.startswith("[ERROR] NEW_SCENARIO_FAILED: ")
    assert "it is not UTF-8 (byte 0xff at position 0)" in completed.stderr


def test_generate_and_readme_report_it_too(layout):
    path = layout / "scenarios/SZZ-0005/scenario.yml"
    _reencode(path, "utf-16")
    generate = _cli("generate", str(path), "--out", str(layout / "out"))
    assert generate.returncode == 1 and "Traceback" not in generate.stderr
    assert generate.stderr.startswith("[ERROR] GENERATION_FAILED: Scenario validation failed.")
    readme = _cli("readme", str(path.parent))
    assert readme.returncode == 1 and "Traceback" not in readme.stderr
    assert "1 unreadable" in readme.stdout


def test_utf8_with_a_bom_is_still_read(layout):
    path = layout / "scenarios/SZZ-0005/scenario.yml"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    data, result = load_yaml(path)
    assert data is not None and not result.findings
    assert _cli("validate", str(path)).returncode == 0
