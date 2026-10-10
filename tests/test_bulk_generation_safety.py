"""What generate-all-repos generates, and where (issue #168).

Three gaps.  A directory name present under both scenario roots was
generated twice into one ``<out-root>/<id>/default``, the graph scenario
overwriting the classic output as a routine "Regenerated".  Scenario files
were found recursively, so with ``--out-root`` inside a scenario root the
next run took the copy of the scenario that every output keeps in
``metadata/`` for a scenario named ``metadata``; such an ``--out-root`` is
refused now, and only ``<root>/*/`` is read.  And a stale output was removed
before its regeneration began, so a regeneration that failed left a partial
output where a complete one had been.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import szzbench.graph_validator as graph_validator
import szzbench.validator as validator
from szzbench.bulk_generator import generate_all_repositories

ROOT = Path(__file__).resolve().parents[1]
MESSAGE = 'message: "Initial required field annotation"'        # SZZ-0005's c0
#: the issue's edit: a message ending with a newline, which verification rejects (E602)
FAILING = "message: |\n      Initial required field annotation"


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    scenarios, advanced = tmp_path / "scenarios", tmp_path / "advanced-scenarios"
    shutil.copytree(ROOT / "scenarios/SZZ-0005", scenarios / "SZZ-0005")
    advanced.mkdir()
    return scenarios, advanced, tmp_path / "repos"


def _run(scenarios: Path, advanced: Path, out: Path):
    return generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)


def _cli(cwd: Path, out_root: str) -> subprocess.CompletedProcess:
    """``generate-all-repos`` with roots relative to ``cwd``."""
    return subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "generate-all-repos", "--scenarios-root", "scenarios",
         "--advanced-scenarios-root", "advanced-scenarios", "--out-root", out_root],
        cwd=cwd, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})


def _replace(scenarios: Path, old: str, new: str) -> None:
    path = scenarios / "SZZ-0005/scenario.yml"
    path.write_text(path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")


def _failing_regeneration(monkeypatch, scenarios: Path) -> None:
    """The issue's edit.  Validation has refused it since #163 (E012), so the rule is switched off, as
    tests/test_commit_message_shape.py does, and the regeneration fails at its verification."""
    for module in (validator, graph_validator):
        monkeypatch.setattr(module, "commit_message_problem", lambda message: None, raising=False)
    _replace(scenarios, MESSAGE, FAILING)


@pytest.mark.parametrize("classic_name, graph_name", [("DUP-0001", "DUP-0001"), ("DUP-0001", "dup-0001")])
def test_an_id_in_both_suites_stops_the_run_before_anything_is_written(tmp_path, classic_name, graph_name):
    """Letter case does not count: a case-insensitive file system has one directory for both outputs."""
    shutil.copytree(ROOT / "scenarios/SZZ-0005", tmp_path / "scenarios" / classic_name)
    shutil.copytree(ROOT / "advanced-scenarios/SZZG-0107", tmp_path / "advanced-scenarios" / graph_name)
    completed = _cli(tmp_path, "repos")
    assert completed.returncode == 1 and completed.stdout == ""
    assert completed.stderr.startswith("[ERROR] GENERATE_ALL_REPOS_FAILED: Two scenarios share an id")
    root = tmp_path.resolve()
    assert str(root / "scenarios" / classic_name / "scenario.yml") in completed.stderr
    assert str(root / "advanced-scenarios" / graph_name / "scenario.graph.yml") in completed.stderr
    assert not (tmp_path / "repos").exists()


@pytest.mark.parametrize("out_root, option, root", [("scenarios", "--scenarios-root", "scenarios"),
                                                    ("advanced-scenarios/repos", "--advanced-scenarios-root",
                                                     "advanced-scenarios")])
def test_an_out_root_inside_a_scenario_root_is_refused(tmp_path, out_root, option, root):
    scenarios, _, _ = _roots(tmp_path)
    completed = _cli(tmp_path, out_root)
    assert completed.returncode == 1 and completed.stdout == ""
    base = tmp_path.resolve()
    where = "the same directory as" if out_root == root else "inside"
    assert completed.stderr.startswith(f"[ERROR] GENERATE_ALL_REPOS_FAILED: --out-root {base / out_root} is {where} "
                                       f"{option} {base / root}: the outputs would be written among the scenarios.")
    assert not (tmp_path / "advanced-scenarios/repos").exists() and not (scenarios / "SZZ-0005/default").exists()


def test_output_copies_below_a_scenario_root_are_not_taken_for_scenarios(tmp_path):
    """Only ``<root>/*/scenario.yml`` is a scenario, as the README says: not the copy an output keeps in
    ``metadata/``, such as one ``generate --out scenarios/SZZ-0005/default`` left below the root."""
    scenarios, advanced, out = _roots(tmp_path)
    (scenarios / "SZZ-0005/default/metadata").mkdir(parents=True)
    shutil.copy2(scenarios / "SZZ-0005/scenario.yml", scenarios / "SZZ-0005/default/metadata/scenario.yml")
    result = _run(scenarios, advanced, out)
    assert [(item.scenario_id, item.status) for item in result.items] == [("SZZ-0005", "generated")]
    assert sorted(child.name for child in out.iterdir()) == ["SZZ-0005"]


def test_a_failed_regeneration_leaves_the_complete_output_in_place(tmp_path, monkeypatch):
    scenarios, advanced, out = _roots(tmp_path)
    _run(scenarios, advanced, out)
    output, attempt = out.resolve() / "SZZ-0005/default", out.resolve() / "SZZ-0005/default.tmp"
    before = {path.name: path.read_bytes() for path in (output / "metadata").iterdir()}
    assert "manifest.json" in before

    _failing_regeneration(monkeypatch, scenarios)
    [item] = _run(scenarios, advanced, out).items
    assert (item.status, item.stale_reason) == ("failed", "its scenario file has changed since it was generated")
    assert {path.name: path.read_bytes() for path in (output / "metadata").iterdir()} == before
    assert (output / "repo/.git").is_dir()
    assert item.error == ("Generated repository failed verification; the previous output was left in place, "
                          f"and the files of this attempt are in {attempt}")
    error = json.loads((attempt / "metadata/generation-error.json").read_text(encoding="utf-8"))
    assert error["error"] == "Generated repository failed verification."
    assert (attempt / "metadata/generation.log").is_file() and not (attempt / "metadata/manifest.json").exists()


def test_the_next_generation_replaces_the_failed_attempt_and_the_output(tmp_path, monkeypatch):
    scenarios, advanced, out = _roots(tmp_path)
    _run(scenarios, advanced, out)
    _failing_regeneration(monkeypatch, scenarios)
    _run(scenarios, advanced, out)
    output, attempt = out.resolve() / "SZZ-0005/default", out.resolve() / "SZZ-0005/default.tmp"
    assert attempt.is_dir()

    _replace(scenarios, FAILING, 'message: "Annotate the required field"')
    [item] = _run(scenarios, advanced, out).items
    assert (item.status, item.stale_reason) == ("generated", "its scenario file has changed since it was generated")
    assert not attempt.exists()
    assert sorted(child.name for child in output.parent.iterdir()) == ["default"]
    assert _run(scenarios, advanced, out).items[0].status == "skipped"       # complete, with its manifest


def test_a_directory_in_the_attempts_place_that_is_not_one_is_kept(tmp_path):
    """``default.tmp`` is replaced under the rule ``generate --force`` follows (issue #165)."""
    scenarios, advanced, out = _roots(tmp_path)
    attempt = out / "SZZ-0005/default.tmp"
    attempt.mkdir(parents=True)
    (attempt / "notes.txt").write_text("mine\n", encoding="utf-8")
    [item] = _run(scenarios, advanced, out).items
    assert item.status == "failed" and "is not a generated output (it holds notes.txt)" in item.error
    assert (attempt / "notes.txt").read_text(encoding="utf-8") == "mine\n"
    assert not (out / "SZZ-0005/default").exists()
