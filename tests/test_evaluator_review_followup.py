"""Regression tests for the PR #27 review follow-up.

1. A scenario that declares ``expect_no_bic: true`` with an empty
   ``bug_introducing_commits`` list must pass validation, generate, verify and
   evaluate through the normal workflow.
2. Allowances (``acceptable_related`` etc.) are ignored when ``expect_no_bic``
   is effective, so the false-positive accounting agrees with the FAIL status.
3. Oracle-related result notes are visible in the Markdown report and are
   promoted to report warnings (which the CLI prints).
"""

from pathlib import Path
import json
import subprocess
import sys
import textwrap

from szzbench.evaluator import Prediction, evaluate_predictions, evaluate_scenario
from szzbench.graph_validator import validate_graph_scenario_file

REPO_ROOT = Path(__file__).resolve().parents[1]

NO_BIC_SCENARIO = textwrap.dedent(
    """\
    schema_version: graph-0.1-draft
    meta:
      id: SZZG-9400
      title: Timeout raised after an external service changed its limits
      slug: external-cause-no-bic
      description: The fix reacts to an external change; no commit in this repository induced the fault.
      category: "Evaluation policy variants"
      category_code: "G9"
      factors:
      - expect-no-bic
      - external-cause
      difficulty: advanced
      status: draft
    repository:
      name: SZZG-9400-external-cause-no-bic
      default_branch: main
      language: java
      build_system: none
      source_root: src/main/java
    graph:
      model: commit_dag
    commits:
    - id: c0
      branch: main
      parents: []
      message: Add the upstream client with its default timeout
      role: initial
      operations:
      - type: write_file
        path: src/main/java/example/UpstreamClient.java
        content: |
          package example;

          public class UpstreamClient {
              public int timeoutSeconds() {
                  return 30;
              }
          }
    - id: c1
      branch: main
      parents:
      - c0
      message: Raise the upstream timeout after the provider changed its limits
      role: bug_fixing
      operations:
      - type: replace
        path: src/main/java/example/UpstreamClient.java
        old: return 30;
        new: return 60;
    bugs:
    - id: B001
      title: Requests time out after the provider changed its limits
      bug_introducing_commits: []
      bug_fixing_commits:
      - commit: c1
        role: complete_fix
      fixes:
      - id: X001
        commit: c1
        file: src/main/java/example/UpstreamClient.java
        statement: return 60;
        fix_type: line_modification
    expected_szz:
      commit_level:
        evaluation_policy: exact_set
        expect_no_bic: true
        required: []
    """
)


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "szzbench.cli", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _write_no_bic_scenario(tmp_path: Path) -> tuple[Path, Path, Path]:
    advanced_root = tmp_path / "advanced-scenarios"
    scenario_path = advanced_root / "SZZG-9400" / "scenario.graph.yml"
    scenario_path.parent.mkdir(parents=True)
    scenario_path.write_text(NO_BIC_SCENARIO, encoding="utf-8")
    generated_root = tmp_path / "generated-input-repos"
    return advanced_root, scenario_path, generated_root


def test_expect_no_bic_scenario_passes_validation_with_an_info_finding(tmp_path):
    _, scenario_path, _ = _write_no_bic_scenario(tmp_path)
    _, result = validate_graph_scenario_file(scenario_path, simulate=True, strict_paths=True)
    codes = [finding.code for finding in result.findings]
    assert not result.has_errors(), codes
    assert "GE084" not in codes
    assert "GI086" in codes


def test_expect_no_bic_without_declaration_is_still_rejected(tmp_path):
    _, scenario_path, _ = _write_no_bic_scenario(tmp_path)
    scenario_path.write_text(NO_BIC_SCENARIO.replace("    expect_no_bic: true\n", ""), encoding="utf-8")
    _, result = validate_graph_scenario_file(scenario_path, simulate=True, strict_paths=True)
    assert "GE084" in [finding.code for finding in result.findings]


def test_expect_no_bic_scenario_validates_generates_and_evaluates(tmp_path):
    advanced_root, scenario_path, generated_root = _write_no_bic_scenario(tmp_path)
    out = generated_root / "SZZG-9400" / "default"

    validated = _run_cli("validate-graph", "--simulate", "--strict-paths", str(scenario_path))
    assert validated.returncode == 0, validated.stdout + validated.stderr
    generated = _run_cli("generate-graph", str(scenario_path), "--out", str(out), "--force")
    assert generated.returncode == 0, generated.stdout + generated.stderr
    assert (out / "repo" / ".git").exists()
    assert (out / "metadata" / "verify-result.json").exists()

    scenarios_root = tmp_path / "scenarios"
    scenarios_root.mkdir()

    empty = tmp_path / "empty.jsonl"
    empty.write_text(json.dumps({"scenario_id": "SZZG-9400", "predictions": []}) + "\n", encoding="utf-8")
    report = evaluate_predictions(empty, generated_root=generated_root, scenarios_root=scenarios_root, advanced_scenarios_root=advanced_root)
    assert report.errors == []
    [item] = report.scenarios
    assert item.status == "PASS"
    assert item.expect_no_bic is True
    assert item.expected_bics == []
    assert item.fix_shape == {"c1": "modifies"}

    predicted = tmp_path / "predicted.jsonl"
    predicted.write_text(json.dumps({"scenario_id": "SZZG-9400", "predictions": [{"inducing_commit": "c0"}]}) + "\n", encoding="utf-8")
    report = evaluate_predictions(predicted, generated_root=generated_root, scenarios_root=scenarios_root, advanced_scenarios_root=advanced_root)
    [item] = report.scenarios
    assert item.status == "FAIL"
    assert item.false_positives == ["c0"]
    assert item.hard_false_positives == ["c0"]


def test_expect_no_bic_ignores_allowances_and_counts_every_prediction_as_false_positive(tmp_path):
    scenario = {
        "meta": {"category": "no-bic"},
        "bugs": [{"id": "B001", "bug_introducing_commits": [], "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}]}],
        "expected_szz": {
            "commit_level": {
                "evaluation_policy": "exact_set",
                "expect_no_bic": True,
                "required": [],
                "acceptable_related": ["c1"],
                "related_origins": ["c0"],
            }
        },
    }
    commit_map = {"c0": {"hash": "0" * 40}, "c1": {"hash": "1" * 40}, "c2": {"hash": "2" * 40}}
    result = evaluate_scenario(
        "SZZG-test",
        scenario,
        tmp_path / "scenario.graph.yml",
        "advanced-scenarios",
        commit_map,
        [Prediction(scenario_id="SZZG-test", inducing_commit="c1"), Prediction(scenario_id="SZZG-test", inducing_commit="c0")],
    )
    assert result.status == "FAIL"
    assert result.false_positives == ["c0", "c1"]
    assert result.hard_false_positives == ["c0", "c1"]
    assert result.allowed_false_positives == []
    assert result.related_origin_hits == []
    assert result.acceptable_related_hits == []
    assert any("acceptable_related, related_origins ignored" in note for note in result.result_notes)


def test_oracle_notes_are_rendered_in_markdown_and_promoted_to_warnings(tmp_path):
    advanced_root = tmp_path / "advanced-scenarios"
    generated_root = tmp_path / "generated-input-repos"
    source = REPO_ROOT / "advanced-scenarios" / "SZZG-0116" / "scenario.graph.yml"
    target = advanced_root / "SZZG-0116" / "scenario.graph.yml"
    target.parent.mkdir(parents=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    generated = _run_cli("generate-graph", str(target), "--out", str(generated_root / "SZZG-0116" / "default"), "--force", "--no-verify")
    assert generated.returncode == 0, generated.stdout + generated.stderr
    scenarios_root = tmp_path / "scenarios"
    scenarios_root.mkdir()

    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(json.dumps({"scenario_id": "SZZG-0116", "predictions": [{"inducing_commit": "c1"}]}) + "\n", encoding="utf-8")
    report = evaluate_predictions(predictions, generated_root=generated_root, scenarios_root=scenarios_root, advanced_scenarios_root=advanced_root)

    [item] = report.scenarios
    assert item.status == "PASS"
    assert any("required BICs inferred" in note for note in item.result_notes)
    assert any("not used by commit-level evaluation" in note for note in item.result_notes)
    # promoted to report warnings (printed by the CLI)
    assert any(w.startswith("SZZG-0116: ") and "required BICs inferred" in w for w in report.warnings)
    assert any(w.startswith("SZZG-0116: ") and "not used by commit-level evaluation" in w for w in report.warnings)
    # and rendered in the human-readable report
    markdown = report.to_markdown()
    assert "## Scenario notes" in markdown
    assert "- SZZG-0116: commit_level.required is missing or empty" in markdown
    assert "## Warnings" in markdown


# ---------------------------------------------------------------------------
# Prediction reference format (issue #8): what a tool may name a commit with
# ---------------------------------------------------------------------------


def test_reference_format_restricts_how_predictions_name_commits():
    from szzbench.evaluator import REFERENCE_FORMATS, _normalize_commit_ref

    commit_map = {"c0": {"hash": "a" * 40}, "c1": {"hash": "b" * 40}}
    hash_to_id = {"a" * 40: "c0", "b" * 40: "c1"}
    logical, full, short = "c1", "b" * 40, "b" * 8

    assert REFERENCE_FORMATS == ("auto", "hash", "logical")

    # auto (the default) keeps accepting every form
    for ref in (logical, full, short):
        assert _normalize_commit_ref(ref, commit_map, hash_to_id) == "c1"

    # hash: only what a tool reading the repository can produce
    assert _normalize_commit_ref(logical, commit_map, hash_to_id, reference_format="hash") is None
    assert _normalize_commit_ref(full, commit_map, hash_to_id, reference_format="hash") == "c1"
    assert _normalize_commit_ref(short, commit_map, hash_to_id, reference_format="hash") == "c1"

    # logical: only scenario ids, for adapters and fixtures
    assert _normalize_commit_ref(logical, commit_map, hash_to_id, reference_format="logical") == "c1"
    assert _normalize_commit_ref(full, commit_map, hash_to_id, reference_format="logical") is None
    assert _normalize_commit_ref(short, commit_map, hash_to_id, reference_format="logical") is None

    try:
        _normalize_commit_ref(logical, commit_map, hash_to_id, reference_format="hashes")
    except ValueError as exc:
        assert "reference_format" in str(exc)
    else:  # pragma: no cover - the call above must raise
        raise AssertionError("an unknown reference_format must be rejected")
