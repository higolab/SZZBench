"""Oracle values and statements that validation passed and the evaluator or the verifier misread.

- Issue #146: ``bool`` is a subclass of ``int``, so ``true`` passed for 1 in
  ``rank``, ``k_values``, ``minimum_required`` and ``credit``; ``status_k: true``
  was dropped with a note, and a ``top_k`` oracle decided at the largest ``k``.
- Issue #159: a ``cherry_pick_of`` / ``backport_of`` naming the commit itself,
  an unknown id in ``known_distractors``, and ``required`` beside
  ``expect_no_bic: true`` passed ``validate-graph``.
- Issue #161: the author lint swallowed every exception and passed in silence.
- Issue #237: E351 tested only that ``missing_statement`` was there, and the
  graph suite checked no statement value: an empty one turned verification of
  its location off.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from szzbench import graph_validator
from szzbench.evaluator import Prediction, evaluate_scenario, load_predictions
from szzbench.findings import ValidationResult
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.validator import lint_author_coincidence, validate_scenario_file

from support import scenario_file

COMMIT_MAP = {f"c{i}": {"hash": str(i) * 40} for i in range(5)}


def _shipped(sid: str) -> dict:
    return yaml.safe_load(scenario_file(sid).read_text(encoding="utf-8"))


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / data["meta"]["id"] / ("scenario.graph.yml" if data["meta"]["id"].startswith("SZZG-")
                                            else "scenario.yml")
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _errors(result: ValidationResult) -> list[tuple[str, str | None]]:
    return [(finding.code, finding.location) for finding in result.error_findings()]


# --- issue #146: a boolean is not a number ---------------------------------------------------

@pytest.mark.parametrize("change, location", [
    ({"k_values": [True, 3]}, "k_values[0]"),
    ({"status_k": True}, "status_k"),
    ({"minimum_required": True}, "minimum_required"),
    ({"acceptable_related": [{"commit": "c0", "credit": True}]}, "acceptable_related[0].credit"),
    # float() raised OverflowError, and validate-graph ended in a traceback (GW130 asks the evaluator)
    ({"acceptable_related": [{"commit": "c0", "credit": 10 ** 400}]}, "acceptable_related[0].credit"),
])
def test_a_value_the_evaluator_does_not_read_as_a_number_is_ge131(tmp_path, change, location):
    data = _shipped("SZZG-0140")
    data["expected_szz"]["commit_level"].update(change)
    _, result = validate_graph_scenario_file(_write(tmp_path, data))
    assert _errors(result) == [("GE131", f"expected_szz.commit_level.{location}")]


def test_the_evaluator_ignores_a_boolean_number_with_a_note(tmp_path):
    def evaluate(sid: str, change: dict, inducing: list[tuple[str, int]]):
        scenario = _shipped(sid)
        scenario["expected_szz"]["commit_level"].update(change)
        predictions = [Prediction(scenario_id=sid, inducing_commit=commit, rank=rank) for commit, rank in inducing]
        return evaluate_scenario(sid, scenario, tmp_path / "scenario.graph.yml", "advanced-scenarios", COMMIT_MAP,
                                 predictions)

    top_k = evaluate("SZZG-0140", {"k_values": [True, 3], "status_k": True}, [("c2", 1), ("c1", 2)])
    assert (top_k.top_k["k_values"], top_k.top_k["status_k"], top_k.top_k["hit_at"]) == ([3], 3, {"3": True})
    assert {"k_values entries must be positive integers; ignoring True.",
            "status_k must be a positive integer; ignoring it."} <= set(top_k.result_notes)
    partial = evaluate("SZZG-0033", {"minimum_required": True, "acceptable_related": [{"commit": "c0", "credit": True}]},
                       [("c1", 1), ("c0", 2)])
    assert partial.minimum_required is None and partial.acceptable_related_hits == [{"commit": "c0", "credit": 0.0}]
    assert {"minimum_required must be a non-negative integer; ignoring it.",
            "acceptable_related credit of 'c0' must be a number; ignoring it."} <= set(partial.result_notes)


def test_a_boolean_rank_or_confidence_is_a_loading_error(tmp_path):
    path = tmp_path / "predictions.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in [
        {"scenario_id": "SZZG-0140", "predictions": [{"inducing_commit": "c2", "rank": True}]},
        {"scenario_id": "SZZG-0001", "inducing_commit": "c1", "confidence": False},
    ]) + "\n", encoding="utf-8")
    predictions, _, _, invalid, _, errors, _ = load_predictions(path)
    assert [error.split(": ", 1)[1] for error in errors] == ["rank must be an integer when present.",
                                                            "confidence must be a number when present."]
    assert predictions == {} and sorted(invalid) == ["SZZG-0001", "SZZG-0140"]


# --- issue #159: three reference checks --------------------------------------------------------

@pytest.mark.parametrize("key, index", [("cherry_pick_of", 1), ("backport_of", 2)])
def test_a_replay_annotation_naming_the_commit_itself_is_ge043(key, index):
    data = _shipped("SZZG-0001")
    data["commits"][index][key] = data["commits"][index]["id"]
    result = validate_graph_static(data)
    assert _errors(result) == [("GE043", f"commits[{index}].{key}")]
    assert "itself" in result.error_findings()[0].message


def test_known_distractors_are_checked_as_the_other_commit_lists():
    data = _shipped("SZZG-0140")
    data["expected_szz"]["commit_level"]["known_distractors"] = ["c2", "zzz", 5]
    data["expected_szz"]["evaluation_variants"] = [
        {"name": "lenient", "commit_level": {"evaluation_policy": "top_k", "required": ["c1"], "known_distractors": "c2"}}]
    assert _errors(validate_graph_static(data)) == [
        ("GE126", "expected_szz.commit_level.known_distractors[1]"),
        ("GE125", "expected_szz.commit_level.known_distractors[2]"),
        ("GE124", "expected_szz.evaluation_variants[0].commit_level.known_distractors")]


def test_required_beside_expect_no_bic_is_ge132():
    data = _shipped("SZZG-0001")
    data["expected_szz"]["commit_level"]["expect_no_bic"] = True
    data["expected_szz"]["evaluation_variants"] = [
        {"name": "empty", "commit_level": {"required": [], "expect_no_bic": True}},       # the intended spelling
        {"name": "both", "commit_level": {"required": ["c1"], "expect_no_bic": True}}]
    result = validate_graph_static(data)
    assert _errors(result) == [("GE132", "expected_szz.commit_level.expect_no_bic"),
                               ("GE132", "expected_szz.evaluation_variants[1].commit_level.expect_no_bic")]
    assert "keep required and ignore expect_no_bic" in result.error_findings()[0].message


# --- issue #161: a lint that cannot run says so ------------------------------------------------

def test_the_author_lint_says_when_it_cannot_resolve_the_history():
    """The static checks report the date first (E013 / GE071, issue #152), so the lint
    is called directly here, as it would meet such a value if they did not."""
    graph = _shipped("SZZG-0001")
    graph["commits"][1]["date"] = {"year": 2024}
    classic = _shipped("SZZ-0005")
    classic["commits"][0]["date"] = {"year": 2023}
    for data, suite, prefix in ((graph, "advanced-scenarios", "GW"), (classic, "scenarios", "W")):
        result = ValidationResult()
        lint_author_coincidence(data, suite, result, prefix=prefix)
        assert [(f.severity, f.code, f.location) for f in result.findings] == [("WARNING", f"{prefix}413", "commits")]
        assert "could not resolve the history" in result.findings[0].message


def test_the_origin_lint_says_when_it_cannot_resolve_the_oracle(monkeypatch):
    def unreadable(*args):
        raise ValueError("an oracle the evaluator cannot read")

    monkeypatch.setattr(graph_validator, "_commit_level_policy", unreadable)
    data = _shipped("SZZG-0018")
    result = ValidationResult()
    graph_validator._lint_origin_coverage(data["bugs"], data, result)
    assert [(f.severity, f.code, f.location) for f in result.findings] == [("WARNING", "GW450", "expected_szz")]


# --- issue #237: a statement is text that is not blank -----------------------------------------

@pytest.mark.parametrize("value, what", [("", "is empty"), ("  \n", "is empty"), (None, "not null"), (5, "not int")])
def test_a_blank_or_non_string_missing_statement_is_e351(tmp_path, value, what):
    data = _shipped("SZZ-0047")
    data["bugs"][0]["fault"]["missing_statement"] = value
    _, result, _ = validate_scenario_file(_write(tmp_path, data), simulate=True)
    assert _errors(result) == [("E351", "bugs[0].fault.missing_statement")]
    assert what in result.error_findings()[0].message


_DROP = object()


def _set_or_drop(entry: dict, key: str, value) -> None:
    if value is _DROP:
        del entry[key]
    else:
        entry[key] = value


@pytest.mark.parametrize("kind, index, key, value", [
    ("faults", 2, "missing_statement", ""),           # F003, an omission
    ("faults", 2, "missing_statement", None),
    ("faults", 2, "missing_statement", _DROP),        # the counterpart of E351
    ("faults", 0, "statement", " "),                  # F001, a line fault: found 58 times
    ("faults", 0, "statement", 5),                    # verify-graph skipped GE663 and the blame check
    ("fixes", 0, "statement", ""),                    # X001
], ids=["missing-empty", "missing-null", "missing-absent", "statement-blank", "statement-number", "fix-empty"])
def test_a_blank_or_non_string_graph_statement_is_ge104_without_simulation(kind, index, key, value):
    data = _shipped("SZZG-0138")
    _set_or_drop(data["bugs"][0][kind][index], key, value)
    assert _errors(validate_graph_static(data)) == [("GE104", f"bugs[0].{kind}[{index}].{key}")]


def test_a_graph_omission_with_a_statement_is_gw106():
    data = _shipped("SZZG-0138")
    data["bugs"][0]["faults"][2]["statement"] = "if (cents < 0) {"
    result = validate_graph_static(data)
    assert _errors(result) == []
    assert [(f.code, f.location) for f in result.findings if f.code == "GW106"] == [("GW106", "bugs[0].faults[2].statement")]
