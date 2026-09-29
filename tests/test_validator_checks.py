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
    """Error and warning codes, in order. Information items (I/GI codes) do not fail
    `--strict` and are not lint findings in the sense these tests assert; see info_codes()."""
    return [f.code for f in result.findings if f.severity != "INFO"]


def info_codes(result) -> list[str]:
    return [f.code for f in result.findings if f.severity == "INFO"]


def classic_scenario() -> dict:
    return {
        "schema_version": "1.0",
        "meta": {"id": "SZZ-9900", "title": "Lint fixture", "category": "fixture", "tier": "control", "difficulty": "medium", "factors": ["single-bic", "single-bfc", "line-modification"]},
        "repository": {"name": "lint-fixture", "default_branch": "main", "language": "java"},
        "commits": [
            {"id": "c0", "message": "Initial implementation", "role": "initial", "author": "Ann Example <ann@example.com>",
             "operations": [{"type": "write_file", "path": JAVA, "content": RANGE_OK}]},
            {"id": "c1", "message": "Tighten range check", "role": "bug_introducing", "author": "Ann Example <ann@example.com>",
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
        "meta": {"id": "SZZG-9900", "title": "Graph lint fixture", "category": "fixture", "tier": "control", "difficulty": "medium", "factors": ["rebase", "branch"]},
        "repository": {"name": "graph-lint-fixture", "default_branch": "main"},
        "commits": [
            {"id": "c0", "branch": "main", "parents": [], "message": "Initial implementation", "role": "initial", "author": "Ann Example <ann@example.com>",
             "operations": [{"type": "write_file", "path": JAVA, "content": RANGE_OK}]},
            {"id": "c1", "branch": "main", "parents": ["c0"], "message": "Tighten range check", "role": "bug_introducing", "author": "Ann Example <ann@example.com>",
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


# --- default_variant (GE129) --------------------------------------------------

BOUNDARY_VARIANT = {"name": "boundary-commit", "commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}


@pytest.mark.parametrize("default_variant, variants", [
    ("default", [BOUNDARY_VARIANT]),            # SZZG-0136 until 2026-09-29: a name no variant has
    ("boundary", [BOUNDARY_VARIANT]),
    ("boundary-commit", None),                  # no variants at all
    ("", [BOUNDARY_VARIANT]),
    (None, [BOUNDARY_VARIANT]),                 # present but null: the evaluator falls back without a note
    (5, [BOUNDARY_VARIANT]),
])
def test_a_default_variant_that_names_no_variant_is_an_error(default_variant, variants):
    # the evaluator ignored it and scored commit_level, noting it at every evaluation
    data = graph_scenario()
    if variants is not None:
        data["expected_szz"]["evaluation_variants"] = deepcopy(variants)
    data["expected_szz"]["default_variant"] = default_variant
    ge129 = [f for f in validate_graph_static(data).findings if f.code == "GE129"]
    assert [(f.severity, f.location) for f in ge129] == [("ERROR", "expected_szz.default_variant")]


@pytest.mark.parametrize("blank", ["default_variant:", "default_variant: null", "default_variant: ~"])
def test_a_blank_default_variant_in_a_scenario_file_is_an_error(tmp_path, blank):
    # YAML reads all three as None, which the check first took for an absent key (PR #105 review)
    data = graph_scenario()
    data["expected_szz"]["evaluation_variants"] = [deepcopy(BOUNDARY_VARIANT)]
    data["expected_szz"]["default_variant"] = "__BLANK__"
    path = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", data)
    text = path.read_text(encoding="utf-8")
    assert text.count("default_variant: __BLANK__") == 1
    path.write_text(text.replace("default_variant: __BLANK__", blank), encoding="utf-8")
    loaded, result = validate_graph_scenario_file(path)
    assert "default_variant" in loaded["expected_szz"] and loaded["expected_szz"]["default_variant"] is None
    ge129 = [f for f in result.findings if f.code == "GE129"]
    assert [(f.severity, f.location) for f in ge129] == [("ERROR", "expected_szz.default_variant")]
    assert "blank" in ge129[0].message


def test_without_a_default_variant_commit_level_is_the_default_and_nothing_is_reported():
    data = graph_scenario()
    data["expected_szz"]["evaluation_variants"] = [deepcopy(BOUNDARY_VARIANT)]
    assert "GE129" not in codes(validate_graph_static(data))


@pytest.mark.parametrize("default_variant", ["boundary-commit", "boundary_commit", "Boundary-Commit"])
def test_a_default_variant_the_evaluator_resolves_is_accepted(default_variant):
    data = graph_scenario()
    data["expected_szz"]["evaluation_variants"] = [deepcopy(BOUNDARY_VARIANT)]
    data["expected_szz"]["default_variant"] = default_variant
    assert "GE129" not in codes(validate_graph_static(data))
    notes: list[str] = []
    assert evaluator._selected_evaluation_variant(data["expected_szz"], None, notes)["name"] == "boundary-commit"
    assert notes == []


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
    assert codes(result).count("E400") == 1
    assert "E402" in codes(result)
    assert [f.location for f in result.findings if f.code == "E400"] == ["meta.factors[0]"]

    data["meta"]["factors"] = []
    assert codes(lint_classic(data)) == ["E401"]

    data["meta"]["factors"] = ["single-bic", "omission-bug"]
    assert lint_classic(data).findings == []


def test_factor_vocabulary_lints_graph():
    data = graph_scenario()
    data["meta"]["factors"] = ["write_file", "edit", "branch"]
    assert codes(lint_graph(data)).count("GE400") == 2

    data["meta"]["factors"] = []
    assert codes(lint_graph(data)) == ["GE401"]

    data["meta"]["factors"] = ["rebase", "single_bfc"]
    assert lint_graph(data).findings == []


ORIGIN_AWARE_VARIANT = {
    "name": "origin-aware",
    "commit_level": {
        "evaluation_policy": "relaxed_with_related",
        "required": ["c1"],
        "acceptable_related": [{"commit": "c0", "reason": "origin_bic", "credit": 0.5}],
    },
}


def test_graph_role_vocabulary_lint():
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"] = [{"commit": "c1", "role": "direct_squash_bic"}, {"commit": "c0", "role": "origin"}]
    data["bugs"][0]["bug_fixing_commits"] = [{"commit": "c2", "role": "main_fix"}]
    data["expected_szz"]["commit_level"]["related_origins"] = ["c0"]
    data["expected_szz"]["evaluation_variants"] = [deepcopy(ORIGIN_AWARE_VARIANT)]
    result = lint_graph(data)
    assert codes(result) == ["GE403", "GE404"]
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
    # chmod and commit_generator are faithful since the generator records file
    # modes and expands commit_generator into real commits, so they no longer warn.
    assert codes(result) == ["GW440", "GW443"]
    assert "file-level approximation" in result.findings[0].message
    assert "not implemented" in result.findings[1].message
    assert result.findings[1].location == "commits[3].operations[3]"


def test_origin_bic_must_be_mentioned_by_expected_szz():
    """GW450: an origin named nowhere in expected_szz."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "origin"})
    result = lint_graph(data)
    assert "GW450" in codes(result)
    assert result.findings[0].location == "bugs[0].bug_introducing_commits[1]"


def test_origin_must_be_related_origins_in_the_default_variant():
    """GW451: mentioning the origin somewhere is not enough (contract D2).

    Both shapes below satisfied the old "mentioned anywhere" rule and are what
    most of the suite carried before the direct/origin contract was decided.
    """
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "origin"})

    only_in_variant = deepcopy(data)
    only_in_variant["expected_szz"]["evaluation_variants"] = [deepcopy(ORIGIN_AWARE_VARIANT)]
    assert codes(only_in_variant := lint_graph(only_in_variant)) == ["GW451"]
    assert only_in_variant.findings[0].location == "bugs[0].bug_introducing_commits[1]"

    as_not_correct = deepcopy(data)
    as_not_correct["expected_szz"]["commit_level"]["related_but_not_correct"] = ["c0"]
    assert codes(lint_graph(as_not_correct)) == ["GW451", "GW452"]

    conforming = deepcopy(data)
    conforming["expected_szz"]["commit_level"]["related_origins"] = ["c0"]
    conforming["expected_szz"]["evaluation_variants"] = [deepcopy(ORIGIN_AWARE_VARIANT)]
    assert lint_graph(conforming).findings == []


def test_required_origin_needs_no_variant():
    """An origin that is itself the answer is exempt (SZZG-0018)."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "origin"})
    data["expected_szz"]["commit_level"]["required"] = ["c0", "c1"]
    data["commits"][1]["author"] = "Bob Example <bob@example.com>"   # otherwise Ann owns exactly {c0, c1}: GW413 (#43)
    assert lint_graph(data).findings == []


def _origin_scenario():
    """A conforming origin scenario: origin in related_origins plus an origin-aware variant."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "origin"})
    data["expected_szz"]["commit_level"]["related_origins"] = ["c0"]
    data["expected_szz"]["evaluation_variants"] = [deepcopy(ORIGIN_AWARE_VARIANT)]
    return data


def test_origin_aware_variant_must_actually_accept_the_origin():
    """GW453: membership in acceptable_related is not the same as acceptance.

    Both shapes below keep the origin in `acceptable_related`, so a check that
    tested membership called them fine; the evaluator rejects the very
    prediction the variant exists to accept (PR #45 review).
    """
    assert lint_graph(_origin_scenario()).findings == []

    # a related_but_not_correct entry left behind by the migration still counts
    # as a relaxed false positive, even for a commit that is also acceptable
    leftover = _origin_scenario()
    leftover["expected_szz"]["evaluation_variants"][0]["commit_level"]["related_but_not_correct"] = ["c0"]
    result = lint_graph(leftover)
    assert codes(result) == ["GW453"]
    assert result.findings[0].location == "expected_szz.evaluation_variants"
    assert "FAIL" in result.findings[0].message

    # expect_no_bic discards the allowance entirely
    no_bic = _origin_scenario()
    level = no_bic["expected_szz"]["evaluation_variants"][0]["commit_level"]
    level["required"] = []
    level["expect_no_bic"] = True
    assert codes(lint_graph(no_bic)) == ["GW453"]


def test_default_variant_decides_which_commit_level_is_checked():
    """GW451 must ask the evaluator which variant is the default.

    A scenario may carry a base `commit_level` *and* a `default_variant`; the
    evaluator honours the latter.  Reading the base level directly both missed
    violations and warned about conforming scenarios (PR #45 review).
    """
    # the base level conforms, but the selected default does not
    misleading = _origin_scenario()
    misleading["expected_szz"]["default_variant"] = "direct-only"
    misleading["expected_szz"]["evaluation_variants"].append({
        "name": "direct-only",
        "commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]},
    })
    assert "GW451" in codes(lint_graph(misleading))

    # and the mirror image: the base level looks wrong, the selected default is right
    conforming = _origin_scenario()
    del conforming["expected_szz"]["commit_level"]["related_origins"]
    conforming["expected_szz"]["default_variant"] = "direct-only"
    conforming["expected_szz"]["evaluation_variants"].append({
        "name": "direct-only",
        "commit_level": {"evaluation_policy": "exact_set", "required": ["c1"], "related_origins": ["c0"]},
    })
    assert lint_graph(conforming).findings == []


def test_origin_coverage_ignores_non_origin_roles():
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "contributing"})
    assert lint_graph(data).findings == []


def test_leakage_lint_catches_the_forms_the_first_version_missed():
    """Regression examples from the PR #34 re-review.

    The original patterns were anchored, lower-case and required the literal
    word "bug" within three *unhyphenated* words of "introduce", so each of the
    messages below passed the lint while naming its own role.
    """
    data = classic_scenario()
    bic = data["commits"][1]

    # hyphenated words between "introduce" and "bug"
    for message in ("Introduce context-sensitive bug",
                    "Introduce context-sensitive caller bug",
                    "introduce release-specific range bug"):
        bic["message"] = message
        assert codes(lint_classic(data)) == ["W410"], message

    # an admission of a fault without the word "bug" at all
    for message in ("Introduce ambiguous faulty statement",
                    "Rewrite the buggy comparison",
                    "Keep the faulty line for now"):
        bic["message"] = message
        assert codes(lint_classic(data)) == ["W410"], message

    # a logical id behind a legitimate work-item id, and a capitalised one
    for message, exposed in (("WI-001 c1: implement the range feature", "c1"),
                             ("WI-418 C1: reject oversold reservations", "C1"),
                             ("Rel1: cut the release branch", "Rel1"),
                             ("Fix the check; suspected c0", "c0")):
        bic["message"] = message
        result = lint_classic(data)
        assert codes(result) == ["W411"], message
        assert exposed in result.findings[0].message

    # legitimate identifiers and natural wording stay clean
    for message in ("WI-001 implement the range feature",
                    "ISSUE-482 keep blank middle names as empty strings",
                    "PAY-314 bypass the EU checkout challenge",
                    "Add a webhook date regression test",
                    "Rename the cubic interpolation helper"):
        bic["message"] = message
        assert lint_classic(data).findings == [], message


def test_tier_lint_requires_a_declared_vocabulary_value():
    """W460 / GW460: every scenario says what it is for (issue #14)."""
    from szzbench.validator import SCENARIO_TIERS

    assert SCENARIO_TIERS == ("control", "discriminating")

    data = classic_scenario()
    data["meta"].pop("tier", None)
    result = lint_classic(data)
    assert "W460" in codes(result)
    assert "meta.tier is missing" in [f.message for f in result.findings if f.code == "W460"][0]

    data["meta"]["tier"] = "controls"          # near miss
    assert "W460" in codes(lint_classic(data))

    for tier in SCENARIO_TIERS:
        data["meta"]["tier"] = tier
        assert "W460" not in codes(lint_classic(data))

    graph = graph_scenario()
    graph["meta"].pop("tier", None)
    assert "GW460" in codes(lint_graph(graph))
    graph["meta"]["tier"] = "control"
    assert "GW460" not in codes(lint_graph(graph))


def test_index_factors_must_match_the_scenario(tmp_path):
    """IE043: the index repeats meta.factors, so the copy has to be checked.

    Before this check the two drifted silently: a factor sweep over 122
    scenarios left every index entry stale and `validate-index` still passed
    (issue #19).
    """
    from szzbench.validator import validate_index_file

    root = tmp_path / "scenarios"
    (root / "SZZ-0001").mkdir(parents=True)
    scenario = graph_scenario()
    scenario["meta"] = {"id": "SZZ-0001", "title": "A scenario", "factors": ["boundary-condition"]}
    (root / "SZZ-0001" / "scenario.yml").write_text(yaml.safe_dump(scenario, sort_keys=False))

    def index(factors):
        path = tmp_path / "index.yml"
        path.write_text(yaml.safe_dump(
            {"scenarios": [{"id": "SZZ-0001", "title": "A scenario", "factors": factors}]}, sort_keys=False))
        return path

    assert validate_index_file(index(["boundary-condition"]), root, "scenario.yml").findings == []
    stale = validate_index_file(index(["boundary_condition"]), root, "scenario.yml")
    assert [f.code for f in stale.findings] == ["IE043"]
    assert "boundary_condition" in stale.findings[0].message


def test_index_factors_of_the_wrong_type_are_reported_not_coerced(tmp_path):
    """IE044: neither side is validated before this check runs.

    `list()` on an int raises and aborts the whole command, and `list()` on a
    mapping silently compares its keys, so a wrong value passes (PR #46 review).
    """
    from szzbench.validator import validate_index_file

    root = tmp_path / "scenarios"
    (root / "SZZ-0001").mkdir(parents=True)

    def write(meta_factors):
        scenario = graph_scenario()
        scenario["meta"] = {"id": "SZZ-0001", "title": "A scenario", "factors": meta_factors}
        (root / "SZZ-0001" / "scenario.yml").write_text(yaml.safe_dump(scenario, sort_keys=False))

    def index(factors):
        path = tmp_path / "index.yml"
        path.write_text(yaml.safe_dump(
            {"scenarios": [{"id": "SZZ-0001", "title": "A scenario", "factors": factors}]}, sort_keys=False))
        return path

    # an int on the index side used to raise TypeError
    write(["boundary-condition"])
    assert [f.code for f in validate_index_file(index(1), root, "scenario.yml").findings] == ["IE044"]
    # a mapping used to compare equal, because list() keeps only its keys
    assert [f.code for f in validate_index_file(index({"boundary-condition": "incorrect-value"}),
                                                root, "scenario.yml").findings] == ["IE044"]
    # and the scenario side is just as unvalidated
    write(True)
    assert [f.code for f in validate_index_file(index(["boundary-condition"]), root, "scenario.yml").findings] == ["IE044"]


def test_index_status_must_match_the_scenario(tmp_path):
    """IE045: status is mirrored in the index too, and drifted the same way."""
    from szzbench.validator import validate_index_file

    root = tmp_path / "scenarios"
    (root / "SZZ-0001").mkdir(parents=True)
    scenario = graph_scenario()
    scenario["meta"] = {"id": "SZZ-0001", "title": "A scenario", "status": "active"}
    (root / "SZZ-0001" / "scenario.yml").write_text(yaml.safe_dump(scenario, sort_keys=False))

    def index(status):
        path = tmp_path / "index.yml"
        path.write_text(yaml.safe_dump(
            {"scenarios": [{"id": "SZZ-0001", "title": "A scenario", "status": status}]}, sort_keys=False))
        return path

    assert validate_index_file(index("active"), root, "scenario.yml").findings == []
    stale = validate_index_file(index("draft"), root, "scenario.yml")
    assert [f.code for f in stale.findings] == ["IE045"]


def test_readme_expected_history_must_match_the_operations(tmp_path):
    """GW454: the README's history block is a copy of data that lives in the YAML.

    This is how SZZG-0001/0003/0017 went stale: repairing their histories for
    the graph-1.0 freeze changed the operations, and nothing read the README.
    """
    from szzbench.graph_validator import validate_graph_scenario_file

    scenario = graph_scenario()
    scenario["meta"]["id"] = "SZZG-9900"
    path = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", scenario)
    readme = path.with_name("README.md")

    def lint_with(history: str) -> list[str]:
        readme.write_text(f"# SZZG-9900\n\n## Expected history\n\n```text\n{history}\n```\n")
        _, result = validate_graph_scenario_file(path, strict_paths=True, lint=True)
        return [f.code for f in result.findings if f.code == "GW454"]

    faithful = (f"c0: create initial state (write_file {JAVA})\n"
                f"c1: introduce bug (replace {JAVA})\n"
                f"c2: fix bug (replace {JAVA})")
    assert lint_with(faithful) == []

    # an operation the README does not mention
    assert lint_with(faithful.replace(f"c1: introduce bug (replace {JAVA})",
                                      "c1: introduce bug (write_file other.java)")) == ["GW454"]
    # a commit the scenario does not define
    assert lint_with(faithful + "\nc9: do something (replace x.java)") == ["GW454"]
    # prose READMEs carry no such block and are not linted
    readme.write_text("# SZZG-9900\n\nThe history is described in prose here.\n")
    _, result = validate_graph_scenario_file(path, strict_paths=True, lint=True)
    assert [f.code for f in result.findings if f.code == "GW454"] == []
    # and a missing README is not an error
    readme.unlink()
    _, result = validate_graph_scenario_file(path, strict_paths=True, lint=True)
    assert [f.code for f in result.findings if f.code == "GW454"] == []


def test_index_mirrors_of_slug_category_and_difficulty(tmp_path):
    """IE046: the index copies four more meta scalars, and checked none of them."""
    from szzbench.validator import validate_index_file

    root = tmp_path / "scenarios"
    (root / "SZZ-0001").mkdir(parents=True)
    scenario = graph_scenario()
    scenario["meta"] = {"id": "SZZ-0001", "title": "A scenario", "slug": "a-scenario",
                        "category": "Basic semantic line changes", "category_code": "S1",
                        "difficulty": "medium", "status": "active"}
    (root / "SZZ-0001" / "scenario.yml").write_text(yaml.safe_dump(scenario, sort_keys=False))

    def index(**overrides):
        entry = {"id": "SZZ-0001", "title": "A scenario", "slug": "a-scenario",
                 "category": "Basic semantic line changes", "category_code": "S1",
                 "difficulty": "medium", "status": "active"}
        entry.update(overrides)
        path = tmp_path / "index.yml"
        path.write_text(yaml.safe_dump({"scenarios": [entry]}, sort_keys=False))
        return path

    assert validate_index_file(index(), root, "scenario.yml").findings == []
    for key, wrong in (("slug", "other-slug"), ("category", "Omission and deletion bugs"),
                       ("category_code", "S2"), ("difficulty", "hard")):
        codes = [f.code for f in validate_index_file(index(**{key: wrong}), root, "scenario.yml").findings]
        assert codes == ["IE046"], (key, codes)


def test_gw045_does_not_fire_for_commits_git_fills_in():
    """A `revert_of` / `cherry_pick_of` commit without operations is not empty:
    the generator runs git revert / git cherry-pick for it (generator-options §3).
    Until SZZG-0124–0127 no scenario used that path, so the lint had never met it."""
    data = graph_scenario()
    data["commits"].append({"id": "c3", "branch": "main", "parents": ["c2"], "role": "intermediate", "revert_of": "c2"})
    data["commits"].append({"id": "c4", "branch": "main", "parents": ["c3"], "role": "intermediate", "cherry_pick_of": "c1"})
    data["commits"].append({"id": "c5", "branch": "main", "parents": ["c4"], "role": "intermediate", "message": "truly empty"})
    result = validate_graph_static(data, strict_paths=True)
    codes = [(f.code, f.location) for f in result.findings if f.code == "GW045"]
    assert codes == [("GW045", "commits[5]")], codes


def test_issue_documents_must_be_written_and_state_their_date():
    """GW470/GW471: tool-visible context (decisions/tool-visible-context.md) is a copy of
    `issues[].reported_at` inside a committed document; both sides are checked."""
    data = graph_scenario()
    data["commits"][1]["operations"].append({"type": "write_file", "path": "docs/issues/ISSUE-1.md",
                                             "content": "# ISSUE-1\n\nReported: 2024-01-05T10:00:00Z\n\nThe check rejects the bound.\n"})
    data["issues"] = [{"id": "ISSUE-1", "title": "t", "reported_at": "2024-01-05T10:00:00Z", "document": "docs/issues/ISSUE-1.md"}]
    assert [f.code for f in validate_graph_static(data, strict_paths=True).findings if f.code.startswith("GW47")] == []

    data["issues"][0]["reported_at"] = "2024-01-06T10:00:00Z"
    assert [f.code for f in validate_graph_static(data, strict_paths=True).findings if f.code.startswith("GW47")] == ["GW471"]

    data["issues"][0]["document"] = "docs/issues/ISSUE-9.md"
    assert [f.code for f in validate_graph_static(data, strict_paths=True).findings if f.code.startswith("GW47")] == ["GW470"]

    del data["issues"][0]["document"]
    assert [f.code for f in validate_graph_static(data, strict_paths=True).findings if f.code.startswith("GW47")] == ["GW470"]


def test_issue_document_checks_survive_malformed_containers():
    """The containers GE030/GE044 diagnose are still raw when the issue-document check runs
    (PR #56 review): a TypeError there replaced the structured diagnostics with a traceback."""
    data = graph_scenario()
    data["issues"] = [{"id": "ISSUE-1", "title": "t", "reported_at": "2024-01-05T10:00:00Z", "document": "docs/issues/ISSUE-1.md"}]
    bad_ops = dict(data); bad_ops["commits"] = [dict(data["commits"][0], operations=42)] + data["commits"][1:]
    codes = [f.code for f in validate_graph_static(bad_ops, strict_paths=True).findings]
    assert "GE044" in codes and "GW470" in codes, codes          # reported, not raised
    bad_commits = dict(data); bad_commits["commits"] = 42
    codes = [f.code for f in validate_graph_static(bad_commits, strict_paths=True).findings]
    assert "GE030" in codes, codes
    no_issues = dict(data); no_issues["issues"] = []
    validate_graph_static(no_issues, strict_paths=True)          # must not raise


def test_issue_document_dates_are_compared_as_timestamps_not_strings():
    """PyYAML turns an unquoted ISO 8601 value into a datetime; gating on str let a wrong date
    pass with zero findings (PR #56 review). Values are normalised and compared as instants."""
    from datetime import datetime, timezone

    def scenario(reported_at, doc_line="Reported: 2024-01-05T10:00:00Z"):
        data = graph_scenario()
        data["commits"][1]["operations"].append({"type": "write_file", "path": "docs/issues/ISSUE-1.md",
                                                 "content": f"# ISSUE-1\n\n{doc_line}\n\nThe check rejects the bound.\n"})
        data["issues"] = [{"id": "ISSUE-1", "title": "t", "reported_at": reported_at, "document": "docs/issues/ISSUE-1.md"}]
        return [f.code for f in validate_graph_static(data, strict_paths=True).findings if f.code.startswith("GW47")]

    utc = timezone.utc
    assert scenario(datetime(2024, 1, 5, 10, 0, tzinfo=utc)) == []                       # unquoted, same instant
    assert scenario(datetime(2025, 1, 5, 10, 0, tzinfo=utc)) == ["GW471"]                # unquoted, wrong year
    assert scenario("2024-01-05T19:00:00+09:00") == []                                    # same instant, other offset
    assert scenario(42) == ["GW472"]                                                       # not a timestamp at all
    assert scenario("2024-01-05T10:00:00Z", doc_line="Filed on 2024-01-05.") == ["GW471"]  # document has no Reported: line
    assert scenario("2024-01-05T10:00:00Z", doc_line="Reported: yesterday") == ["GW471"]   # document's value unparsable


# --- author coincidence lint (#43) ---------------------------------------------

def _with_authors(data: dict, *authors: str) -> dict:
    for commit, author in zip(data["commits"], authors):
        commit["author"] = f"{author} <{author.lower()}@example.com>"
    return data


def test_author_coincidence_on_a_one_commit_oracle_is_information():
    """An author who wrote exactly the single required commit: the author baseline solves the
    scenario by coincidence, but one-commit oracles are cheap to solve anyway -> I413 / GI413."""
    result = lint_classic(_with_authors(classic_scenario(), "Ann", "Bob", "Ann"))
    assert codes(result) == [] and info_codes(result) == ["I413"]
    finding = result.findings[0]
    assert "'Bob <bob@example.com>'" in finding.message and "['c1']" in finding.message and "(explicit)" in finding.message
    result = lint_graph(_with_authors(graph_scenario(), "Ann", "Bob", "Ann"))
    assert codes(result) == [] and info_codes(result) == ["GI413"]


def test_no_author_coincidence_when_the_author_also_wrote_another_commit():
    for result in (lint_classic(_with_authors(classic_scenario(), "Ann", "Ann", "Bob")),
                   lint_graph(_with_authors(graph_scenario(), "Ann", "Ann", "Bob"))):
        assert codes(result) == [] and info_codes(result) == []


def test_author_coincidence_on_a_multi_commit_oracle_is_a_warning():
    """SZZG-0118 and SZZG-0028 (#41, #42): two required commits, one author, nothing else by that
    author -> GW413. Giving one of them another author clears it."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"] = [{"commit": "c0", "role": "direct"}, {"commit": "c1", "role": "direct"}]
    data["expected_szz"]["commit_level"]["required"] = ["c0", "c1"]
    result = lint_graph(_with_authors(deepcopy(data), "Ann", "Ann", "Bob"))
    assert codes(result) == ["GW413"]
    assert "['c0', 'c1']" in result.findings[0].message and result.findings[0].location == "commits"
    cleared = lint_graph(_with_authors(deepcopy(data), "Ann", "Cid", "Bob"))
    assert codes(cleared) == [] and info_codes(cleared) == []


def test_author_coincidence_resolves_the_oracle_like_the_evaluator():
    """A default evaluation variant supplies the oracle (SZZG-0022 style); reading
    expected_szz.commit_level directly would see nothing."""
    data = graph_scenario()
    data["expected_szz"] = {
        "evaluation_variants": [
            {"name": "direct-only", "commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}},
        ],
        "default_variant": "direct-only",
    }
    assert info_codes(lint_graph(_with_authors(deepcopy(data), "Ann", "Bob", "Ann"))) == ["GI413"]
    # without explicit authors the generator's deterministic rotation decides; the lint must reproduce it
    from collections import defaultdict
    from szzbench.gitutils import resolve_commit_metadata
    plain = deepcopy(data)
    for commit in plain["commits"]:
        commit.pop("author", None)
    owned = defaultdict(set)
    for index, commit in enumerate(plain["commits"]):
        owned[resolve_commit_metadata(plain, commit, index).author].add(commit["id"])
    result = lint_graph(plain)
    assert codes(result) == []
    if any(ids == {"c1"} for ids in owned.values()):
        assert info_codes(result) == ["GI413"] and "generator-assigned" in result.findings[0].message
    else:
        assert info_codes(result) == []


def test_author_coincidence_compares_identities_as_git_records_them():
    """PR #64 review: two spellings of one identity must be one author. `Aiko Tanaka <a@x>` and
    `Aiko Tanaka<a@x>` are the same Git author, so together they own {c0, c1} -> GW413."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"] = [{"commit": "c0", "role": "direct"}, {"commit": "c1", "role": "direct"}]
    data["expected_szz"]["commit_level"]["required"] = ["c0", "c1"]
    data["commits"][0]["author"] = "Aiko Tanaka <aiko.tanaka@example.com>"
    data["commits"][1]["author"] = "Aiko Tanaka<aiko.tanaka@example.com>"
    data["commits"][2]["author"] = "Bob Example <bob@example.com>"
    result = lint_graph(data)
    assert codes(result) == ["GW413"]
    assert "'Aiko Tanaka <aiko.tanaka@example.com>'" in result.findings[0].message   # the canonical spelling
    # a name without an e-mail gets the benchmark's default address, like the generator gives it
    from szzbench.gitutils import canonical_author
    assert canonical_author(" Bob ") == "Bob <szz-benchmark@example.com>"
    assert canonical_author("A <a@x>") == canonical_author("A<a@x>") == canonical_author("  A   <a@x>  ")


def _generated_history_fixture(shared_author: str) -> dict:
    """graph fixture whose fix commit also expands one commit_generator commit; c0 and c1 (the oracle)
    share `shared_author`."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"] = [{"commit": "c0", "role": "direct"}, {"commit": "c1", "role": "direct"}]
    data["expected_szz"]["commit_level"]["required"] = ["c0", "c1"]
    data["commits"][0]["author"] = shared_author
    data["commits"][1]["author"] = shared_author
    data["commits"][2]["author"] = "Bob Example <bob@example.com>"
    data["commits"][2]["operations"].insert(0, {"type": "commit_generator", "generator": "catalog_sync", "count": 1, "files": 1, "path": "generated/catalog"})
    return data


def test_author_coincidence_counts_the_commits_commit_generator_expands():
    """PR #64 review: the author baseline sees generated commits through `git log --all`. When the
    generated commit's deterministic author is the required commits' author, that author's set is
    {c0, c1, c2.g1}, not the oracle, and there is no coincidence to report."""
    from szzbench.gitutils import canonical_author, deterministic_author
    generated_author = canonical_author(deterministic_author("SZZG-9900", "c2.g1"))
    with_generated = lint_graph(_generated_history_fixture(generated_author))
    assert codes(with_generated) == [] and info_codes(with_generated) == []
    other = "Zed Example <zed@example.com>"
    assert other != generated_author
    warned = lint_graph(_generated_history_fixture(other))
    assert codes(warned) == ["GW413"]


def test_history_model_matches_the_generated_repository(tmp_path):
    """`resolved_commit_authors` is what the lint and the leakage guard reason about; it must list every
    commit of the generated repository, generated ones included, with the author Git records."""
    from szzbench.gitutils import deterministic_author, canonical_author, resolved_commit_authors
    from szzbench.graph_generator import generate_graph_repository
    import subprocess
    data = _generated_history_fixture(canonical_author(deterministic_author("SZZG-9900", "c2.g1")))
    path = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", data)
    commit_map, verify = generate_graph_repository(path, tmp_path / "out", force=True)
    assert not verify.has_errors(), verify.to_dict()
    log = subprocess.run(["git", "log", "--all", "--format=%H%x00%an <%ae>"], cwd=tmp_path / "out" / "repo",
                         capture_output=True, text=True, check=True).stdout
    by_hash = {line.split("\x00")[0]: line.split("\x00")[1] for line in log.splitlines() if line}
    from_git = {cid: by_hash[entry["hash"]] for cid, entry in commit_map.items()}
    assert dict(resolved_commit_authors(data)) == from_git
    assert "c2.g1" in from_git


def _scratch_branch_fixture(*, delete: bool, tag: bool = False, keep_branch: bool = False) -> dict:
    """SZZG-0007-shaped reproduction from the PR #64 review: Aiko writes the two required commits and a
    commit d1 on a scratch branch; the lifecycle deletes the branch, optionally keeping d1 reachable
    through a tag or a second branch."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"] = [{"commit": "c0", "role": "direct"}, {"commit": "c1", "role": "direct"}]
    data["expected_szz"]["commit_level"]["required"] = ["c0", "c1"]
    aiko = "Aiko Tanaka <aiko.tanaka@example.com>"
    data["commits"][0]["author"] = aiko
    data["commits"][1]["author"] = aiko
    data["commits"][2]["author"] = "Bob Example <bob@example.com>"
    scratch = {"id": "d1", "branch": "scratch", "parents": ["c1"], "author": aiko, "message": "Document pagination usage",
               "role": "intermediate", "operations": [{"type": "write_file", "path": "docs/paging.md", "content": "Pagination usage examples.\n"}]}
    data["commits"].insert(2, scratch)
    if keep_branch:
        data["commits"].append({"id": "k1", "branch": "keep", "parents": ["d1"], "author": "Bob Example <bob@example.com>",
                                "message": "Keep the scratch work on another branch", "role": "intermediate",
                                "operations": [{"type": "write_file", "path": "docs/keep.md", "content": "kept\n"}]})
    lifecycle = {}
    if delete:
        lifecycle["delete_branches"] = ["scratch"]
    if tag:
        lifecycle["tags"] = [{"name": "scratch-tip", "commit": "d1"}]
    if lifecycle:
        data["graph"] = {"model": "commit_dag", "ref_lifecycle": lifecycle}
    return data


def test_author_coincidence_ignores_commits_no_ref_reaches_after_the_lifecycle():
    """PR #64 re-review: after `delete_branches: [scratch]` Aiko's *visible* commits are exactly
    {c0, c1}, so the author baseline returns the oracle and the lint must warn."""
    assert codes(lint_graph(_scratch_branch_fixture(delete=True))) == ["GW413"]
    # d1 still reachable: through its branch, through a tag, or through another branch that kept it
    for data in (_scratch_branch_fixture(delete=False), _scratch_branch_fixture(delete=True, tag=True),
                 _scratch_branch_fixture(delete=True, keep_branch=True)):
        result = lint_graph(data)
        assert codes(result) == [] and info_codes(result) == [], data.get("graph")


@pytest.mark.parametrize("variant", ["deleted", "deleted-but-tagged", "deleted-but-kept-by-a-branch", "not-deleted"])
def test_history_model_matches_git_log_all_after_the_ref_lifecycle(tmp_path, variant):
    """`resolved_commit_authors` must list exactly the commits `git log --all` sees, whatever the lifecycle did."""
    from szzbench.gitutils import resolved_commit_authors
    from szzbench.graph_generator import generate_graph_repository
    import subprocess
    data = {"deleted": _scratch_branch_fixture(delete=True), "deleted-but-tagged": _scratch_branch_fixture(delete=True, tag=True),
            "deleted-but-kept-by-a-branch": _scratch_branch_fixture(delete=True, keep_branch=True),
            "not-deleted": _scratch_branch_fixture(delete=False)}[variant]
    path = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", data)
    commit_map, verify = generate_graph_repository(path, tmp_path / "out", force=True)
    assert not verify.has_errors(), verify.to_dict()
    log = subprocess.run(["git", "log", "--all", "--format=%H%x00%an <%ae>"], cwd=tmp_path / "out" / "repo",
                         capture_output=True, text=True, check=True).stdout
    by_hash = {l.split("\x00")[0]: l.split("\x00")[1] for l in log.splitlines() if l}
    from_git = {cid: by_hash[e["hash"]] for cid, e in commit_map.items() if e["hash"] in by_hash}
    assert dict(resolved_commit_authors(data)) == from_git
    assert ("d1" in from_git) == (variant != "deleted")


@pytest.mark.parametrize("sid", ["SZZG-0072", "SZZG-0122", "SZZG-0075"])
def test_history_model_matches_the_shipped_scenarios_with_a_ref_lifecycle(tmp_path, sid):
    """The shipped scenarios whose lifecycle deletes a branch (0072, 0122) or adds a tag (0075)."""
    from szzbench.gitutils import resolved_commit_authors
    from szzbench.graph_generator import generate_graph_repository
    import subprocess
    root = Path(__file__).resolve().parent.parent
    path = root / "advanced-scenarios" / sid / "scenario.graph.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    commit_map, verify = generate_graph_repository(path, tmp_path / sid, force=True)
    assert not verify.has_errors(), verify.to_dict()
    log = subprocess.run(["git", "log", "--all", "--format=%H%x00%an <%ae>"], cwd=tmp_path / sid / "repo",
                         capture_output=True, text=True, check=True).stdout
    by_hash = {l.split("\x00")[0]: l.split("\x00")[1] for l in log.splitlines() if l}
    from_git = {cid: by_hash[e["hash"]] for cid, e in commit_map.items() if e["hash"] in by_hash}
    assert dict(resolved_commit_authors(data)) == from_git
    assert len(from_git) < len(commit_map) or sid == "SZZG-0075"


def _tagged_generated_chain_fixture(*, count: int, tag_at: str | None, shared_author: str = "Dana Okafor <dana.okafor@example.com>") -> dict:
    """PR #64 third review: Dana writes the two required commits; a scratch-branch commit d1 by Bob expands
    `count` generated commits d1.g1..d1.gN (the generator attributes them by its rotation); the scratch
    branch is deleted and a tag may point into the generated chain."""
    data = graph_scenario()
    data["bugs"][0]["bug_introducing_commits"] = [{"commit": "c0", "role": "direct"}, {"commit": "c1", "role": "direct"}]
    data["expected_szz"]["commit_level"]["required"] = ["c0", "c1"]
    data["commits"][0]["author"] = shared_author
    data["commits"][1]["author"] = shared_author
    data["commits"][2]["author"] = "Bob Example <bob@example.com>"
    data["commits"].insert(2, {"id": "d1", "branch": "scratch", "parents": ["c1"], "author": "Bob Example <bob@example.com>",
                               "message": "Document pagination usage", "role": "intermediate",
                               "operations": [{"type": "commit_generator", "generator": "catalog_sync", "count": count, "files": 1, "path": "generated/catalog"},
                                              {"type": "write_file", "path": "docs/paging.md", "content": "Pagination usage examples.\n"}]})
    lifecycle = {"delete_branches": ["scratch"]}
    if tag_at:
        lifecycle["tags"] = [{"name": "catalog-snapshot", "commit": tag_at}]
    data["graph"] = {"model": "commit_dag", "ref_lifecycle": lifecycle}
    return data


def test_a_tag_on_a_generated_commit_keeps_it_and_its_ancestors_reachable():
    """The generated chain sits between the owner's first parent and the owner: c1 <- d1.g1 <- d1.g2 <- d1.g3 <- d1.
    A tag at d1.g2 on the deleted scratch branch keeps d1.g1 and d1.g2 visible; d1.g3 and d1 stay unreachable."""
    from szzbench.gitutils import reachable_commit_ids, resolved_commit_authors
    data = _tagged_generated_chain_fixture(count=3, tag_at="d1.g2")
    reachable = reachable_commit_ids(data)
    assert {"c0", "c1", "c2", "d1.g1", "d1.g2"} <= reachable
    assert not {"d1", "d1.g3"} & reachable
    ids = [cid for cid, _ in resolved_commit_authors(data)]
    assert "d1.g1" in ids and "d1.g2" in ids and "d1.g3" not in ids and "d1" not in ids
    # without the tag the whole scratch chain is gone
    assert not {"d1", "d1.g1", "d1.g2", "d1.g3"} & reachable_commit_ids(_tagged_generated_chain_fixture(count=3, tag_at=None))


def test_author_coincidence_sees_a_tagged_generated_commit_by_the_same_author():
    """The review's reproduction: the tag keeps d1.g1 visible, and when the rotation gives d1.g1 to the
    required commits' author, her visible set is {c0, c1, d1.g1} and there is nothing to warn about."""
    from szzbench.gitutils import canonical_author, deterministic_author
    generated_author = canonical_author(deterministic_author("SZZG-9900", "d1.g1"))
    quiet = lint_graph(_tagged_generated_chain_fixture(count=1, tag_at="d1.g1", shared_author=generated_author))
    assert codes(quiet) == [] and info_codes(quiet) == []
    # the same history with the tag on the owner's chain removed: d1.g1 is unreachable and the coincidence is real
    assert codes(lint_graph(_tagged_generated_chain_fixture(count=1, tag_at=None, shared_author=generated_author))) == ["GW413"]


@pytest.mark.parametrize("tag_at", ["d1.g1", "d1.g2", None])
def test_history_model_matches_git_log_all_with_a_tag_inside_a_generated_chain(tmp_path, tag_at):
    from szzbench.gitutils import resolved_commit_authors
    from szzbench.graph_generator import generate_graph_repository
    import subprocess
    data = _tagged_generated_chain_fixture(count=3, tag_at=tag_at)
    path = write_yaml(tmp_path / "SZZG-9900" / "scenario.graph.yml", data)
    commit_map, verify = generate_graph_repository(path, tmp_path / "out", force=True)
    assert not verify.has_errors(), verify.to_dict()
    log = subprocess.run(["git", "log", "--all", "--format=%H%x00%an <%ae>"], cwd=tmp_path / "out" / "repo",
                         capture_output=True, text=True, check=True).stdout
    by_hash = {l.split("\x00")[0]: l.split("\x00")[1] for l in log.splitlines() if l}
    from_git = {cid: by_hash[e["hash"]] for cid, e in commit_map.items() if e["hash"] in by_hash}
    assert dict(resolved_commit_authors(data)) == from_git
    expected_generated = {"d1.g1": {"d1.g1"}, "d1.g2": {"d1.g1", "d1.g2"}, None: set()}[tag_at]
    assert {cid for cid in from_git if cid.startswith("d1")} == expected_generated


def test_difficulty_lint_requires_a_graded_value():
    """W461 / GW461: difficulty is easy, medium or hard; the graph suite's `advanced` is retired (issue #35)."""
    from szzbench.validator import SCENARIO_DIFFICULTIES

    assert SCENARIO_DIFFICULTIES == ("easy", "medium", "hard")
    data = classic_scenario()
    data["meta"].pop("difficulty", None)
    result = lint_classic(data)
    assert "W461" in codes(result)
    assert "meta.difficulty is missing" in [f.message for f in result.findings if f.code == "W461"][0]
    data["meta"]["difficulty"] = "advanced"
    assert "W461" in codes(lint_classic(data))
    for difficulty in SCENARIO_DIFFICULTIES:
        data["meta"]["difficulty"] = difficulty
        assert "W461" not in codes(lint_classic(data))

    graph = graph_scenario()
    graph["meta"]["difficulty"] = "advanced"
    assert "GW461" in codes(lint_graph(graph))
    graph["meta"]["difficulty"] = "hard"
    assert "GW461" not in codes(lint_graph(graph))


def test_every_shipped_scenario_declares_a_graded_difficulty():
    from szzbench.validator import SCENARIO_DIFFICULTIES

    root = Path(__file__).resolve().parents[1]
    for path in sorted(root.glob("scenarios/SZZ-*/scenario.yml")) + sorted(root.glob("advanced-scenarios/SZZG-*/scenario.graph.yml")):
        difficulty = yaml.safe_load(path.read_text(encoding="utf-8"))["meta"].get("difficulty")
        assert difficulty in SCENARIO_DIFFICULTIES, f"{path.parent.name}: {difficulty!r}"


def test_defeats_lint_checks_the_family_vocabulary_and_the_tier():
    """W462 / GW462: `meta.defeats` names cheap-rule families; a discriminating scenario defeats them all (issue #35)."""
    from szzbench.validator import DEFEATABLE_FAMILIES

    assert DEFEATABLE_FAMILIES == ("blame", "shape", "position")
    data = classic_scenario()
    assert "W462" not in codes(lint_classic(data))                      # optional
    data["meta"]["defeats"] = ["blame", "shape"]
    assert "W462" not in codes(lint_classic(data))
    data["meta"]["defeats"] = []
    assert "W462" not in codes(lint_classic(data))
    data["meta"]["defeats"] = ["blame", "blame-deleted-lines"]         # a rule name, not a family
    assert "W462" in codes(lint_classic(data))
    data["meta"]["defeats"] = "blame"
    assert "W462" in codes(lint_classic(data))
    data["meta"]["defeats"] = ["blame", "blame"]
    assert "W462" in codes(lint_classic(data))
    data["meta"]["defeats"] = ["blame"]
    data["meta"]["tier"] = "discriminating"
    assert "W462" in codes(lint_classic(data))                          # must list every family
    data["meta"]["defeats"] = ["blame", "shape", "position"]
    assert "W462" not in codes(lint_classic(data))

    graph = graph_scenario()
    graph["meta"]["defeats"] = ["merge"]
    assert "GW462" in codes(lint_graph(graph))
