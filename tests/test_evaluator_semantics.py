"""Evaluator semantics covered by GitHub issue #15.

These tests pin down the role vocabulary, the overall ``top_k`` status, the
missing-oracle fallback and ``expect_no_bic``, the ``known_distractors``
diagnostic, and the fix-shape classification.
"""

from pathlib import Path
import json
import subprocess
import sys
import textwrap

import pytest

from szzbench.evaluator import EvaluationReport, Prediction, classify_diff_text, evaluate_predictions, evaluate_scenario
from szzbench.graph_scenario import DIRECT_BIC_ROLES, graph_bic_entries, normalize_bic_role
from szzbench.graph_verifier import verify_graph_generated_repo

REPO_ROOT = Path(__file__).resolve().parents[1]

COMMIT_MAP = {"c0": {"hash": "0" * 40}, "c1": {"hash": "1" * 40}, "c2": {"hash": "2" * 40}, "c3": {"hash": "3" * 40}}


def _evaluate_graph(scenario, predictions, tmp_path, *, evaluation_variant=None, commit_map=COMMIT_MAP):
    return evaluate_scenario(
        "SZZG-test",
        scenario,
        tmp_path / "scenario.graph.yml",
        "advanced-scenarios",
        commit_map,
        [Prediction(scenario_id="SZZG-test", **kwargs) for kwargs in predictions],
        evaluation_variant=evaluation_variant,
    )


def _generate_graph_scenario(scenario_path: Path, out: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "generate-graph", str(scenario_path), "--out", str(out), "--force", "--no-verify"],
        check=True,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# --------------------------------------------------------------------------- #
# Task 1: role vocabulary
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (None, "direct"),
        ("", "direct"),
        ("direct", "direct"),
        ("direct_squash_bic", "direct"),
        ("merge_introducing", "direct"),
        ("bug_introducing", "direct"),
        ("DIRECT", "direct"),
        ("origin", "origin"),
        ("origin_bic", "origin"),
        ("old_origin_bic", "origin"),
        ("origin_bug_introducing", "origin"),
        ("reintroducing", "reintroducing"),
        ("direct_reintroduction", "reintroducing"),
        ("related_reintroducing", "reintroducing"),
        ("bug_reintroducing", "reintroducing"),
        ("contributing", "contributing"),
        ("contributing_bic", "contributing"),
        ("distractor", "other"),
        ("refactoring", "other"),
        (42, "other"),
    ],
)
def test_normalize_bic_role(role, expected):
    assert normalize_bic_role(role) == expected


def test_graph_bic_entries_filters_by_normalized_role():
    bug = {
        "bug_introducing_commits": [
            "c0",
            {"commit": "c1", "role": "merge_introducing"},
            {"commit": "c2", "role": "old_origin_bic"},
            {"commit": "c3", "role": "related_reintroducing"},
        ]
    }
    assert [entry["commit"] for entry in graph_bic_entries(bug)] == ["c0", "c1", "c2", "c3"]
    assert [entry["commit"] for entry in graph_bic_entries(bug, roles=DIRECT_BIC_ROLES)] == ["c0", "c1", "c3"]
    assert [entry["commit"] for entry in graph_bic_entries(bug, roles={"origin"})] == ["c2"]


def test_inferred_required_set_recognises_merge_introducing_role(tmp_path):
    scenario = {
        "meta": {"category": "roles"},
        "bugs": [
            {
                "id": "B001",
                "bug_introducing_commits": [
                    {"commit": "c3", "role": "merge_introducing"},
                    {"commit": "c1", "role": "origin_bic"},
                ],
            }
        ],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set"}},
    }
    result = _evaluate_graph(scenario, [{"inducing_commit": "c3"}], tmp_path)
    assert result.expected_bics == ["c3"]
    assert result.status == "PASS"


def test_verifier_basic_blame_accepts_merge_introducing_role(tmp_path):
    scenario_path = REPO_ROOT / "advanced-scenarios" / "SZZG-0045" / "scenario.graph.yml"
    out = tmp_path / "generated"
    _generate_graph_scenario(scenario_path, out)

    result = verify_graph_generated_repo(out / "repo", scenario_path)

    codes = [finding.code for finding in result.findings]
    assert "GW703" not in codes
    assert "GI703" in codes


# --------------------------------------------------------------------------- #
# Task 2: overall top_k status
# --------------------------------------------------------------------------- #


def _top_k_scenario(commit_level_extra):
    return {
        "meta": {"category": "top-k"},
        "expected_szz": {"commit_level": {"evaluation_policy": "top_k", "required": ["c2"], **commit_level_extra}},
    }


RANK3_PREDICTIONS = [
    {"inducing_commit": "c0", "rank": 1},
    {"inducing_commit": "c1", "rank": 2},
    {"inducing_commit": "c2", "rank": 3},
]


def test_top_k_status_fails_when_relevant_commit_is_outside_k(tmp_path):
    result = _evaluate_graph(_top_k_scenario({"k_values": [1]}), RANK3_PREDICTIONS, tmp_path)
    assert result.status == "FAIL"
    assert result.top_k["best_rank"] == 3
    assert result.top_k["status_k"] == 1
    assert result.top_k["hit_at"] == {"1": False}


def test_top_k_status_passes_when_relevant_commit_is_within_k(tmp_path):
    result = _evaluate_graph(_top_k_scenario({"k_values": [3]}), RANK3_PREDICTIONS, tmp_path)
    assert result.status == "PASS"
    assert result.top_k["status_k"] == 3
    assert result.top_k["hit_at"] == {"3": True}


def test_top_k_explicit_status_k_overrides_largest_k(tmp_path):
    result = _evaluate_graph(_top_k_scenario({"k_values": [1, 3, 5], "status_k": 1}), RANK3_PREDICTIONS, tmp_path)
    assert result.status == "FAIL"
    assert result.top_k["status_k"] == 1
    assert result.top_k["hit_at"] == {"1": False, "3": True, "5": True}


def test_top_k_without_k_values_defaults_status_k_to_one(tmp_path):
    result = _evaluate_graph(_top_k_scenario({}), RANK3_PREDICTIONS, tmp_path)
    assert result.status == "FAIL"
    assert result.top_k["k_values"] == [1, 3, 5]
    assert result.top_k["status_k"] == 1
    assert _evaluate_graph(_top_k_scenario({}), [{"inducing_commit": "c2"}], tmp_path).status == "PASS"


def test_top_k_invalid_status_k_is_ignored_with_note(tmp_path):
    result = _evaluate_graph(_top_k_scenario({"k_values": [3], "status_k": 0}), RANK3_PREDICTIONS, tmp_path)
    assert result.status == "PASS"
    assert result.top_k["status_k"] == 3
    assert any("status_k must be a positive integer" in note for note in result.result_notes)


def test_top_k_miss_fails_and_is_rendered_in_markdown(tmp_path):
    result = _evaluate_graph(_top_k_scenario({"k_values": [3]}), [{"inducing_commit": "c0", "rank": 1}], tmp_path)
    assert result.status == "FAIL"
    assert result.top_k["best_rank"] is None
    markdown = EvaluationReport([result]).to_markdown()
    assert "| miss (k=3) |" in markdown


# --------------------------------------------------------------------------- #
# Task 3: missing commit-level oracle and expect_no_bic
# --------------------------------------------------------------------------- #

BUGS_WITH_C1 = [{"id": "B001", "bug_introducing_commits": [{"commit": "c1", "role": "direct"}], "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}]}]


def test_missing_commit_level_falls_back_with_explicit_note(tmp_path):
    scenario = {
        "meta": {"category": "fallback"},
        "bugs": BUGS_WITH_C1,
        "expected_szz": {"line_level": {"available": False}, "entity_level": {"available": True}},
    }
    result = _evaluate_graph(scenario, [], tmp_path)
    assert result.expected_bics == ["c1"]
    assert result.status == "FAIL"
    assert result.false_negatives == ["c1"]
    assert result.expect_no_bic is False
    assert any("required BICs inferred from bugs[].bug_introducing_commits" in note and "c1" in note for note in result.result_notes)
    assert any("entity_level, line_level" in note and "not used by commit-level evaluation" in note for note in result.result_notes)


def test_missing_commit_level_without_inferable_bics_notes_empty_required(tmp_path):
    scenario = {
        "meta": {"category": "fallback"},
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "origin"}]}],
        "expected_szz": {},
    }
    result = _evaluate_graph(scenario, [], tmp_path)
    assert result.expected_bics == []
    assert result.status == "PASS"
    assert any("no BICs could be inferred" in note and "expect_no_bic" in note for note in result.result_notes)


def test_expect_no_bic_passes_only_without_predictions(tmp_path):
    scenario = {
        "meta": {"category": "no-bic"},
        "bugs": BUGS_WITH_C1,
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "expect_no_bic": True}},
    }
    empty = _evaluate_graph(scenario, [], tmp_path)
    assert empty.status == "PASS"
    assert empty.expected_bics == []
    assert empty.expect_no_bic is True
    assert empty.to_dict()["expect_no_bic"] is True
    assert not any("inferred" in note for note in empty.result_notes)

    predicted = _evaluate_graph(scenario, [{"inducing_commit": "c1"}], tmp_path)
    assert predicted.status == "FAIL"
    assert predicted.false_positives == ["c1"]
    assert predicted.expect_no_bic is True

    unknown = _evaluate_graph(scenario, [{"inducing_commit": "deadbeefcafe"}], tmp_path)
    assert unknown.status == "FAIL"
    assert unknown.unknown_predictions == ["deadbeefcafe"]


def test_expect_no_bic_inside_variant(tmp_path):
    scenario = {
        "meta": {"category": "no-bic"},
        "bugs": BUGS_WITH_C1,
        "expected_szz": {
            "commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]},
            "evaluation_variants": [
                {"name": "external-cause", "commit_level": {"expect_no_bic": True}},
            ],
        },
    }
    default = _evaluate_graph(scenario, [], tmp_path)
    assert default.status == "FAIL"
    assert default.expect_no_bic is False

    variant = _evaluate_graph(scenario, [], tmp_path, evaluation_variant="external-cause")
    assert variant.status == "PASS"
    assert variant.expect_no_bic is True
    assert variant.expected_bics == []
    assert variant.evaluation_policy == "exact_set"


def test_expect_no_bic_with_required_is_ignored_with_note(tmp_path):
    scenario = {
        "meta": {"category": "no-bic"},
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"], "expect_no_bic": True}},
    }
    result = _evaluate_graph(scenario, [{"inducing_commit": "c1"}], tmp_path)
    assert result.status == "PASS"
    assert result.expect_no_bic is False
    assert any("ignoring expect_no_bic" in note for note in result.result_notes)


# --------------------------------------------------------------------------- #
# Task 4: known_distractors diagnostic
# --------------------------------------------------------------------------- #


def _classic_scenario_dict(known_distractors):
    commit_level = {"true_positives": ["c1"], "false_positives_allowed": []}
    if known_distractors is not None:
        commit_level["known_distractors"] = known_distractors
    return {
        "meta": {"category": "distractors"},
        "bugs": [
            {
                "id": "B001",
                "bug_fixing_commit": "c3",
                "bug_introducing_commits": ["c1"],
                "expected_szz": {"commit_level": commit_level},
            }
        ],
    }


def _evaluate_classic(scenario, predictions, tmp_path):
    return evaluate_scenario(
        "SZZ-test",
        scenario,
        tmp_path / "scenario.yml",
        "scenarios",
        COMMIT_MAP,
        [Prediction(scenario_id="SZZ-test", inducing_commit=commit) for commit in predictions],
    )


def test_known_distractor_hits_are_reported_without_changing_status(tmp_path):
    with_distractors = _evaluate_classic(_classic_scenario_dict(["c2"]), ["c1", "c2"], tmp_path)
    without = _evaluate_classic(_classic_scenario_dict(None), ["c1", "c2"], tmp_path)

    assert with_distractors.known_distractor_hits == ["c2"]
    assert with_distractors.to_dict()["known_distractor_hits"] == ["c2"]
    assert without.known_distractor_hits == []
    assert with_distractors.status == without.status == "FAIL"
    assert with_distractors.false_positives == without.false_positives == ["c2"]

    clean = _evaluate_classic(_classic_scenario_dict(["c2"]), ["c1"], tmp_path)
    assert clean.status == "PASS"
    assert clean.known_distractor_hits == []


def test_known_distractors_in_graph_commit_level(tmp_path):
    scenario = {
        "meta": {"category": "distractors"},
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"], "known_distractors": ["c0", "c2"]}},
    }
    result = _evaluate_graph(scenario, [{"inducing_commit": "c2"}, {"inducing_commit": "c1"}], tmp_path)
    assert result.status == "FAIL"
    assert result.known_distractor_hits == ["c2"]


def test_known_distractor_hits_in_summary_and_markdown(tmp_path):
    report = EvaluationReport(
        [
            _evaluate_classic(_classic_scenario_dict(["c2"]), ["c1", "c2"], tmp_path),
            _evaluate_classic(_classic_scenario_dict(["c2"]), ["c1"], tmp_path),
        ]
    )
    assert report.summary()["known_distractor_hits"] == 1
    markdown = report.to_markdown()
    assert "- Known distractor hits: 1" in markdown
    assert "| Distractor hits |" in markdown


# --------------------------------------------------------------------------- #
# Task 5: fix-shape classification
# --------------------------------------------------------------------------- #


def test_classify_diff_text():
    assert classify_diff_text("") == "empty_first_parent"
    assert classify_diff_text("\n") == "empty_first_parent"
    new_file = textwrap.dedent(
        """\
        diff --git a/src/guard.txt b/src/guard.txt
        new file mode 100644
        index 0000000..1111111
        --- /dev/null
        +++ b/src/guard.txt
        @@ -0,0 +1 @@
        +guard=on
        """
    )
    assert classify_diff_text(new_file) == "addition_only"
    modification = textwrap.dedent(
        """\
        diff --git a/src/example.txt b/src/example.txt
        index 1111111..2222222 100644
        --- a/src/example.txt
        +++ b/src/example.txt
        @@ -1 +1 @@
        -state=buggy
        +state=fixed
        """
    )
    assert classify_diff_text(modification) == "modifies"
    deleted_line_starting_with_dashes = textwrap.dedent(
        """\
        diff --git a/src/example.txt b/src/example.txt
        index 1111111..2222222 100644
        --- a/src/example.txt
        +++ b/src/example.txt
        @@ -1 +0,0 @@
        --- separator
        """
    )
    assert classify_diff_text(deleted_line_starting_with_dashes) == "modifies"


def _write_classic_scenario(path: Path, scenario_id: str, *, addition_only_fix: bool) -> None:
    if addition_only_fix:
        fix_operation = textwrap.dedent(
            """\
                  - type: "write_file"
                    path: "src/guard.txt"
                    content: |
                      guard=on
            """
        )
        fix_file, fix_statement = "src/guard.txt", "guard=on"
    else:
        fix_operation = textwrap.dedent(
            """\
                  - type: "replace"
                    path: "src/example.txt"
                    old: "state=buggy"
                    new: "state=fixed"
            """
        )
        fix_file, fix_statement = "src/example.txt", "state=fixed"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        textwrap.dedent(
            f"""\
            schema_version: "1.0"
            meta:
              id: "{scenario_id}"
              title: "Fix shape smoke"
              category: "smoke"
              factors: []
            repository:
              name: "{scenario_id.lower()}-fix-shape-smoke"
              default_branch: "main"
              language: "text"
            commits:
              - id: "c0"
                message: "Introduce text bug"
                role: "bug_introducing"
                operations:
                  - type: "write_file"
                    path: "src/example.txt"
                    content: |
                      state=buggy
              - id: "c1"
                message: "Fix text bug"
                role: "bug_fixing"
                operations:
            """
        )
        + textwrap.indent(fix_operation, "    ")
        + textwrap.dedent(
            f"""\
            bugs:
              - id: "B001"
                bug_fixing_commit: "c1"
                bug_introducing_commits:
                  - "c0"
                fault:
                  commit: "c0"
                  file: "src/example.txt"
                  statement: "state=buggy"
                  change_type: "line_modification"
                fix:
                  commit: "c1"
                  file: "{fix_file}"
                  statement: "{fix_statement}"
            """
        ),
        encoding="utf-8",
    )


def _generate_classic_scenario(scenario_path: Path, out: Path) -> None:
    subprocess.run(
        [sys.executable, "-m", "szzbench.cli", "generate", str(scenario_path), "--out", str(out), "--force", "--no-verify"],
        check=True,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_fix_shape_is_classified_from_generated_repositories(tmp_path):
    scenarios_root = tmp_path / "scenarios"
    advanced_scenarios_root = tmp_path / "advanced-scenarios"
    generated_root = tmp_path / "generated-input-repos"
    _write_classic_scenario(scenarios_root / "SZZ-9300" / "scenario.yml", "SZZ-9300", addition_only_fix=False)
    _write_classic_scenario(scenarios_root / "SZZ-9301" / "scenario.yml", "SZZ-9301", addition_only_fix=True)
    for scenario_id in ["SZZ-9300", "SZZ-9301"]:
        _generate_classic_scenario(scenarios_root / scenario_id / "scenario.yml", generated_root / scenario_id / "default")
    merge_fix = REPO_ROOT / "advanced-scenarios" / "SZZG-0042" / "scenario.graph.yml"
    (advanced_scenarios_root / "SZZG-0042").mkdir(parents=True)
    (advanced_scenarios_root / "SZZG-0042" / "scenario.graph.yml").write_text(merge_fix.read_text(encoding="utf-8"), encoding="utf-8")
    _generate_graph_scenario(merge_fix, generated_root / "SZZG-0042" / "default")

    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(
        "\n".join(
            [
                json.dumps({"scenario_id": "SZZ-9300", "predictions": [{"inducing_commit": "c0"}]}),
                json.dumps({"scenario_id": "SZZ-9301", "predictions": [{"inducing_commit": "c0"}]}),
                json.dumps({"scenario_id": "SZZG-0042", "predictions": [{"inducing_commit": "c1"}]}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report = evaluate_predictions(
        predictions,
        generated_root=generated_root,
        scenarios_root=scenarios_root,
        advanced_scenarios_root=advanced_scenarios_root,
    )

    assert report.errors == []
    by_id = {item.scenario_id: item for item in report.scenarios}
    assert by_id["SZZ-9300"].fix_shape == {"c1": "modifies"}
    assert by_id["SZZ-9301"].fix_shape == {"c1": "addition_only"}
    assert by_id["SZZG-0042"].fix_shape == {"c3": "empty_first_parent"}
    assert all(item.status == "PASS" for item in report.scenarios)
    assert report.summary()["fix_shape_counts"] == {"empty_first_parent": 1, "addition_only": 1, "modifies": 1}
    markdown = report.to_markdown()
    assert "- Fix shapes (per BFC): empty_first_parent 1, addition_only 1, modifies 1" in markdown
    assert "| c3:empty_first_parent |" in markdown
    assert by_id["SZZG-0042"].to_dict()["fix_shape"] == {"c3": "empty_first_parent"}


def test_fix_shape_is_skipped_with_note_when_repository_is_missing(tmp_path):
    scenario = {"meta": {"category": "fix-shape"}, "bugs": BUGS_WITH_C1, "expected_szz": {"commit_level": {"required": ["c1"]}}}
    result = evaluate_scenario(
        "SZZG-test",
        scenario,
        tmp_path / "scenario.graph.yml",
        "advanced-scenarios",
        COMMIT_MAP,
        [Prediction(scenario_id="SZZG-test", inducing_commit="c1")],
        repo_dir=tmp_path / "missing" / "repo",
    )
    assert result.status == "PASS"
    assert result.fix_shape is None
    assert any("fix_shape not computed" in note and "not found" in note for note in result.result_notes)

    unit_level = _evaluate_graph(scenario, [{"inducing_commit": "c1"}], tmp_path)
    assert unit_level.fix_shape is None
    assert not any("fix_shape" in note for note in unit_level.result_notes)


# --------------------------------------------------------------------------- #
# Interface: logical ids, hashes, and unique hash prefixes are all accepted
# --------------------------------------------------------------------------- #


def test_predictions_accept_logical_ids_hashes_and_unique_prefixes(tmp_path):
    scenario = {"meta": {"category": "ids"}, "expected_szz": {"commit_level": {"required": ["c1", "c2", "c3"]}}}
    result = _evaluate_graph(
        scenario,
        [{"inducing_commit": "c1"}, {"inducing_commit": "2" * 40}, {"inducing_commit": "3333333"}],
        tmp_path,
    )
    assert result.status == "PASS"
    assert result.actual_bics == ["c1", "c2", "c3"]
