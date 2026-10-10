"""A commit dated before its parent is refused by validation (issue #241).

As soon as a scenario writes one date, its other commits get the plain
schedule, ``repository.base_date`` (or ``2024-01-01T10:00:00Z``) plus the
commit's index in days.  A written date that does not fit it, or two written
dates in the wrong order, put a child before its parent.  Neither validator
compared the dates: the graph suite found it after generation (GE630, which
named two hashes), and the classic suite generated and verified such a
history.  ``validate`` (E016) and ``validate-graph`` (GE073) now report it
without ``--simulate``, naming both commits; ``verify`` reports a classic
repository that has one (E610), and GE630 names the logical commits.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

import szzbench.generator as generator
import szzbench.graph_generator as graph_generator
from szzbench.findings import ValidationResult
from szzbench.generator import generate_repository
from szzbench.graph_generator import generate_graph_repository
from szzbench.graph_validator import validate_graph_scenario_file
from szzbench.graph_verifier import verify_graph_generated_repo
from szzbench.validator import validate_scenario_file
from szzbench.verifier import verify_generated_repo

from support import ROOT

#: Every date written: c0 2023-10-16T16:36:00Z, c1 2023-10-19T11:36:00Z, c2 2023-10-23T11:29:00Z.
CLASSIC = "scenarios/SZZ-0005/scenario.yml"
#: No date written, three commits; SZZG-0060 merges c1 of `feature` as c3.
GRAPH, MERGE = "advanced-scenarios/SZZG-0001/scenario.graph.yml", "advanced-scenarios/SZZG-0060/scenario.graph.yml"


def _variant(tmp_path: Path, source: str, edit) -> Path:
    data = yaml.safe_load((ROOT / source).read_text(encoding="utf-8"))
    edit(data["commits"])
    path = tmp_path / Path(source).parent.name / Path(source).name
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _pin(**dates):
    """Write ``dates`` ({"c1_date": ...}) on the commits; None removes the key."""
    def edit(commits):
        by_id = {commit["id"]: commit for commit in commits}
        for name, value in dates.items():
            cid, key = name.split("_", 1)
            if value is None:
                by_id[cid].pop(key)
            else:
                by_id[cid][key] = value
    return edit


def _findings(result: ValidationResult, code: str) -> list[tuple[str, str | None]]:
    return [(f.message, f.location) for f in result.findings if f.code == code]


@pytest.mark.parametrize("source, dates, child, parent, location", [
    (GRAPH, {"c1_date": "2023-12-31T10:00:00Z"}, "c1", "c0", "commits[1].date"),           # c0 is scheduled 2024-01-01
    (GRAPH, {"c0_date": "2024-01-05T10:00:00Z"}, "c1", "c0", "commits[0].date"),           # c1 is scheduled 2024-01-02
    (GRAPH, {"c1_committer_date": "2023-12-31T10:00:00Z"}, "c1", "c0", "commits[1].committer_date"),
    (GRAPH, {"c0_date": "2024-03-01T10:00:00Z", "c1_date": "2024-03-05T10:00:00Z", "c2_date": "2024-03-04T10:00:00Z"},
     "c2", "c1", "commits[2].date"),
    (MERGE, {"c1_date": "2024-01-10T10:00:00Z"}, "c3", "c1", "commits[1].date"),           # the merge c3: 2024-01-04
], ids=["child-pinned-early", "parent-pinned-late", "committer-date-only", "all-pinned", "merge"])
def test_validate_graph_refuses_a_commit_dated_before_a_parent(tmp_path, source, dates, child, parent, location):
    _, result = validate_graph_scenario_file(_variant(tmp_path, source, _pin(**dates)))
    [(message, where)] = _findings(result, "GE073")
    assert message.startswith(f"Commit '{child}' would be committed at ") and f"before its parent '{parent}' at " in message
    assert where == location
    assert [f.code for f in result.findings if f.severity == "ERROR"] == ["GE073"]


@pytest.mark.parametrize("dates, message", [
    ({"c1_date": "2023-10-15T11:36:00Z"},
     "Commit 'c1' would be committed at 2023-10-15T11:36:00Z (its date), before its parent 'c0' at "
     "2023-10-16T16:36:00Z (its date): write an earlier date for 'c0' or a later one for 'c1'."),
    ({"c0_date": None},
     "Commit 'c1' would be committed at 2023-10-19T11:36:00Z (its date), before its parent 'c0' at "
     "2024-01-01T10:00:00Z (scheduled from the default base date, as 'c0' writes no date or committer_date): "
     "write a date for 'c0' too, or a later one for 'c1'."),
], ids=["all-pinned", "partly-pinned"])
def test_validate_refuses_a_classic_commit_dated_before_its_parent(tmp_path, dates, message):
    _, result, _ = validate_scenario_file(_variant(tmp_path, CLASSIC, _pin(**dates)))
    assert _findings(result, "E016") == [(message, "commits[1].date")]
    assert [f.code for f in result.findings if f.severity == "ERROR"] == ["E016"]


def test_the_dates_are_compared_as_instants(tmp_path):
    # 2023-10-16T20:00:00+09:00 is 11:00 UTC: before c0's 16:36 UTC, although it sorts after it as text
    early = _variant(tmp_path / "early", CLASSIC, _pin(c1_date="2023-10-16T20:00:00+09:00"))
    assert [location for _, location in _findings(validate_scenario_file(early)[1], "E016")] == ["commits[1].date"]
    # 2023-10-16T12:00:00-05:00 is 17:00 UTC, after it, although it sorts before it as text
    late = _variant(tmp_path / "late", CLASSIC, _pin(c1_date="2023-10-16T12:00:00-05:00"))
    assert not validate_scenario_file(late)[1].has_errors()


def _utc(message: str) -> str:
    """Git 2.39 prints a UTC date (``%cI``) with ``+00:00``, Git 2.50 with ``Z``."""
    return message.replace("+00:00", "Z")


def test_verify_reports_a_classic_commit_committed_before_its_parent(tmp_path, monkeypatch):
    # a repository generated before validation refused such dates
    monkeypatch.setattr(generator, "validate_scenario_file", lambda path, simulate: (None, ValidationResult(), None))
    scenario = _variant(tmp_path, CLASSIC, _pin(c0_date=None))
    commit_map, _ = generate_repository(scenario, tmp_path / "out", verify=False)
    result = verify_generated_repo(tmp_path / "out" / "repo", scenario)
    c0, c1 = commit_map["c0"]["hash"][:8], commit_map["c1"]["hash"][:8]
    assert [(_utc(message), location) for message, location in _findings(result, "E610")] == [
        (f"Commit {c1} (c1) was committed at 2023-10-19T11:36:00Z, before its parent {c0} (c0) at 2024-01-01T10:00:00Z.",
         "commits.c1")]


def test_ge630_names_the_logical_commits(tmp_path, monkeypatch):
    monkeypatch.setattr(graph_generator, "validate_graph_scenario_file", lambda path: (None, ValidationResult()))
    scenario = _variant(tmp_path, GRAPH, _pin(c1_date="2023-12-31T10:00:00Z"))
    commit_map, _ = generate_graph_repository(scenario, tmp_path / "out", verify=False)
    result = verify_graph_generated_repo(tmp_path / "out" / "repo", scenario)
    c0, c1 = commit_map["c0"]["hash"][:8], commit_map["c1"]["hash"][:8]
    assert [_utc(message) for message, _ in _findings(result, "GE630")] == [
        f"Commit {c1} (c1) was committed at 2023-12-31T10:00:00Z, before its parent {c0} (c0) at 2024-01-01T10:00:00Z."]
