"""The skeleton builders add their entry to the shipped indexes without breaking them (issue #111).

`new-scenario` and `new-graph-scenario` appended a two-space-indented entry to
the end of `index.yml`.  The shipped indexes list their entries at column 0,
and `advanced-scenarios/index.yml` ends with a top-level `notes:` block, so
both files stopped loading, `scenario_count` went stale, and a second run
refused to start.  The earlier tests ran the builders on an empty root, or on
a fixture in the builders' own style; these run them on copies of the shipped
suites.  Since issue #200 both indexes have one shape, with no `scenario_count`
or `notes`, and the builders write entries of that shape.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from szzbench.graph_scenario_builder import create_new_graph_scenario
from szzbench.validator import validate_scenario_indexes

REPO = Path(__file__).resolve().parents[1]

# command -> (suite root, scenario file, --category, --factor); --category gives the name, and the entry gets the code too
SUITES = {
    "new-scenario": ("scenarios", "scenario.yml", "Basic semantic line changes", "line-modification"),
    "new-graph-scenario": ("advanced-scenarios", "scenario.graph.yml", "Evaluation policy variants", "evaluation-variant"),
}
CODES = {"Basic semantic line changes": "S1", "Evaluation policy variants": "G9"}


@pytest.fixture
def work(tmp_path):
    """A directory holding copies of both shipped suites, as a checkout does."""
    for suite in ("scenarios", "advanced-scenarios"):
        shutil.copytree(REPO / suite, tmp_path / suite)
    return tmp_path


def _szzbench(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, text=True, capture_output=True)


def _new(cwd: Path, command: str, title: str = "Probe", *root: str) -> subprocess.CompletedProcess:
    _, _, category, factor = SUITES[command]
    return _szzbench(cwd, command, "--title", title, "--category", category, "--factor", factor, "--tier", "control",
                     *root)


def _entry_block(lines: list[str], scenario_id: str) -> tuple[int, int]:
    """The [start, end) lines of ``scenario_id``'s entry in a column-0 list."""
    start = lines.index(f"- id: {scenario_id}\n")
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith(" ")), len(lines))
    return start, end


def _ids(index: Path) -> list[str]:
    return [entry["id"] for entry in yaml.safe_load(index.read_text(encoding="utf-8"))["scenarios"]]


def _after(ids: list[str], step: int = 1) -> str:
    """The id ``step`` numbers after the highest of ``ids``."""
    prefix, number = max(ids).split("-")
    return f"{prefix}-{int(number) + step:04d}"


def _findings(work: Path) -> list[str]:
    result = validate_scenario_indexes(work / "scenarios", work / "advanced-scenarios")
    return [f"{finding.code}: {finding.message}" for finding in result.findings]


@pytest.mark.parametrize("roots", ["default", "relative"])
@pytest.mark.parametrize("command", SUITES)
def test_the_entry_ends_the_list_and_no_other_line_changes(work, command, roots):
    suite, scenario_file, category, factor = SUITES[command]
    index = work / suite / "index.yml"
    before = index.read_text(encoding="utf-8")
    old = yaml.safe_load(before)
    new_id = _after(_ids(index))

    if roots == "default":
        cwd, root = work, ()
    else:                                   # a relative --root, from another directory
        cwd, root = work / "elsewhere", ("--root", f"../{suite}")
        cwd.mkdir()
    completed = _new(cwd, command, "Probe", *root)
    assert completed.returncode == 0, completed.stderr
    assert "Updated" in completed.stdout

    after = index.read_text(encoding="utf-8")
    lines = after.splitlines(keepends=True)
    start, end = _entry_block(lines, new_id)
    # The entry follows the last old entry, at the end of the file, and every other line is as it was.
    assert end == len(lines)
    assert lines[:start] + lines[end:] == before.splitlines(keepends=True)

    # the keys of both indexes, in their order (issue #200)
    entry = {"id": new_id, "title": "Probe", "slug": "probe", "category_code": CODES[category], "category": category,
             "factors": [factor], "difficulty": "medium", "status": "draft", "path": f"{suite}/{new_id}/{scenario_file}",
             "readme": f"{suite}/{new_id}/README.md"}
    assert lines[start:end] == yaml.safe_dump([entry], sort_keys=False).splitlines(keepends=True)

    new = yaml.safe_load(after)
    assert new == {"scenarios": old["scenarios"] + [entry]}
    assert _findings(work) == []


def test_both_commands_run_twice_and_validate_index_stays_clean(work):
    """The reproduction in issue #111, with a second run of each command."""
    for command, (suite, *_) in SUITES.items():
        index = work / suite / "index.yml"
        old = _ids(index)
        for title in ("First probe", "Second probe"):
            completed = _new(work, command, title)
            assert completed.returncode == 0, completed.stderr
        assert _ids(index) == old + [_after(old), _after(old, 2)]
    completed = _szzbench(work, "validate-index")
    assert completed.returncode == 0, completed.stdout
    assert "Summary: 0 error(s), 0 warning(s), 0 info item(s)" in completed.stdout


@pytest.mark.parametrize("command", SUITES)
def test_crlf_line_ends_are_kept(work, tmp_path, command):
    """An index with CRLF line ends gets the same edit, in CRLF, and no line of it turns into LF."""
    suite = SUITES[command][0]
    lf = tmp_path / "lf"
    lf.mkdir()
    shutil.copytree(work / suite, lf / suite)
    index = work / suite / "index.yml"
    index.write_bytes(index.read_bytes().replace(b"\n", b"\r\n"))
    for cwd in (work, lf):
        completed = _new(cwd, command)
        assert completed.returncode == 0, completed.stderr
    assert index.read_bytes() == (lf / suite / "index.yml").read_bytes().replace(b"\n", b"\r\n")
    assert _findings(work) == []


@pytest.mark.parametrize("command", SUITES)
def test_an_index_that_cannot_be_extended_in_place_is_left_alone(tmp_path, command):
    """A flow-style list has no line to insert after.  The builder writes nothing and fails."""
    suite, scenario_file, _, _ = SUITES[command]
    prefix = "SZZG" if suite == "advanced-scenarios" else "SZZ"
    root = tmp_path / suite
    root.mkdir()
    index = root / "index.yml"
    index.write_text(f"scenarios: [{{id: {prefix}-0001, title: One, path: {suite}/{prefix}-0001/{scenario_file}}}]\n",
                     encoding="utf-8")
    before = index.read_bytes()
    completed = _new(tmp_path, command)
    assert completed.returncode == 1
    assert "FAILED" in completed.stderr and "nothing was written" in completed.stderr.lower()
    assert "Updated" not in completed.stdout
    assert index.read_bytes() == before
    assert sorted(path.name for path in root.iterdir()) == ["index.yml"]


def test_an_empty_list_between_other_keys_takes_the_entry_and_the_other_keys_stay(tmp_path):
    """An index of the former graph shape: its keys besides `scenarios` stay as they are, a
    `scenario_count` included, which nothing raises any more (validate-index reports it, IW004)."""
    root = tmp_path / "advanced-scenarios"
    root.mkdir()
    (root / "index.yml").write_text(
        "schema_version: graph-index-0.1-draft\nscenario_count: 0\nscenarios: []\nnotes:\n- Keep this note.\n",
        encoding="utf-8")
    create_new_graph_scenario(title="Probe", category="G4", factors=["branch-merge"], tier="control", root=root)
    assert (root / "index.yml").read_text(encoding="utf-8") == (
        "schema_version: graph-index-0.1-draft\nscenario_count: 0\nscenarios:\n"
        "- id: SZZG-0001\n  title: Probe\n  slug: probe\n  category_code: G4\n"
        "  category: Branch, merge, cherry-pick, backport, and release branches\n"
        "  factors:\n  - branch-merge\n  difficulty: medium\n  status: draft\n"
        "  path: advanced-scenarios/SZZG-0001/scenario.graph.yml\n"
        "  readme: advanced-scenarios/SZZG-0001/README.md\n"
        "notes:\n- Keep this note.\n")
