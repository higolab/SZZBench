"""``--force`` replaces a generated output and nothing else (issue #165).

``generate --force`` used to ``shutil.rmtree`` whatever ``--out`` named: a
directory of unrelated files (exit 0), the directory holding the scenario
being generated (which then failed for want of the scenario), the current
directory (a crash after emptying it), or a file (``NotADirectoryError``,
a traceback).  Each of these is now refused before anything is removed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from szzbench.bulk_generator import generate_all_repositories
from szzbench.cleaner import replaceable_output_problem
from szzbench.generator import GenerationError, generate_repository
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "scenarios/SZZ-0005/scenario.yml"
GRAPH = ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml"


def _tree(path: Path) -> list[str]:
    return sorted(p.relative_to(path).as_posix() for p in path.rglob("*"))


@pytest.mark.parametrize("generate, error, scenario", [
    (generate_repository, GenerationError, CLASSIC),
    (generate_graph_repository, GraphGenerationError, GRAPH),
], ids=["classic", "graph"])
def test_an_out_with_unrelated_files_is_refused_and_kept(tmp_path, generate, error, scenario):
    out = tmp_path / "precious"
    (out / "docs").mkdir(parents=True)
    (out / "docs/notes.txt").write_text("notes\n")
    (out / "README.md").write_text("readme\n")
    before = _tree(out)
    with pytest.raises(error, match=r"is not a generated output \(it holds README.md, docs\)"):
        generate(scenario, out, force=True)
    assert _tree(out) == before


def test_the_directory_holding_the_scenario_is_refused_and_kept(tmp_path):
    shutil.copytree(CLASSIC.parent, tmp_path / "SZZ-0005")
    scenario = tmp_path / "SZZ-0005/scenario.yml"
    with pytest.raises(GenerationError, match="contains the scenario file being generated"):
        generate_repository(scenario, scenario.parent, force=True)
    assert _tree(tmp_path / "SZZ-0005") == ["README.md", "scenario.yml"]


def test_a_generated_output_holding_its_scenario_copy_is_not_regenerated_from_it(tmp_path):
    out = tmp_path / "out"
    generate_repository(CLASSIC, out, force=True)
    copy = out / "metadata/scenario.yml"
    with pytest.raises(GenerationError, match="contains the scenario file being generated"):
        generate_repository(copy, out, force=True)
    assert copy.is_file()


def test_the_current_directory_and_its_parents_are_refused(tmp_path, monkeypatch):
    cwd = tmp_path / "work" / "here"
    (cwd / "keep").mkdir(parents=True)
    (cwd / "keep/file.txt").write_text("x\n")
    monkeypatch.chdir(cwd)
    for out in (Path("."), cwd.parent):
        with pytest.raises(GenerationError, match="is the current directory or one of its parents"):
            generate_repository(CLASSIC, out, force=True)
    assert _tree(cwd) == ["keep", "keep/file.txt"]


@pytest.mark.parametrize("force", [False, True])
def test_a_file_is_refused_without_a_traceback(tmp_path, force):
    out = tmp_path / "a-file"
    out.write_text("data\n")
    with pytest.raises(GenerationError, match="exists and is not a directory"):
        generate_repository(CLASSIC, out, force=force)
    assert out.read_text() == "data\n"


def test_the_cli_reports_a_refusal_as_generation_failed(tmp_path):
    out = tmp_path / "a-file"
    out.write_text("data\n")
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", "generate", str(CLASSIC), "--out", str(out), "--force"],
                               capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert completed.returncode == 1
    assert "Traceback" not in completed.stderr
    assert completed.stderr.startswith("[ERROR] GENERATION_FAILED: --out ")
    assert "exists and is not a directory." in completed.stderr


def test_a_generated_output_is_still_replaced(tmp_path):
    out = tmp_path / "out"
    first, _ = generate_repository(CLASSIC, out, force=True)
    marker = out / "metadata/marker.txt"
    marker.write_text("old\n")
    (out / "szz-unleashed").mkdir()                      # what an adapter run leaves inside an output
    second, _ = generate_repository(CLASSIC, out, force=True)
    assert second == first and not marker.exists() and not (out / "szz-unleashed").exists()


@pytest.mark.parametrize("entries", [[], ["repo"], ["repo", "metadata"]], ids=["empty", "repo", "repo+metadata"])
def test_an_empty_or_interrupted_output_may_be_replaced(tmp_path, entries):
    out = tmp_path / "out"
    out.mkdir()
    for name in entries:
        (out / name).mkdir()
    assert replaceable_output_problem(out, CLASSIC) is None
    generate_repository(CLASSIC, out, force=True)
    assert (out / "metadata/manifest.json").is_file()


def test_generate_all_repos_reports_a_refused_output_and_goes_on(tmp_path):
    scenarios, advanced, out_root = tmp_path / "scenarios", tmp_path / "advanced-scenarios", tmp_path / "out"
    for sid in ("SZZ-0005", "SZZ-0006"):
        shutil.copytree(ROOT / "scenarios" / sid, scenarios / sid)
    advanced.mkdir()
    blocked = out_root / "SZZ-0005/default"
    blocked.mkdir(parents=True)
    (blocked / "notes.txt").write_text("mine\n")
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out_root,
                                       overwrite=True, verify=True)
    by_id = {item.scenario_id: item for item in result.items}
    assert by_id["SZZ-0005"].status == "failed" and "is not a generated output" in by_id["SZZ-0005"].error
    assert by_id["SZZ-0006"].status == "generated"
    assert (blocked / "notes.txt").read_text() == "mine\n"
