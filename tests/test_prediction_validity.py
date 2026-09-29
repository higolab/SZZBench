"""Unknown references, tool failures and missing records are not answers (issue #95).

Until 2026-09-29 three things a tool run can produce were scored as ordinary
answers.  An unresolvable commit reference failed its scenario but was left out
of precision, so ``c1`` plus an unknown hash reported precision 1.0 and recall
1.0, in the scenario and in the aggregate.  A scenario without a prediction
record was scored as an empty prediction, and the PySZZ adapter wrote an empty
record for a scenario on which the tool raised; both read as a deliberate
abstention, so SZZG-0135, whose oracle is empty, PASSed for a tool that never
ran on it.

Now an unknown reference is a false positive of its own kind -- listed in
``unknown_predictions``, counted in the precision denominator and in the
summary, and holding its place in a ranking -- a record with ``status: error``
and a scenario without a record FAIL with a ``run_status`` that says why, and
only an explicit record is an answer: an explicit empty one is still a valid
abstention.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from szzbench.evaluator import evaluate_predictions  # noqa: E402
from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402

UNKNOWN = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
OTHER_UNKNOWN = "feedfacefeedfacefeedfacefeedfacefeedface"


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    """SZZ-0006 (oracle {c1}), SZZG-0135 (empty oracle) and SZZG-0140 (top_k, relevant c1)."""
    root = tmp_path_factory.mktemp("generated")
    generate_repository(ROOT / "scenarios/SZZ-0006/scenario.yml", root / "SZZ-0006/default", force=True)
    for sid in ("SZZG-0135", "SZZG-0140"):
        generate_graph_repository(ROOT / f"advanced-scenarios/{sid}/scenario.graph.yml", root / sid / "default",
                                  force=True)
    return root


def _hash(generated: Path, sid: str, cid: str) -> str:
    return json.loads((generated / sid / "default/metadata/commit-map.json").read_text())[cid]["hash"]


def _evaluate(generated: Path, tmp_path: Path, records: list[dict], *, include_generated: bool = False):
    path = tmp_path / "predictions.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    report = evaluate_predictions(path, generated_root=generated, scenarios_root=ROOT / "scenarios",
                                  advanced_scenarios_root=ROOT / "advanced-scenarios",
                                  include_generated=include_generated)
    return report, {item.scenario_id: item for item in report.scenarios}


def _predict(*refs: str) -> list[dict]:
    return [{"inducing_commit": ref} for ref in refs]


@pytest.mark.parametrize(
    "refs, status, false_positives, unknown, precision",
    [
        (["c1"], "PASS", [], [], 1.0),
        (["c1", "c0"], "FAIL", ["c0"], [], 0.5),
        (["c1", UNKNOWN], "FAIL", [], [UNKNOWN], 0.5),
        (["c1", UNKNOWN, UNKNOWN], "FAIL", [], [UNKNOWN], 0.5),
        (["c1", UNKNOWN, OTHER_UNKNOWN], "FAIL", [], sorted([UNKNOWN, OTHER_UNKNOWN]), 1 / 3),
        (["c1", "c0", UNKNOWN], "FAIL", ["c0"], [UNKNOWN], 1 / 3),
    ],
    ids=["correct-only", "known-wrong", "correct-plus-unknown", "duplicate-unknowns", "two-unknowns",
         "known-wrong-plus-unknown"],
)
def test_an_unknown_reference_counts_as_a_false_positive(generated, tmp_path, refs, status, false_positives,
                                                         unknown, precision):
    report, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZ-0006", "predictions": _predict(*refs)}])
    item = by_id["SZZ-0006"]
    assert report.errors == []
    assert (item.status, item.true_positives, item.false_positives, item.unknown_predictions) == \
        (status, ["c1"], false_positives, unknown)
    assert item.precision == pytest.approx(precision)
    assert item.recall == 1.0
    summary = report.summary()
    assert summary["unknown_predictions"] == len(unknown)
    assert summary["precision"] == pytest.approx(precision)


def test_the_case_in_issue_95_with_the_generated_hash(generated, tmp_path):
    report, by_id = _evaluate(generated, tmp_path, [
        {"scenario_id": "SZZ-0006", "predictions": _predict(_hash(generated, "SZZ-0006", "c1"), UNKNOWN)}])
    item = by_id["SZZ-0006"]
    assert (item.status, item.precision, item.recall) == ("FAIL", 0.5, 1.0)
    assert report.summary()["precision"] == 0.5


def test_unknown_only(generated, tmp_path):
    _, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZ-0006", "predictions": _predict(UNKNOWN)}])
    item = by_id["SZZ-0006"]
    assert (item.status, item.true_positives, item.unknown_predictions) == ("FAIL", [], [UNKNOWN])
    assert (item.precision, item.recall) == (0.0, 0.0)


def test_an_explicit_empty_record_is_still_an_abstention(generated, tmp_path):
    _, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZG-0135", "predictions": []}])
    item = by_id["SZZG-0135"]
    assert (item.status, item.run_status, item.run_errors) == ("PASS", "ok", [])
    assert (item.precision, item.recall) == (None, None)


def test_an_unknown_reference_fails_an_empty_oracle_with_precision_zero(generated, tmp_path):
    _, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZG-0135", "predictions": _predict(UNKNOWN)}])
    item = by_id["SZZG-0135"]
    assert (item.status, item.precision, item.recall) == ("FAIL", 0.0, None)


def test_a_scenario_without_a_record_fails_instead_of_abstaining(generated, tmp_path):
    report, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZ-0006", "predictions": _predict("c1")}],
                              include_generated=True)
    assert (by_id["SZZ-0006"].status, by_id["SZZ-0006"].run_status) == ("PASS", "ok")
    for sid in ("SZZG-0135", "SZZG-0140"):
        assert (by_id[sid].status, by_id[sid].run_status) == ("FAIL", "missing")
    summary = report.summary()
    assert (summary["pass"], summary["fail"], summary["missing_records"]) == (1, 2, 2)
    assert any(w.startswith("SZZG-0135:") and "no prediction record" in w for w in report.warnings)


def test_no_predictions_file_at_all_passes_nothing(generated):
    report = evaluate_predictions(None, generated_root=generated, scenarios_root=ROOT / "scenarios",
                                  advanced_scenarios_root=ROOT / "advanced-scenarios", include_generated=True)
    assert report.summary()["pass"] == 0
    assert {item.run_status for item in report.scenarios} == {"missing"}


def test_a_record_reporting_a_tool_error_fails_with_the_error(generated, tmp_path):
    report, by_id = _evaluate(generated, tmp_path, [
        {"scenario_id": "SZZG-0135", "status": "error", "errors": ["RuntimeError: boom"], "predictions": []}])
    item = by_id["SZZG-0135"]
    assert (item.status, item.run_status, item.run_errors) == ("FAIL", "error", ["RuntimeError: boom"])
    assert any("RuntimeError: boom" in note for note in item.result_notes)
    assert report.summary()["tool_errors"] == 1


def test_an_error_record_needs_no_inducing_commit_and_keeps_partial_predictions(generated, tmp_path):
    report, by_id = _evaluate(generated, tmp_path, [
        {"scenario_id": "SZZG-0135", "status": "ERROR"},
        {"scenario_id": "SZZ-0006", "status": "error", "errors": "timed out after c2", "inducing_commit": "c1"}])
    assert report.errors == []
    assert (by_id["SZZG-0135"].status, by_id["SZZG-0135"].run_status) == ("FAIL", "error")
    assert by_id["SZZG-0135"].run_errors == ["the tool reported an error"]
    partial = by_id["SZZ-0006"]
    assert (partial.status, partial.run_status, partial.true_positives) == ("FAIL", "error", ["c1"])
    assert partial.run_errors == ["timed out after c2"]


@pytest.mark.parametrize("status", ["timeout", "", 1, None])
def test_a_status_that_is_neither_ok_nor_error_is_a_loading_error(generated, tmp_path, status):
    record = {"scenario_id": "SZZG-0135", "predictions": []}
    record["status"] = status
    report, by_id = _evaluate(generated, tmp_path, [record])
    if status is None:          # an explicit null is an omitted status
        assert report.errors == [] and by_id["SZZG-0135"].status == "PASS"
        return
    assert any("status" in error for error in report.errors)
    assert "SZZG-0135" not in by_id or by_id["SZZG-0135"].status == "FAIL"


def test_an_unknown_reference_holds_its_place_in_a_ranking(generated, tmp_path):
    # SZZG-0140: top_k, relevant c1, status_k 1
    _, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZG-0140", "predictions": [
        {"inducing_commit": UNKNOWN, "rank": 1}, {"inducing_commit": "c1", "rank": 2}]}])
    top_k = by_id["SZZG-0140"].top_k
    assert top_k["best_rank"] == 2
    assert top_k["hit_at"] == {"1": False, "3": True, "5": True}
    assert top_k["mrr"] == 0.5
    assert top_k["ranked_actual_bics"] == [UNKNOWN, "c1"]


def test_the_markdown_report_shows_unknown_references_and_the_run_status(generated, tmp_path):
    report, _ = _evaluate(generated, tmp_path, [
        {"scenario_id": "SZZ-0006", "predictions": _predict("c1", UNKNOWN)},
        {"scenario_id": "SZZG-0135", "status": "error", "errors": ["RuntimeError: boom"]}],
        include_generated=True)
    markdown = report.to_markdown()
    assert "- Unknown predictions (counted as false positives): 1" in markdown
    assert "- Tool errors: 1" in markdown
    assert "- Missing prediction records: 1" in markdown
    header = next(line for line in markdown.splitlines() if line.startswith("| Scenario |"))
    columns = [cell.strip() for cell in header.strip("|").split("|")]
    rows = {line.split("|")[1].strip(): [cell.strip() for cell in line.strip("|").split("|")]
            for line in markdown.splitlines() if line.startswith("| SZZ")}
    assert rows["SZZ-0006"][columns.index("Unknown")] == UNKNOWN
    assert rows["SZZG-0135"][columns.index("Run")] == "error"
    assert rows["SZZG-0140"][columns.index("Run")] == "missing"


# ---------------------------------------------------------------------------
# adapters: a failure is written into the record, an empty result is a record
# ---------------------------------------------------------------------------

def _classic_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    scenarios = tmp_path / "scenarios"
    advanced = tmp_path / "advanced-scenarios"
    advanced.mkdir()
    repos = tmp_path / "repos"
    (scenarios / "SZZ-0006").mkdir(parents=True)
    (scenarios / "SZZ-0006/scenario.yml").write_bytes((ROOT / "scenarios/SZZ-0006/scenario.yml").read_bytes())
    generate_repository(scenarios / "SZZ-0006/scenario.yml", repos / "SZZ-0006/default", force=True)
    return scenarios, advanced, repos


@pytest.mark.parametrize("behaviour, expected_status", [("raise", "error"), ("nothing", None)])
def test_the_pydriller_adapter_records_failures_and_empty_results(tmp_path, behaviour, expected_status):
    scenarios, advanced, repos = _classic_fixture(tmp_path)
    fake = tmp_path / "fake-pydriller/pydriller"
    fake.mkdir(parents=True)
    body = 'raise RuntimeError("boom")' if behaviour == "raise" else "return {}"
    fake.joinpath("__init__.py").write_text(textwrap.dedent(f"""\
        class Git:
            def __init__(self, path):
                self.path = path
            def get_commit(self, commit_hash):
                return type("Commit", (), {{"hash": commit_hash}})()
            def get_commits_last_modified_lines(self, commit):
                {body}
        """), encoding="utf-8")
    out = tmp_path / "predictions.jsonl"
    completed = subprocess.run([sys.executable, str(ROOT / "tools/adapters/pydriller_to_predictions.py"),
                                "--pydriller-path", str(fake.parent), "--generated-root", str(repos),
                                "--scenarios-root", str(scenarios), "--advanced-scenarios-root", str(advanced),
                                "--out", str(out)], capture_output=True, text=True)
    assert completed.returncode == (1 if expected_status == "error" else 0), completed.stderr
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["scenario_id"] == "SZZ-0006" and record["predictions"] == []
    assert record.get("status") == expected_status
    if expected_status == "error":
        assert any("RuntimeError: boom" in error for error in record["errors"])


def _load_pyszz_adapter(monkeypatch):
    if importlib.util.find_spec("git") is None:     # the adapter imports GitPython at module level
        monkeypatch.setitem(sys.modules, "git", types.SimpleNamespace(Repo=object))
    spec = importlib.util.spec_from_file_location("pyszz_adapter",
                                                  ROOT / "tools/adapters/pyszz_variants_to_predictions.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)    # dataclasses resolve their module through it
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("behaviour, expected_status", [("raise", "error"), ("nothing", None)])
def test_the_pyszz_adapter_records_failures_and_empty_results(tmp_path, monkeypatch, behaviour, expected_status):
    _, _, repos = _classic_fixture(tmp_path)
    fake = tmp_path / "fake-pyszz/szz"
    fake.mkdir(parents=True)
    fake.joinpath("__init__.py").write_text("", encoding="utf-8")
    body = 'raise RuntimeError("boom")' if behaviour == "raise" else "return []"
    fake.joinpath("b_szz.py").write_text(textwrap.dedent(f"""\
        class BaseSZZ:
            def __init__(self, repo_full_name, repo_url, repos_dir):
                pass
            def get_impacted_files(self, fix_commit_hash, file_ext_to_parse, only_deleted_lines):
                return []
            def find_bic(self, fix_commit_hash, impacted_files, **kwargs):
                {body}
        """), encoding="utf-8")
    monkeypatch.syspath_prepend(str(fake.parent))
    monkeypatch.delitem(sys.modules, "szz", raising=False)
    monkeypatch.delitem(sys.modules, "szz.b_szz", raising=False)
    adapter = _load_pyszz_adapter(monkeypatch)
    scenarios = adapter.collect_scenarios(repos, "default")
    adapter.run_tool("b-szz", scenarios, repos, tmp_path / "out", fake.parent)
    record = json.loads((tmp_path / "out/b-szz/b-szz-predictions.jsonl").read_text(encoding="utf-8"))
    assert record["scenario_id"] == "SZZ-0006" and record["predictions"] == []
    assert record.get("status") == expected_status
    if expected_status == "error":
        assert any("RuntimeError: boom" in error for error in record["errors"])


def test_the_szz_unleashed_adapter_writes_an_error_record_for_an_unreadable_result(tmp_path):
    _, _, repos = _classic_fixture(tmp_path)
    result = repos / "SZZ-0006/default/szz-unleashed/run-depth1/results/fix_and_introducers_pairs.json"
    result.parent.mkdir(parents=True)
    result.write_text("{ not json", encoding="utf-8")
    out = tmp_path / "predictions.jsonl"
    completed = subprocess.run([sys.executable, str(ROOT / "tools/adapters/szz_unleashed_to_predictions.py"),
                                "--generated-root", str(repos), "--out", str(out)], capture_output=True, text=True)
    assert completed.returncode == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert (record["scenario_id"], record["status"], record["predictions"]) == ("SZZ-0006", "error", [])
    assert "Invalid JSON" in record["errors"][0]


def test_the_cli_summary_counts_tool_errors_missing_records_and_unknown_references(generated, tmp_path):
    path = tmp_path / "predictions.jsonl"
    path.write_text(json.dumps({"scenario_id": "SZZ-0006", "predictions": _predict("c1", UNKNOWN)}) + "\n"
                    + json.dumps({"scenario_id": "SZZG-0135", "status": "error"}) + "\n", encoding="utf-8")
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", "evaluate", "--predictions", str(path),
                                "--generated-root", str(generated), "--scenarios-root", str(ROOT / "scenarios"),
                                "--advanced-scenarios-root", str(ROOT / "advanced-scenarios"), "--include-generated"],
                               capture_output=True, text=True, check=True,
                               env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    lines = {line.split(":")[0].strip(): line.split(":", 1)[1].strip()
             for line in completed.stdout.splitlines() if line.startswith("  ")}
    assert (lines["PASS"], lines["Tool errors"], lines["Missing records"], lines["Unknown (as FP)"]) == ("0", "1", "1", "1")
    assert lines["Precision"] == "0.500"


def test_an_adapter_error_record_is_scored_as_a_tool_error(tmp_path):
    scenarios, advanced, repos = _classic_fixture(tmp_path)
    out = tmp_path / "predictions.jsonl"
    out.write_text(json.dumps({"scenario_id": "SZZ-0006", "status": "error", "errors": ["boom"],
                               "predictions": []}) + "\n", encoding="utf-8")
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", "evaluate", "--predictions", str(out),
                                "--generated-root", str(repos), "--scenarios-root", str(scenarios),
                                "--advanced-scenarios-root", str(advanced), "--json"],
                               capture_output=True, text=True, check=True,
                               env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    item = json.loads(completed.stdout)["scenarios"][0]
    assert (item["status"], item["run_status"], item["run_errors"]) == ("FAIL", "error", ["boom"])
