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

A manifest also vouches only for what is still there.  In the review of
PR #103, SZZ-0006's ``repo/`` was moved aside with its manifest kept:
``generate-all-repos`` reported it as skipped, and a prediction naming the
original c1 hash and the matching repository id PASSed.  An output is stale
as well when ``repo/.git``, a commit it was generated with, the commit map,
the scenario copy or the graph map is missing or changed.  The first version of
that check passed ``--git-dir`` as given while Git ran inside the repository,
so under the CLI's roots, which are relative by default, every fresh output was
reported stale.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from szzbench import manifest
from szzbench.baselines import run_baselines
from szzbench.bulk_generator import generate_all_repositories
from szzbench.coverage import run_coverage
from szzbench.evaluator import evaluate_predictions
from szzbench.generator import generate_repository
from szzbench.gitutils import run_git
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository

ROOT = Path(__file__).resolve().parents[1]

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


# ---------------------------------------------------------------------------
# a manifest vouches only for what is still there (the review of PR #103)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pristine(tmp_path_factory) -> Path:
    """The scratch layout of ``_layout``, generated once; a test works on a ``_copy``."""
    root = tmp_path_factory.mktemp("pristine")
    _generate_all(*_layout(root))
    return root


def _copy(pristine: Path, tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "copy"
    shutil.copytree(pristine, root, symlinks=True)
    return root / "scenarios", root / "advanced-scenarios", root / "generated"


MISSING_REPOSITORY = "SZZ-0006: the generated repository is stale: its repository is missing (no repo/.git)"


def _without_repository(pristine, tmp_path):
    """The reproduction in the review: SZZ-0006 generated, then its repo/ moved aside, its manifest kept."""
    classic, graph, generated = _copy(pristine, tmp_path)
    output = generated / "SZZ-0006/default"
    record = {"scenario_id": "SZZ-0006", "repository_id": manifest.read_manifest(output)["repository_id"],
              "inducing_commit": _commit_map(generated, "SZZ-0006")["c1"]["hash"]}
    (output / "repo").rename(tmp_path / "repo-aside")
    assert manifest.read_manifest(output) is not None
    return classic, graph, generated, record


def test_an_output_without_its_repository_is_not_scored(pristine, tmp_path):
    classic, graph, generated, record = _without_repository(pristine, tmp_path)
    report = _evaluate(classic, graph, generated, [record], tmp_path, reference_format="hash")
    assert report.scenarios == []                                  # it used to be scored: PASS
    assert any(error.startswith(MISSING_REPOSITORY) for error in report.errors)


def test_an_output_without_its_repository_does_not_drop_out_of_a_run(pristine, tmp_path):
    # the runs that go through the generated outputs looked for repo/.git and never saw it
    classic, graph, generated, _ = _without_repository(pristine, tmp_path)
    report = _evaluate(classic, graph, generated, [{"scenario_id": "SZZG-0030", "inducing_commit": "c1"}], tmp_path,
                       include_generated=True)
    assert [item.scenario_id for item in report.scenarios] == ["SZZG-0030"]
    assert any(error.startswith(MISSING_REPOSITORY) for error in report.errors)
    roots = dict(generated_root=generated, scenarios_root=classic, advanced_scenarios_root=graph)
    assert any(error.startswith(MISSING_REPOSITORY) for error in run_baselines(**roots)["errors"])
    assert any(error.startswith(MISSING_REPOSITORY) for error in run_coverage(**roots)["errors"])


def test_an_output_without_its_repository_is_regenerated(pristine, tmp_path):
    classic, graph, generated, record = _without_repository(pristine, tmp_path)
    assert _generate_all(classic, graph, generated) == {                  # it used to be skipped
        "SZZ-0006": ("generated", "its repository is missing (no repo/.git)"), "SZZG-0030": ("skipped", None)}
    report = _evaluate(classic, graph, generated, [record], tmp_path, reference_format="hash")
    assert report.errors == [] and report.scenarios[0].status == "PASS"   # the same history again


def _replaced_by_another_scenarios_repository(output, generated):
    shutil.rmtree(output / "repo")
    shutil.copytree(generated / "SZZG-0030/default/repo", output / "repo", symlinks=True)


def _reinitialized(output, generated):
    shutil.rmtree(output / "repo")
    (output / "repo").mkdir()
    run_git(output / "repo", ["init", "-q"])


def _last_commit_pruned(output, generated):
    repo = output / "repo"
    run_git(repo, ["reset", "-q", "--hard", "HEAD~1"])
    run_git(repo, ["reflog", "expire", "--expire=now", "--all"])
    run_git(repo, ["gc", "-q", "--prune=now"])


def _git_directory_emptied_inside_a_repository_with_every_commit(output, generated):
    # Git looks for a repository in the directories above a .git that is not
    # one -- and the default generated root sits inside the SZZBench checkout
    shutil.copytree(output / "repo/.git", generated.parent / ".git", symlinks=True)
    shutil.rmtree(output / "repo/.git")
    (output / "repo/.git").mkdir()


def _hash_edited(output, generated):
    path = output / "metadata/commit-map.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["c1"]["hash"] = data["c0"]["hash"]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _scenario_copy_edited(output, generated):
    _edit_message(output / "metadata/scenario.yml", 1, "Edited in the output")


@pytest.mark.parametrize("sid, damage, reason", [
    ("SZZ-0006", _replaced_by_another_scenarios_repository,
     "its repository lacks 3 of the 3 commits it was generated with (c0, c1, c2)"),
    ("SZZ-0006", _reinitialized, "its repository lacks 3 of the 3 commits it was generated with (c0, c1, c2)"),
    ("SZZ-0006", _last_commit_pruned, "its repository lacks 1 of the 3 commits it was generated with (c2)"),
    ("SZZ-0006", _git_directory_emptied_inside_a_repository_with_every_commit, "its repository cannot be read"),
    ("SZZ-0006", lambda output, _: (output / "metadata/commit-map.json").unlink(),
     "its commit map (metadata/commit-map.json) is missing or unreadable"),
    ("SZZ-0006", _hash_edited, "its commit map (metadata/commit-map.json) has changed since it was generated"),
    ("SZZ-0006", lambda output, _: (output / "metadata/scenario.yml").unlink(),
     "its copy of the scenario (metadata/scenario.yml) is missing or differs from the scenario file"),
    ("SZZ-0006", _scenario_copy_edited,
     "its copy of the scenario (metadata/scenario.yml) is missing or differs from the scenario file"),
    ("SZZG-0030", lambda output, _: (output / "metadata/scenario.graph.yml").unlink(),
     "its copy of the scenario (metadata/scenario.graph.yml) is missing or differs from the scenario file"),
    ("SZZG-0030", lambda output, _: (output / "metadata/graph-map.json").unlink(),
     "its graph map (metadata/graph-map.json) is missing"),
], ids=["another-repository", "reinitialized", "commit-pruned", "git-dir-not-a-repository", "commit-map-removed",
        "commit-map-edited", "scenario-copy-removed", "scenario-copy-edited", "graph-scenario-copy-removed",
        "graph-map-removed"])
def test_an_output_that_lost_part_of_what_its_manifest_describes_is_stale(pristine, tmp_path, sid, damage, reason):
    classic, graph, generated = _copy(pristine, tmp_path)
    output = generated / sid / "default"
    scenario = (classic / sid / "scenario.yml") if sid.startswith("SZZ-") else (graph / sid / "scenario.graph.yml")
    damage(output, generated)
    assert (manifest.staleness(output, scenario) or "").startswith(reason)
    assert _generate_all(classic, graph, generated)[sid][0] == "generated"
    assert manifest.staleness(output, scenario) is None


def test_what_an_szz_tool_may_do_in_the_repository_keeps_the_output_fresh(pristine, tmp_path):
    # a checkout, a commit of its own, a branch and a tag: every generated commit is still there
    classic, graph, generated = _copy(pristine, tmp_path)
    repo = generated / "SZZ-0006/default/repo"
    run_git(repo, ["checkout", "-q", "--detach", "HEAD~1"])
    run_git(repo, ["-c", "user.name=A tool", "-c", "user.email=tool@example.com",
                   "commit", "-q", "--allow-empty", "-m", "a commit of the tool's own"])
    run_git(repo, ["branch", "tool-branch"])
    run_git(repo, ["tag", "tool-tag"])
    assert manifest.staleness(repo.parent, classic / "SZZ-0006/scenario.yml") is None
    assert _generate_all(classic, graph, generated)["SZZ-0006"] == ("skipped", None)


def test_a_scenario_that_was_never_generated_is_named_as_such(pristine, tmp_path):
    classic, graph, generated = _copy(pristine, tmp_path)
    shutil.rmtree(generated / "SZZG-0030")
    report = _evaluate(classic, graph, generated, [{"scenario_id": "SZZG-0030", "inducing_commit": "c1"}], tmp_path)
    assert report.scenarios == []
    assert any(error.startswith("SZZG-0030: the generated repository is stale: nothing has been generated at")
               for error in report.errors)


def test_the_manifest_is_the_last_file_a_generation_writes(pristine):
    for output in sorted((pristine / "generated").glob("*/default")):
        written = (output / "metadata/manifest.json").stat().st_mtime_ns
        others = [path for path in output.rglob("*") if path.is_file() and path.name != "manifest.json"]
        assert others and all(path.stat().st_mtime_ns <= written for path in others), output


# ---------------------------------------------------------------------------
# the CLI's roots are relative to the working directory by default
# ---------------------------------------------------------------------------

def _cli(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "szzbench.cli", *args], cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, "PYTHONPATH": str(ROOT / "src")})


@pytest.mark.parametrize("roots", ["default", "relative"])
def test_the_cli_scores_fresh_outputs_under_relative_roots(pristine, tmp_path, roots):
    # Git ran inside the repository with the relative --git-dir it was given, so
    # every fresh output was stale: "its repository cannot be read"
    _, _, generated = _copy(pristine, tmp_path)
    cwd = generated.parent
    if roots == "default":                              # scenarios, advanced-scenarios, generated-input-repos
        generated.rename(cwd / "generated-input-repos")
        args = []
    else:
        args = ["--generated-root", "generated", "--scenarios-root", "scenarios",
                "--advanced-scenarios-root", "advanced-scenarios"]
    (cwd / "predictions.jsonl").write_text(json.dumps({"scenario_id": "SZZ-0006", "inducing_commit": "c1"}) + "\n",
                                           encoding="utf-8")
    evaluated = _cli(cwd, "evaluate", "--predictions", "predictions.jsonl", "--json", *args)
    assert evaluated.returncode == 0, evaluated.stderr
    report = json.loads(evaluated.stdout)
    assert report["errors"] == [] and report["summary"]["total_scenarios"] == 1
    for command in ("baselines", "coverage"):
        completed = _cli(cwd, command, "--json", *args)
        assert completed.returncode == 0, completed.stderr
        assert json.loads(completed.stdout)["scenario_count"] == 2


def test_staleness_reads_a_relative_output_path(pristine, tmp_path, monkeypatch):
    _, _, generated = _copy(pristine, tmp_path)
    monkeypatch.chdir(generated.parent)
    output, scenario = Path("generated/SZZ-0006/default"), Path("scenarios/SZZ-0006/scenario.yml")
    assert manifest.staleness(output, scenario) is None
    _last_commit_pruned(output, generated)                 # and the commit check still runs
    assert (manifest.staleness(output, scenario) or "").startswith("its repository lacks 1 of the 3 commits")


def test_the_cli_says_why_no_output_could_be_scored(pristine, tmp_path):
    # with every output stale, baselines and coverage said only "no generated repository found"
    classic, graph, generated = _copy(pristine, tmp_path)
    for sid in ("SZZ-0006", "SZZG-0030"):
        (generated / sid / "default/metadata/manifest.json").unlink()
    roots = ["--generated-root", str(generated), "--scenarios-root", str(classic), "--advanced-scenarios-root", str(graph)]
    for command in ("baselines", "coverage"):
        completed = _cli(tmp_path, command, *roots)
        assert completed.returncode == 1
        assert "[ERROR] SZZ-0006: the generated repository is stale: it has no generation manifest" in completed.stderr
        assert f"[ERROR] {command.upper()}_FAILED: no generated repository could be scored" in completed.stderr


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
    result = generated / "SZZ-0006/default/szz-unleashed/run-depth3/results/fix_and_introducers_pairs.json"
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
