"""The skeletons that new-scenario and new-graph-scenario write (issues #156 and #157).

The classic skeleton was `commits: []`, so its first `validate` stopped at
E011 and no lint ever reached its factors; the graph skeleton passed
`validate-graph --strict` and failed `--lint` five times over its own text (no
`meta.tier`, a c1 message that says `Introduce bug`, and a README history block
of `TODO` paths that GW454 compares with the operations).  Both builders wrote
`--status`, `--category` and `--factor` into `meta` and the index without
looking at `decisions/vocabulary.md`.  A fresh skeleton now passes
`--simulate --strict --lint` as it is, and an option outside the vocabulary is
refused before anything is written.
"""
from __future__ import annotations

import pytest
import yaml

from szzbench.cli import main
from szzbench.graph_scenario_builder import NewGraphScenarioError, create_new_graph_scenario
from szzbench.graph_validator import validate_graph_scenario_file
from szzbench.scenario_builder import NewScenarioError, create_new_scenario
from szzbench.validator import validate_scenario_file

# command -> (suite root, scenario file, the validate command and its options, the info the lint may give,
#             a category of the suite by code and by name)
SUITES = {
    "new-scenario": ("scenarios", "SZZ-0001/scenario.yml", ["validate", "--simulate", "--strict", "--lint"], "I413",
                     ("S3", "Intermediate noise and history noise")),
    "new-graph-scenario": ("advanced-scenarios", "SZZG-0001/scenario.graph.yml",
                           ["validate-graph", "--simulate", "--strict", "--strict-paths", "--lint"], "GI413",
                           ("G4", "Branch, merge, cherry-pick, backport, and release branches")),
}


def _findings(path):
    if path.name == "scenario.yml":
        _, result, _ = validate_scenario_file(path, simulate=True, lint=True)
    else:
        _, result = validate_graph_scenario_file(path, strict_paths=True, simulate=True, lint=True)
    return [finding.format() for finding in result.findings]


@pytest.mark.parametrize("tier", ["control", "discriminating"])
@pytest.mark.parametrize("command", SUITES)
def test_a_fresh_skeleton_passes_the_strict_lint_as_it_is(tmp_path, command, tier):
    suite, scenario_file, validate, info, (code, _) = SUITES[command]
    root = tmp_path / suite
    assert main([command, "--title", "Probe", "--category", code, "--factor", "line-modification", "--tier", tier,
                 "--root", str(root)]) == 0
    path = root / scenario_file
    findings = _findings(path)
    assert [line for line in findings if not line.startswith(f"[INFO] {info}:")] == []
    assert main([*validate, str(path)]) == 0
    meta = yaml.safe_load(path.read_text(encoding="utf-8"))["meta"]
    assert meta["tier"] == tier
    # a discriminating scenario defeats every family (W462 / GW462)
    assert meta.get("defeats") == (["blame", "shape", "position"] if tier == "discriminating" else None)


@pytest.mark.parametrize("command", SUITES)
def test_a_category_by_code_or_by_name_writes_both(tmp_path, command):
    suite, category = SUITES[command][0], SUITES[command][-1]
    root = tmp_path / suite
    for value in category:
        assert main([command, "--title", value, "--category", value, "--factor", "probe", "--tier", "control",
                     "--root", str(root)]) == 0
    entries = yaml.safe_load((root / "index.yml").read_text(encoding="utf-8"))["scenarios"]
    assert len(entries) == 2
    for entry in entries:
        meta = yaml.safe_load((tmp_path / entry["path"]).read_text(encoding="utf-8"))["meta"]
        for copy in (entry, meta):
            assert (copy["category_code"], copy["category"]) == category


@pytest.mark.parametrize(("options", "words"), [
    ({"category": "not a category"}, ["--category", "vocabulary.md section 3", "S1 (Basic semantic line changes)"]),
    ({"factors": ["write_file", "has space"]}, ["E400: Factor 'write_file'", "factor 'has space'", "section 1.1"]),
    ({"factors": ["multi_bic", "multi-bfc"]}, ["E402: Factors mix hyphen and underscore styles"]),
    ({"factors": []}, ["at least one --factor"]),
    ({"status": "retired"}, ["--status must be one of draft, active, not 'retired'"]),
    ({"tier": "middle"}, ["--tier must be one of control, discriminating, not 'middle'"]),
])
def test_an_option_outside_the_vocabulary_is_refused_and_nothing_is_written(tmp_path, options, words):
    for build, error, suite, prefix, category in (
            (create_new_scenario, NewScenarioError, "scenarios", "", "S1"),
            (create_new_graph_scenario, NewGraphScenarioError, "advanced-scenarios", "G", "G9")):
        arguments = {"title": "Probe", "category": category, "factors": ["line-modification"], "tier": "control",
                     **options}
        with pytest.raises(error) as raised:
            build(**arguments, root=tmp_path / suite)
        for word in words:                   # the graph builder cites the graph lint's codes
            assert word.replace("E40", f"{prefix}E40") in str(raised.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command", SUITES)
def test_the_cli_requires_a_tier_and_a_factor_and_offers_only_the_new_statuses(tmp_path, capsys, command):
    root = str(tmp_path / SUITES[command][0])
    base = [command, "--title", "Probe", "--category", SUITES[command][-1][0], "--root", root]
    for extra, message in ((["--factor", "line-modification"], "the following arguments are required: --tier"),
                           (["--tier", "control"], "the following arguments are required: --factor"),
                           (["--tier", "control", "--factor", "line-modification", "--status", "whatever"],
                            "argument --status: invalid choice: 'whatever'")):
        with pytest.raises(SystemExit) as raised:
            main([*base, *extra])
        assert raised.value.code == 2
        assert message in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
