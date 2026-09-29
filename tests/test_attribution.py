"""A scenario with several bug-fixing commits is also scored per fix (issue #92).

Commit-level scoring compares the union of the predicted BICs with the union of
the expected ones, and ignored ``fix_commit`` unless a scenario declared
``expected_szz.branch_level``.  For SZZG-0030 -- c1 writes a fault that c2
fixes while writing another one, which c3 fixes -- the swapped answer
(c2 -> c2, c3 -> c1) therefore passed exactly like the right one
(c2 -> c1, c3 -> c2), although it names a fix as its own cause.  Nine shipped
scenarios have several bug-fixing commits and no branch-level oracle.

Each of them is now scored per bug-fixing commit as well, the way a declared
``branch_level`` block is: a fix must lead to the direct BICs of the bugs it
fixes; a prediction counts for the fix its ``fix_commit`` names, one without
``fix_commit`` for every fix, and one whose ``fix_commit`` names no declared
fix for none; a fix whose predictions do not match fails the scenario.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from szzbench.baselines import run_baselines  # noqa: E402
from szzbench.evaluator import _scenario_bfc_ids, evaluate_predictions  # noqa: E402
from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402
from szzbench.graph_scenario import DIRECT_BIC_ROLES, graph_bfc_entries, graph_bic_entries  # noqa: E402

GRAPH = ROOT / "advanced-scenarios"


def _several_fixes() -> list[str]:
    ids = []
    for path in sorted(GRAPH.glob("SZZG-*/scenario.graph.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if len(set(_scenario_bfc_ids(data))) > 1 and not (data.get("expected_szz") or {}).get("branch_level"):
            ids.append(data["meta"]["id"])
    return ids


SEVERAL_FIXES = _several_fixes()


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("generated")
    for sid in SEVERAL_FIXES + ["SZZG-0049"]:
        generate_graph_repository(GRAPH / sid / "scenario.graph.yml", root / sid / "default", force=True)
    generate_repository(ROOT / "scenarios/SZZ-0006/scenario.yml", root / "SZZ-0006/default", force=True)
    return root


def _hash(generated: Path, sid: str, cid: str) -> str:
    return json.loads((generated / sid / "default/metadata/commit-map.json").read_text())[cid]["hash"]


def _evaluate(generated, tmp_path, sid, pairs, *, reference_format="auto"):
    """``pairs`` are (fix, inducing) with fix None for a prediction that names no fix."""
    predictions = [{"inducing_commit": bic} if fix is None else {"fix_commit": fix, "inducing_commit": bic}
                   for fix, bic in pairs]
    path = tmp_path / "predictions.jsonl"
    path.write_text(json.dumps({"scenario_id": sid, "predictions": predictions}) + "\n", encoding="utf-8")
    report = evaluate_predictions(path, generated_root=generated, scenarios_root=ROOT / "scenarios",
                                  advanced_scenarios_root=GRAPH, reference_format=reference_format)
    assert report.errors == []
    [item] = report.scenarios
    return report, item


def _fixes(item) -> dict[str, tuple[list[str], str]]:
    return {bfc: (entry["predicted"], entry["status"]) for bfc, entry in item.attribution["fixes"].items()}


def test_the_nine_are_the_scenarios_the_issue_names():
    assert SEVERAL_FIXES == ["SZZG-0018", "SZZG-0029", "SZZG-0030", "SZZG-0031", "SZZG-0032", "SZZG-0035",
                             "SZZG-0036", "SZZG-0056", "SZZG-0077"]


def test_the_right_attribution_passes_and_the_swapped_one_fails(generated, tmp_path):
    _, right = _evaluate(generated, tmp_path, "SZZG-0030", [("c2", "c1"), ("c3", "c2")])
    assert right.status == "PASS" and right.attribution["status"] == "PASS"
    _, swapped = _evaluate(generated, tmp_path, "SZZG-0030", [("c2", "c2"), ("c3", "c1")])
    assert (swapped.precision, swapped.recall) == (1.0, 1.0)      # the set is still right
    assert swapped.status == "FAIL" and swapped.attribution["status"] == "FAIL"
    assert _fixes(swapped) == {"c2": (["c2"], "FAIL"), "c3": (["c1"], "FAIL")}
    assert any("attribution" in note and "c2, c3" in note for note in swapped.result_notes)


def test_hash_references_are_attributed_the_same_way(generated, tmp_path):
    h = {cid: _hash(generated, "SZZG-0030", cid) for cid in ("c1", "c2", "c3")}
    _, right = _evaluate(generated, tmp_path, "SZZG-0030", [(h["c2"], h["c1"]), (h["c3"], h["c2"])],
                         reference_format="hash")
    _, swapped = _evaluate(generated, tmp_path, "SZZG-0030", [(h["c2"], h["c2"]), (h["c3"], h["c1"])],
                           reference_format="hash")
    assert (right.status, swapped.status) == ("PASS", "FAIL")


def test_a_prediction_without_fix_commit_counts_for_every_fix(generated, tmp_path):
    # the fixes of SZZG-0030 lead to different commits, so an unattributed set cannot pass
    _, unattributed = _evaluate(generated, tmp_path, "SZZG-0030", [(None, "c1"), (None, "c2")])
    assert unattributed.status == "FAIL"
    assert _fixes(unattributed) == {"c2": (["c1", "c2"], "FAIL"), "c3": (["c1", "c2"], "FAIL")}
    # both fixes of SZZG-0031 lead to c1, so it can
    _, shared = _evaluate(generated, tmp_path, "SZZG-0031", [(None, "c1")])
    assert shared.status == "PASS" and shared.attribution["status"] == "PASS"


@pytest.mark.parametrize("sid, first, second, bic", [
    ("SZZG-0029", "c2", "c3", "c1"),     # partial fix, then the complete one
    ("SZZG-0031", "c2", "c3", "c1"),     # two partial fixes
    ("SZZG-0032", "c2", "c3", "c1"),
    ("SZZG-0036", "c3", "c4", "c1"),     # a fix split across two commits
    ("SZZG-0077", "c3", "c4", "r1"),     # a rebased BIC fixed twice
])
def test_answering_from_one_fix_only_fails_the_other(generated, tmp_path, sid, first, second, bic):
    _, one = _evaluate(generated, tmp_path, sid, [(first, bic)])
    assert one.status == "FAIL" and _fixes(one)[second] == ([], "FAIL")
    _, both = _evaluate(generated, tmp_path, sid, [(first, bic), (second, bic)])
    assert both.status == "PASS"


def test_independent_bugs_with_one_cause_pass_when_each_fix_leads_to_it(generated, tmp_path):
    _, item = _evaluate(generated, tmp_path, "SZZG-0035", [("c2", "c1"), ("c3", "c1")])
    assert item.status == "PASS" and item.attribution["status"] == "PASS"


def test_clone_instances_fixed_one_by_one_need_their_own_causes(generated, tmp_path):
    # SZZG-0018: c2 fixes the instance c0 wrote, c3 the one c1 copied
    _, right = _evaluate(generated, tmp_path, "SZZG-0018", [("c2", "c0"), ("c3", "c1")])
    _, swapped = _evaluate(generated, tmp_path, "SZZG-0018", [("c2", "c1"), ("c3", "c0")])
    assert (right.status, swapped.status) == ("PASS", "FAIL")


def test_a_fix_reference_that_names_no_declared_fix_counts_for_none(generated, tmp_path):
    # the right answer plus two strays still passes; the strays are named in a note
    pairs = [("c2", "c1"), ("c3", "c2"), ("c0", "c1"), ("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef", "c2")]
    report, item = _evaluate(generated, tmp_path, "SZZG-0030", pairs)
    assert item.status == "PASS"
    assert any("no declared bug-fixing commit" in note and "c0" in note for note in item.result_notes)
    assert any("SZZG-0030" in warning and "no declared bug-fixing commit" in warning for warning in report.warnings)
    # strays alone answer no fix
    _, strays = _evaluate(generated, tmp_path, "SZZG-0030", [("c0", "c1"), ("c1", "c2")])
    assert strays.status == "FAIL" and _fixes(strays) == {"c2": ([], "FAIL"), "c3": ([], "FAIL")}


def test_a_single_fix_scenario_notes_a_stray_fix_reference_and_keeps_its_status(generated, tmp_path):
    _, item = _evaluate(generated, tmp_path, "SZZ-0006", [("c0", "c1")])
    assert item.status == "PASS" and item.attribution is None
    assert any("no declared bug-fixing commit" in note for note in item.result_notes)


def test_a_declared_branch_level_oracle_takes_precedence(generated, tmp_path):
    _, item = _evaluate(generated, tmp_path, "SZZG-0049", [(None, "c1")])
    assert item.attribution is None and item.branch_level is not None


@pytest.mark.parametrize("sid", SEVERAL_FIXES)
def test_every_scenario_with_several_fixes_is_attributed_and_its_oracle_passes(generated, tmp_path, sid):
    data = yaml.safe_load((GRAPH / sid / "scenario.graph.yml").read_text(encoding="utf-8"))
    pairs = []
    for bug in data["bugs"]:
        causes = [entry["commit"] for entry in graph_bic_entries(bug, roles=DIRECT_BIC_ROLES)]
        for fix in graph_bfc_entries(bug):
            pairs += [(fix["commit"], cause) for cause in causes]
    _, item = _evaluate(generated, tmp_path, sid, sorted(set(pairs)))
    assert item.attribution is not None, item.result_notes
    assert item.status == "PASS" and item.attribution["status"] == "PASS"


def test_the_report_counts_attribution(generated, tmp_path):
    report, _ = _evaluate(generated, tmp_path, "SZZG-0030", [("c2", "c2"), ("c3", "c1")])
    summary = report.summary()
    assert (summary["attribution_scenarios"], summary["attribution_failures"]) == (1, 1)
    assert "- Attribution failures: 1 of 1 scenario(s) with several bug-fixing commits" in report.to_markdown()


def test_blame_and_shape_answer_per_fix_and_keep_their_scenarios(generated):
    report = run_baselines(generated_root=generated, scenarios_root=ROOT / "scenarios", advanced_scenarios_root=GRAPH)
    assert report["errors"] == []
    solved = {entry["name"]: set(entry["solved"]) for entry in report["baselines"]}
    for name in ("blame-deleted-lines", "shape-last-toucher"):
        assert {"SZZG-0018", "SZZG-0030"} <= solved[name], name
    # a rule that names every non-fix commit cannot say which fix it answers
    assert "SZZG-0018" not in solved["position-all-non-fix"]
