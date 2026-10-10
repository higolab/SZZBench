"""The generate commands print JSON and can fail on a warning; clean guards its root (issues #169, #171).

#169: ``validate``, ``verify`` and ``evaluate`` had ``--json`` and ``--strict``;
``generate``, ``generate-graph``, ``generate-all-repos`` and ``clean`` refused
both (exit 2), and ``generate-all-repos`` dropped the verification result, so
a W700 warning (W703 since issue #275) was written to ``metadata/verify-result.json``
and never shown.

#171: ``clean --root`` scanned and emptied whatever it was given -- ``/``, the
home directory, the checkout -- without asking, and a ``manifest.json`` that
does not parse was reported as "no generation manifest".
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from szzbench import cli, manifest
from szzbench.bulk_generator import generate_all_repositories

ROOT = Path(__file__).resolve().parents[1]
#: shipped scenarios whose verification warns: basic blame misses the expected BIC
WARNED = {"generate": ("scenarios/SZZ-0078/scenario.yml", "W703"),
          "generate-graph": ("advanced-scenarios/SZZG-0016/scenario.graph.yml", "GW703")}


def _cli(*args, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *map(str, args)], cwd=cwd,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True)


def _roots(tmp_path: Path, classic: tuple[str, ...], graph: tuple[str, ...]) -> tuple[Path, Path, Path]:
    scenarios, advanced = tmp_path / "scenarios", tmp_path / "advanced-scenarios"
    advanced.mkdir()
    for sid in classic:
        shutil.copytree(ROOT / "scenarios" / sid, scenarios / sid)
    for sid in graph:
        shutil.copytree(ROOT / "advanced-scenarios" / sid, advanced / sid)
    return scenarios, advanced, tmp_path / "repos"


@pytest.mark.parametrize("command", sorted(WARNED))
def test_generate_json_holds_the_verification_and_strict_fails_on_its_warning(tmp_path, command):
    scenario, code = WARNED[command]
    out = tmp_path / "out"
    completed = _cli(command, scenario, "--out", out, "--json")
    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)             # the document, and nothing else, on stdout
    assert (document["kind"], document["status"], document["error"]) == (
        "graph" if command == "generate-graph" else "classic", "generated", None)
    assert (document["output_dir"], document["commit_count"]) == (str(out.resolve()), 3)
    assert document["verification"]["warnings"] == 1
    assert [f["code"] for f in document["verification"]["findings"] if f["severity"] == "WARNING"] == [code]

    strict = _cli(command, scenario, "--out", out, "--force", "--strict")
    assert strict.returncode == 1 and f"[WARNING] {code}: " in strict.stdout
    assert _cli(command, scenario, "--out", out, "--force").returncode == 0      # a warning alone, as before
    assert _cli(command, scenario, "--out", out, "--strict", "--no-verify").returncode == 2   # nothing to be strict about

    failed = _cli(command, scenario, "--out", out, "--json")                    # a failed generation is a document too
    assert failed.returncode == 1
    document = json.loads(failed.stdout)
    assert document["status"] == "failed" and document["error"].startswith("Output directory already exists: ")


def test_generate_all_repos_prints_keeps_and_fails_on_the_verification_warnings(tmp_path):
    scenarios, advanced, out = _roots(tmp_path, ("SZZ-0005", "SZZ-0078"), ("SZZG-0016",))
    roots = ("--scenarios-root", scenarios, "--advanced-scenarios-root", advanced, "--out-root", out)
    first = _cli("generate-all-repos", *roots)
    assert first.returncode == 0, first.stderr
    warnings = [line for line in first.stderr.splitlines() if ": [WARNING] " in line]
    assert [line.split(": [WARNING] ")[0] for line in warnings] == ["SZZ-0078", "SZZG-0016"]
    assert warnings[0].startswith("SZZ-0078: [WARNING] W703: bug B001: basic git blame reaches ")
    assert "  Warned:      2 " in first.stdout

    # every output is up to date now: the verification each generation recorded still counts
    second = _cli("generate-all-repos", *roots, "--json", "--strict")
    assert second.returncode == 1 and second.stderr == ""
    document = json.loads(second.stdout)
    assert document["summary"] == {"total": 3, "generated": 0, "skipped": 3, "overwritten": 0, "regenerated": 0,
                                   "failed": 0, "warned": 2, "orphaned": 0}
    by_id = {item["scenario_id"]: item for item in document["items"]}
    assert by_id["SZZ-0005"]["verification"]["warnings"] == 0
    assert [f["code"] for f in by_id["SZZ-0078"]["verification"]["findings"]] == ["W703"]
    assert by_id["SZZG-0016"]["output_dir"] == str(out.resolve() / "SZZG-0016" / "default")

    (out / "SZZ-0078/default/metadata/verify-result.json").unlink()
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    item = next(item for item in result.items if item.scenario_id == "SZZ-0078")
    assert (item.status, item.stale_reason, item.warned) == (
        "generated", "its verification result (metadata/verify-result.json) is missing or unreadable", True)


def test_clean_refuses_the_file_system_root_the_home_directory_and_the_working_directory(tmp_path, monkeypatch, capsys):
    def scan(self, pattern):
        raise AssertionError(f"clean scanned {self}")

    monkeypatch.setattr(Path, "rglob", scan)
    home, work = tmp_path / "home", tmp_path / "checkout" / "work"
    home.mkdir()
    work.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(work)
    for root, reason in (("/", "the file-system root"), (str(home), "the home directory"),
                         (".", "the current directory or one of its parents"),
                         ("..", "the current directory or one of its parents")):
        assert cli.main(["clean", "--root", root, "--dry-run"]) == 1, root
        captured = capsys.readouterr()
        assert f"is {reason}; clean removes every generated output below its root" in captured.err
        assert captured.out == ""


class _Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def _fake_output(path: Path) -> Path:
    """What ``clean`` takes for a generated output."""
    (path / "repo" / ".git").mkdir(parents=True)
    (path / "metadata").mkdir()
    (path / "metadata" / "commit-map.json").write_text("{}\n", encoding="utf-8")
    return path


def test_clean_asks_before_removing_outputs_outside_the_default_root(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    output = _fake_output(tmp_path / "elsewhere" / "SZZ-0005" / "default")
    refused = _cli("clean", "--root", "elsewhere", cwd=tmp_path)        # no terminal to ask on, and no --yes
    assert refused.returncode == 1 and refused.stdout == "" and output.is_dir()
    assert "1 generated output(s) found under " in refused.stderr and "pass --yes" in refused.stderr

    for answer in ("n\n", ""):                                          # a no, and the end of the input
        monkeypatch.setattr(sys, "stdin", _Terminal(answer))
        assert cli.main(["clean", "--root", "elsewhere"]) == 1
        assert "Remove these 1 generated output(s) under " in capsys.readouterr().err and output.is_dir()
    monkeypatch.setattr(sys, "stdin", _Terminal("y\n"))
    assert cli.main(["clean", "--root", "elsewhere"]) == 0 and not output.exists()

    output = _fake_output(output)
    completed = _cli("clean", "--root", "elsewhere", "--yes", "--json", cwd=tmp_path)
    assert completed.returncode == 0 and not output.exists()
    assert json.loads(completed.stdout) == {"root": str((tmp_path / "elsewhere").resolve()), "dry_run": False,
                                            "outputs": [str(output.resolve())], "summary": {"found": 1, "removed": 1}}

    default = _fake_output(tmp_path / "generated-input-repos" / "SZZ-0005" / "default")
    completed = _cli("clean", cwd=tmp_path)                              # the default root, as before: no question
    assert completed.returncode == 0 and not default.exists()


def test_a_damaged_manifest_is_reported_as_unreadable_not_as_missing(tmp_path):
    scenarios, advanced, out = _roots(tmp_path, ("SZZ-0005",), ())
    generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    output, scenario = out / "SZZ-0005" / "default", scenarios / "SZZ-0005" / "scenario.yml"
    path = output / "metadata" / "manifest.json"
    path.write_text("[1]\n", encoding="utf-8")
    assert manifest.staleness(output, scenario) == ("its manifest (metadata/manifest.json) is unreadable: "
                                                    "it holds a JSON array, not an object")
    path.unlink()
    assert manifest.staleness(output, scenario) == ("it has no generation manifest (an interrupted generation, "
                                                    "or one made before 2026-09-29)")

    generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    path.write_text("{broken\n", encoding="utf-8")                       # the issue's reproduction
    result = generate_all_repositories(scenarios_root=scenarios, advanced_scenarios_root=advanced, output_root=out)
    assert result.items[0].stale_reason == ("its manifest (metadata/manifest.json) is unreadable: Expecting "
                                            "property name enclosed in double quotes: line 1 column 2 (char 1)")
