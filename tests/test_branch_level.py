"""The branch-level oracle (`expected_szz.branch_level`, issue #22, decided 2026-09-22).

A graph scenario may fix one fault on several branches and require a tool
started from each fix to report that branch's BICs.  These tests pin the
scoring rule of `docs/evaluation-policies.md` section 1.5 on a synthetic
scenario, the validator's checks of the declaration, and the scenario built
for the rule, SZZG-0143: behaviour at every commit, the blame each fix leads
to, and a real evaluation with per-fix predictions.
"""
from __future__ import annotations

import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from support import export_tree, git, needs_jdk
from szzbench.evaluator import Prediction, evaluate_prediction_map, evaluate_scenario
from szzbench.graph_generator import generate_graph_repository
from szzbench.graph_validator import validate_graph_static

ROOT = Path(__file__).resolve().parents[1]

JAVA = "src/main/java/example/Range.java"
COMMIT_MAP = {cid: {"hash": ch * 40} for cid, ch in (("c0", "0"), ("c1", "1"), ("r1", "a"), ("c2", "2"), ("c3", "3"), ("r2", "b"))}


def _scenario() -> dict:
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9910", "title": "Branch-level fixture", "slug": "branch-level-fixture", "category": "Branch",
                 "category_code": "G4", "factors": ["branch", "multi-bfc"], "difficulty": "advanced", "status": "active",
                 "tier": "control"},
        "repository": {"name": "branch-level-fixture", "default_branch": "main", "language": "java"},
        "graph": {},
        "commits": [
            {"id": "c0", "branch": "main", "parents": [], "message": "Initial", "role": "initial",
             "operations": [{"type": "write_file", "path": JAVA, "content": "class Range { int min = 0; }\n"}]},
            {"id": "c1", "branch": "main", "parents": ["c0"], "message": "Change", "role": "bug_introducing",
             "operations": [{"type": "replace", "path": JAVA, "old": "min = 0", "new": "min = 1"}]},
            {"id": "r1", "branch": "release", "parents": ["c1"], "message": "Cut release", "role": "release_branch_point",
             "operations": [{"type": "write_file", "path": "docs/release.md", "content": "release\n"}]},
            {"id": "c2", "branch": "main", "parents": ["c1"], "message": "Docs", "role": "intermediate",
             "operations": [{"type": "write_file", "path": "docs/main.md", "content": "main\n"}]},
            {"id": "c3", "branch": "main", "parents": ["c2"], "message": "Fix on main", "role": "bug_fixing",
             "operations": [{"type": "replace", "path": JAVA, "old": "min = 1", "new": "min = 0"}]},
            {"id": "r2", "branch": "release", "parents": ["r1"], "message": "Fix on release", "role": "bug_fixing",
             "operations": [{"type": "replace", "path": JAVA, "old": "min = 1", "new": "min = 0 /* release */"}]},
        ],
        "bugs": [{"id": "B001", "title": "Wrong minimum",
                  "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c3", "role": "complete_fix"}, {"commit": "r2", "role": "complete_fix"}],
                  "faults": [{"file": JAVA, "commit": "c1", "statement": "min = 1"}],
                  "fixes": [{"file": JAVA, "commit": "c3", "statement": "min = 0"}, {"file": JAVA, "commit": "r2", "statement": "min = 0 /* release */"}]}],
        "expected_szz": {
            "commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]},
            "branch_level": {"main": {"bfc": "c3", "required": ["c1"]}, "release": {"bfc": "r2", "required": ["c1"]}},
        },
    }


def _evaluate(predictions, tmp_path, scenario=None):
    return evaluate_scenario("SZZG-9910", scenario or _scenario(), tmp_path / "scenario.graph.yml", "advanced-scenarios",
                             COMMIT_MAP, [Prediction(scenario_id="SZZG-9910", **kwargs) for kwargs in predictions])


# --- the scoring rule --------------------------------------------------------------------

def test_each_fix_is_scored_against_its_own_branch(tmp_path):
    result = _evaluate([{"inducing_commit": "c1", "fix_commit": "c3"}, {"inducing_commit": "c1", "fix_commit": "r2"}], tmp_path)
    assert result.status == "PASS"
    assert result.branch_level["status"] == "PASS"
    assert result.branch_level["branches"]["main"] == {"bfc": "c3", "required": ["c1"], "predicted": ["c1"], "false_positives": [],
                                                       "false_negatives": [], "unknown_predictions": [], "status": "PASS"}
    assert result.branch_level["branches"]["release"]["status"] == "PASS"
    assert result.to_dict()["branch_level"]["status"] == "PASS"


def test_a_wrong_answer_from_one_fix_fails_that_branch_and_the_scenario(tmp_path):
    # from the release fix the tool reports the reformat r1 instead of c1
    result = _evaluate([{"inducing_commit": "c1", "fix_commit": "c3"}, {"inducing_commit": "r1", "fix_commit": "r2"}], tmp_path)
    assert result.branch_level["branches"]["main"]["status"] == "PASS"
    assert result.branch_level["branches"]["release"] == {"bfc": "r2", "required": ["c1"], "predicted": ["r1"], "false_positives": ["r1"],
                                                          "false_negatives": ["c1"], "unknown_predictions": [], "status": "FAIL"}
    assert result.branch_level["status"] == "FAIL" and result.status == "FAIL"


def test_silence_from_one_fix_fails_the_scenario_although_the_union_passes(tmp_path):
    """Commit-level sees {c1} and passes; the release branch saw nothing and fails."""
    result = _evaluate([{"inducing_commit": "c1", "fix_commit": "c3"}], tmp_path)
    assert result.true_positives == ["c1"] and result.false_positives == [] and result.false_negatives == []
    assert result.branch_level["branches"]["release"]["false_negatives"] == ["c1"]
    assert result.status == "FAIL"
    assert any("branch(es) release fail" in note for note in result.result_notes)


def test_a_prediction_without_fix_commit_counts_for_every_branch(tmp_path):
    result = _evaluate([{"inducing_commit": "c1"}], tmp_path)
    assert result.status == "PASS" and result.branch_level["status"] == "PASS"
    assert result.branch_level["branches"]["main"]["predicted"] == ["c1"]
    assert result.branch_level["branches"]["release"]["predicted"] == ["c1"]


def test_fix_commit_may_be_a_hash_or_prefix_and_a_stray_one_counts_for_no_branch(tmp_path):
    result = _evaluate([{"inducing_commit": "1" * 40, "fix_commit": "3333333"},      # main by prefix
                        {"inducing_commit": "c1", "fix_commit": "b" * 40},           # release by hash
                        {"inducing_commit": "c2", "fix_commit": "c2"}], tmp_path)   # not a declared BFC
    assert result.branch_level["branches"]["main"]["predicted"] == ["c1"]
    assert result.branch_level["branches"]["release"]["predicted"] == ["c1"]
    assert result.branch_level["status"] == "PASS"
    assert any("resolve to no declared branch BFC (c2)" in note for note in result.result_notes)
    # the stray prediction still reaches the commit-level oracle as a false positive
    assert result.false_positives == ["c2"] and result.status == "FAIL"


def test_a_scenario_without_branch_level_is_scored_per_fix_by_attribution(tmp_path):
    # Until issue #92 such a scenario was scored as one set, so an answer from c3 alone passed.
    # Now every scenario with several bug-fixing commits is scored per fix even without a
    # branch_level block: the fixes' oracles come from bugs[], and each needs its own answer.
    scenario = _scenario()
    del scenario["expected_szz"]["branch_level"]
    one = _evaluate([{"inducing_commit": "c1", "fix_commit": "c3"}], tmp_path, scenario)
    assert one.branch_level is None and one.status == "FAIL"
    assert one.attribution["fixes"]["r2"]["false_negatives"] == ["c1"]
    assert not any(note.startswith("branch_level") for note in one.result_notes)
    both = _evaluate([{"inducing_commit": "c1", "fix_commit": "c3"}, {"inducing_commit": "c1", "fix_commit": "r2"}],
                     tmp_path, scenario)
    assert both.status == "PASS" and both.attribution["status"] == "PASS"


def test_branch_level_is_no_longer_reported_as_an_unread_section(tmp_path):
    result = _evaluate([{"inducing_commit": "c1"}], tmp_path)
    assert not any("branch_level" in note and "not used" in note for note in result.result_notes)


# --- the declaration is validated -----------------------------------------------------------

def _codes(scenario) -> list[str]:
    return [f.code for f in validate_graph_static(scenario).findings if f.severity == "ERROR"]


def test_validator_accepts_the_declaration_and_rejects_malformed_ones():
    assert _codes(_scenario()) == []
    broken = _scenario()
    broken["expected_szz"]["branch_level"] = []
    assert _codes(broken) == ["GE127"]
    broken = _scenario()
    broken["expected_szz"]["branch_level"]["release"] = {"required": ["c1"]}
    assert _codes(broken) == ["GE127"]
    broken = _scenario()
    broken["expected_szz"]["branch_level"]["release"]["bfc"] = "r9"
    assert _codes(broken) == ["GE128"]
    broken = _scenario()
    broken["expected_szz"]["branch_level"]["main"]["required"] = ["c1", "zz"]
    assert _codes(broken) == ["GE126"]
    # a blank `required:` is None in YAML and must not become an oracle that expects nothing (PR #71 review)
    broken = _scenario()
    broken["expected_szz"]["branch_level"]["release"]["required"] = None
    assert _codes(broken) == ["GE127"]
    explicit_empty = _scenario()
    explicit_empty["expected_szz"]["branch_level"]["release"]["required"] = []
    assert _codes(explicit_empty) == []


def test_a_null_required_fails_the_branch_even_before_validation(tmp_path):
    scenario = _scenario()
    scenario["expected_szz"]["branch_level"]["release"]["required"] = None
    result = _evaluate([{"inducing_commit": "c1", "fix_commit": "c3"}], tmp_path, scenario)
    assert result.branch_level["branches"]["release"]["status"] == "FAIL"
    assert result.branch_level["branches"]["release"]["required"] is None
    assert result.status == "FAIL"
    assert any("has no list under required" in note for note in result.result_notes)


def test_an_entry_without_bfc_fails_and_takes_no_prediction_even_before_validation(tmp_path):
    """A fix_commit that resolves to nothing compared equal to the missing bfc (None == None), so
    `release` took that prediction and passed, while the note said it counted for no branch (issue #147)."""
    scenario = _scenario()
    del scenario["expected_szz"]["branch_level"]["release"]["bfc"]
    result = _evaluate([{"inducing_commit": "c1", "fix_commit": "c3"},
                        {"inducing_commit": "c1", "fix_commit": "zzzzzzzzzzzz"}], tmp_path, scenario)
    assert result.branch_level["branches"]["release"] == {
        "bfc": None, "required": ["c1"], "predicted": [], "false_positives": [], "false_negatives": [],
        "unknown_predictions": [], "status": "FAIL"}
    assert result.branch_level["branches"]["main"]["status"] == "PASS"
    assert result.status == "FAIL"
    assert "branch_level: entry 'release' has no commit id under bfc (GE127); the branch fails." in result.result_notes
    assert any("resolve to no declared branch BFC (zzzzzzzzzzzz)" in note for note in result.result_notes)


def test_an_invalid_fix_reference_in_a_predictions_file_is_an_error_not_an_unspecified_fix(tmp_path):
    """The loader used to coerce 123, [] or "" to None, which the branch-level rule reads as
    'counts for every branch' (PR #71 review)."""
    import json
    from szzbench.evaluator import load_predictions

    path = tmp_path / "predictions.jsonl"
    records = [
        {"scenario_id": "SZZG-9910", "inducing_commit": "c1", "fix_commit": 123},
        {"scenario_id": "SZZG-9910", "inducing_commit": "c1", "fix_commit": []},
        {"scenario_id": "SZZG-9910", "inducing_commit": "c1", "bug_fixing_commit": ""},
        {"scenario_id": "SZZG-9910", "inducing_commit": "c1", "fix_commit": None},      # allowed: unspecified
        {"scenario_id": "SZZG-9910", "inducing_commit": "c1"},                          # allowed: omitted
        {"scenario_id": "SZZG-9910", "inducing_commit": "c1", "fix_commit": "r2"},      # valid
    ]
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
    predictions, explicit, _, invalid, _, errors, _ = load_predictions(path)
    assert len(errors) == 3 and all("must be a non-empty string when present" in error for error in errors)
    # the records are not read, and their scenario fails as invalid (issue #138)
    assert invalid == {"SZZG-9910": errors}
    assert "fix_commit" in errors[0] and "123" in errors[0] and "bug_fixing_commit" in errors[2]
    loaded = predictions["SZZG-9910"]
    assert [p.fix_commit for p in loaded] == [None, None, "r2"]
    # the surviving records score as before: two unspecified (every branch) and one for release
    result = evaluate_scenario("SZZG-9910", _scenario(), tmp_path / "s.yml", "advanced-scenarios", COMMIT_MAP, loaded)
    assert result.status == "PASS" and result.branch_level["status"] == "PASS"


# --- SZZG-0143 ------------------------------------------------------------------------------

TICKET = "src/main/java/example/Ticket.java"
DRIVER = "public class Drive { public static void main(String[] a) { System.out.print(new example.Ticket().isValid(4000, 1000, 10)); } }"


@pytest.fixture(scope="module")
def szzg_0143(tmp_path_factory):
    out = tmp_path_factory.mktemp("szzg0143") / "SZZG-0143" / "default"
    commit_map, verify = generate_graph_repository(ROOT / "advanced-scenarios/SZZG-0143/scenario.graph.yml", out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    return {cid: entry["hash"] for cid, entry in commit_map.items()}, out


def test_szzg_0143_blame_reaches_the_bic_from_main_and_the_reformat_from_release(szzg_0143):
    hashes, out = szzg_0143
    repo = out / "repo"
    # -w does not help from r2: r1 split the line, it did not change whitespace inside a line
    for bfc, owner, with_w in (("c3", "c1", "c1"), ("r2", "r1", "r1")):
        parent = git(repo, "show", f"{hashes[bfc]}^:{TICKET}").split("\n")
        diff = git(repo, "diff", "-U0", f"{hashes[bfc]}^", hashes[bfc], "--", TICKET)
        deleted = [line[1:] for line in diff.split("\n") if line.startswith("-") and not line.startswith("---")]
        assert deleted, diff
        for line in deleted:
            no = parent.index(line) + 1
            plain = git(repo, "blame", "-l", "-L", f"{no},{no}", f"{hashes[bfc]}^", "--", TICKET).split()[0].lstrip("^")
            w = git(repo, "blame", "-w", "-l", "-L", f"{no},{no}", f"{hashes[bfc]}^", "--", TICKET).split()[0].lstrip("^")
            assert hashes[owner].startswith(plain), (bfc, line, plain[:7])
            assert hashes[with_w].startswith(w), (bfc, line, w[:7])
    # the release fix is not a cherry-pick of the main fix
    assert git(repo, "show", f"{hashes['r2']}:{TICKET}") != git(repo, "show", f"{hashes['c3']}:{TICKET}")
    assert "cherry picked" not in git(repo, "log", "-1", "--format=%B", hashes["r2"])


@needs_jdk
def test_szzg_0143_fault_is_visible_on_both_branches_until_each_fix(szzg_0143, tmp_path):
    hashes, out = szzg_0143
    expected = {"c0": "false", "c1": "true", "r1": "true", "c2": "true", "c3": "false", "r2": "false"}
    observed = {}
    for cid in expected:
        work = tmp_path / cid
        work.mkdir()
        export_tree(out / "repo", hashes[cid], work)
        (work / "Drive.java").write_text(DRIVER)
        subprocess.run(["javac", "-d", str(work / "out"), str(work / TICKET), str(work / "Drive.java")], check=True, capture_output=True)
        observed[cid] = subprocess.run(["java", "-cp", str(work / "out"), "Drive"], capture_output=True, text=True, check=True).stdout
    assert observed == expected


def test_szzg_0143_evaluates_per_fix_with_hashes(szzg_0143):
    hashes, out = szzg_0143
    generated_root = out.parent.parent
    def run(predictions):
        preds = {"SZZG-0143": [Prediction(scenario_id="SZZG-0143", **kwargs) for kwargs in predictions]}
        report = evaluate_prediction_map(preds, generated_root=generated_root, scenarios_root=ROOT / "scenarios",
                                         advanced_scenarios_root=ROOT / "advanced-scenarios")
        assert not report.errors, report.errors
        return report.scenarios[0]
    # a blame-based tool: c1 from the main fix, r1 from the release fix
    blame = run([{"inducing_commit": hashes["c1"], "fix_commit": hashes["c3"]},
                 {"inducing_commit": hashes["r1"], "fix_commit": hashes["r2"]}])
    assert blame.branch_level["branches"]["main"]["status"] == "PASS"
    assert blame.branch_level["branches"]["release"]["status"] == "FAIL"
    assert blame.status == "FAIL" and blame.known_distractor_hits == ["r1"]
    # a tool that looks past whitespace: c1 from both
    good = run([{"inducing_commit": hashes["c1"], "fix_commit": hashes["c3"]},
                {"inducing_commit": hashes["c1"], "fix_commit": hashes["r2"]}])
    assert good.status == "PASS" and good.branch_level["status"] == "PASS"
