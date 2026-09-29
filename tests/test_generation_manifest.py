"""A generated output says what it was made from, and stale outputs are not scored (issue #93).

Until 2026-09-29 an output counted as done as soon as ``repo/.git`` existed.
After a scenario was edited, ``generate-all-repos`` skipped its old repository
and ``evaluate`` scored the edited oracle against it, PASS with no error or
warning (the issue's reproduction with SZZ-0006); a generation that failed half
way left a ``repo/.git`` with no commits that the next run reported as Skipped;
and in one real checkout 190 outputs from an older suite were all stale, 11 of
them with a changed oracle, so the stale repository's own correct answer
FAILed.

Now a generation writes ``metadata/manifest.json`` last.  An output without one,
or whose scenario file or generator code has changed since, is stale:
``generate-all-repos`` regenerates it and says why, and ``evaluate``,
``baselines`` and ``coverage`` refuse to score it.  Prediction records carry
the repository id of the output they were made on; a different one FAILs the
scenario with ``run_status: stale``.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from szzbench import manifest  # noqa: E402
from szzbench.baselines import run_baselines  # noqa: E402
from szzbench.bulk_generator import generate_all_repositories  # noqa: E402
from szzbench.coverage import run_coverage  # noqa: E402
from szzbench.evaluator import evaluate_predictions  # noqa: E402
from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository  # noqa: E402


def _layout(tmp_path: Path) -> tuple[Path, Path, Path]:
    """SZZ-0006 and SZZG-0030 copied into a scratch layout, not yet generated."""
    classic, graph, generated = tmp_path / "scenarios", tmp_path / "advanced-scenarios", tmp_path / "generated"
    for suite, sid, name in (("scenarios", "SZZ-0006", "scenario.yml"),
                             ("advanced-scenarios", "SZZG-0030", "scenario.graph.yml")):
        target = tmp_path / suite / sid / name
        target.parent.mkdir(parents=True)
        target.write_bytes((ROOT / suite / sid / name).read_bytes())
    return classic, graph, generated


def _generate_all(classic, graph, generated):
    result = generate_all_repositories(scenarios_root=classic, advanced_scenarios_root=graph, output_root=generated)
    return {item.scenario_id: (item.status, item.stale_reason) for item in result.items}


def _edit_message(path: Path, index: int, message: str) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["commits"][index]["message"] = message
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _evaluate(classic, graph, generated, records, tmp_path, **kwargs):
    path = tmp_path / "predictions.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    return evaluate_predictions(path, generated_root=generated, scenarios_root=classic,
                                advanced_scenarios_root=graph, **kwargs)


def _commit_map(generated, sid):
    return json.loads((generated / sid / "default/metadata/commit-map.json").read_text(encoding="utf-8"))


def test_a_generation_writes_its_manifest(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    data = manifest.read_manifest(generated / "SZZ-0006/default")
    assert data["scenario_id"] == "SZZ-0006" and data["verified"] is True
    assert data["scenario_sha256"] == manifest.file_sha256(classic / "SZZ-0006/scenario.yml")
    assert data["generator"] == manifest.generator_fingerprint()
    assert data["repository_id"] == manifest.repository_id(_commit_map(generated, "SZZ-0006"))


def test_a_failed_generation_leaves_no_manifest_and_is_regenerated(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    good = (graph / "SZZG-0030/scenario.graph.yml").read_text(encoding="utf-8")
    data = yaml.safe_load(good)
    data["commits"][3]["operations"][0]["old"] = "this text is not in the file"   # c3 fails after c0-c2
    (graph / "SZZG-0030/scenario.graph.yml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    with pytest.raises(GraphGenerationError):
        generate_graph_repository(graph / "SZZG-0030/scenario.graph.yml", generated / "SZZG-0030/default")
    assert (generated / "SZZG-0030/default/repo/.git").is_dir()
    assert manifest.read_manifest(generated / "SZZG-0030/default") is None
    (graph / "SZZG-0030/scenario.graph.yml").write_text(good, encoding="utf-8")
    status, reason = _generate_all(classic, graph, generated)["SZZG-0030"]
    assert status == "generated" and "no generation manifest" in reason


def test_generate_all_skips_only_outputs_that_still_match(tmp_path, monkeypatch):
    classic, graph, generated = _layout(tmp_path)
    assert _generate_all(classic, graph, generated) == {"SZZ-0006": ("generated", None),
                                                        "SZZG-0030": ("generated", None)}
    assert _generate_all(classic, graph, generated) == {"SZZ-0006": ("skipped", None),
                                                        "SZZG-0030": ("skipped", None)}
    _edit_message(classic / "SZZ-0006/scenario.yml", 1, "Revised scenario after generation")
    rerun = _generate_all(classic, graph, generated)
    assert rerun["SZZ-0006"][0] == "generated" and "scenario file has changed" in rerun["SZZ-0006"][1]
    assert rerun["SZZG-0030"] == ("skipped", None)
    monkeypatch.setattr(manifest, "_fingerprint", "0" * 64)          # as if the generator code had changed
    changed = _generate_all(classic, graph, generated)
    assert all(status == "generated" and "generator code has changed" in reason
               for status, reason in changed.values())


def test_the_reproduction_in_issue_93_is_refused_until_regenerated(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    old_c1 = _commit_map(generated, "SZZ-0006")["c1"]["hash"]
    _edit_message(classic / "SZZ-0006/scenario.yml", 1, "Revised scenario after generation")
    records = [{"scenario_id": "SZZ-0006", "inducing_commit": old_c1}]
    stale = _evaluate(classic, graph, generated, records, tmp_path, include_generated=True)
    assert [item.scenario_id for item in stale.scenarios] == ["SZZG-0030"]        # SZZ-0006 is not scored
    assert any(error.startswith("SZZ-0006: the generated repository is stale") for error in stale.errors)
    _generate_all(classic, graph, generated)                                      # regenerates SZZ-0006
    new_c1 = _commit_map(generated, "SZZ-0006")["c1"]["hash"]
    fresh = _evaluate(classic, graph, generated, [{"scenario_id": "SZZ-0006", "inducing_commit": new_c1}], tmp_path)
    assert fresh.errors == [] and fresh.scenarios[0].status == "PASS"


def test_an_output_from_before_the_manifest_is_not_scored_anywhere(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    (generated / "SZZG-0030/default/metadata/manifest.json").unlink()
    report = _evaluate(classic, graph, generated, [{"scenario_id": "SZZG-0030", "inducing_commit": "c1"}], tmp_path)
    assert report.scenarios == [] and any("SZZG-0030: the generated repository is stale" in e for e in report.errors)
    roots = dict(generated_root=generated, scenarios_root=classic, advanced_scenarios_root=graph)
    assert any("SZZG-0030" in error and "stale" in error for error in run_baselines(**roots)["errors"])
    assert any("SZZG-0030" in error and "stale" in error for error in run_coverage(**roots)["errors"])


def test_predictions_are_matched_to_the_repository_they_were_made_on(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    current = manifest.read_manifest(generated / "SZZ-0006/default")["repository_id"]
    matching = _evaluate(classic, graph, generated,
                         [{"scenario_id": "SZZ-0006", "repository_id": current, "inducing_commit": "c1"}], tmp_path)
    assert matching.warnings == [] and matching.scenarios[0].status == "PASS"
    other = _evaluate(classic, graph, generated,
                      [{"scenario_id": "SZZ-0006", "repository_id": "0123456789abcdef", "inducing_commit": "c1"}],
                      tmp_path)
    item = other.scenarios[0]
    assert (item.status, item.run_status) == ("FAIL", "stale")
    assert "0123456789abcdef" in item.run_errors[0] and other.summary()["stale_predictions"] == 1
    legacy = _evaluate(classic, graph, generated, [{"scenario_id": "SZZ-0006", "inducing_commit": "c1"}], tmp_path)
    assert legacy.scenarios[0].status == "PASS"
    assert any("without repository_id" in warning for warning in legacy.warnings)


def test_conflicting_repository_ids_for_one_scenario_are_a_loading_error(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    report = _evaluate(classic, graph, generated, [
        {"scenario_id": "SZZ-0006", "repository_id": "aaaaaaaaaaaaaaaa", "inducing_commit": "c1"},
        {"scenario_id": "SZZ-0006", "repository_id": "bbbbbbbbbbbbbbbb", "inducing_commit": "c0"}], tmp_path)
    assert any("repository_id" in error and "differs" in error for error in report.errors)


def test_regenerating_an_unchanged_scenario_keeps_its_repository_id(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    before = manifest.read_manifest(generated / "SZZG-0030/default")["repository_id"]
    generate_graph_repository(graph / "SZZG-0030/scenario.graph.yml", generated / "SZZG-0030/default", force=True)
    assert manifest.read_manifest(generated / "SZZG-0030/default")["repository_id"] == before


def test_the_fingerprint_covers_every_module_the_generators_import():
    source = ROOT / "src/szzbench"

    def imports(module):
        tree = ast.parse((source / f"{module}.py").read_text(encoding="utf-8"))
        return {node.module.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module}

    reached, todo = set(), ["generator", "graph_generator"]
    while todo:
        module = todo.pop()
        if module not in reached:
            reached.add(module)
            todo.extend(imports(module) - reached)
    reached.discard("manifest")
    fingerprinted, excluded = set(manifest.GENERATION_MODULES), set(manifest.EXCLUDED_FROM_FINGERPRINT)
    assert not fingerprinted & excluded
    assert sorted(reached - fingerprinted - excluded) == [], "classify every module the generators import"


# ---------------------------------------------------------------------------
# the adapters write the repository id of the output they ran on
# ---------------------------------------------------------------------------

def test_the_adapters_write_the_repository_id(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    current = manifest.read_manifest(generated / "SZZ-0006/default")["repository_id"]
    # PyDriller, through a fake that finds nothing
    fake = tmp_path / "fake-pydriller/pydriller"
    fake.mkdir(parents=True)
    fake.joinpath("__init__.py").write_text(textwrap.dedent("""\
        class Git:
            def __init__(self, path):
                pass
            def get_commit(self, commit_hash):
                return type("Commit", (), {"hash": commit_hash})()
            def get_commits_last_modified_lines(self, commit):
                return {}
        """), encoding="utf-8")
    out = tmp_path / "pydriller.jsonl"
    subprocess.run([sys.executable, str(ROOT / "tools/adapters/pydriller_to_predictions.py"),
                    "--pydriller-path", str(fake.parent), "--generated-root", str(generated),
                    "--scenarios-root", str(classic), "--advanced-scenarios-root", str(graph), "--out", str(out)],
                   check=True, capture_output=True)
    records = {json.loads(line)["scenario_id"]: json.loads(line) for line in out.read_text().splitlines()}
    assert records["SZZ-0006"]["repository_id"] == current
    # SZZ-Unleashed, from a result file
    result = generated / "SZZ-0006/default/szz-unleashed/run-depth1/results/fix_and_introducers_pairs.json"
    result.parent.mkdir(parents=True)
    hashes = _commit_map(generated, "SZZ-0006")
    result.write_text(json.dumps([[hashes["c2"]["hash"], hashes["c1"]["hash"]]]), encoding="utf-8")
    out = tmp_path / "unleashed.jsonl"
    subprocess.run([sys.executable, str(ROOT / "tools/adapters/szz_unleashed_to_predictions.py"),
                    "--generated-root", str(generated), "--out", str(out)], check=True, capture_output=True)
    assert json.loads(out.read_text().splitlines()[0])["repository_id"] == current
    # and evaluate accepts what they wrote without the legacy warning
    report = evaluate_predictions(out, generated_root=generated, scenarios_root=classic, advanced_scenarios_root=graph)
    assert report.scenarios[0].status == "PASS" and report.warnings == []


def test_the_pyszz_adapter_reads_the_repository_id(tmp_path, monkeypatch):
    import importlib.util
    import types
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    if importlib.util.find_spec("git") is None:
        monkeypatch.setitem(sys.modules, "git", types.SimpleNamespace(Repo=object))
    spec = importlib.util.spec_from_file_location("pyszz_adapter_93", ROOT / "tools/adapters/pyszz_variants_to_predictions.py")
    adapter = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, adapter)
    spec.loader.exec_module(adapter)
    by_id = {s.scenario_id: s for s in adapter.collect_scenarios(generated, "default")}
    assert by_id["SZZ-0006"].repository_id == manifest.read_manifest(generated / "SZZ-0006/default")["repository_id"]


def test_the_cli_reports_regenerated_outputs(tmp_path):
    classic, graph, generated = _layout(tmp_path)
    _generate_all(classic, graph, generated)
    _edit_message(classic / "SZZ-0006/scenario.yml", 1, "Revised scenario after generation")
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", "generate-all-repos", "--out-root", str(generated),
                                "--scenarios-root", str(classic), "--advanced-scenarios-root", str(graph)],
                               capture_output=True, text=True, check=True,
                               env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert "Regenerated [classic] SZZ-0006" in completed.stdout and "scenario file has changed" in completed.stdout
    assert "Regenerated: 1" in completed.stdout
