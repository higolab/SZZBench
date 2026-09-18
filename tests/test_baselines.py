"""Cheap-baseline family (#14, #35).

The baselines exist to publish the floor a real SZZ variant has to beat, so
the tests check two things: that each predictor reads only what its family is
allowed to read, and that the runner scores them through the ordinary
evaluator rather than with its own notion of a correct answer.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from szzbench.baselines import (
    FAMILIES,
    CommitInfo,
    GitProbe,
    Scenario,
    _all_non_bfc,
    _at_index,
    _before_bfc,
    _by_author,
    _message_admits_fault,
    build_predictors,
    format_report,
    run_baselines,
)
from szzbench.graph_generator import generate_graph_repository

REPO_ROOT = Path(__file__).resolve().parents[1]


def _scenario(subjects=None, authors=None, bfc="h3") -> Scenario:
    """A four-commit history, named by hash as the predictors see it."""
    subjects = subjects or {
        "h0": "add the range check", "h1": "make the range check exclusive",
        "h2": "document the range check", "h3": "accept the bounds again"}
    authors = authors or {"h0": "A <a@x>", "h1": "B <b@x>", "h2": "A <a@x>", "h3": "C <c@x>"}
    return Scenario(
        scenario_id="SZZG-9000", suite="graph", category="G1", tier="control",
        commits=[CommitInfo(hash=h, logical_id=f"c{i}", author=authors[h], subject=subjects[h])
                 for i, h in enumerate(["h0", "h1", "h2", "h3"])],
        bfc_hashes={bfc}, repo_dir=Path("/nonexistent"),
    )


def test_position_predictors_read_only_the_order():
    scenario = _scenario()
    assert _at_index(0)(scenario) == ["h0"]
    assert _at_index(1)(scenario) == ["h1"]
    assert _at_index(9)(scenario) == []
    assert _before_bfc(scenario) == ["h2"]
    assert _all_non_bfc(scenario) == ["h0", "h1", "h2"]

    # a fix in first position has no predecessor
    assert _before_bfc(_scenario(bfc="h0")) == []


def test_author_predictor_returns_every_commit_of_that_author():
    scenario = _scenario()
    assert _by_author("A <a@x>")(scenario) == ["h0", "h2"]
    assert _by_author("B <b@x>")(scenario) == ["h1"]
    assert _by_author("nobody")(scenario) == []


def test_message_predictor_uses_its_own_vocabulary_and_skips_the_fix():
    scenario = _scenario(subjects={
        "h0": "add the range check",
        "h1": "introduce context-sensitive bug",     # hyphenated: the lint pattern misses it
        "h2": "keep the faulty line for now",        # no "bug" at all
        "h3": "fix the bug",                          # the fix may say so
    })
    assert _message_admits_fault(scenario) == ["h1", "h2"]


def test_every_predictor_declares_a_known_family():
    predictors = build_predictors([_scenario()], GitProbe())
    names = [name for name, _, _, _ in predictors]
    assert len(names) == len(set(names)), "baseline names must be unique"
    assert {family for _, family, _, _ in predictors} <= set(FAMILIES)
    # one rule per author, plus the fixed rules
    assert sum(1 for name in names if name.startswith("author:")) == 3
    for fixed in ("message-admits-fault", "position-1", "position-before-fix",
                  "shape-last-toucher", "blame-deleted-lines"):
        assert fixed in names


def _generate(tmp_path: Path, scenario_id: str, commits, bugs, tier: str = "control") -> None:
    data = {
        "schema_version": "graph-0.1-draft",
        "meta": {"id": scenario_id, "title": "baseline fixture", "category": "test",
                 "category_code": "G1", "tier": tier, "factors": []},
        "repository": {"name": scenario_id.lower(), "default_branch": "main",
                       "language": "java", "source_root": "src/main/java"},
        "graph": {"model": "commit_dag"},
        "commits": commits,
        "bugs": bugs,
    }
    directory = tmp_path / "advanced-scenarios" / scenario_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "scenario.graph.yml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    generate_graph_repository(path, tmp_path / "repos" / scenario_id / "default", force=True)


def test_runner_scores_through_the_evaluator(tmp_path):
    """A history whose BIC is the second commit must be solved by position-1."""
    java = "package example;\npublic class Range {\n  public boolean contains(int v, int lo, int hi) {\n    return v %s lo;\n  }\n}\n"
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the range check", "role": "initial",
         "operations": [{"type": "write_file", "path": "src/main/java/example/Range.java", "content": java % ">="}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "require values above the minimum",
         "role": "bug_introducing",
         "operations": [{"type": "replace", "path": "src/main/java/example/Range.java",
                         "old": "return v >= lo;", "new": "return v > lo;"}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "accept the lower bound again",
         "role": "bug_fixing",
         "operations": [{"type": "replace", "path": "src/main/java/example/Range.java",
                         "old": "return v > lo;", "new": "return v >= lo;"}]},
    ]
    bugs = [{"id": "B001",
             "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
             "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
             "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}}}]
    _generate(tmp_path, "SZZG-9000", commits, bugs)

    report = run_baselines(
        generated_root=tmp_path / "repos",
        scenarios_root=tmp_path,
        advanced_scenarios_root=tmp_path / "advanced-scenarios",
    )
    assert report["scenario_count"] == 1
    assert report["errors"] == []
    by_name = {item["name"]: item for item in report["baselines"]}
    assert by_name["position-1"]["passed"] == 1
    assert by_name["blame-deleted-lines"]["passed"] == 1
    assert by_name["position-0"]["passed"] == 0
    assert by_name["message-admits-fault"]["passed"] == 0
    assert report["solved_by_any_baseline"] == 1
    assert report["unsolved"] == []
    assert report["per_category"]["G1"] == {"total": 1, "solved": 1}

    # families can be restricted, and the text report mentions every baseline run
    only_position = run_baselines(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                                  advanced_scenarios_root=tmp_path / "advanced-scenarios",
                                  families=["position"])
    assert only_position["scenario_count"] == 1
    assert {item["family"] for item in only_position["baselines"]} == {"position"}
    # in a three-commit history the BIC is both the second commit and the one before the fix
    assert {item["name"] for item in only_position["baselines"] if item["passed"]} == {
        "position-1", "position-before-fix"}
    text = format_report(report)
    assert "position-1" in text and "solved by no baseline" in text
    assert json.dumps(report)  # the report is JSON-serialisable for --json / --out


# ---------------------------------------------------------------------------
# Regressions from the PR #37 review
# ---------------------------------------------------------------------------

JAVA = ("package example;\npublic class Range {\n  public boolean contains(int v, int lo) {\n"
        "    return v %s lo;\n  }\n}\n")
RANGE_PATH = "src/main/java/example/Range.java"


def _range_commits(bic_extra_ops=None):
    return [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the range check", "role": "initial",
         "operations": [{"type": "write_file", "path": RANGE_PATH, "content": JAVA % ">="}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "require values above the minimum",
         "role": "bug_introducing",
         "operations": (bic_extra_ops or []) + [
             {"type": "replace", "path": RANGE_PATH, "old": "return v >= lo;", "new": "return v > lo;"}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "accept the lower bound again",
         "role": "bug_fixing",
         "operations": [{"type": "replace", "path": RANGE_PATH, "old": "return v > lo;", "new": "return v >= lo;"}]},
    ]


def _range_bugs():
    return [{"id": "B001",
             "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
             "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
             "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}}}]


def _run(tmp_path):
    return run_baselines(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                         advanced_scenarios_root=tmp_path / "advanced-scenarios")


def test_commits_expanded_by_commit_generator_are_visible(tmp_path):
    """Generated commits are real history; a position rule must count them.

    With two generated commits in front of it, the bug-introducing commit is
    the *fourth* commit, so "report the second commit" must fail. Reading the
    order from the scenario YAML instead reported a false PASS.
    """
    commits = _range_commits(bic_extra_ops=[
        {"type": "commit_generator", "generator": "catalog_sync", "count": 2, "files": 1,
         "path": "generated/catalog"}])
    _generate(tmp_path, "SZZG-9001", commits, _range_bugs())
    report = _run(tmp_path)
    assert report["errors"] == []
    by_name = {item["name"]: item for item in report["baselines"]}

    from szzbench.baselines import GitProbe, _load_scenarios
    git = GitProbe()
    scenarios, _ = _load_scenarios(tmp_path / "repos", tmp_path, tmp_path / "advanced-scenarios",
                                   "default", git)
    ids = [c.logical_id for c in scenarios[0].commits]
    assert ids == ["c0", "c1.g1", "c1.g2", "c1", "c2"], ids
    assert by_name["position-1"]["passed"] == 0, "c1.g1 is the second commit, not the BIC"
    assert by_name["position-before-fix"]["passed"] == 1
    assert by_name["blame-deleted-lines"]["passed"] == 1


def test_a_file_name_with_a_space_does_not_break_the_blame_baseline(tmp_path):
    """Git terminates a `--- a/<path>` header with a tab when the path has a space."""
    path = "config/setting file.txt"
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the setting", "role": "initial",
         "operations": [{"type": "write_file", "path": path, "content": "enabled=true\n"}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "disable the feature",
         "role": "bug_introducing",
         "operations": [{"type": "replace", "path": path, "old": "enabled=true", "new": "enabled=false"}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "enable the feature again",
         "role": "bug_fixing",
         "operations": [{"type": "replace", "path": path, "old": "enabled=false", "new": "enabled=true"}]},
    ]
    _generate(tmp_path, "SZZG-9002", commits, _range_bugs())
    report = _run(tmp_path)
    assert report["errors"] == []
    by_name = {item["name"]: item for item in report["baselines"]}
    assert by_name["blame-deleted-lines"]["passed"] == 1
    assert by_name["shape-last-toucher"]["passed"] == 1


def test_an_inherited_message_is_what_the_message_predictor_reads(tmp_path):
    """A rebased commit carries its source's subject; the YAML has no message."""
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the range check", "role": "initial",
         "operations": [{"type": "write_file", "path": RANGE_PATH, "content": JAVA % ">="}]},
        {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "introduce the boundary bug",
         "role": "origin_bug_introducing",
         "operations": [{"type": "replace", "path": RANGE_PATH, "old": "return v >= lo;", "new": "return v > lo;"}]},
        {"id": "r1", "branch": "main", "parents": ["c0"], "role": "bug_introducing", "rebase_of": "f1",
         "inherit_message": True,
         "operations": [{"type": "replace", "path": RANGE_PATH, "old": "return v >= lo;", "new": "return v > lo;"}]},
        {"id": "c2", "branch": "main", "parents": ["r1"], "message": "accept the lower bound again",
         "role": "bug_fixing",
         "operations": [{"type": "replace", "path": RANGE_PATH, "old": "return v > lo;", "new": "return v >= lo;"}]},
    ]
    bugs = [{"id": "B001",
             "bug_introducing_commits": [{"commit": "r1", "role": "direct"}],
             "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
             "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["r1"]}}}]
    _generate(tmp_path, "SZZG-9003", commits, bugs)

    from szzbench.baselines import GitProbe, _load_scenarios
    git = GitProbe()
    scenarios, _ = _load_scenarios(tmp_path / "repos", tmp_path, tmp_path / "advanced-scenarios",
                                   "default", git)
    subjects = {c.logical_id: c.subject for c in scenarios[0].commits}
    assert subjects["r1"] == "introduce the boundary bug", subjects
    assert git.failures == []


def test_a_failing_git_call_is_reported_rather_than_counted_as_no_prediction(tmp_path):
    from szzbench.baselines import GitProbe

    git = GitProbe()
    assert git(tmp_path, "log", "-1") == ""
    assert len(git.failures) == 1 and "git log -1 failed" in git.failures[0]


def test_a_filtered_run_does_not_claim_promotion_candidates(tmp_path):
    """A control the selected family misses is not "solved by no cheap rule".

    Promotion asserts that *no* declared baseline solves the scenario, which a
    filtered run cannot establish; refuting a `discriminating` declaration by
    finding a solver stays valid either way (PR #39 review).
    """
    guard = ("package example;\npublic class Range {\n  public boolean valid(int v) {\n"
             "%s    return true;\n  }\n}\n")
    with_guard = guard % "    if (v < 0) {\n      return false;\n    }\n"
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the validity check", "role": "initial",
         "operations": [{"type": "write_file", "path": RANGE_PATH, "content": with_guard}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "drop the negative-value guard",
         "role": "bug_introducing",
         "operations": [{"type": "replace", "path": RANGE_PATH,
                         "old": "    if (v < 0) {\n      return false;\n    }\n", "new": ""}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "reject negative values again",
         "role": "bug_fixing",
         "operations": [{"type": "replace", "path": RANGE_PATH, "old": "    return true;",
                         "new": "    if (v < 0) {\n      return false;\n    }\n    return true;"}]},
    ]
    bugs = [{"id": "B001",
             "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
             "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
             "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}}}]
    _generate(tmp_path, "SZZG-9004", commits, bugs, tier="control")

    full = _run(tmp_path)
    by_name = {i["name"]: i for i in full["baselines"]}
    # the fix only adds lines, so blame has nothing to go on; position does
    assert by_name["blame-deleted-lines"]["passed"] == 0
    assert by_name["position-1"]["passed"] == 1
    assert full["complete"] is True
    assert full["declared_control_but_unsolved"] == []

    blame_only = run_baselines(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                               advanced_scenarios_root=tmp_path / "advanced-scenarios",
                               families=["blame"])
    assert blame_only["complete"] is False
    assert blame_only["families_run"] == ["blame"]
    assert blame_only["unsolved"] == ["SZZG-9004"]                 # scoped to the family that ran
    assert blame_only["declared_control_but_unsolved"] is None     # not assessed
    text = format_report(blame_only)
    assert "not assessed" in text and "promotion candidates" in text
    assert "SZZG-9004" not in text.split("promotion candidates")[1].split("\n")[0]

    # refuting a `discriminating` declaration still works from a partial run
    scenario_file = tmp_path / "advanced-scenarios" / "SZZG-9004" / "scenario.graph.yml"
    data = yaml.safe_load(scenario_file.read_text())
    data["meta"]["tier"] = "discriminating"
    scenario_file.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    position_only = run_baselines(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                                  advanced_scenarios_root=tmp_path / "advanced-scenarios",
                                  families=["position"])
    assert position_only["declared_discriminating_but_solved"] == ["SZZG-9004"]


def test_restricting_the_position_indices_changes_nothing(tmp_path):
    """The enumeration skips `position-k` rules that cannot score, and only those.

    `position-k` predicts a single commit, so it can only be credited when the
    commit at index k is part of the answer. The restricted enumeration is
    compared here against a full 0..n-1 sweep.
    """
    from szzbench.baselines import GitProbe, _answer_hashes, _load_scenarios, position_indices

    _generate(tmp_path, "SZZG-9005", _range_commits(), _range_bugs())
    long_history = _range_commits()
    for extra in range(3):
        long_history.insert(1, {"id": f"n{extra}", "branch": "main", "parents": [],
                                "message": f"unrelated note {extra}", "role": "intermediate",
                                "operations": [{"type": "write_file", "path": f"docs/n{extra}.md",
                                                "content": f"note {extra}\n"}]})
    for i, commit in enumerate(long_history):
        commit["parents"] = [] if i == 0 else [long_history[i - 1]["id"]]
    _generate(tmp_path, "SZZG-9006", long_history, _range_bugs())

    git = GitProbe()
    scenarios, _ = _load_scenarios(tmp_path / "repos", tmp_path, tmp_path / "advanced-scenarios",
                                   "default", git)
    answers = _answer_hashes(scenarios, tmp_path, tmp_path / "advanced-scenarios")
    restricted = position_indices(scenarios, answers)
    longest = max(len(s.commits) for s in scenarios)
    assert restricted != list(range(longest)), "the fixture must exercise the restriction"

    def solved_by_index(indices):
        out = {}
        for index in indices:
            predictor = _at_index(index)
            out[index] = {s.scenario_id for s in scenarios if predictor(s)}
        return out

    # every omitted index predicts a commit that is in no answer, so it scores nothing
    for index in set(range(longest)) - set(restricted):
        for scenario in scenarios:
            predicted = _at_index(index)(scenario)
            assert not (set(predicted) & answers.get(scenario.scenario_id, set())), index
