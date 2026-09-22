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


def _write(tmp_path: Path, scenario_id: str, commits, bugs, category="G1", **top_level) -> None:
    data = {
        "schema_version": "graph-0.1-draft",
        "meta": {"id": scenario_id, "title": "coverage fixture", "category": "test",
                 "category_code": category, "factors": ["single-bic"]},
        "repository": {"name": scenario_id.lower(), "default_branch": "main",
                       "language": "java", "source_root": "src/main/java"},
        "graph": {"model": "commit_dag"},
        "commits": commits,
        "bugs": bugs,
        **top_level,
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


# --- fault statement reuse (#13) ---------------------------------------------

def test_fault_statements_are_collected_from_every_fault_list_normalised_and_deduplicated():
    from szzbench.coverage import _fault_statements
    data = {"bugs": [
        {"fault": {"statement": "return  value > min\n    && value < max;"},
         "faults": [{"statement": "return value > min && value < max;"}, {"statement": "  "}, "not a dict"],
         "origin_faults": [{"statement": "return s.trim();"}]},
        {"faults": [{"statement": "return s.trim();"}, {"no_statement": True}]},
        "not a bug",
    ]}
    assert _fault_statements(data) == ["return value > min && value < max;", "return s.trim();"]
    assert _fault_statements({"bugs": None}) == [] and _fault_statements({}) == []


def test_fault_statement_reuse_is_reported_overall_and_per_category(tmp_path):
    """Two G1 fixtures share `return v > lo;`; a G2 fixture declares its own statement.
    The report names the shared statement, its carriers and the per-category share (#13)."""
    _write(tmp_path, "SZZG-9931", _linear(False), _bugs(["c1"]), category="G1")
    _write(tmp_path, "SZZG-9932", _linear(True), _bugs(["c1"]), category="G1")
    commits = _linear(False)                       # the same history with a different fault: != instead of >
    commits[1]["operations"][0]["new"] = "return v != lo;"
    commits[3]["operations"][0]["old"] = "return v != lo;"
    own = _bugs(["c1"])
    own[0]["faults"][0]["statement"] = "return v != lo;"
    _write(tmp_path, "SZZG-9933", commits, own, category="G2")
    report = _run(tmp_path)
    reuse = report["fault_reuse"]
    assert reuse["scenarios_with_a_statement"] == 3 and reuse["distinct_statements"] == 2
    assert reuse["shared"] == [{"statement": "return v > lo;", "scenarios": 2, "by_suite": {"advanced-scenarios": 2},
                                "scenario_ids": ["SZZG-9931", "SZZG-9932"]}]
    assert reuse["per_category"]["G1"] == {"scenarios": 2, "distinct_statements": 1, "most_reused": "return v > lo;", "most_reused_scenarios": 2}
    assert reuse["per_category"]["G2"] == {"scenarios": 1, "distinct_statements": 1, "most_reused": "return v != lo;", "most_reused_scenarios": 1}
    assert all("fault_statements" in shape for shape in report["shapes"])
    text = format_report(report)
    assert "fault statement reuse" in text and "  2x  return v > lo;   (advanced-scenarios 2)" in text
    assert "most reused statement per category: G1 2/2" in text
    json.dumps(report)


# --- blame_class: what naive blame does with the oracle (issue #35) ---------------

def _rewriting_noise():
    """c2 rewrites the faulty line (parentheses) without changing behaviour, and c3 fixes from that."""
    commits = _linear(noise_touches_fault_file=False)
    commits[2]["operations"] = [{"type": "replace", "path": PATH, "old": "return v > lo;", "new": "return (v > lo);"}]
    commits[3]["operations"] = [{"type": "replace", "path": PATH, "old": "return (v > lo);", "new": "return v >= lo;"}]
    return commits


def _fix_also_touching_an_old_line():
    """c3 fixes the faulty line and rewrites the class header c0 wrote, so blame names c1 and c0."""
    commits = _linear(noise_touches_fault_file=False)
    commits[3]["operations"] = [
        {"type": "replace", "path": PATH, "old": "return v > lo;", "new": "return v >= lo;"},
        {"type": "replace", "path": PATH, "old": "public class Range {", "new": "public final class Range {"},
    ]
    return commits


def _addition_only_fix():
    """c1 drops a guard; c3 puts a guard back by inserting a line, deleting nothing."""
    commits = _linear(noise_touches_fault_file=False)
    commits[0]["operations"] = [{"type": "write_file", "path": PATH, "content": JAVA % ">=" }]
    commits[1]["operations"] = [{"type": "replace", "path": PATH, "old": "return v >= lo;", "new": "return v >= lo; // no guard"}]
    # insert_after appends right after the anchor text, so the content starts with the line break
    commits[3]["operations"] = [{"type": "insert_after", "path": PATH, "anchor": "  public boolean contains(int v, int lo) {",
                                 "content": "\n    if (lo < 0) return false;"}]
    return commits


def test_blame_class_is_measured_from_the_generated_repository(tmp_path):
    _write(tmp_path, "SZZG-9120", _linear(noise_touches_fault_file=False), _bugs(["c1"]))     # exact
    _write(tmp_path, "SZZG-9121", _rewriting_noise(), _bugs(["c1"]))                          # miss: blame stops at c2
    _write(tmp_path, "SZZG-9122", _fix_also_touching_an_old_line(), _bugs(["c1"]))            # extra: c1 and c0
    _write(tmp_path, "SZZG-9123", _linear(noise_touches_fault_file=False), _bugs(["c1", "c2"]))  # miss: c2 never blamed
    bugs = _bugs(["c1"])
    bugs[0]["faults"][0]["statement"] = "return v >= lo; // no guard"
    bugs[0]["fixes"][0]["statement"] = "if (lo < 0) return false;"
    _write(tmp_path, "SZZG-9124", _addition_only_fix(), bugs)                                 # addition-only
    report = _run(tmp_path)
    assert report["errors"] == [], report["errors"]
    classes = {s["scenario_id"]: s["blame_class"] for s in report["shapes"]}
    assert classes == {"SZZG-9120": "exact", "SZZG-9121": "miss", "SZZG-9122": "extra", "SZZG-9123": "miss",
                       "SZZG-9124": "addition-only"}
    assert report["distributions"]["blame_class"] == {"addition-only": 1, "exact": 1, "extra": 1, "miss": 2}
    # the class is measured, so it is not part of the redundancy signature
    assert "blame_class" not in SIGNATURE_FIELDS
    assert "blame_class            " in format_report(report)


def test_declared_difficulty_is_tabulated_against_the_measured_blame_class(tmp_path):
    _write(tmp_path, "SZZG-9130", _linear(noise_touches_fault_file=False), _bugs(["c1"]))
    _write(tmp_path, "SZZG-9131", _rewriting_noise(), _bugs(["c1"]))
    scenario = tmp_path / "advanced-scenarios" / "SZZG-9131" / "scenario.graph.yml"
    data = yaml.safe_load(scenario.read_text())
    data["meta"]["difficulty"] = "hard"
    scenario.write_text(yaml.safe_dump(data, sort_keys=False))
    report = _run(tmp_path)
    assert report["difficulty_by_blame_class"] == {"advanced-scenarios": {"exact": {"None": 1}, "miss": {"hard": 1}}}
    assert "declared difficulty by measured blame class" in format_report(report)


def test_empty_first_parent_fix_is_its_own_class(tmp_path):
    """SZZG-0042's fix is a merge that records the fix arriving from the branch; its first-parent
    diff is empty, so there is nothing to blame at all."""
    from pathlib import Path as _P
    root = _P(__file__).resolve().parents[1]
    src = root / "advanced-scenarios" / "SZZG-0042" / "scenario.graph.yml"
    generate_graph_repository(src, tmp_path / "repos" / "SZZG-0042" / "default", force=True)
    report = run_coverage(generated_root=tmp_path / "repos", scenarios_root=root / "scenarios",
                          advanced_scenarios_root=root / "advanced-scenarios")
    assert report["errors"] == []
    assert [s["blame_class"] for s in report["shapes"]] == ["empty-first-parent"]


def test_a_root_bug_fixing_commit_is_diffed_against_the_empty_tree(tmp_path):
    """A one-commit scenario whose root commit is the fix (PR #74 review): the root has no
    ``<hash>^``, and the failed Git call must not be read as an empty first-parent diff."""
    commits = [{"id": "c0", "branch": "main", "parents": [], "message": "add the range check with its guard",
                "role": "bug_fixing",
                "operations": [{"type": "write_file", "path": PATH, "content": JAVA % ">="}]}]
    bugs = [{"id": "B001", "bug_introducing_commits": [],
             "bug_fixing_commits": [{"commit": "c0", "role": "complete_fix"}],
             "faults": [],
             "fixes": [{"id": "X001", "commit": "c0", "file": PATH, "statement": "return v >= lo;",
                        "fix_type": "line_addition"}]}]
    # a bug without introducing commits is accepted when the scenario declares expect_no_bic (GI086)
    _write(tmp_path, "SZZG-9150", commits, bugs,
           expected_szz={"commit_level": {"evaluation_policy": "exact_set", "expect_no_bic": True, "required": []}})
    report = _run(tmp_path)
    assert report["errors"] == []
    assert [s["blame_class"] for s in report["shapes"]] == ["addition-only"]
