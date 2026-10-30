"""Naive-baseline family (#14, #35).

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
    ABSTAIN,
    FAMILIES,
    CommitInfo,
    GitProbe,
    History,
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


def _history(subjects=None, authors=None, bfc="h3") -> History:
    """A four-commit history, named by hash as the predictors see it."""
    subjects = subjects or {
        "h0": "add the range check", "h1": "make the range check exclusive",
        "h2": "document the range check", "h3": "accept the bounds again"}
    authors = authors or {"h0": "A <a@x>", "h1": "B <b@x>", "h2": "A <a@x>", "h3": "C <c@x>"}
    return History(
        commits=[CommitInfo(hash=h, author=authors[h], subject=subjects[h]) for h in ["h0", "h1", "h2", "h3"]],
        bfc_hashes={bfc}, repo_dir=Path("/nonexistent"),
    )


def test_position_predictors_read_only_the_order():
    history = _history()
    assert _at_index(0)(history) == ["h0"]
    assert _at_index(1)(history) == ["h1"]
    assert _at_index(9)(history) == []
    assert _before_bfc(history) == ["h2"]
    assert _all_non_bfc(history) == ["h0", "h1", "h2"]

    # a fix in first position has no predecessor
    assert _before_bfc(_history(bfc="h0")) == []


def test_author_predictor_returns_every_commit_of_that_author():
    history = _history()
    assert _by_author("A <a@x>")(history) == ["h0", "h2"]
    assert _by_author("B <b@x>")(history) == ["h1"]
    assert _by_author("nobody")(history) == []


def test_message_predictor_uses_its_own_vocabulary_and_skips_the_fix():
    history = _history(subjects={
        "h0": "add the range check",
        "h1": "introduce context-sensitive bug",     # hyphenated: the lint pattern misses it
        "h2": "keep the faulty line for now",        # no "bug" at all
        "h3": "fix the bug",                          # the fix may say so
    })
    assert _message_admits_fault(history) == ["h1", "h2"]


def test_every_predictor_declares_a_known_family():
    record = Scenario(scenario_id="SZZG-9000", suite="advanced-scenarios", category="G1", tier="control",
                      history=_history(), logical_ids={})
    predictors = build_predictors([record], GitProbe())
    names = [b.name for b in predictors]
    assert len(names) == len(set(names)), "baseline names must be unique"
    assert {b.family for b in predictors} <= set(FAMILIES)
    # one rule per author, plus the fixed rules
    assert sum(1 for name in names if name.startswith("author:")) == 3
    for fixed in ("message-admits-fault", "position-1", "position-before-fix",
                  "shape-last-toucher", "blame-deleted-lines", "abstain"):
        assert fixed in names
    # exactly one rule is credited for predicting nothing
    abstaining = [b.name for b in predictors if b.scores_on_abstention]
    assert abstaining == ["abstain"]


def _generate(tmp_path: Path, scenario_id: str, commits, bugs, tier: str = "control",
              expected_szz: dict | None = None) -> None:
    data = {
        "schema_version": "graph-1.0",
        "meta": {"id": scenario_id, "title": "baseline fixture", "category": "test",
                 "category_code": "G1", "tier": tier, "factors": []},
        "repository": {"name": scenario_id.lower(), "default_branch": "main",
                       "language": "java", "source_root": "src/main/java"},
        "graph": {"model": "commit_dag"},
        "commits": commits,
        "bugs": bugs,
    }
    if expected_szz is not None:
        data["expected_szz"] = expected_szz
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
    ids = [scenarios[0].logical_ids.get(h) for h in scenarios[0].history.hashes]
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
    subjects = {scenarios[0].logical_ids.get(c.hash): c.subject for c in scenarios[0].history.commits}
    assert subjects["r1"] == "introduce the boundary bug", subjects
    assert git.failures == []


def test_a_rule_is_handed_the_history_and_nothing_the_scenario_declares(tmp_path, monkeypatch):
    """What the runner hands a rule carries no logical id, tier, category or `defeats` (issue #190).

    Every predictor and attributor is wrapped, so a field added back fails here
    whichever rule would read it; the fields are listed, not excluded.
    """
    import dataclasses

    import szzbench.baselines as baselines

    _generate(tmp_path, "SZZG-9005", _range_commits(), _range_bugs())
    handed = []

    def recording(rule):
        def call(view):
            handed.append(view)
            return rule(view)
        return call

    build = baselines.build_predictors

    def build_recording(*args, **kwargs):
        rules = build(*args, **kwargs)
        for rule in rules:
            rule.predict = recording(rule.predict)
            if rule.attribute is not None:
                rule.attribute = recording(rule.attribute)
        return rules

    monkeypatch.setattr(baselines, "build_predictors", build_recording)
    report = _run(tmp_path)
    assert report["errors"] == [] and report["scenario_count"] == 1
    assert handed
    for view in handed:
        assert [f.name for f in dataclasses.fields(view)] == ["commits", "bfc_hashes", "repo_dir"]
        for commit in view.commits:
            assert [f.name for f in dataclasses.fields(commit)] == ["hash", "author", "subject"]


def test_a_failing_git_call_is_reported_rather_than_counted_as_no_prediction(tmp_path):
    from szzbench.baselines import GitProbe

    git = GitProbe()
    assert git(tmp_path, "log", "-1") == ""
    assert len(git.failures) == 1 and "git log -1 failed" in git.failures[0]


def test_a_filtered_run_does_not_claim_promotion_candidates(tmp_path):
    """A control the selected family misses is not "solved by no naive rule".

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
    # the edit makes the output stale (issue #93): it carries a copy of the scenario
    generate_graph_repository(scenario_file, tmp_path / "repos" / "SZZG-9004" / "default", force=True)
    position_only = run_baselines(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                                  advanced_scenarios_root=tmp_path / "advanced-scenarios",
                                  families=["position"])
    assert position_only["declared_discriminating_but_solved"] == ["SZZG-9004"]


def test_the_restriction_keeps_every_passing_rule(tmp_path):
    """Skipping `position-k` rules must never drop one that would have passed.

    The first version of this check asserted that omitted predictions do not
    intersect `required`, which is the same reasoning the restriction was built
    on - and that reasoning was wrong: under `top_k` a prediction passes on a
    hit in `relevant`, which need not overlap `required`. This sweeps every
    index through the real evaluator instead (PR #40 review).
    """
    from szzbench.baselines import GitProbe, _answer_hashes, _load_scenarios, position_indices
    from szzbench.evaluator import Prediction, evaluate_prediction_map

    def op(old_text, new_text):
        return {"type": "replace", "path": RANGE_PATH, "old": old_text, "new": new_text}

    faulty, fixed = "return v > lo;", "return v >= lo;"
    java = ("package example;\npublic class Range {\n  public boolean contains(int v, int lo) {\n"
            "    return v >= lo;\n  }\n}\n")
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the range check", "role": "initial",
         "operations": [{"type": "write_file", "path": RANGE_PATH, "content": java}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "document the range check",
         "role": "intermediate",
         "operations": [{"type": "write_file", "path": "docs/a.md", "content": "a\n"}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "document the caller",
         "role": "intermediate",
         "operations": [{"type": "write_file", "path": "docs/b.md", "content": "b\n"}]},
        {"id": "c3", "branch": "main", "parents": ["c2"], "message": "require values above the minimum",
         "role": "bug_introducing", "operations": [op(fixed, faulty)]},
        {"id": "c4", "branch": "main", "parents": ["c3"], "message": "accept the lower bound again",
         "role": "bug_fixing", "operations": [op(faulty, fixed)]},
        {"id": "c5", "branch": "main", "parents": ["c4"], "message": "require it above the minimum once more",
         "role": "bug_introducing", "operations": [op(fixed, faulty)]},
        {"id": "c6", "branch": "main", "parents": ["c5"], "message": "accept the lower bound once more",
         "role": "bug_fixing", "operations": [op(faulty, fixed)]},
    ]
    bugs = [{"id": "B001",
             "bug_introducing_commits": [{"commit": "c3", "role": "origin"},
                                         {"commit": "c5", "role": "reintroducing"}],
             "bug_fixing_commits": [{"commit": "c6", "role": "complete_fix"}]}]

    # top_k credits a hit in `relevant`, which here is the origin and not the
    # required commit, so the passing rule is position-3 rather than position-5
    _generate(tmp_path, "SZZG-9200", commits, bugs, expected_szz={
        "commit_level": {"evaluation_policy": "top_k", "required": ["c5"],
                         "related_origins": ["c3"], "relevant": ["c3"], "status_k": 1}})
    # a plain exact-set scenario alongside it
    _generate(tmp_path, "SZZG-9201", commits, bugs, expected_szz={
        "commit_level": {"evaluation_policy": "exact_set", "required": ["c5"]}})

    git = GitProbe()
    scenarios, _ = _load_scenarios(tmp_path / "repos", tmp_path, tmp_path / "advanced-scenarios",
                                   "default", git)
    retained = position_indices(scenarios, _answer_hashes(scenarios, tmp_path,
                                                          tmp_path / "advanced-scenarios"))

    passing: dict[str, set[int]] = {s.scenario_id: set() for s in scenarios}
    longest = max(len(s.history.commits) for s in scenarios)
    for index in range(longest):
        predictor = _at_index(index)
        predictions = {s.scenario_id: [Prediction(scenario_id=s.scenario_id, inducing_commit=h)
                                       for h in predictor(s.history)] for s in scenarios}
        report = evaluate_prediction_map(
            {k: v for k, v in predictions.items() if v},
            generated_root=tmp_path / "repos", scenarios_root=tmp_path,
            advanced_scenarios_root=tmp_path / "advanced-scenarios", include_generated=True)
        for item in report.scenarios:
            if item.status == "PASS":
                passing[item.scenario_id].add(index)

    assert passing["SZZG-9200"] == {3}, "the fixture must exercise a relevant-only pass"
    assert passing["SZZG-9201"] == {5}
    for scenario_id, indices in passing.items():
        assert indices <= set(retained), f"{scenario_id}: dropped passing rule(s) {sorted(indices - set(retained))}"
    assert set(retained) != set(range(longest)), "the fixture must exercise the restriction"


def test_silence_is_credited_only_to_the_abstain_rule(tmp_path):
    """A rule that says nothing must not be credited for an empty oracle.

    `expect_no_bic` makes "no commit" the correct answer, so an empty
    prediction passes. Every `position-k` rule is empty on a history shorter
    than k, so scoring silence would hand each of them a free pass on that
    scenario - and the pruning that dropped such rules as worthless was wrong
    for the same reason (PR #40 review). Only the rule that exists to say
    nothing is scored on silence; the rest are credited where they predict.

    Histories of three different lengths make the out-of-range case real
    rather than hypothetical, and every claim below is read back from the real
    evaluator.
    """
    from szzbench.baselines import _answer_hashes, _load_scenarios, position_indices
    from szzbench.evaluator import Prediction, evaluate_prediction_map

    def op(old_text, new_text):
        return {"type": "replace", "path": RANGE_PATH, "old": old_text, "new": new_text}

    faulty, fixed = "return v > lo;", "return v >= lo;"
    java = JAVA % ">="

    def history(length: int, bic_index: int | None) -> list[dict]:
        """`length` commits on main; the last one is the fix."""
        commits = [{"id": "c0", "branch": "main", "parents": [], "message": "add the range check",
                    "role": "initial",
                    "operations": [{"type": "write_file", "path": RANGE_PATH, "content": java}]}]
        for index in range(1, length - 1):
            if index == bic_index:
                commits.append({"id": f"c{index}", "branch": "main", "parents": [f"c{index - 1}"],
                                "message": "require values above the minimum", "role": "bug_introducing",
                                "operations": [op(fixed, faulty)]})
            else:
                commits.append({"id": f"c{index}", "branch": "main", "parents": [f"c{index - 1}"],
                                "message": f"document step {index}", "role": "intermediate",
                                "operations": [{"type": "write_file", "path": f"docs/{index}.md",
                                                "content": f"{index}\n"}]})
        last = length - 1
        # With no bug-introducing commit the fix answers a contract that
        # changed outside the repository: the code was right when written, so
        # the fix tightens it rather than undoing an earlier edit.
        fix = op(faulty, fixed) if bic_index is not None else op(fixed, "return v >= lo && lo >= 0;")
        commits.append({"id": f"c{last}", "branch": "main", "parents": [f"c{last - 1}"],
                        "message": "accept the lower bound again" if bic_index is not None
                                   else "reject a negative lower bound", "role": "bug_fixing",
                        "operations": [fix]})
        return commits

    def bug(bic_index: int | None, length: int) -> list[dict]:
        introducing = [] if bic_index is None else [{"commit": f"c{bic_index}", "role": "direct"}]
        return [{"id": "B001", "bug_introducing_commits": introducing,
                 "bug_fixing_commits": [{"commit": f"c{length - 1}", "role": "complete_fix"}]}]

    # four commits, answer at index 1
    _generate(tmp_path, "SZZG-9300", history(4, 1), bug(1, 4), expected_szz={
        "commit_level": {"evaluation_policy": "exact_set", "required": ["c1"]}})
    # seven commits, answer at index 5 - out of range for the other two
    _generate(tmp_path, "SZZG-9301", history(7, 5), bug(5, 7), expected_szz={
        "commit_level": {"evaluation_policy": "exact_set", "required": ["c5"]}})
    # five commits, and the answer is "no commit": the fault came from outside
    _generate(tmp_path, "SZZG-9302", history(5, None), bug(None, 5), expected_szz={
        "commit_level": {"evaluation_policy": "exact_set", "required": [], "expect_no_bic": True}})

    roots = dict(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                 advanced_scenarios_root=tmp_path / "advanced-scenarios")

    # what the evaluator actually does with an explicit empty prediction (a
    # scenario with no record at all fails instead, issue #95)
    silent = evaluate_prediction_map({}, explicit_scenarios={"SZZG-9300", "SZZG-9301", "SZZG-9302"}, **roots)
    assert {i.scenario_id for i in silent.scenarios if i.status == "PASS"} == {"SZZG-9302"}, \
        "the fixture must exercise an oracle that silence satisfies"

    report = run_baselines(**roots)
    assert report["errors"] == []
    solved_by = {b["name"]: set(b["solved"]) for b in report["baselines"]}

    # the empty oracle is solved, and by exactly one rule
    assert {name for name, solved in solved_by.items() if "SZZG-9302" in solved} == {ABSTAIN}
    assert solved_by[ABSTAIN] == {"SZZG-9302"}
    assert report["unsolved"] == []

    # no other rule is credited on a scenario it makes no prediction for
    git = GitProbe()
    scenarios, _ = _load_scenarios(tmp_path / "repos", tmp_path, tmp_path / "advanced-scenarios",
                                   "default", git)
    for baseline in build_predictors(scenarios, git, _answer_hashes(scenarios, tmp_path,
                                                                   tmp_path / "advanced-scenarios")):
        if baseline.scores_on_abstention:
            continue
        quiet = {s.scenario_id for s in scenarios if not list(baseline.predict(s.history))}
        assert not (quiet & solved_by[baseline.name]), \
            f"{baseline.name} was credited without predicting: {sorted(quiet & solved_by[baseline.name])}"

    # position-5 exists, is out of range on the two shorter histories, and is
    # credited only on the one it names a commit for
    assert solved_by["position-5"] == {"SZZG-9301"}
    assert solved_by["position-1"] == {"SZZG-9300"}

    # and no index whose prediction passes is pruned from the enumeration
    retained = set(position_indices(scenarios, _answer_hashes(scenarios, tmp_path,
                                                             tmp_path / "advanced-scenarios")))
    for index in range(max(len(s.history.commits) for s in scenarios)):
        predictor = _at_index(index)
        predictions = {s.scenario_id: [Prediction(scenario_id=s.scenario_id, inducing_commit=h)
                                       for h in predictor(s.history)] for s in scenarios}
        predictions = {k: v for k, v in predictions.items() if v}
        if not predictions:
            continue
        passing = evaluate_prediction_map(predictions, include_generated=False, **roots)
        if any(i.status == "PASS" for i in passing.scenarios):
            assert index in retained, f"position-{index} passes but was not enumerated"


# --- meta.defeats: the families a scenario is built to make fail (issue #35) -----------

def _with_defeats(tmp_path, sid, defeats, tier="control"):
    path = tmp_path / "advanced-scenarios" / sid / "scenario.graph.yml"
    data = yaml.safe_load(path.read_text())
    data["meta"]["defeats"] = defeats
    data["meta"]["tier"] = tier
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    # an edited scenario makes its output stale (issue #93), so generate it again
    generate_graph_repository(path, tmp_path / "repos" / sid / "default", force=True)


def test_a_declared_defeat_that_a_rule_solves_is_reported(tmp_path):
    """The four-commit range fixture is solved by blame, by position-1 and by the last toucher."""
    _generate(tmp_path, "SZZG-9020", _range_commits(), _range_bugs())
    _generate(tmp_path, "SZZG-9021", _range_commits(), _range_bugs())
    _generate(tmp_path, "SZZG-9022", _range_commits(), _range_bugs())
    _with_defeats(tmp_path, "SZZG-9020", ["blame"])              # wrong: blame solves it
    _with_defeats(tmp_path, "SZZG-9021", [])                     # a control that promises nothing
    # SZZG-9022 declares nothing at all
    report = _run(tmp_path)
    assert report["scenarios_declaring_defeats"] == 2
    assert report["declared_defeated_but_solved"] == [
        {"scenario_id": "SZZG-9020", "family": "blame", "solved_by": ["blame-deleted-lines"]}]
    # a filtered run only checks the families it ran
    position_only = run_baselines(generated_root=tmp_path / "repos", scenarios_root=tmp_path,
                                  advanced_scenarios_root=tmp_path / "advanced-scenarios", families=["position"])
    assert position_only["declared_defeated_but_solved"] == []
    assert "declared defeat" in format_report(report).lower() or "defeat" in format_report(report).lower()
