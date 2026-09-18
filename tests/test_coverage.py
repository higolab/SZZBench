"""Coverage report (#12): what each scenario contributes, measured.

The review's merge/delete list described scenarios that have all since been
rebuilt, so redundancy has to be derived from the current suite rather than
read off a list. These tests pin the dimensions the derivation uses.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from szzbench.coverage import SIGNATURE_FIELDS, format_report, run_coverage
from szzbench.graph_generator import generate_graph_repository

JAVA = ("package example;\npublic class Range {\n  public boolean contains(int v, int lo) {\n"
        "    return v %s lo;\n  }\n}\n")
PATH = "src/main/java/example/Range.java"
NOTE = "docs/note.md"


def _write(tmp_path: Path, scenario_id: str, commits, bugs, category="G1") -> None:
    data = {
        "schema_version": "graph-0.1-draft",
        "meta": {"id": scenario_id, "title": "coverage fixture", "category": "test",
                 "category_code": category, "factors": ["single-bic"]},
        "repository": {"name": scenario_id.lower(), "default_branch": "main",
                       "language": "java", "source_root": "src/main/java"},
        "graph": {"model": "commit_dag"},
        "commits": commits,
        "bugs": bugs,
    }
    directory = tmp_path / "advanced-scenarios" / scenario_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "scenario.graph.yml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    generate_graph_repository(directory / "scenario.graph.yml",
                              tmp_path / "repos" / scenario_id / "default", force=True)


def _linear(noise_touches_fault_file: bool):
    """c0 add, c1 BIC, c2 noise, c3 fix - the noise either touches the fault file or not."""
    noise_op = ({"type": "replace", "path": PATH, "old": "public class Range {",
                 "new": "public class Range {\n  // reviewed"}
                if noise_touches_fault_file
                else {"type": "write_file", "path": NOTE, "content": "release note\n"})
    return [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the range check", "role": "initial",
         "operations": [{"type": "write_file", "path": PATH, "content": JAVA % ">="}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "require values above the minimum",
         "role": "bug_introducing",
         "operations": [{"type": "replace", "path": PATH, "old": "return v >= lo;", "new": "return v > lo;"}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "tidy up", "role": "intermediate",
         "operations": [noise_op]},
        {"id": "c3", "branch": "main", "parents": ["c2"], "message": "accept the lower bound again",
         "role": "bug_fixing",
         "operations": [{"type": "replace", "path": PATH, "old": "return v > lo;", "new": "return v >= lo;"}]},
    ]


def _bugs(required):
    return [{"id": "B001",
             "bug_introducing_commits": [{"commit": c, "role": "direct"} for c in required],
             "bug_fixing_commits": [{"commit": "c3", "role": "complete_fix"}],
             "faults": [{"id": "F001", "commit": required[0], "file": PATH,
                         "statement": "return v > lo;", "change_type": "line_modification"}],
             "fixes": [{"id": "X001", "commit": "c3", "file": PATH,
                        "statement": "return v >= lo;", "fix_type": "line_modification"}],
             "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": required}}}]


def _run(tmp_path):
    return run_coverage(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                        advanced_scenarios_root=tmp_path / "advanced-scenarios")


def test_shapes_measure_depth_and_candidate_density(tmp_path):
    _write(tmp_path, "SZZG-9100", _linear(noise_touches_fault_file=True), _bugs(["c1"]))
    _write(tmp_path, "SZZG-9101", _linear(noise_touches_fault_file=False), _bugs(["c1"]))
    report = _run(tmp_path)
    assert report["errors"] == []
    shapes = {s["scenario_id"]: s for s in report["shapes"]}

    for sid in ("SZZG-9100", "SZZG-9101"):
        assert shapes[sid]["oracle_size"] == 1
        assert shapes[sid]["commit_count"] == 4
        assert shapes[sid]["ref_count"] == 1
        # c1 is two commits before the fix
        assert shapes[sid]["bic_depth"] == 2

    # distractors exclude the answer: c0 created the file, c2 is the noise commit
    assert shapes["SZZG-9100"]["fault_file_distractors"] == 2
    assert shapes["SZZG-9101"]["fault_file_distractors"] == 1
    # so the two scenarios are not redundant with each other
    assert report["redundant_groups"] == []
    assert sorted(report["unique_scenarios"]) == ["SZZG-9100", "SZZG-9101"]


def test_scenarios_that_agree_on_every_dimension_are_reported_as_redundant(tmp_path):
    _write(tmp_path, "SZZG-9110", _linear(noise_touches_fault_file=True), _bugs(["c1"]))
    _write(tmp_path, "SZZG-9111", _linear(noise_touches_fault_file=True), _bugs(["c1"]))
    # a different category is a different purpose, so it is kept apart
    _write(tmp_path, "SZZG-9112", _linear(noise_touches_fault_file=True), _bugs(["c1"]), category="G5")
    report = _run(tmp_path)
    assert report["distinct_signatures"] == 2
    assert [g["size"] for g in report["redundant_groups"]] == [2]
    assert report["redundant_groups"][0]["scenarios"] == ["SZZG-9110", "SZZG-9111"]
    assert report["redundant_groups"][0]["signature"]["category"] == "G1"
    assert report["unique_scenarios"] == ["SZZG-9112"]
    assert set(report["redundant_groups"][0]["signature"]) == set(SIGNATURE_FIELDS)


def test_oracle_size_separates_scenarios_of_the_same_shape(tmp_path):
    """Oracle size is the dimension the cheap baselines cannot absorb."""
    two_bic = _linear(noise_touches_fault_file=True)
    two_bic[2] = {"id": "c2", "branch": "main", "parents": ["c1"],
                  "message": "narrow the upper bound too", "role": "bug_introducing",
                  "operations": [{"type": "replace", "path": PATH, "old": "public class Range {",
                                  "new": "public class Range {\n  // second fault"}]}
    _write(tmp_path, "SZZG-9120", _linear(noise_touches_fault_file=True), _bugs(["c1"]))
    _write(tmp_path, "SZZG-9121", two_bic, _bugs(["c1", "c2"]))
    report = _run(tmp_path)
    shapes = {s["scenario_id"]: s for s in report["shapes"]}
    assert shapes["SZZG-9120"]["oracle_size"] == 1
    assert shapes["SZZG-9121"]["oracle_size"] == 2
    # the depth is the distance to the *farthest* required BIC: c1, not c2
    assert shapes["SZZG-9121"]["bic_depth"] == 2
    assert shapes["SZZG-9120"]["bic_depth"] == 2
    assert report["redundant_groups"] == []
    assert json.dumps(report)                      # serialisable for --json / --out
    assert "distinct signatures" in format_report(report)


# ---------------------------------------------------------------------------
# Regressions from the PR #38 review
# ---------------------------------------------------------------------------


def test_the_oracle_is_resolved_exactly_as_the_evaluator_resolves_it():
    """Every shipped scenario must agree with the evaluator's required set.

    Reading the YAML fields directly missed a graph scenario's default
    evaluation variant and the inferred direct BICs of a scenario that omits
    `required`, which made four shipped scenarios look like empty oracles.
    """
    from szzbench.coverage import _oracle_ids
    from szzbench.evaluator import _commit_level_policy, _find_scenario_path, _load_scenario_for_evaluation

    root = Path(__file__).resolve().parents[1]
    checked = disagreements = 0
    for pattern, suite in ((f"scenarios/SZZ-*/scenario.yml", "scenarios"),
                           (f"advanced-scenarios/SZZG-*/scenario.graph.yml", "advanced-scenarios")):
        for path in sorted(root.glob(pattern)):
            scenario_id = path.parent.name
            found, found_suite = _find_scenario_path(scenario_id, root / "scenarios",
                                                     root / "advanced-scenarios")
            assert found == path and found_suite == suite
            data, errors = _load_scenario_for_evaluation(path, suite)
            assert data is not None and not errors
            checked += 1
            if _oracle_ids(data, suite) != set(_commit_level_policy(data, suite, None).required):
                disagreements += 1
    assert checked > 200
    assert disagreements == 0


def test_a_default_evaluation_variant_and_an_inferred_bic_are_both_picked_up(tmp_path):
    from szzbench.coverage import _oracle_ids

    # `required` omitted: the direct BICs are inferred
    inferred = {"bugs": [{"id": "B001",
                          "bug_introducing_commits": [{"commit": "c1", "role": "direct"},
                                                      {"commit": "c0", "role": "origin"}],
                          "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
                          "expected_szz": {"commit_level": {"evaluation_policy": "exact_set"}}}]}
    assert _oracle_ids(inferred, "advanced-scenarios") == {"c1"}

    # a default variant selects the required set
    variant = {"bugs": [{"id": "B001",
                         "bug_introducing_commits": [{"commit": "c1", "role": "origin"},
                                                     {"commit": "c2", "role": "direct"}],
                         "bug_fixing_commits": [{"commit": "c3", "role": "complete_fix"}],
                         "expected_szz": {"commit_level": {
                             "default_variant": "direct-only",
                             "evaluation_variants": {
                                 "direct-only": {"evaluation_policy": "exact_set", "required": ["c2"]},
                                 "with-origin": {"evaluation_policy": "exact_set", "required": ["c1", "c2"]}}}}}]}
    assert _oracle_ids(variant, "advanced-scenarios") == {"c2"}
