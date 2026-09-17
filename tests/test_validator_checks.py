"""Tests for the validator checks added for issue #16.

Always-on checks: dangling rewrite references (GE046/GE047), the shared
policy vocabulary (GW123 incl. evaluation variants) and index consistency
(IE*/IW*).  Opt-in lints (--lint): W4xx for the classic suite and GW4xx for
the graph suite.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import pytest
import yaml

from szzbench import evaluator
from szzbench.cli import main
from szzbench.graph_validator import lint_graph_scenario, validate_graph_scenario_file, validate_graph_static
from szzbench.policies import SUPPORTED_EVALUATION_POLICIES
from szzbench.validator import lint_scenario, simulate_commits, validate_index_file, validate_static

JAVA = "src/main/java/example/Range.java"
RANGE_OK = (
    "package example;\n\npublic class Range {\n"
    "    public boolean contains(int value, int min, int max) {\n"
    "        return value >= min && value <= max;\n    }\n}\n"
)
GUARDED = (
    "package example;\n\npublic class Range {\n"
    "    public boolean valid(int index, int size) {\n"
    "        if (index < 0 || index >= size) {\n"
    "            return false;\n"
    "        }\n"
    "        return true;\n    }\n}\n"
)
# The same method with the guard removed and the surviving line untouched ...
UNGUARDED = (
    "package example;\n\npublic class Range {\n"
    "    public boolean valid(int index, int size) {\n"
    "        return true;\n    }\n}\n"
)
# ... and the template-indentation artefact from issue #7 (re-indented return).
GUARDED_REINDENTED = (
    "package example;\n\npublic class Range {\n"
    "    public boolean valid(int index, int size) {\n"
    "        if (index < 0 || index >= size) {\n"
    "                return false;\n"
    "            }\n"
    "            return true;\n    }\n}\n"
)
UNGUARDED_REINDENTED = (
    "package example;\n\npublic class Range {\n"
    "    public boolean valid(int index, int size) {\n"
    "            return true;\n    }\n}\n"
)


def codes(result) -> list[str]:
    return [f.code for f in result.findings]


def classic_scenario() -> dict:
    return {
        "schema_version": "1.0",
        "meta": {"id": "SZZ-9900", "title": "Lint fixture", "category": "fixture", "factors": ["single-bic", "single-bfc", "line-modification"]},
        "repository": {"name": "lint-fixture", "default_branch": "main", "language": "java"},
        "commits": [
            {"id": "c0", "message": "Initial implementation", "role": "initial",
             "operations": [{"type": "write_file", "path": JAVA, "content": RANGE_OK}]},
            {"id": "c1", "message": "Tighten range check", "role": "bug_introducing",
             "operations": [{"type": "replace", "path": JAVA, "old": "value >= min && value <= max", "new": "value > min && value < max"}]},
            {"id": "c2", "message": "Fix boundary condition", "role": "bug_fixing",
             "operations": [{"type": "replace", "path": JAVA, "old": "value > min && value < max", "new": "value >= min && value <= max"}]},
        ],
        "bugs": [{
            "id": "B001",
            "bug_fixing_commit": "c2",
            "bug_introducing_commits": ["c1"],
            "fault": {"commit": "c1", "file": JAVA, "statement": "return value > min && value < max;", "change_type": "line_modification"},
            "fix": {"commit": "c2", "file": JAVA, "statement": "return value >= min && value <= max;", "fix_type": "line_modification"},
        }],
    }


def graph_scenario() -> dict:
    return {
        "schema_version": "graph-0.1-draft",
        "meta": {"id": "SZZG-9900", "title": "Graph lint fixture", "category": "fixture", "factors": ["rebase", "branch"]},
        "repository": {"name": "graph-lint-fixture", "default_branch": "main"},
        "commits": [
            {"id": "c0", "branch": "main", "parents": [], "message": "Initial implementation", "role": "initial",
             "operations": [{"type": "write_file", "path": JAVA, "content": RANGE_OK}]},
            {"id": "c1", "branch": "main", "parents": ["c0"], "message": "Tighten range check", "role": "bug_introducing",
             "operations": [{"type": "replace", "path": JAVA, "old": "value >= min && value <= max", "new": "value > min && value < max"}]},
            {"id": "c2", "branch": "main", "parents": ["c1"], "message": "Fix boundary condition", "role": "bug_fixing",
             "operations": [{"type": "replace", "path": JAVA, "old": "value > min && value < max", "new": "value >= min && value <= max"}]},
        ],
        "bugs": [{
            "id": "B001",
            "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
            "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
            "faults": [{"commit": "c1", "file": JAVA, "statement": "return value > min && value < max;"}],
            "fixes": [{"commit": "c2", "file": JAVA, "statement": "return value >= min && value <= max;"}],
        }],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}},
    }


def lint_classic(data: dict):
    static = validate_static(data)
    assert not static.has_errors(), codes(static)
    snapshots, sim = simulate_commits(data)
    assert not sim.has_errors(), codes(sim)
    return lint_scenario(data, snapshots)


def lint_graph(data: dict):
    static = validate_graph_static(data, strict_paths=True)
    assert not static.has_errors(), codes(static)
    return lint_graph_scenario(data)


def write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


# --- policy vocabulary -------------------------------------------------------

def test_policy_set_matches_evaluator():
    assert SUPPORTED_EVALUATION_POLICIES == evaluator._SUPPORTED_GRAPH_POLICIES
    assert "origin_aware" not in SUPPORTED_EVALUATION_POLICIES
    assert "relaxed_with_related" in SUPPORTED_EVALUATION_POLICIES


def test_unknown_policy_is_reported_in_commit_level_and_in_variants():
    data = graph_scenario()
    data["expected_szz"]["commit_level"]["evaluation_policy"] = "origin_aware"
    data["expected_szz"]["evaluation_variants"] = [
        {"name": "relaxed", "commit_level": {"evaluation_policy": "relaxed_with_related", "required": ["c1"]}},
        {"name": "bogus", "commit_level": {"evaluation_policy": "made_up", "required": ["c1"]}},
    ]
    result = validate_graph_static(data)
    gw123 = [f for f in result.findings if f.code == "GW123"]
    assert [f.severity for f in gw123] == ["WARNING", "WARNING"]
    assert [f.location for f in gw123] == [
        "expected_szz.commit_level.evaluation_policy",
        "expected_szz.evaluation_variants[1].commit_level.evaluation_policy",
    ]


@pytest.mark.parametrize("policy", sorted(SUPPORTED_EVALUATION_POLICIES))
def test_every_supported_policy_is_accepted(policy):
    data = graph_scenario()
    data["expected_szz"]["commit_level"]["evaluation_policy"] = policy
    assert "GW123" not in codes(validate_graph_static(data))


# --- dangling rewrite references ----------------------------------------------

@pytest.mark.parametrize(
    "key,value,location",
    [
        ("rebase_of", "f1", "commits[1].rebase_of"),
        ("rebase_of", ["c0", "f2"], "commits[1].rebase_of[1]"),
        ("squashes", ["f1", "c0"], "commits[1].squashes[0]"),
        ("revert_of", "c2", "commits[1].revert_of"),  # later commit
        ("rebase_of", "c1", "commits[1].rebase_of"),  # self reference
    ],
)
def test_dangling_rewrite_reference_is_an_error(key, value, location):
    data = graph_scenario()
    data["commits"][1][key] = value
    result = validate_graph_static(data)
    found = [f for f in result.findings if f.code == "GE047"]
    assert len(found) == 1
    assert found[0].severity == "ERROR"
    assert found[0].location == location


@pytest.mark.parametrize("key,value", [("rebase_of", "c0"), ("rebase_of", ["c0"]), ("squashes", ["c0"]), ("revert_of", "c0")])
def test_resolvable_rewrite_reference_is_accepted(key, value):
    data = graph_scenario()
    data["commits"][1][key] = value
    assert not validate_graph_static(data).has_errors()


@pytest.mark.parametrize("key,value", [("rebase_of", 3), ("squashes", "c0"), ("revert_of", ["c0"]), ("squashes", [1])])
def test_rewrite_reference_with_wrong_type_is_an_error(key, value):
    data = graph_scenario()
    data["commits"][1][key] = value
    result = validate_graph_static(data)
    assert "GE046" in codes(result)
    assert "GE047" not in codes(result)


def test_dangling_rebase_of_references_are_reported_per_commit():
    # This is the shape SZZG-0067 had before its repair in this PR: two replayed
    # commits whose rebase_of names feature commits that do not exist.
    data = graph_scenario()
    data["commits"][1]["rebase_of"] = "f1"
    data["commits"][2]["rebase_of"] = "f2"
    result = validate_graph_static(data)
    ge047 = [f for f in result.findings if f.code == "GE047"]
    assert result.has_errors()
    assert sorted(f.message for f in ge047) == [
        "rebase_of refers to unknown or later commit 'f1'.",
        "rebase_of refers to unknown or later commit 'f2'.",
    ]


def test_szzg_0067_repaired_scenario_is_accepted():
    _, result = validate_graph_scenario_file(Path("advanced-scenarios/SZZG-0067/scenario.graph.yml"), simulate=True, strict_paths=True)
    assert not result.has_errors()
    assert "GE047" not in codes(result)


def test_szzg_0064_valid_rebase_of_is_still_accepted():
    _, result = validate_graph_scenario_file(Path("advanced-scenarios/SZZG-0064/scenario.graph.yml"), simulate=True, strict_paths=True)
    assert not result.has_errors()


# --- index consistency --------------------------------------------------------

def _write_index_scenario(root: Path, sid: str, title: str, filename: str, *, meta_id: str | None = None) -> None:
    write_yaml(root / sid / filename, {"schema_version": "1.0", "meta": {"id": meta_id or sid, "title": title}})


def _write_index(root: Path, entries: list[dict], count: int | None = None) -> None:
    doc: dict = {"scenarios": entries}
    if count is not None:
        doc = {"scenario_count": count, **doc}
    write_yaml(root / "index.yml", doc)


def test_consistent_index_has_no_findings(tmp_path):
    root = tmp_path / "scenarios"
    _write_index_scenario(root, "SZZ-0001", "One", "scenario.yml")
    _write_index(root, [{"id": "SZZ-0001", "title": "One", "path": "scenarios/SZZ-0001/scenario.yml"}], count=1)
    assert validate_index_file(root / "index.yml", root, "scenario.yml").findings == []


def test_index_inconsistencies_are_reported(tmp_path):
    root = tmp_path / "advanced-scenarios"
    _write_index_scenario(root, "SZZG-0001", "One", "scenario.graph.yml")
    _write_index_scenario(root, "SZZG-0002", "Two", "scenario.graph.yml")  # no index entry
    _write_index_scenario(root, "SZZG-0003", "Three", "scenario.graph.yml", meta_id="SZZG-0004")
    _write_index(
        root,
        [
            {"id": "SZZG-0001", "title": "Wrong title", "path": "advanced-scenarios/SZZG-0001/scenario.graph.yml"},
            {"id": "SZZG-0003", "title": "Three", "path": "advanced-scenarios/SZZG-0033/scenario.graph.yml"},
            {"id": "SZZG-0009", "title": "Missing"},
            {"id": "SZZG-0001", "title": "One"},
            "not-an-object",
        ],
        count=116,
    )
    result = validate_index_file(root / "index.yml", root, "scenario.graph.yml")
    by_code = {f.code: f for f in result.findings}
    assert sorted(codes(result)) == sorted(["IE010", "IE041", "IW023", "IE040", "IE022", "IE021", "IE020", "IE030"])
    assert by_code["IE010"].message == "scenario_count is 116, but the index lists 5 entries."
    assert by_code["IW023"].severity == "WARNING"
    assert "SZZG-0002" in by_code["IE030"].message
    assert by_code["IE010"].location == f"{(root / 'index.yml').as_posix()}:scenario_count"


def test_validate_index_cli_exit_code_and_json(tmp_path, capsys):
    s_root = tmp_path / "scenarios"
    a_root = tmp_path / "advanced-scenarios"
    _write_index_scenario(s_root, "SZZ-0001", "One", "scenario.yml")
    _write_index(s_root, [{"id": "SZZ-0001", "title": "One"}])
    _write_index_scenario(a_root, "SZZG-0001", "Graph one", "scenario.graph.yml")
    _write_index(a_root, [{"id": "SZZG-0001", "title": "Graph one"}], count=2)
    argv = ["validate-index", "--scenarios-root", str(s_root), "--advanced-scenarios-root", str(a_root), "--json"]

    assert main(argv) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["errors"] == 1
    assert report["findings"][0]["code"] == "IE010"

    _write_index(a_root, [{"id": "SZZG-0001", "title": "Graph one"}], count=1)
    assert main(argv) == 0
    assert json.loads(capsys.readouterr().out)["findings"] == []


# --- --lint flag ----------------------------------------------------------------

def test_clean_fixtures_have_no_lint_findings():
    assert lint_classic(classic_scenario()).findings == []
    assert lint_graph(graph_scenario()).findings == []


def test_classic_lint_is_opt_in(tmp_path, capsys):
    data = classic_scenario()
    data["commits"][1]["message"] = "c1: introduce boundary bug"
    path = write_yaml(tmp_path / "SZZ-9900" / "scenario.yml", data)

    assert main(["validate", "--simulate", "--strict", str(path)]) == 0
    assert "W41" not in capsys.readouterr().out

    assert main(["validate", "--strict", "--lint", str(path)]) == 1
    out = capsys.readouterr().out
    assert "[WARNING] W410" in out
    assert "[WARNING] W411" in out


def test_graph_lint_is_opt_in(tmp_path, capsys):
    data = graph_scenario()
    data["commits"][1]["message"] = "c1: introduce bug (replace Range.java)"
    path = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", data)

    assert main(["validate-graph", "--simulate", "--strict", "--strict-paths", str(path)]) == 0
    assert "GW41" not in capsys.readouterr().out

    assert main(["validate-graph", "--strict", "--strict-paths", "--lint", str(path)]) == 1
    out = capsys.readouterr().out
    assert "[WARNING] GW410" in out
    assert "[WARNING] GW411" in out


# --- vocabulary lints -----------------------------------------------------------

def test_factor_vocabulary_lints_classic():
    data = classic_scenario()
    data["meta"]["factors"] = ["expected_szz", "single-bic", "multiple_bic"]
    result = lint_classic(data)
    assert codes(result).count("W400") == 1
    assert "W402" in codes(result)
    assert [f.location for f in result.findings if f.code == "W400"] == ["meta.factors[0]"]

    data["meta"]["factors"] = []
    assert codes(lint_classic(data)) == ["W401"]

    data["meta"]["factors"] = ["single-bic", "omission-bug"]
    assert lint_classic(data).findings == []


def test_factor_vocabulary_lints_graph():
    data = graph_scenario()
    data["meta"]["factors"] = ["write_file", "edit", "branch"]
    assert codes(lint_graph(data)).count("GW400") == 2

    data["meta"]["factors"] = []
    assert codes(lint_graph(data)) == ["GW401"]

    data["meta"]["factors"] = ["rebase", "single_bfc"]
    assert lint_graph(data).findings == []


def test_graph_role_vocabulary_lint():
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"] = [{"commit": "c1", "role": "direct_squash_bic"}, {"commit": "c0", "role": "origin"}]
    data["bugs"][0]["bug_fixing_commits"] = [{"commit": "c2", "role": "main_fix"}]
    data["expected_szz"]["commit_level"]["related_origins"] = ["c0"]
    result = lint_graph(data)
    assert codes(result) == ["GW403", "GW404"]
    assert result.findings[0].location == "bugs[0].bug_introducing_commits[0].role"

    data["bugs"][0]["bug_introducing_commits"][0]["role"] = "direct"
    data["bugs"][0]["bug_fixing_commits"][0]["role"] = "partial_fix"
    assert lint_graph(data).findings == []


# --- leakage lint -----------------------------------------------------------------

def test_leakage_lint_flags_role_wording_and_prefixes_but_not_the_bfc():
    data = classic_scenario()
    data["commits"][0]["message"] = "c0: initial state"
    data["commits"][1]["message"] = "Introduce boundary bug"
    data["commits"][2]["message"] = "Fix bug introduced by the tighter range check"  # BFC: allowed
    result = lint_classic(data)
    assert codes(result) == ["W411", "W410", "W410"]
    assert result.findings[0].location == "commits[0].message"
    assert "'initial state'" in result.findings[1].message
    assert "'Introduce boundary bug'" in result.findings[2].message


def test_leakage_lint_flags_written_file_contents():
    data = classic_scenario()
    data["commits"][1]["operations"].append({"type": "write_file", "path": "docs/note.md", "content": "This commit is a ranking distractor.\n"})
    result = lint_classic(data)
    assert codes(result) == ["W412"]
    assert result.findings[0].location == "commits[1].operations[1].content"

    graph = graph_scenario()
    graph["commits"][2]["operations"][0]["new"] = "value >= min && value <= max; // BFC"
    result = lint_graph(graph)
    assert codes(result) == ["GW412"]
    assert "replace.new" in result.findings[0].message


def test_leakage_lint_is_case_insensitive_and_word_bounded():
    data = classic_scenario()
    data["commits"][1]["message"] = "Adjust bic handling for BIC codes"  # \bBIC\b, case-insensitive
    assert codes(lint_classic(data)) == ["W410"]
    data["commits"][1]["message"] = "Rename cubic helper"  # 'bic' inside a word is not flagged
    assert lint_classic(data).findings == []


# --- ghost invariants (classic) -------------------------------------------------

def _omission_scenario(bfc_result: str) -> dict:
    data = classic_scenario()
    data["meta"]["factors"] = ["single-bic", "single-bfc", "omission-bug", "line-addition-fix"]
    data["commits"][0]["operations"][0]["content"] = "package example;\n\npublic class Range {\n}\n"
    data["commits"][1]["operations"] = [{"type": "write_file", "path": JAVA, "content": UNGUARDED}]
    data["commits"][2]["operations"] = [{"type": "replace", "path": JAVA, "old": UNGUARDED, "new": bfc_result}]
    data["bugs"][0]["fault"] = {"commit": "c1", "file": JAVA, "change_type": "omission", "missing_statement": "if (index < 0 || index >= size) {"}
    data["bugs"][0]["fix"] = {"commit": "c2", "file": JAVA, "added_statement": "if (index < 0 || index >= size) {", "fix_type": "line_addition"}
    return data


def test_omission_bug_with_addition_only_fix_type_must_not_modify_lines():
    result = lint_classic(_omission_scenario(GUARDED_REINDENTED))
    w420 = [f for f in result.findings if f.code == "W420"]
    assert len(w420) == 1
    assert "omission bug with an addition-only fix_type" in w420[0].message
    assert "(first: 'return true;')" in w420[0].message
    assert "W431" not in codes(result)  # the modified line belongs to the BIC


def test_omission_bug_with_pure_insertion_is_clean():
    assert lint_classic(_omission_scenario(GUARDED)).findings == []


def test_declared_addition_only_fix_factor_applies_to_any_bug():
    data = classic_scenario()
    data["meta"]["factors"].append("addition-only-fix")
    result = lint_classic(data)
    assert codes(result) == ["W420"]
    assert "declared as an addition-only fix" in result.findings[0].message


def _deletion_bic_scenario(bic_result: str) -> dict:
    data = classic_scenario()
    data["meta"]["factors"] = ["single-bic", "single-bfc", "line-deletion-bic"]
    data["commits"][0]["operations"][0]["content"] = GUARDED
    data["commits"][1]["operations"] = [{"type": "replace", "path": JAVA, "old": GUARDED, "new": bic_result}]
    data["commits"][2]["operations"] = [{"type": "replace", "path": JAVA, "old": bic_result, "new": GUARDED}]
    data["bugs"][0]["fault"] = {"commit": "c1", "file": JAVA, "statement": "return true;", "change_type": "line_modification"}
    data["bugs"][0]["fix"] = {"commit": "c2", "file": JAVA, "statement": "if (index < 0 || index >= size) {", "fix_type": "line_addition"}
    return data


def test_declared_deletion_only_bic_must_not_add_lines():
    result = lint_classic(_deletion_bic_scenario(UNGUARDED_REINDENTED))
    w421 = [f for f in result.findings if f.code == "W421"]
    assert len(w421) == 1
    assert "adds 1 line(s)" in w421[0].message


def test_declared_deletion_only_bic_with_pure_deletion_is_clean():
    assert lint_classic(_deletion_bic_scenario(UNGUARDED)).findings == []


def test_ghost_invariants_are_not_checked_without_declaration():
    data = classic_scenario()  # plain line_modification: BFC modifies a line, BIC adds one
    assert lint_classic(data).findings == []


# --- fault-line integrity (classic) ------------------------------------------------

def test_intermediate_commit_removing_fault_statement_warns_unless_declared():
    data = classic_scenario()
    data["commits"].insert(2, {
        "id": "c1b", "message": "Compact the comparison", "role": "refactoring",
        "operations": [{"type": "replace", "path": JAVA, "old": "value > min && value < max", "new": "value>min && value<max"}],
    })
    data["commits"][3]["operations"][0]["old"] = "value>min && value<max"
    result = lint_classic(data)
    w430 = [f for f in result.findings if f.code == "W430"]
    assert len(w430) == 1
    assert w430[0].location == "commits[2]"
    assert "'c1b'" in w430[0].message
    assert "W431" in codes(result)  # the BFC now deletes a c1b-authored line

    data["meta"]["factors"].append("expression-rewrite-after-bic")
    assert "W430" not in codes(lint_classic(data))


def test_bfc_deleting_non_bic_lines_warns_unless_tangled():
    data = classic_scenario()
    data["commits"][2]["operations"].append({"type": "replace", "path": JAVA, "old": "package example;", "new": "package example; // reviewed"})
    result = lint_classic(data)
    w431 = [f for f in result.findings if f.code == "W431"]
    assert len(w431) == 1
    assert "['c0']" in w431[0].message
    assert "(first: 'package example;')" in w431[0].message

    data["meta"]["factors"].append("tangled-bfc")
    assert "W431" not in codes(lint_classic(data))


def test_bfc_deleting_only_bic_lines_is_clean():
    data = classic_scenario()
    data["commits"].insert(2, {
        "id": "c1b", "message": "Document the class", "role": "refactoring",
        "operations": [{"type": "replace", "path": JAVA, "old": "public class Range {", "new": "/** Range helper. */\npublic class Range {"}],
    })
    assert lint_classic(data).findings == []


# --- graph-only lints ------------------------------------------------------------------

def test_approximate_operations_warn_with_explanations():
    data = graph_scenario()
    data["commits"].append({
        "id": "c3", "branch": "main", "parents": ["c2"], "message": "Housekeeping", "role": "intermediate",
        "operations": [
            {"type": "chmod", "path": JAVA, "mode": "755"},
            {"type": "commit_generator", "generator": "filler", "count": 3},
            {"type": "copy_entity", "entity": {"type": "method", "name": "contains"}, "from_file": JAVA, "to_file": "src/main/java/example/Copy.java"},
            {"type": "apply_patch", "path": JAVA, "patch": "--- a\n+++ b\n"},
        ],
    })
    result = lint_graph(data)
    assert codes(result) == ["GW442", "GW441", "GW440", "GW443"]
    assert "core.filemode=false" in result.findings[0].message
    assert "does not create additional commits" in result.findings[1].message
    assert "file-level approximation" in result.findings[2].message
    assert "not implemented" in result.findings[3].message
    assert result.findings[3].location == "commits[3].operations[3]"


def test_origin_bic_must_be_mentioned_by_expected_szz():
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "origin"})
    result = lint_graph(data)
    assert codes(result) == ["GW450"]
    assert result.findings[0].location == "bugs[0].bug_introducing_commits[1]"

    in_variant = deepcopy(data)
    in_variant["expected_szz"]["evaluation_variants"] = [{
        "name": "origin-aware",
        "commit_level": {"required": ["c1"], "acceptable_related": [{"commit": "c0", "reason": "origin_bic", "credit": 0.5}]},
    }]
    assert lint_graph(in_variant).findings == []

    in_commit_level = deepcopy(data)
    in_commit_level["expected_szz"]["commit_level"]["related_but_not_correct"] = ["c0"]
    assert lint_graph(in_commit_level).findings == []


def test_origin_coverage_ignores_non_origin_roles():
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "contributing"})
    assert lint_graph(data).findings == []
