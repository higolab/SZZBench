"""Regression tests for the PR #27 review follow-up.

1. A scenario that declares ``expect_no_bic: true`` with an empty
   ``bug_introducing_commits`` list must pass validation, generate, verify and
   evaluate through the normal workflow.
2. Allowances (``acceptable_related`` etc.) are ignored when ``expect_no_bic``
   is effective, so the false-positive accounting agrees with the FAIL status.
3. Oracle-related result notes are visible in the Markdown report and are
   promoted to report warnings (which the CLI prints), except the note that an
   oracle section is not read: that one is information (issue #126).
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
    schema_version: graph-1.0
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


def _szzg_0116_before_issue_118(tmp_path: Path) -> dict[str, Path]:
    """SZZG-0116 as it was until issue #118, with no commit_level, generated: the
    evaluator infers its required set, so it carries both kinds of oracle note."""
    advanced_root = tmp_path / "advanced-scenarios"
    generated_root = tmp_path / "generated-input-repos"
    source = REPO_ROOT / "advanced-scenarios" / "SZZG-0116" / "scenario.graph.yml"
    target = advanced_root / "SZZG-0116" / "scenario.graph.yml"
    target.parent.mkdir(parents=True)
    declared = "  commit_level:\n    evaluation_policy: exact_set\n    required:\n    - c1\n"
    text = source.read_text(encoding="utf-8")
    assert text.count(declared) == 1
    target.write_text(text.replace(declared, ""), encoding="utf-8")
    generated = _run_cli("generate-graph", str(target), "--out", str(generated_root / "SZZG-0116" / "default"), "--force", "--no-verify")
    assert generated.returncode == 0, generated.stdout + generated.stderr
    scenarios_root = tmp_path / "scenarios"
    scenarios_root.mkdir()
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(json.dumps({"scenario_id": "SZZG-0116", "predictions": [{"inducing_commit": "c1"}]}) + "\n", encoding="utf-8")
    return {"predictions": predictions, "generated_root": generated_root, "scenarios_root": scenarios_root,
            "advanced_scenarios_root": advanced_root}


INFERRED = "SZZG-0116: commit_level.required is missing or empty; required BICs inferred"
UNREAD = ("SZZG-0116: expected_szz also declares entity_level, line_level; these sections are not used by "
          "commit-level evaluation.")


def _section(markdown: str, heading: str) -> str:
    return markdown.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_oracle_notes_are_rendered_and_split_into_warnings_and_information(tmp_path):
    layout = _szzg_0116_before_issue_118(tmp_path)
    report = evaluate_predictions(layout["predictions"], generated_root=layout["generated_root"],
                                  scenarios_root=layout["scenarios_root"],
                                  advanced_scenarios_root=layout["advanced_scenarios_root"])
    [item] = report.scenarios
    assert item.status == "PASS"
    # both notes stay with the scenario, in the JSON and in the Markdown
    assert any("required BICs inferred" in note for note in item.result_notes)
    assert any("not used by commit-level evaluation" in note for note in item.result_notes)
    markdown = report.to_markdown()
    assert INFERRED in _section(markdown, "Scenario notes") and UNREAD in _section(markdown, "Scenario notes")
    # an oracle the author can complete is a warning; a section the evaluator does not
    # read is information: nothing is wrong, but a PASS still carries the caveat (#126)
    scenario_warnings = [w for w in report.warnings if w.startswith("SZZG-0116: ")]
    assert len(scenario_warnings) == 1 and scenario_warnings[0].startswith(INFERRED)
    assert report.info == [UNREAD]
    assert report.to_dict()["info"] == [UNREAD] and UNREAD not in report.to_dict()["warnings"]
    assert INFERRED in _section(markdown, "Warnings") and UNREAD not in _section(markdown, "Warnings")
    assert _section(markdown, "Information").strip() == f"- {UNREAD}"


def test_evaluate_prints_an_unread_section_as_info_and_an_inferred_oracle_as_a_warning(tmp_path):
    layout = _szzg_0116_before_issue_118(tmp_path)
    completed = _run_cli("evaluate", "--predictions", str(layout["predictions"]),
                         "--generated-root", str(layout["generated_root"]),
                         "--scenarios-root", str(layout["scenarios_root"]),
                         "--advanced-scenarios-root", str(layout["advanced_scenarios_root"]))
    assert completed.returncode == 0, completed.stderr
    lines = completed.stderr.splitlines()
    assert f"[INFO] {UNREAD}" in lines
    assert any(line.startswith(f"[WARNING] {INFERRED}") for line in lines)
    assert not any(line.startswith("[WARNING]") and "not used by commit-level evaluation" in line for line in lines)


def _graph(commit_level=None, **expected) -> dict:
    data = {
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c1", "role": "direct"}]}],
        "expected_szz": {**({"commit_level": commit_level} if commit_level is not None else {}), **expected},
    }
    return data


def test_only_the_unread_section_note_is_information():
    from szzbench.evaluator import _commit_level_policy, _is_information_note

    cases = {
        # the actionable notes, which stay warnings
        "inferred": (_graph({"evaluation_policy": "exact_set"}), None),
        "nothing to infer": (dict(_graph({"evaluation_policy": "exact_set"}), bugs=[]), None),
        "unknown variant": (_graph({"evaluation_policy": "exact_set", "required": ["c1"]}), "nope"),
        "unsupported policy": (_graph({"evaluation_policy": "best_guess", "required": ["c1"]}), None),
        "ignored allowances": (_graph({"evaluation_policy": "exact_set", "expect_no_bic": True,
                                       "acceptable_related": ["c0"]}), None),
        "bad status_k": (_graph({"evaluation_policy": "top_k", "required": ["c1"], "status_k": 0}), None),
        # the one that is information
        "unread": (_graph({"evaluation_policy": "exact_set", "required": ["c1"]}, line_level={"available": False}), None),
    }
    classified = {}
    for name, (data, variant) in cases.items():
        notes = _commit_level_policy(data, "advanced-scenarios", variant).notes
        assert len(notes) == 1, (name, notes)
        classified[name] = _is_information_note(notes[0])
    assert [name for name, info in classified.items() if info] == ["unread"]


def test_no_shipped_scenario_warns_at_evaluation_time():
    """The reproduction of #126: a run over the shipped suite prints no oracle warning."""
    from szzbench.evaluator import _commit_level_policy, _is_information_note
    from szzbench.scenario import load_yaml

    warned = []
    for suite, name in (("scenarios", "scenario.yml"), ("advanced-scenarios", "scenario.graph.yml")):
        for path in sorted((REPO_ROOT / suite).glob(f"*/{name}")):
            data, _ = load_yaml(path)
            warned += [(path.parent.name, note) for note in _commit_level_policy(data, suite, None).notes
                       if not _is_information_note(note)]
    assert warned == []


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
