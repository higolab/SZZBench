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

from szzbench.evaluator import evaluate_predictions
from szzbench.generator import generate_repository
from szzbench.graph_generator import generate_graph_repository
from support import git

ROOT = Path(__file__).resolve().parents[1]

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


def _evaluate(generated: Path, tmp_path: Path, records: list[dict], *, include_generated: bool = False,
              reference_format: str = "auto"):
    path = tmp_path / "predictions.jsonl"
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    report = evaluate_predictions(path, generated_root=generated, scenarios_root=ROOT / "scenarios",
                                  advanced_scenarios_root=ROOT / "advanced-scenarios",
                                  include_generated=include_generated, reference_format=reference_format)
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


# --- the file's encoding (issue #137) -------------------------------------------

def _evaluate_bytes(generated: Path, path: Path):
    return evaluate_predictions(path, generated_root=generated, scenarios_root=ROOT / "scenarios",
                                advanced_scenarios_root=ROOT / "advanced-scenarios")


def test_a_bom_costs_no_record(generated, tmp_path):
    """Windows editors and PowerShell write one; it used to make line 1 invalid JSON."""
    records = [{"scenario_id": "SZZ-0006", "predictions": _predict("c1")}, {"scenario_id": "SZZG-0135", "predictions": []}]
    path = tmp_path / "bom.jsonl"
    path.write_bytes(b"\xef\xbb\xbf" + "".join(json.dumps(r) + "\n" for r in records).encode("utf-8"))
    report = _evaluate_bytes(generated, path)
    assert report.errors == []
    assert {item.scenario_id: item.status for item in report.scenarios} == {"SZZ-0006": "PASS", "SZZG-0135": "PASS"}


def test_a_bom_before_a_whole_json_document_is_accepted_too(generated, tmp_path):
    path = tmp_path / "bom.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps([{"scenario_id": "SZZ-0006", "predictions": _predict("c1")}]).encode())
    report = _evaluate_bytes(generated, path)
    assert report.errors == [] and [item.status for item in report.scenarios] == ["PASS"]


@pytest.mark.parametrize("encoding, byte", [("latin-1", 0xE9), ("utf-16", 0xFF)])
def test_a_file_that_is_not_utf8_is_a_loading_error_not_a_traceback(generated, tmp_path, encoding, byte):
    record = {"scenario_id": "SZZ-0006", "predictions": [{"inducing_commit": "c1", "tool": "caf\u00e9"}]}
    raw = (json.dumps(record, ensure_ascii=False) + "\n").encode(encoding)
    path = tmp_path / "predictions.jsonl"
    path.write_bytes(raw)
    report = _evaluate_bytes(generated, path)
    assert report.errors == [f"Cannot read predictions file: {path} is not UTF-8 "
                             f"(byte 0x{byte:02x} at position {raw.index(bytes([byte]))}); save it as UTF-8."]
    assert report.scenarios == []


@pytest.mark.parametrize("raw, byte, position", [
    (b"\xef\xbb\xbf\xe9", 0xE9, 3),
    (b"\xef\xbb\xbf" + '{"scenario_id": "SZZ-0006", "predictions": [{"inducing_commit": "c1", "tool": "caf\u00e9"}]}\n'
     .encode("latin-1"), 0xE9, 85),
], ids=["minimal", "record"])
def test_the_byte_and_offset_after_a_bom_are_the_files_own(generated, tmp_path, raw, byte, position):
    """utf-8-sig counted from after the BOM and named the wrong byte (PR #217 review)."""
    assert raw[position] == byte
    path = tmp_path / "predictions.jsonl"
    path.write_bytes(raw)
    report = _evaluate_bytes(generated, path)
    assert report.errors == [f"Cannot read predictions file: {path} is not UTF-8 "
                             f"(byte 0x{byte:02x} at position {position}); save it as UTF-8."]


def test_the_cli_reports_it_writes_its_report_and_exits_1(generated, tmp_path):
    path = tmp_path / "predictions.jsonl"
    path.write_bytes('{"scenario_id": "SZZ-0006", "predictions": [{"inducing_commit": "c1", "tool": "caf\u00e9"}]}\n'
                     .encode("latin-1"))
    completed = subprocess.run([sys.executable, "-m", "szzbench.cli", "evaluate", "--predictions", str(path),
                                "--generated-root", str(generated), "--out", str(tmp_path / "out")],
                               capture_output=True, text=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert completed.returncode == 1 and "Traceback" not in completed.stderr
    assert "[ERROR] Cannot read predictions file: " in completed.stderr and "is not UTF-8 (byte 0xe9" in completed.stderr
    assert (tmp_path / "out/evaluation-results.json").is_file() and (tmp_path / "out/evaluation-results.md").is_file()


def test_an_unknown_reference_holds_its_place_in_a_ranking(generated, tmp_path):
    # SZZG-0140: top_k, relevant c1, status_k 1
    _, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZG-0140", "predictions": [
        {"inducing_commit": UNKNOWN, "rank": 1}, {"inducing_commit": "c1", "rank": 2}]}])
    top_k = by_id["SZZG-0140"].top_k
    assert top_k["best_rank"] == 2
    assert top_k["hit_at"] == {"1": False, "3": True, "5": True}
    assert top_k["mrr"] == 0.5
    assert (top_k["ranked_actual_bics"], top_k["unknown_ranks"]) == (["c1"], [1])


def test_an_unknown_reference_spelled_like_a_relevant_id_is_not_a_hit(generated, tmp_path):
    # PR #99 review: with --reference-format hash the logical id "c1" is an unknown reference,
    # and the full ranking once read it as the relevant commit c1 at rank 1.
    _, by_id = _evaluate(generated, tmp_path, [{"scenario_id": "SZZG-0140", "predictions": [
        {"inducing_commit": "c1", "rank": 1},
        {"inducing_commit": _hash(generated, "SZZG-0140", "c1"), "rank": 2}]}], reference_format="hash")
    item = by_id["SZZG-0140"]
    assert (item.status, item.unknown_predictions, item.true_positives) == ("FAIL", ["c1"], ["c1"])
    top_k = item.top_k
    assert (top_k["best_rank"], top_k["mrr"]) == (2, 0.5)
    assert top_k["hit_at"] == {"1": False, "3": True, "5": True}
    assert (top_k["ranked_actual_bics"], top_k["unknown_ranks"]) == (["c1"], [1])


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


def _run_fake_b_szz(tmp_path, monkeypatch, find_bic_lines, before_run=None):
    """Run the PySZZ adapter's B-SZZ on SZZ-0006 with ``find_bic`` replaced by the given lines.

    ``before_run`` may damage the generated output first.
    """
    _, _, repos = _classic_fixture(tmp_path)
    if before_run is not None:
        before_run(repos)
    fake = tmp_path / "fake-pyszz/szz"
    fake.mkdir(parents=True)
    fake.joinpath("__init__.py").write_text("", encoding="utf-8")
    body = "".join(f"        {line}\n" for line in find_bic_lines)
    fake.joinpath("b_szz.py").write_text(
        "import logging as log\n"
        "import traceback\n"
        "\n"
        "class BaseSZZ:\n"
        "    def __init__(self, repo_full_name, repo_url, repos_dir):\n"
        "        pass\n"
        "    def get_impacted_files(self, fix_commit_hash, file_ext_to_parse, only_deleted_lines):\n"
        "        return []\n"
        "    def find_bic(self, fix_commit_hash, impacted_files, **kwargs):\n" + body,
        encoding="utf-8")
    monkeypatch.syspath_prepend(str(fake.parent))
    monkeypatch.delitem(sys.modules, "szz", raising=False)
    monkeypatch.delitem(sys.modules, "szz.b_szz", raising=False)
    adapter = _load_pyszz_adapter(monkeypatch)
    adapter.run_tool("b-szz", adapter.collect_scenarios(repos, "default"), repos, tmp_path / "out", fake.parent)
    record = json.loads((tmp_path / "out/b-szz/b-szz-predictions.jsonl").read_text(encoding="utf-8"))
    raw = json.loads((tmp_path / "out/b-szz/raw/SZZ-0006.json").read_text(encoding="utf-8"))
    return record, raw


@pytest.mark.parametrize("damage, problem", [
    (lambda metadata: (metadata / "commit-map.json").unlink(), "commit-map.json is missing"),
    (lambda metadata: (metadata / "commit-map.json").write_text("{ not json", encoding="utf-8"),
     "commit-map.json cannot be read (JSONDecodeError"),
    # valid JSON, but no commit map
    (lambda metadata: (metadata / "commit-map.json").write_text("[]", encoding="utf-8"),
     "commit-map.json holds an array, not a JSON object"),
    (lambda metadata: (metadata / "scenario.yml").write_text("bugs: [\n", encoding="utf-8"),
     "scenario.yml cannot be read (ParserError"),
])
def test_a_generated_output_pyszz_cannot_run_on_is_a_tool_error_not_left_out(tmp_path, monkeypatch, damage, problem):
    """An incomplete generation must neither vanish from the run (the gap the PR #114 review found) nor
    stop it (the #116 review)."""
    record, raw = _run_fake_b_szz(
        tmp_path, monkeypatch, ["raise AssertionError('B-SZZ ran on an incomplete output')"],
        before_run=lambda repos: damage(repos / "SZZ-0006/default/metadata"))
    assert (record["scenario_id"], record["status"], record["predictions"]) == ("SZZ-0006", "error", [])
    (error,) = record["errors"]
    assert problem in error and error.endswith("the generated output is incomplete")
    assert record["repository_id"]           # the manifest still says which generation it was
    assert raw["errors"] == record["errors"]


def test_a_pyszz_run_with_a_tool_error_exits_non_zero(monkeypatch):
    """Every record is written either way, but a run with errors must not exit as a clean one."""
    adapter = _load_pyszz_adapter(monkeypatch)
    assert adapter.exit_status([{"tool": "b-szz", "error_count": 0}, {"tool": "ag-szz", "error_count": 0}]) == 0
    assert adapter.exit_status([{"tool": "b-szz", "error_count": 0}, {"tool": "ag-szz", "error_count": 1}]) == 1


@pytest.mark.parametrize("logged, expected_error", [
    # what GitPython 3.1.62 raised inside MA-SZZ's blame, which MA-SZZ caught and logged
    (["try:",
      "    raise RuntimeError('--ignore-revs-file is not allowed')",
      "except Exception:",
      "    log.error(traceback.format_exc())"],
     "RuntimeError: --ignore-revs-file is not allowed"),
    (["log.error('unable to analyze commit: repo abc123')"], "unable to analyze commit: repo abc123"),
])
def test_an_exception_pyszz_caught_and_logged_fails_the_scenario(tmp_path, monkeypatch, logged, expected_error):
    """PySZZ catches its own exceptions, so a blame that raised looks like a blame that found nothing."""
    record, raw = _run_fake_b_szz(tmp_path, monkeypatch, [*logged, "return []"])
    assert record["status"] == "error" and record["predictions"] == []
    assert record["errors"] == [f"PySZZ logged an error and carried on: {expected_error}"]
    assert (tmp_path / "out/b-szz/raw/SZZ-0006.pyszz-errors.txt").exists()
    assert raw["pyszz_logged"] == []


@pytest.mark.parametrize("message", ["file not supported by srcML: retry.properties",
                                     "unable to parse comments for: retry.py"])
def test_a_file_whose_comments_pyszz_cannot_find_is_not_a_tool_error(tmp_path, monkeypatch, message):
    """PySZZ keeps such a file's comment lines in its own environment too: that is the tool's behaviour."""
    record, raw = _run_fake_b_szz(tmp_path, monkeypatch, [f"log.error({message!r})", "return []"])
    assert "status" not in record and record["predictions"] == []
    assert raw["pyszz_logged"] == [message]


def test_the_comment_skipping_variants_refuse_to_run_without_srcml(tmp_path, monkeypatch, capsys):
    adapter = _load_pyszz_adapter(monkeypatch)
    monkeypatch.setattr(adapter.shutil, "which", lambda name: None)
    code = adapter.main(["--tool-root", str(tmp_path), "--generated-root", str(tmp_path),
                         "--output-root", str(tmp_path / "out"), "--tools", "b-szz", "ag-szz", "r-szz"])
    assert code == 2
    assert "ag-szz, r-szz skip comment lines" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_the_adapter_refuses_to_run_without_the_libraries_pyszz_imports(tmp_path, monkeypatch, capsys):
    """Its own stand-in for them changes PySZZ's answers, so it is used only when asked for (--compat-layer)."""
    adapter = _load_pyszz_adapter(monkeypatch)
    monkeypatch.setitem(sys.modules, "pydriller", None)
    code = adapter.main(["--tool-root", str(tmp_path), "--generated-root", str(tmp_path),
                         "--output-root", str(tmp_path / "out"), "--tools", "b-szz"])
    assert code == 2
    assert "PySZZ imports PyDriller 1.x" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_a_run_fixes_the_hash_seed_l_szz_breaks_ties_with(monkeypatch):
    """L-SZZ keeps the first of equally large candidates in set order, which follows the hash seed."""
    adapter = _load_pyszz_adapter(monkeypatch)
    command, environment = adapter.fixed_hash_seed_command({"PATH": "/bin"}, ["adapter.py", "--tools", "l-szz"],
                                                           "/venv/bin/python")
    assert command == ["/venv/bin/python", "adapter.py", "--tools", "l-szz"]
    assert environment == {"PATH": "/bin", "PYTHONHASHSEED": "0"}
    assert adapter.fixed_hash_seed_command({"PYTHONHASHSEED": "random"}, ["adapter.py"], "/venv/bin/python") is None
    monkeypatch.setenv("PYTHONHASHSEED", "7")
    assert adapter.run_environment({})["PYTHONHASHSEED"] == "7"


def test_pyszz_runs_git_without_the_callers_configuration(monkeypatch):
    adapter = _load_pyszz_adapter(monkeypatch)
    caller = {"HOME": "/home/me", "PATH": "/bin", "LANG": "C.UTF-8", "GIT_DIR": "/elsewhere/.git",
              "GIT_CONFIG_GLOBAL": "/home/me/.gitconfig", "GIT_EXEC_PATH": "/usr/libexec/git-core"}
    assert adapter.isolated_git_environment(caller, "/empty") == {
        "HOME": "/empty", "XDG_CONFIG_HOME": "/empty", "PATH": "/bin", "LANG": "C.UTF-8",
        "GIT_EXEC_PATH": "/usr/libexec/git-core", "GIT_CONFIG_NOSYSTEM": "1", "GIT_ATTR_NOSYSTEM": "1"}


@pytest.mark.parametrize("module, expected", [
    (types.SimpleNamespace(GitRepository=object, RepositoryMining=object, ModificationType=object), True),
    (types.SimpleNamespace(Repository=object, Git=object, ModificationType=object), False),    # PyDriller 2
    (None, False),                                                                              # not installed
])
def test_the_adapter_uses_the_pydriller_1x_pyszz_imports_when_it_is_installed(monkeypatch, module, expected):
    adapter = _load_pyszz_adapter(monkeypatch)
    monkeypatch.setitem(sys.modules, "pydriller", module)
    assert adapter.pydriller_1x_available() is expected


def test_the_szz_unleashed_adapter_writes_an_error_record_for_an_unreadable_result(tmp_path):
    _, _, repos = _classic_fixture(tmp_path)
    result = repos / "SZZ-0006/default/szz-unleashed/run-depth3/results/fix_and_introducers_pairs.json"
    result.parent.mkdir(parents=True)
    result.write_text("{ not json", encoding="utf-8")
    out = tmp_path / "predictions.jsonl"
    completed = subprocess.run([sys.executable, str(ROOT / "tools/adapters/szz_unleashed_to_predictions.py"),
                                "--generated-root", str(repos), "--out", str(out)], capture_output=True, text=True)
    assert completed.returncode == 1
    record = json.loads(out.read_text(encoding="utf-8"))
    assert (record["scenario_id"], record["status"], record["predictions"]) == ("SZZ-0006", "error", [])
    assert "Invalid JSON" in record["errors"][0]


FAKE_JAVA = """\
import json, os, sys
args = sys.argv[1:]
if args == ["-version"]:
    print('java version "fake"', file=sys.stderr)
    sys.exit(0)
with open(os.environ["FAKE_JAVA_LOG"], "w") as log:
    json.dump({"args": args, "HOME": os.environ.get("HOME"), "GIT_DIR": os.environ.get("GIT_DIR")}, log)
issues = json.load(open(args[args.index("-i") + 1]))
if os.environ["FAKE_JAVA_MODE"] == "exit":
    sys.exit(3)
if os.environ["FAKE_JAVA_MODE"] == "trace":
    print("java.text.ParseException: Unparseable date: x")
    print("\\tat heuristics.SimpleBugIntroducerFinder.isWithinTimeframe(SimpleBugIntroducerFinder.java:80)")
os.makedirs("results", exist_ok=True)
pairs = [[issue["hash"], os.environ["FAKE_JAVA_BIC"]] for issue in issues.values()]
json.dump(pairs + pairs, open("results/fix_and_introducers_pairs.json", "w"))
"""


def _run_fake_szz_unleashed(tmp_path, mode, before_run=None):
    """Run the SZZ Unleashed adapter with --jar on SZZ-0006, with a stand-in for java that answers c1.

    ``before_run`` may damage the generated output first. The java log is None when java never ran.
    """
    _, _, repos = _classic_fixture(tmp_path)
    hashes = json.loads((repos / "SZZ-0006/default/metadata/commit-map.json").read_text(encoding="utf-8"))
    if before_run is not None:
        before_run(repos)
    java = tmp_path / "fake-java"
    java.write_text(f"#!{sys.executable}\n{FAKE_JAVA}", encoding="utf-8")
    java.chmod(0o755)
    jar = tmp_path / "szz_find_bug_introducers.jar"
    jar.write_bytes(b"not a jar")
    log = tmp_path / "java-log.json"
    env = {**os.environ, "FAKE_JAVA_MODE": mode, "FAKE_JAVA_LOG": str(log), "FAKE_JAVA_BIC": hashes["c1"]["hash"],
           "GIT_DIR": str(tmp_path / "elsewhere.git")}
    out = tmp_path / "predictions.jsonl"
    completed = subprocess.run([sys.executable, str(ROOT / "tools/adapters/szz_unleashed_to_predictions.py"),
                                "--jar", str(jar), "--java", str(java), "--generated-root", str(repos),
                                "--out", str(out)], capture_output=True, text=True, env=env)
    record = json.loads(out.read_text(encoding="utf-8"))
    java_log = json.loads(log.read_text(encoding="utf-8")) if log.exists() else None
    return completed, record, hashes, java_log, repos


@pytest.mark.skipif(os.name == "nt", reason="the stand-in for java is a script run through its shebang line")
def test_the_szz_unleashed_adapter_runs_the_jar_on_every_generated_repository(tmp_path):
    completed, record, hashes, java_log, repos = _run_fake_szz_unleashed(tmp_path, "ok")
    assert completed.returncode == 0, completed.stderr
    # one prediction per pair, however often SZZ Unleashed repeats it, with the logical ids
    assert record["predictions"] == [{
        "fix_commit": hashes["c2"]["hash"], "inducing_commit": hashes["c1"]["hash"], "tool": "szz-unleashed",
        "raw_file": "SZZ-0006/default/szz-unleashed/run-depth3/results/fix_and_introducers_pairs.json",
        "fix_commit_id": "c2", "inducing_commit_id": "c1"}]
    assert "status" not in record and record["repository_id"]
    # SZZ Unleashed's own default depth; JGit and git kept away from the caller's configuration
    args = java_log["args"]
    assert args[args.index("-d") + 1] == "3"
    assert args[0] == f"-Duser.home={java_log['HOME']}" and java_log["GIT_DIR"] is None
    # the issue counts as reported when it was fixed, so the timeframe filter keeps every older candidate
    issue_list = repos / "SZZ-0006/default/szz-unleashed/run-depth3/issue_list.json"
    (issue,) = json.loads(issue_list.read_text(encoding="utf-8")).values()
    assert issue["hash"] == hashes["c2"]["hash"]
    assert issue["creationdate"] == issue["resolutiondate"] == issue["commitdate"]
    assert issue["creationdate"] == git(repos / "SZZ-0006/default/repo", "log", "-1", "--format=%ci", issue["hash"])
    assert json.loads((tmp_path / "szz-unleashed-run.json").read_text(encoding="utf-8"))["depth"] == 3


@pytest.mark.skipif(os.name == "nt", reason="the stand-in for java is a script run through its shebang line")
@pytest.mark.parametrize("mode, expected", [
    ("exit", "SZZ Unleashed exited with status 3"),
    # it prints an exception and carries on, so the run exits 0 with an answer the exception cut short
    ("trace", "SZZ Unleashed printed a stack trace and carried on: java.text.ParseException"),
])
def test_a_failed_szz_unleashed_run_is_a_tool_error(tmp_path, mode, expected):
    completed, record, _, _, _ = _run_fake_szz_unleashed(tmp_path, mode)
    assert completed.returncode == 1
    assert (record["status"], record["predictions"]) == ("error", [])
    assert expected in record["errors"]


@pytest.mark.skipif(os.name == "nt", reason="the stand-in for java is a script run through its shebang line")
@pytest.mark.parametrize("damage, problem", [
    (lambda metadata: (metadata / "commit-map.json").unlink(), "commit-map.json is missing"),
    (lambda metadata: (metadata / "commit-map.json").write_text("{ not json", encoding="utf-8"),
     "commit-map.json cannot be read (JSONDecodeError"),
    # valid JSON, but no commit map
    (lambda metadata: (metadata / "commit-map.json").write_text("[]", encoding="utf-8"),
     "commit-map.json holds an array, not a JSON object"),
    (lambda metadata: (metadata / "scenario.yml").write_text("bugs: [\n", encoding="utf-8"),
     "scenario.yml cannot be read (ParserError"),
])
def test_a_generated_output_szz_unleashed_cannot_run_on_is_a_tool_error_not_left_out(tmp_path, damage, problem):
    """An incomplete generation must neither read as a successful run with nothing to score (PR #114
    review) nor stop the run (the gap the PR #116 review found in the PySZZ adapter)."""
    completed, record, _, java_log, _ = _run_fake_szz_unleashed(
        tmp_path, "ok", before_run=lambda repos: damage(repos / "SZZ-0006/default/metadata"))
    assert completed.returncode == 1, completed.stderr
    assert (record["scenario_id"], record["status"], record["predictions"]) == ("SZZ-0006", "error", [])
    (error,) = record["errors"]
    assert problem in error and error.endswith("the generated output is incomplete")
    assert java_log is None      # SZZ Unleashed never ran on it
    summary = json.loads((tmp_path / "szz-unleashed-run.json").read_text(encoding="utf-8"))
    assert (summary["scenario_count"], summary["error_count"]) == (1, 1)


def test_converting_a_result_leaves_out_the_logical_ids_a_commit_map_that_is_no_json_object_cannot_give(tmp_path):
    """Without --jar the logical ids are extras, left out as for a commit map that cannot be read."""
    _, _, repos = _classic_fixture(tmp_path)
    metadata = repos / "SZZ-0006/default/metadata"
    hashes = json.loads((metadata / "commit-map.json").read_text(encoding="utf-8"))
    result = repos / "SZZ-0006/default/szz-unleashed/run-depth3/results/fix_and_introducers_pairs.json"
    result.parent.mkdir(parents=True)
    result.write_text(json.dumps([[hashes["c2"]["hash"], hashes["c1"]["hash"]]]), encoding="utf-8")
    (metadata / "commit-map.json").write_text("[]", encoding="utf-8")
    out = tmp_path / "predictions.jsonl"
    completed = subprocess.run([sys.executable, str(ROOT / "tools/adapters/szz_unleashed_to_predictions.py"),
                                "--generated-root", str(repos), "--out", str(out)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    (prediction,) = json.loads(out.read_text(encoding="utf-8"))["predictions"]
    assert (prediction["fix_commit"], prediction["inducing_commit"]) == (hashes["c2"]["hash"], hashes["c1"]["hash"])
    assert "fix_commit_id" not in prediction and "inducing_commit_id" not in prediction


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
