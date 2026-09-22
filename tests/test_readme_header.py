"""The generated README header (issue #19, `docs/scenario-readme.md`).

A scenario README opens with a header rendered from the scenario file; the
prose after it belongs to the author.  These tests pin what the header says,
that writing it never touches the prose, that `szzbench readme` and the
W455/GW455 lint agree, and that every shipped README is current.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from szzbench.cli import main
from szzbench.readme import (
    legacy_sections,
    HEADER_BEGIN,
    HEADER_END,
    NO_GRAPH_FEATURE,
    apply_header,
    check_readme,
    graph_features,
    header_rows,
    render_header,
    scenario_files,
    split_header,
)
from szzbench.scenario import load_yaml

REPO = Path(__file__).resolve().parents[1]
JAVA = "src/main/java/example/Range.java"


def _classic() -> dict:
    return {
        "schema_version": "1.0",
        "meta": {"id": "SZZ-9900", "title": "Header fixture", "slug": "header-fixture", "category": "Basic semantic line changes",
                 "category_code": "S1", "factors": ["single-bic", "single-bfc", "wrong-constant"], "difficulty": "easy",
                 "status": "active", "tier": "control"},
        "repository": {"name": "header-fixture", "default_branch": "main", "language": "java"},
        "commits": [
            {"id": "c0", "message": "Initial", "role": "initial",
             "operations": [{"type": "write_file", "path": JAVA, "content": "class Range { int min = 0; }\n"}]},
            {"id": "c1", "message": "Change", "role": "bug_introducing",
             "operations": [{"type": "replace", "path": JAVA, "old": "min = 0", "new": "min = 1"}]},
            {"id": "c2", "message": "Restore", "role": "bug_fixing",
             "operations": [{"type": "replace", "path": JAVA, "old": "min = 1", "new": "min = 0"}]},
        ],
        "bugs": [{"id": "B001", "title": "Wrong minimum", "bug_fixing_commit": "c2", "bug_introducing_commits": ["c1"],
                  "fault": {"file": JAVA, "commit": "c1", "statement": "min = 1"},
                  "fix": {"file": JAVA, "commit": "c2", "statement": "min = 0"},
                  "expected_szz": {"commit_level": {"true_positives": ["c1"], "false_positives_allowed": [],
                                                    "known_distractors": ["c0"]}}}],
        "checks": [],
    }


def _graph() -> dict:
    return {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "Graph header fixture", "slug": "graph-header-fixture",
                 "category": "Branch, merge, cherry-pick, backport, and release branches", "category_code": "G4",
                 "factors": ["branch-merge", "single-bic", "single-bfc"], "difficulty": "advanced", "status": "active",
                 "tier": "control"},
        "repository": {"name": "graph-header-fixture", "default_branch": "main", "language": "java"},
        "graph": {},
        "commits": [
            {"id": "c0", "branch": "main", "parents": [], "message": "Initial", "role": "initial",
             "operations": [{"type": "write_file", "path": JAVA, "content": "class Range { int min = 0; }\n"}]},
            {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "Change", "role": "bug_introducing",
             "operations": [{"type": "replace", "path": JAVA, "old": "min = 0", "new": "min = 1"}]},
            {"id": "c2", "branch": "main", "parents": ["c0", "f1"], "message": "Merge feature", "role": "merge",
             "operations": []},
            {"id": "c3", "branch": "main", "parents": ["c2"], "message": "Restore", "role": "bug_fixing",
             "operations": [{"type": "replace", "path": JAVA, "old": "min = 1", "new": "min = 0"}]},
        ],
        "bugs": [{"id": "B001", "title": "Wrong minimum",
                  "bug_introducing_commits": [{"commit": "f1", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c3", "role": "complete_fix"}],
                  "faults": [{"file": JAVA, "commit": "f1", "statement": "min = 1"}],
                  "fixes": [{"file": JAVA, "commit": "c3", "statement": "min = 0"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["f1"]}},
    }


def _rows(data: dict, suite: str) -> dict[str, str]:
    return dict(header_rows(data, suite))


# --- what the header says ------------------------------------------------------------

def test_classic_header_states_the_metadata_and_the_resolved_oracle():
    header = render_header(_classic(), "scenarios")
    assert header.startswith("# SZZ-9900: Header fixture\n\n" + HEADER_BEGIN + "\n")
    assert header.endswith(HEADER_END + "\n")
    rows = _rows(_classic(), "scenarios")
    assert rows["category"] == "`S1` Basic semantic line changes"
    assert rows["tier"] == "`control`"
    assert rows["status"] == "`active`"
    assert rows["difficulty"] == "`easy`"
    assert rows["language"] == "`java`"
    assert rows["factors"] == "`single-bic`, `single-bfc`, `wrong-constant`"
    assert rows["oracle"] == "`exact_set`; required `c1`; known distractors `c0` · BFC `c2`"
    assert "graph features" not in rows


def test_graph_header_lists_the_graph_only_features_it_uses():
    rows = _rows(_graph(), "advanced-scenarios")
    assert rows["category"] == "`G4` Branch, merge, cherry-pick, backport, and release branches"
    assert rows["oracle"] == "`exact_set`; required `f1` · BFC `c3`"
    assert rows["graph features"] == "2 branches; merge commit `c2`"


def test_graph_features_cover_history_operations_oracle_and_context():
    data = _graph()
    data["commits"][1]["rebase_of"] = "x1"
    data["commits"][3]["operations"].append({"type": "rename_file", "from": JAVA, "to": "src/main/java/example/R.java"})
    data["graph"]["ref_lifecycle"] = {"delete_branches": ["feature"]}
    data["bugs"][0]["bug_introducing_commits"].append({"commit": "c0", "role": "origin"})
    data["bugs"][0]["origin_faults"] = [{"file": JAVA, "commit": "c0", "statement": "min = 0"}]
    data["expected_szz"]["commit_level"]["evaluation_policy"] = "relaxed_with_related"
    data["expected_szz"]["evaluation_variants"] = [
        {"name": "origin-aware", "commit_level": {"evaluation_policy": "relaxed_with_related", "required": ["f1"],
                                                  "acceptable_related": [{"commit": "c0", "credit": 0.5}]}}]
    data["issues"] = [{"id": "ISSUE-1", "title": "Minimum is wrong"}]
    assert graph_features(data) == [
        "2 branches", "merge commit `c2`", "rebase `f1`", "ref lifecycle", "operation `rename_file`",
        "2 BICs", "origin faults", "policy `relaxed_with_related`", "1 evaluation variant (`origin-aware`)", "`issues`",
    ]
    rows = _rows(data, "advanced-scenarios")
    assert rows["oracle"] == ("default: `relaxed_with_related`; required `f1` · "
                              "`origin-aware`: `relaxed_with_related`; required `f1`; acceptable `c0` (credit 0.5) · BFC `c3`")


def test_a_graph_scenario_with_no_graph_only_feature_says_so():
    data = _graph()
    data["commits"] = [c for c in data["commits"] if c["id"] != "c2"]
    for commit in data["commits"]:
        commit["branch"] = "main"
    data["commits"][2]["parents"] = ["f1"]
    assert graph_features(data) == []
    assert _rows(data, "advanced-scenarios")["graph features"] == NO_GRAPH_FEATURE


def test_top_k_and_expect_no_bic_oracles_render_the_way_the_evaluator_reads_them():
    data = _graph()
    data["expected_szz"]["commit_level"] = {"evaluation_policy": "top_k", "relevant": ["f1"], "k_values": [1, 3],
                                            "status_k": 1, "related_but_not_correct": ["c2"]}
    assert _rows(data, "advanced-scenarios")["oracle"] == (
        "`top_k`; relevant `f1`; k = 1, 3; status at k = 1; related but not correct `c2` · BFC `c3`")
    data["expected_szz"]["commit_level"] = {"evaluation_policy": "exact_set", "expect_no_bic": True,
                                            "known_distractors": ["f1"]}
    data["bugs"][0]["bug_introducing_commits"] = []
    assert _rows(data, "advanced-scenarios")["oracle"] == "`exact_set`; expects no BIC; known distractors `f1` · BFC `c3`"


# --- writing never touches the prose ---------------------------------------------------

PROSE = """## Purpose

Hand-written prose with a `## Factors`-like mention inline that must survive.

## Commit structure

- `c0`: initial
- `c1`: the BIC

## Factors

- `single-bic`
- `stale-copy`

## Expected behavior

Report `c1`.
"""


def test_first_write_inserts_the_header_and_drops_the_factor_copy():
    header = render_header(_classic(), "scenarios")
    text = "# SZZ-9900: Header fixture\n\n" + PROSE
    assert check_readme(text, header) == [
        "has no generated header",
        "carries a `## Factors` section, a hand-written copy of what the header states",
    ]
    written = apply_header(text, header)
    assert written.startswith(header + "\n## Purpose\n")
    assert not any(line.startswith("## Factors") for line in written.splitlines())
    assert "`## Factors`-like mention inline" in written
    assert "## Commit structure\n\n- `c0`: initial\n- `c1`: the BIC\n\n## Expected behavior\n\nReport `c1`.\n" in written
    assert check_readme(written, header) == []
    assert apply_header(written, header) == written, "a second write changes nothing"


def test_a_legacy_source_section_is_dropped_too():
    header = render_header(_graph(), "advanced-scenarios")
    text = "# SZZG-9900: Graph header fixture\n\n## Source\n\n- Category: Branch and merge scenarios\n\n## Purpose\n\nProse.\n"
    written = apply_header(text, header)
    assert "## Source" not in written and "Category:" not in written
    assert written.endswith(HEADER_END + "\n\n## Purpose\n\nProse.\n")


def test_a_stale_header_is_replaced_and_the_prose_after_it_is_kept():
    data = _classic()
    header = render_header(data, "scenarios")
    text = apply_header("# SZZ-9900: Header fixture\n\n## Purpose\n\nProse.\n", header)
    data["meta"]["factors"].append("off-by-one")
    data["meta"]["tier"] = "discriminating"
    fresh = render_header(data, "scenarios")
    problems = check_readme(text, fresh)
    assert len(problems) == 1 and problems[0].startswith("header is stale: ")
    assert "`control`" in problems[0] and "`discriminating`" in problems[0]
    rewritten = apply_header(text, fresh)
    assert rewritten == fresh + "\n## Purpose\n\nProse.\n"
    assert split_header(rewritten) == (fresh, "\n## Purpose\n\nProse.\n")


# --- the command and the lint agree ----------------------------------------------------

def _write_scenario(tmp_path: Path, data: dict) -> Path:
    name = "scenario.graph.yml" if data["meta"]["id"].startswith("SZZG") else "scenario.yml"
    path = tmp_path / data["meta"]["id"] / name
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_readme_command_checks_then_writes(tmp_path, capsys):
    classic = _write_scenario(tmp_path, _classic())
    graph = _write_scenario(tmp_path, _graph())
    classic.with_name("README.md").write_text("# SZZ-9900: Header fixture\n\n## Purpose\n\nProse.\n")
    graph.with_name("README.md").write_text("# SZZG-9900: Graph header fixture\n\n## Purpose\n\nGraph prose.\n")

    assert main(["readme", str(classic), str(graph.parent)]) == 1
    out = capsys.readouterr().out
    assert "has no generated header" in out and "2 stale or missing" in out

    assert main(["readme", "--write", str(classic), str(graph.parent)]) == 0
    out = capsys.readouterr().out
    assert "rewrote:" in out and "2 rewritten" in out
    assert classic.with_name("README.md").read_text().startswith(render_header(_classic(), "scenarios"))
    assert graph.with_name("README.md").read_text().endswith("\n## Purpose\n\nGraph prose.\n")

    assert main(["readme", str(classic), str(graph.parent)]) == 0
    assert "2 README header(s) current" in capsys.readouterr().out


def test_lint_reports_a_missing_or_stale_header(tmp_path):
    from szzbench.graph_validator import validate_graph_scenario_file
    from szzbench.validator import validate_scenario_file

    classic = _write_scenario(tmp_path, _classic())
    graph = _write_scenario(tmp_path, _graph())

    def classic_codes():
        _, result, _ = validate_scenario_file(classic, lint=True)
        return [f.code for f in result.findings if f.code.endswith("455")]

    def graph_codes():
        _, result = validate_graph_scenario_file(graph, strict_paths=True, lint=True)
        return [f.code for f in result.findings if f.code.endswith("455")]

    # no README: nothing to compare, not a finding
    assert classic_codes() == [] and graph_codes() == []
    classic.with_name("README.md").write_text("# SZZ-9900: Header fixture\n\n## Purpose\n\nProse.\n")
    graph.with_name("README.md").write_text("# SZZG-9900: Graph header fixture\n\n## Factors\n\n- `branch-merge`\n")
    assert classic_codes() == ["W455"]
    assert graph_codes() == ["GW455", "GW455"], "missing header and a Factors copy are two findings"
    assert main(["readme", "--write", str(classic), str(graph)]) == 0
    assert classic_codes() == [] and graph_codes() == []
    # the YAML changes under the README
    data = deepcopy(_classic())
    data["meta"]["factors"].append("off-by-one")
    classic.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    assert classic_codes() == ["W455"]


def test_new_scenario_skeletons_start_with_a_current_header(tmp_path):
    root = tmp_path / "scenarios"
    assert main(["new-scenario", "--title", "Header skeleton", "--category", "S1", "--root", str(root),
                 "--factor", "single-bic"]) == 0
    scenario = root / "SZZ-0001" / "scenario.yml"
    data, _ = load_yaml(scenario)
    readme = scenario.with_name("README.md").read_text()
    assert readme.startswith(render_header(data, "scenarios"))
    assert check_readme(readme, render_header(data, "scenarios")) == []
    assert "## Purpose" in readme

    groot = tmp_path / "advanced-scenarios"
    assert main(["new-graph-scenario", "--title", "Graph header skeleton", "--category", "G4", "--root", str(groot),
                 "--factor", "branch-merge"]) == 0
    gscenario = groot / "SZZG-0001" / "scenario.graph.yml"
    gdata, _ = load_yaml(gscenario)
    greadme = gscenario.with_name("README.md").read_text()
    assert greadme.startswith(render_header(gdata, "advanced-scenarios"))
    assert "## Expected history" in greadme


# --- the shipped suites -------------------------------------------------------------------

@pytest.mark.parametrize("scenario_path", scenario_files(REPO / "scenarios", REPO / "advanced-scenarios"),
                         ids=lambda p: p.parent.name)
def test_every_shipped_readme_header_is_current(scenario_path: Path):
    """Regenerate with `szzbench readme --write` when a scenario's metadata or oracle changes."""
    from szzbench.readme import suite_of

    data, result = load_yaml(scenario_path)
    assert data is not None, result.findings
    text = scenario_path.with_name("README.md").read_text(encoding="utf-8")
    assert check_readme(text, render_header(data, suite_of(scenario_path))) == []


# --- the body is the author's, byte for byte (PR #66 review) ---------------------------

FENCED_BODY = """## Evidence

The fault is in this Markdown input:

```markdown
## Source
User-authored source text.
```

And this one uses tildes:

~~~
## Factors
- not a section either
~~~

A triple-quoted value with two blank lines inside it:

```python
text = \"\"\"first


last\"\"\"
assert text.count("\\n") == 3
```

This explanation must survive.


## Expected behavior

Keep every input line.
"""


def test_headings_inside_fenced_code_are_not_legacy_sections():
    header = render_header(_classic(), "scenarios")
    text = header + "\n" + FENCED_BODY
    assert check_readme(text, header) == []
    assert apply_header(text, header) == text, "nothing to do, nothing changed"


def test_an_update_replaces_only_the_header_and_keeps_the_body_byte_for_byte():
    data = _classic()
    text = render_header(data, "scenarios") + "\n" + FENCED_BODY
    data["meta"]["title"] = "Header fixture, retitled"
    fresh = render_header(data, "scenarios")
    assert check_readme(text, fresh)[0].startswith("header is stale: ")
    written = apply_header(text, fresh)
    assert written == fresh + "\n" + FENCED_BODY
    assert "first\n\n\nlast" in written and written.count("\n\n\n## Expected") == 1


def test_first_write_keeps_the_body_byte_for_byte_after_the_title():
    header = render_header(_classic(), "scenarios")
    written = apply_header("# SZZ-9900: Header fixture\n\n\n" + FENCED_BODY, header)
    assert written == header + "\n" + FENCED_BODY


def test_a_real_legacy_section_may_contain_a_fence_and_ends_at_the_next_real_heading():
    header = render_header(_classic(), "scenarios")
    body = ("## Purpose\n\nProse.\n\n## Factors\n\n- `single-bic`\n\n```text\n## not a heading\n```\n\n"
            "## Expected behavior\n\nReport `c1`.\n")
    text = header + "\n" + body
    assert check_readme(text, header) == ["carries a `## Factors` section, a hand-written copy of what the header states"]
    assert apply_header(text, header) == header + "\n## Purpose\n\nProse.\n\n## Expected behavior\n\nReport `c1`.\n"


def test_removing_a_trailing_legacy_section_leaves_a_single_final_newline():
    header = render_header(_classic(), "scenarios")
    text = header + "\n## Purpose\n\nProse.\n\n\n## Source\n\n- Category: Old label\n"
    assert apply_header(text, header) == header + "\n## Purpose\n\nProse.\n"


def test_lint_ignores_headings_inside_fenced_code(tmp_path):
    from szzbench.validator import validate_scenario_file

    classic = _write_scenario(tmp_path, _classic())
    readme = classic.with_name("README.md")
    readme.write_text(render_header(_classic(), "scenarios") + "\n" + FENCED_BODY)
    _, result, _ = validate_scenario_file(classic, lint=True)
    assert [f.code for f in result.findings if f.code == "W455"] == []
    assert main(["readme", str(classic)]) == 0
    assert readme.read_text() == render_header(_classic(), "scenarios") + "\n" + FENCED_BODY


# --- a closing fence is markers followed by nothing (PR #66 re-review) --------------------

def _fence_suffix_body(fence: str) -> str:
    return (f"## Evidence\n\n{fence}text\n{fence}literal\n## Source\nThis is example data, not a section.\n{fence}\n\n"
            "This explanation must survive.\n\n## Expected behavior\n\nKeep all of the example.\n")


@pytest.mark.parametrize("fence", ["~~~", "```"], ids=["tilde", "backtick"])
def test_a_fence_marker_with_a_suffix_does_not_close_the_block(fence):
    header = render_header(_classic(), "scenarios")
    text = header + "\n" + _fence_suffix_body(fence)
    assert legacy_sections(text) == []
    assert check_readme(text, header) == []
    assert apply_header(text, header) == text


@pytest.mark.parametrize("fence", ["~~~", "```"], ids=["tilde", "backtick"])
def test_readme_command_and_lint_keep_a_block_open_past_a_suffixed_marker(tmp_path, fence):
    from szzbench.validator import validate_scenario_file

    classic = _write_scenario(tmp_path, _classic())
    readme = classic.with_name("README.md")
    text = render_header(_classic(), "scenarios") + "\n" + _fence_suffix_body(fence)
    readme.write_text(text)
    assert main(["readme", str(classic)]) == 0
    assert main(["readme", "--write", str(classic)]) == 0
    assert readme.read_text() == text
    _, result, _ = validate_scenario_file(classic, lint=True)
    assert [f.code for f in result.findings if f.code == "W455"] == []


def test_fence_rules_follow_commonmark_for_length_and_info_strings():
    # a longer closing fence closes; a shorter one is content; a backtick fence whose info
    # string contains a backtick is not a fence at all, so the heading after it is real
    assert legacy_sections("````\n```\n## Factors\n````\n## Source\n\n- x\n") == [(4, 7, "Source")]
    assert legacy_sections("```\n## Factors\n`````\n## Source\n") == [(3, 4, "Source")]
    assert legacy_sections("````\n## Factors\n```\n## Source\n") == []
    assert legacy_sections("```not`a`fence\n## Factors\n\n- x\n") == [(1, 4, "Factors")]
    assert legacy_sections("   ~~~\n## Factors\n   ~~~\n## Source\n") == [(3, 4, "Source")]
