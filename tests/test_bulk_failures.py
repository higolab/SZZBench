"""generate-all-repos goes on after a scenario fails in any way (issue #162).

The loop caught only GenerationError and GraphGenerationError.  Any other
exception -- here the AttributeError the classic validator raises for a
non-string ``write_file.content`` (#151) -- stopped the run with a traceback:
the scenarios after it were never generated, the ones before it were not
listed, and no summary was printed.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import szzbench.bulk_generator as bulk
from szzbench.bulk_generator import generate_all_repositories

ROOT = Path(__file__).resolve().parents[1]


def _roots(tmp_path: Path) -> tuple[Path, Path, Path]:
    scenarios, advanced = tmp_path / "scenarios", tmp_path / "advanced-scenarios"
    for sid in ("SZZ-0005", "SZZ-0006", "SZZ-0012"):
        shutil.copytree(ROOT / "scenarios" / sid, scenarios / sid)
    shutil.copytree(ROOT / "advanced-scenarios/SZZG-0001", advanced / "SZZG-0001")
    return scenarios, advanced, tmp_path / "repos"


def _break(scenarios: Path, sid: str = "SZZ-0006") -> None:
    path = scenarios / sid / "scenario.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["commits"][0]["operations"][0]["content"] = 12345
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_a_crash_in_one_scenario_fails_that_scenario_only(tmp_path):
    scenarios, advanced, out = _roots(tmp_path)
    _break(scenarios)
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    by_id = {item.scenario_id: item for item in result.items}
    assert [by_id[sid].status for sid in ("SZZ-0005", "SZZ-0006", "SZZ-0012", "SZZG-0001")] == \
        ["generated", "failed", "generated", "generated"]
    failed = by_id["SZZ-0006"]
    assert failed.error.startswith("AttributeError: ")
    assert "Traceback (most recent call last)" in failed.traceback
    assert result.failed_count == 1 and result.generated_count == 3


def test_the_cli_lists_every_scenario_prints_the_summary_and_exits_1(tmp_path):
    scenarios, advanced, out = _roots(tmp_path)
    _break(scenarios)
    completed = subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "generate-all-repos", "--scenarios-root", str(scenarios),
         "--advanced-scenarios-root", str(advanced), "--out-root", str(out)],
        capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert completed.returncode == 1
    assert "Generated [classic] SZZ-0005" in completed.stdout and "Generated [classic] SZZ-0012" in completed.stdout
    assert "Generated [graph] SZZG-0001" in completed.stdout
    assert "Summary:" in completed.stdout and "  Failed:      1" in completed.stdout
    failed_line = next(line for line in completed.stderr.splitlines() if line.startswith("Failed [classic] SZZ-0006"))
    assert "AttributeError: " in failed_line
    assert "  Traceback (most recent call last):" in completed.stderr       # where it came from, indented under it


def test_a_crash_after_the_output_was_begun_marks_it_as_failed(tmp_path, monkeypatch):
    """An exception the generator does not wrap leaves generation-error.json, as its own errors do."""
    scenarios, advanced, out = _roots(tmp_path)

    def crash_after_start(scenario_path, output_dir, *, force=False, verify=True):
        (output_dir / "repo").mkdir(parents=True)
        (output_dir / "metadata").mkdir()
        raise TypeError("expected str, bytes or os.PathLike object, not NoneType")

    monkeypatch.setattr(bulk, "generate_repository", crash_after_start)
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    assert {item.status for item in result.items if item.kind == "classic"} == {"failed"}
    error = json.loads((out / "SZZ-0005/default/metadata/generation-error.json").read_text(encoding="utf-8"))
    assert error["error"] == "TypeError: expected str, bytes or os.PathLike object, not NoneType"
    assert next(item for item in result.items if item.kind == "graph").status == "generated"


def test_a_complete_output_is_not_marked_when_the_crash_comes_before_it_is_replaced(tmp_path, monkeypatch):
    scenarios, advanced, out = _roots(tmp_path)
    generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    monkeypatch.setattr(bulk, "generate_repository", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("early")))
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out,
                                       overwrite=True)
    assert {item.error for item in result.items if item.kind == "classic"} == {"ValueError: early"}
    assert not (out / "SZZ-0005/default/metadata/generation-error.json").exists()
    assert (out / "SZZ-0005/default/metadata/manifest.json").is_file()


def test_a_staleness_check_that_raises_fails_that_scenario_only(tmp_path, monkeypatch):
    """The staleness check reads the scenario file, and was outside the boundary (PR #213 review)."""
    scenarios, advanced, out = _roots(tmp_path)
    generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    shutil.rmtree(out / "SZZ-0012")
    real_staleness = bulk.staleness

    def unreadable_for_one(output_dir, scenario_path, **kwargs):
        if scenario_path.parent.name == "SZZ-0006":
            raise PermissionError(13, "Permission denied", str(scenario_path))
        return real_staleness(output_dir, scenario_path, **kwargs)

    monkeypatch.setattr(bulk, "staleness", unreadable_for_one)
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    by_id = {item.scenario_id: item for item in result.items}
    assert [by_id[sid].status for sid in ("SZZ-0005", "SZZ-0006", "SZZ-0012", "SZZG-0001")] == \
        ["skipped", "failed", "generated", "skipped"]
    assert by_id["SZZ-0006"].error.startswith("PermissionError: ")
    assert "Traceback (most recent call last)" in by_id["SZZ-0006"].traceback
    assert (out / "SZZ-0006/default/metadata/manifest.json").is_file()       # the complete output is left alone
    assert not (out / "SZZ-0006/default/metadata/generation-error.json").exists()


@pytest.mark.skipif(os.name == "nt" or os.geteuid() == 0, reason="needs file permissions that bind the user (root reads anyway)")
def test_an_unreadable_scenario_file_with_an_existing_output_does_not_stop_the_cli(tmp_path):
    """The review's reproduction: chmod 0 on a scenario whose output exists, and a later output removed."""
    scenarios, advanced, out = _roots(tmp_path)
    generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    shutil.rmtree(out / "SZZ-0012")
    unreadable = scenarios / "SZZ-0006/scenario.yml"
    unreadable.chmod(0)
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "szzbench.cli", "generate-all-repos", "--scenarios-root", str(scenarios),
             "--advanced-scenarios-root", str(advanced), "--out-root", str(out)],
            capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    finally:
        unreadable.chmod(0o644)
    assert completed.returncode == 1
    assert "Generated [classic] SZZ-0012" in completed.stdout and "  Failed:      1" in completed.stdout
    assert any(line.startswith("Failed [classic] SZZ-0006") and "PermissionError: " in line
               for line in completed.stderr.splitlines())


@pytest.mark.parametrize("probe", ["is_dir", "exists"])
def test_a_metadata_probe_that_raises_does_not_stop_the_run(tmp_path, monkeypatch, probe):
    """Recording the failure must not raise a second exception (PR #213 review).

    Before Python 3.14, ``Path.exists`` and ``Path.is_dir`` raise PermissionError for
    a ``metadata/`` that cannot be searched (``chmod 0``); 3.14 returns False.  The
    probe is made to raise here, so that the test runs on every Python and as root.
    """
    scenarios, advanced, out = _roots(tmp_path)
    generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    shutil.rmtree(out / "SZZ-0012")
    metadata = out / "SZZ-0006/default/metadata"
    real_generate = bulk.generate_repository

    def crash_for_one(scenario_path, output_dir, **kwargs):
        if scenario_path.parent.name == "SZZ-0006":
            raise PermissionError(13, "Permission denied", str(metadata / "manifest.json"))
        return real_generate(scenario_path, output_dir, **kwargs)

    target = metadata if probe == "is_dir" else metadata / "manifest.json"
    real_probe = getattr(Path, probe)

    def unsearchable(self, *args, **kwargs):
        if self == target:
            raise PermissionError(13, "Permission denied", str(self))
        return real_probe(self, *args, **kwargs)

    monkeypatch.setattr(bulk, "generate_repository", crash_for_one)
    monkeypatch.setattr(Path, probe, unsearchable)
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out,
                                       overwrite=True)
    by_id = {item.scenario_id: item for item in result.items}
    assert [by_id[sid].status for sid in ("SZZ-0005", "SZZ-0006", "SZZ-0012", "SZZG-0001")] == \
        ["generated", "failed", "generated", "generated"]
    assert by_id["SZZ-0006"].error.startswith("PermissionError: ")


def test_an_output_directory_that_cannot_be_inspected_does_not_stop_the_orphan_scan(tmp_path, monkeypatch):
    scenarios, advanced, out = _roots(tmp_path)
    (out / "SZZ-9999/default").mkdir(parents=True)          # a leftover of a scenario that no longer exists
    (out / "SZZ-9998/default").mkdir(parents=True)
    unsearchable = out / "SZZ-9999/default"
    real_is_dir = Path.is_dir

    def is_dir(self, *args, **kwargs):
        if self == unsearchable:
            raise PermissionError(13, "Permission denied", str(self))
        return real_is_dir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "is_dir", is_dir)
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    assert result.failed_count == 0 and result.generated_count == 4
    assert [orphan.name for orphan in result.orphans] == ["SZZ-9998"]


def test_keyboard_interrupt_still_stops_the_run(tmp_path, monkeypatch):
    scenarios, advanced, out = _roots(tmp_path)

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(bulk, "generate_repository", interrupted)
    with pytest.raises(KeyboardInterrupt):
        generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
