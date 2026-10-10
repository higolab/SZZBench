"""How the evaluator reads what it is given (issues #140, #142 and #145).

- ``--evaluation-variant`` with a name a scenario does not define scores what
  the option would score if omitted -- the scenario's ``default_variant``, or
  ``commit_level`` -- and an empty name is an omitted one; a run says so once
  (issue #140, docs/evaluation-policies.md section 1.3).
- A hash in any letter case, or with whitespace around it, names its commit,
  as ``inducing_commit`` and as ``fix_commit`` (issue #142, section 1.1).
- A variant's name relaxes the set-comparison policies only: ``partial_credit``
  and ``top_k`` keep their own rules under a variant called ``origin-aware``
  (issue #145, section 4).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from szzbench.evaluator import Prediction, evaluate_prediction_map, evaluate_scenario
from szzbench.generator import generate_repository
from szzbench.graph_generator import generate_graph_repository

ROOT = Path(__file__).resolve().parents[1]


# --- --evaluation-variant (issue #140) --------------------------------------------------

@pytest.fixture(scope="module")
def generated_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """SZZG-0085, whose whole oracle is in variants (no commit_level), SZZG-0022, which
    defines relaxed-with-credit, and the classic SZZ-0006, generated as `evaluate` reads them."""
    root = tmp_path_factory.mktemp("generated-input-repos")
    for sid in ("SZZG-0085", "SZZG-0022"):
        _, verify = generate_graph_repository(ROOT / "advanced-scenarios" / sid / "scenario.graph.yml",
                                              root / sid / "default", force=True)
        assert not verify.has_errors(), verify.to_dict()
    _, verify = generate_repository(ROOT / "scenarios" / "SZZ-0006" / "scenario.yml", root / "SZZ-0006" / "default",
                                    force=True)
    assert not verify.has_errors(), verify.to_dict()
    return root


def _run(generated_root: Path, evaluation_variant: str | None):
    answers = {"SZZG-0085": ["c3", "c1"], "SZZG-0022": ["c2"], "SZZ-0006": ["c1"]}
    predictions = {sid: [Prediction(sid, inducing_commit=commit) for commit in commits] for sid, commits in answers.items()}
    return evaluate_prediction_map(predictions, generated_root=generated_root, scenarios_root=ROOT / "scenarios",
                                   advanced_scenarios_root=ROOT / "advanced-scenarios",
                                   evaluation_variant=evaluation_variant)


def _by_id(report) -> dict[str, dict]:
    return {item.scenario_id: item.to_dict() for item in report.scenarios}


def test_an_undefined_variant_scores_the_default_variant_and_is_reported_once(generated_root):
    """SZZG-0085 does not define relaxed-with-credit.  It was scored against commit_level,
    which it does not declare, so against BICs inferred from bugs[]: c1 lost its place in
    related_origins and became a hard false positive."""
    omitted = _by_id(_run(generated_root, None))
    report = _run(generated_root, "relaxed-with-credit")
    requested = _by_id(report)

    scored = requested["SZZG-0085"]
    assert scored["evaluation_variant"] == "reintroduction-direct"
    assert scored["related_origin_hits"] == ["c1"] and scored["hard_false_positives"] == []
    assert scored["result_notes"] == ["Requested evaluation variant 'relaxed-with-credit' is not defined; "
                                      "using the default variant 'reintroduction-direct'."]
    # the scores and diagnostics are those of the omitted option
    assert {**scored, "result_notes": []} == {**omitted["SZZG-0085"], "result_notes": []}
    assert requested["SZZG-0022"]["evaluation_variant"] == "relaxed-with-credit"

    # one warning for the run, not one per scenario, and no oracle inferred from bugs[]
    assert report.warnings == [
        "Evaluation variant 'relaxed-with-credit' is not defined in 1 of the 2 graph scenario(s) evaluated; they "
        "were scored as without --evaluation-variant, against their default_variant or else commit_level, and each "
        "one's result notes say which."]
    # the classic suite has no variants: said once
    assert report.info == [
        "--evaluation-variant applies to graph scenarios only; the 1 classic scenario(s) were scored against their "
        "own oracle."]
    # and the note stays with the scenario where people read the result
    assert "- SZZG-0085: Requested evaluation variant 'relaxed-with-credit' is not defined" in report.to_markdown()


@pytest.mark.parametrize("name", ["", "  "])
def test_an_empty_variant_name_is_an_omitted_option(generated_root, name):
    """What an unset shell variable expands to.  It bypassed default_variant without a note."""
    assert _run(generated_root, name).to_dict() == _run(generated_root, None).to_dict()


# --- the spelling of a commit reference (issue #142) ------------------------------------

C1 = "f20baf7c7cf1891e4b620aa38c025b54567d872e"
C2 = "9b0e5d2c41aa3f7e8d6c5b4a39281706f5e4d3c2"
COMMIT_MAP = {"c0": {"hash": "0" * 40}, "c1": {"hash": C1}, "c2": {"hash": C2}}
BRANCH_SCENARIO = {"expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]},
                                    "branch_level": {"main": {"bfc": "c2", "required": ["c1"]}}}}


def _evaluate(predictions, tmp_path, *, scenario=BRANCH_SCENARIO, **options):
    return evaluate_scenario("SZZG-test", scenario, tmp_path / "scenario.graph.yml", "advanced-scenarios", COMMIT_MAP,
                             [Prediction("SZZG-test", **kwargs) for kwargs in predictions], **options)


@pytest.mark.parametrize("spell", [
    str.upper,                                  # Git reads a hash in any letter case
    lambda h: h[:20].upper() + h[20:],          # mixed case
    lambda h: h + "\n",                         # what a shell pipeline leaves on it
    lambda h: f"  {h}\t",
    lambda h: h[:7].upper(),                    # a unique prefix, in upper case
], ids=["upper-case", "mixed-case", "trailing-newline", "spaces-and-tab", "upper-case-prefix"])
def test_a_hash_in_any_letter_case_or_with_whitespace_around_it_names_its_commit(tmp_path, spell):
    result = _evaluate([{"inducing_commit": spell(C1), "fix_commit": spell(C2)}], tmp_path)
    assert result.status == "PASS" and result.unknown_predictions == [] and result.true_positives == ["c1"]
    assert result.branch_level["branches"]["main"]["predicted"] == ["c1"]
    assert not any("resolve to no declared" in note for note in result.result_notes)


def test_a_reference_that_still_names_nothing_is_reported_as_written(tmp_path):
    # a logical id is matched as written, and a blank reference names nothing
    result = _evaluate([{"inducing_commit": "C1"}, {"inducing_commit": " \n"}], tmp_path)
    assert result.status == "FAIL" and result.unknown_predictions == [" \n", "C1"]
    # --reference-format still decides which kind of name counts
    assert _evaluate([{"inducing_commit": " c1 "}], tmp_path, reference_format="hash").unknown_predictions == [" c1 "]
    assert _evaluate([{"inducing_commit": C1.upper()}], tmp_path, reference_format="logical").unknown_predictions == [C1.upper()]
    assert _evaluate([{"inducing_commit": "c1\n"}], tmp_path, reference_format="logical").status == "PASS"
    assert _evaluate([{"inducing_commit": f" {C1.upper()} "}], tmp_path, reference_format="hash").status == "PASS"


# --- what a variant's name changes (issue #145) -----------------------------------------

def test_a_variant_name_relaxes_the_set_comparison_policies_only(tmp_path):
    """docs/evaluation-policies.md section 4: a variant named origin-aware tolerates a related
    origin under exact_set, and changes nothing under partial_credit or top_k."""

    def scored(commit_level: dict, answer: list[str], variant: str | None) -> dict:
        scenario = {"expected_szz": {"commit_level": commit_level,
                                     "evaluation_variants": [{"name": "origin-aware", "commit_level": dict(commit_level)}]}}
        predictions = [{"inducing_commit": commit, "rank": rank} for rank, commit in enumerate(answer, start=1)]
        return _evaluate(predictions, tmp_path, scenario=scenario, evaluation_variant=variant).to_dict()

    exact_set = {"evaluation_policy": "exact_set", "required": ["c2"], "related_origins": ["c0"]}
    assert scored(exact_set, ["c2", "c0"], None)["status"] == "FAIL"
    assert scored(exact_set, ["c2", "c0"], "origin-aware")["status"] == "PASS"

    # SZZG-0033's oracle (one of two) with a related origin: c0 is a false positive whatever the variant is called
    partial = {"evaluation_policy": "partial_credit", "required": ["c1", "c2"], "minimum_required": 1,
               "related_origins": ["c0"]}
    for variant in (None, "origin-aware"):
        result = scored(partial, ["c2", "c0"], variant)
        assert result["evaluation_variant"] == variant
        assert result["minimum_required_met"] is True and result["related_origin_hits"] == ["c0"]
        assert result["hard_false_positives"] == [] and result["status"] == "FAIL"

    # top_k is decided by rank alone: the origin at rank 1 puts c2 at rank 2, outside status_k
    top_k = {"evaluation_policy": "top_k", "required": ["c2"], "status_k": 1, "related_origins": ["c0"]}
    for variant in (None, "origin-aware"):
        result = scored(top_k, ["c0", "c2"], variant)
        assert result["top_k"]["best_rank"] == 2 and result["status"] == "FAIL"
    assert scored(top_k, ["c2", "c0"], "origin-aware")["status"] == "PASS"
