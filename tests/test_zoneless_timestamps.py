"""A pinned timestamp without a zone is UTC, quoted or not (issue #133).

A quoted ``date: "2023-10-16T16:36:00"`` reached Git verbatim, and Git read it
in the local time zone: the same scenario generated different hashes on a
machine in Japan and on a UTC runner, with no finding from validation or
verification.  The same value unquoted is a YAML timestamp, which SZZBench
already read as UTC, so the two spellings of one value disagreed.  Every
pinned value is now parsed and handed to Git with its zone.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

import szzbench.generator as generator
from support import git
from szzbench.findings import ValidationResult
from szzbench.generator import GenerationError, generate_repository
from szzbench.gitutils import _as_timestamp_string, parse_timestamp, resolve_commit_metadata
from szzbench.graph_generator import generate_graph_repository
from szzbench.validator import validate_scenario_file

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "scenarios/SZZ-0005/scenario.yml"
GRAPH = ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml"
ZONES = ("UTC", "Asia/Tokyo", "America/New_York")


def _classic_copy(tmp_path: Path, name: str, rewrite) -> Path:
    path = tmp_path / name / "SZZ-0005" / "scenario.yml"
    path.parent.mkdir(parents=True)
    path.write_text(rewrite(CLASSIC.read_text(encoding="utf-8")), encoding="utf-8")
    return path


def _quoted_without_zone(text: str) -> str:
    return re.sub(r'(date: "[^"]*)Z"', r'\1"', text)


def _unquoted_without_zone(text: str) -> str:
    return re.sub(r'date: "([^"]*)Z"', r"date: \1", text)


def _hashes(scenario: Path, out: Path, *, graph: bool = False) -> dict[str, str]:
    generate = generate_graph_repository if graph else generate_repository
    commit_map, verify = generate(scenario, out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    return {cid: entry["hash"] for cid, entry in commit_map.items()}


@pytest.fixture(scope="module")
def shipped_hashes(tmp_path_factory) -> dict[str, str]:
    return _hashes(CLASSIC, tmp_path_factory.mktemp("shipped") / "out")


@pytest.mark.parametrize("zone", ZONES)
@pytest.mark.parametrize("rewrite", [_quoted_without_zone, _unquoted_without_zone], ids=["quoted", "unquoted"])
def test_a_classic_date_without_a_zone_generates_the_utc_hashes_in_every_time_zone(
        tmp_path, monkeypatch, shipped_hashes, rewrite, zone):
    scenario = _classic_copy(tmp_path, "copy", rewrite)
    assert 'Z"' not in scenario.read_text(encoding="utf-8")
    monkeypatch.setenv("TZ", zone)
    assert _hashes(scenario, tmp_path / "out") == shipped_hashes


def test_the_commit_map_records_the_zone_of_a_date_written_without_one(tmp_path, monkeypatch):
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    scenario = _classic_copy(tmp_path, "copy", _quoted_without_zone)
    generate_repository(scenario, tmp_path / "out", force=True)
    commit_map = json.loads((tmp_path / "out/metadata/commit-map.json").read_text(encoding="utf-8"))
    assert commit_map["c0"]["date"] == "2023-10-16T16:36:00"          # as written in the scenario
    assert commit_map["c0"]["author_date"] == "2023-10-16T16:36:00Z"  # what Git was given
    assert commit_map["c0"]["committer_date"] == "2023-10-16T16:36:00Z"
    assert git(tmp_path / "out/repo", "log", "-1", "--format=%ai|%ci", commit_map["c0"]["hash"]) == \
        "2023-10-16 16:36:00 +0000|2023-10-16 16:36:00 +0000"


@pytest.mark.parametrize("zone", ZONES)
def test_a_graph_date_without_a_zone_generates_the_utc_hashes_in_every_time_zone(tmp_path, monkeypatch, zone):
    data = yaml.safe_load(GRAPH.read_text(encoding="utf-8"))
    for index, commit in enumerate(data["commits"]):
        commit["date"] = f"2024-03-0{index + 1}T09:30:00Z"
    pinned = tmp_path / "pinned/SZZG-0001/scenario.graph.yml"
    pinned.parent.mkdir(parents=True)
    pinned.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    for commit in data["commits"]:
        commit["date"] = commit["date"][:-1]
    zoneless = tmp_path / "zoneless/SZZG-0001/scenario.graph.yml"
    zoneless.parent.mkdir(parents=True)
    zoneless.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    monkeypatch.setenv("TZ", zone)
    assert _hashes(zoneless, tmp_path / "zoneless-out", graph=True) == _hashes(pinned, tmp_path / "pinned-out", graph=True)


@pytest.mark.parametrize("written, given", [
    ("2024-01-02T10:00:00Z", "2024-01-02T10:00:00Z"),
    ("2024-01-02T10:00:00", "2024-01-02T10:00:00Z"),
    ("2024-01-02 10:00:00", "2024-01-02T10:00:00Z"),
    ("2024-01-02T10:00:00+09:00", "2024-01-02T10:00:00+09:00"),
    # the basic offset form, which datetime.fromisoformat reads only from Python 3.11 on
    ("2024-01-02T10:00:00+0900", "2024-01-02T10:00:00+09:00"),
    ("2024-01-02T10:00:00-0530", "2024-01-02T10:00:00-05:30"),
])
def test_every_pinned_value_reaches_git_with_its_zone(written, given):
    metadata = resolve_commit_metadata({"meta": {"id": "SZZ-9900"}}, {"date": written}, 0)
    assert (metadata.author_date, metadata.committer_date) == (given, given)
    assert _as_timestamp_string(written, field="date") == given
    assert parse_timestamp(given) == parse_timestamp(written)


def test_the_offset_written_with_or_without_a_colon_gives_the_same_hashes(tmp_path):
    with_colon = _classic_copy(tmp_path, "colon", lambda text: re.sub(r'(date: "[^"]*)Z"', r'\1+09:00"', text))
    without = _classic_copy(tmp_path, "basic", lambda text: re.sub(r'(date: "[^"]*)Z"', r'\1+0900"', text))
    assert _hashes(with_colon, tmp_path / "colon-out") == _hashes(without, tmp_path / "basic-out")


def test_a_date_that_is_not_iso_8601_is_an_error_naming_the_field(tmp_path, monkeypatch):
    scenario = _classic_copy(tmp_path, "copy", lambda text: text.replace('date: "2023-10-19T11:36:00Z"', 'date: "yesterday"', 1))
    assert '"yesterday"' in scenario.read_text(encoding="utf-8")
    # validate reports it since issue #152, so generate stops before Git
    _, result, _ = validate_scenario_file(scenario, simulate=True)
    assert [(f.code, f.location) for f in result.error_findings()] == [("E013", "commits[1].date")]
    with pytest.raises(GenerationError, match="Scenario validation failed"):
        generate_repository(scenario, tmp_path / "out", force=True)
    # and the generator, without the validator, names the field rather than handing Git the value
    monkeypatch.setattr(generator, "validate_scenario_file", lambda path, simulate: (None, ValidationResult(), None))
    with pytest.raises(GenerationError, match=r"date is not a valid ISO 8601 timestamp: 'yesterday'"):
        generate_repository(scenario, tmp_path / "out", force=True)
