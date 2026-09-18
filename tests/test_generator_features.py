"""Tests for the generator options added for issues #9, #17 and #18.

See docs/generator-options.md for the description of every option.
"""
from __future__ import annotations

from pathlib import Path
import json
import subprocess

import pytest
import yaml

from szzbench.generator import generate_repository
from szzbench.gitutils import DEFAULT_AUTHOR_POOL, deterministic_author, deterministic_date, resolve_commit_metadata
from szzbench.graph_generator import MAX_GENERATED_COMMITS, GraphGenerationError, generate_graph_repository
from szzbench.graph_operations import apply_graph_operation_to_filesystem, commit_generator_directory
from szzbench.operations import apply_operation_to_filesystem


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout


def _log_line(repo: Path, revision: str, fmt: str) -> str:
    return _git(repo, "log", "-1", f"--format={fmt}", revision).rstrip("\n")


def _write_graph_scenario(path: Path, commits: list[dict], *, scenario_id: str = "SZZG-9900", bugs: list[dict] | None = None, extra: dict | None = None, repository: dict | None = None) -> Path:
    if bugs is None:
        bugs = [
            {
                "id": "B001",
                "bug_introducing_commits": [{"commit": commits[0]["id"], "role": "direct"}],
                "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}],
            }
        ]
    data = {
        "schema_version": "graph-0.1-draft",
        "meta": {"id": scenario_id, "title": "feature test", "category": "test", "factors": []},
        "repository": {"name": f"{scenario_id.lower()}-feature-test", "default_branch": "main", **(repository or {})},
        "commits": commits,
        "bugs": bugs,
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": [commits[0]["id"]]}},
    }
    if extra:
        data.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _write_classic_scenario(path: Path, commits: list[dict], *, scenario_id: str = "SZZ-9900", repository: dict | None = None) -> Path:
    data = {
        "schema_version": "1.0",
        "meta": {"id": scenario_id, "title": "feature test", "category": "test", "factors": []},
        "repository": {"name": f"{scenario_id.lower()}-feature-test", "default_branch": "main", "language": "text", **(repository or {})},
        "commits": commits,
        "bugs": [
            {
                "id": "B001",
                "bug_fixing_commit": commits[-1]["id"],
                "bug_introducing_commits": [commits[0]["id"]],
                "fault": {"commit": commits[0]["id"], "file": "src/example.txt", "statement": "state=buggy", "change_type": "line_modification"},
                "fix": {"commit": commits[-1]["id"], "file": "src/example.txt", "statement": "state=fixed"},
            }
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _classic_commits(**overrides: dict) -> list[dict]:
    c0 = {"id": "c0", "message": "Introduce text bug", "role": "bug_introducing", "operations": [{"type": "write_file", "path": "src/example.txt", "content": "state=buggy\n"}]}
    c1 = {"id": "c1", "message": "Fix text bug", "role": "bug_fixing", "operations": [{"type": "replace", "path": "src/example.txt", "old": "state=buggy", "new": "state=fixed"}]}
    c0.update(overrides.get("c0", {}))
    c1.update(overrides.get("c1", {}))
    return [c0, c1]


def _range_java(buggy: bool) -> str:
    op = "> min && value <" if buggy else ">= min && value <="
    return f"package example;\npublic class Range {{\n  public boolean contains(int value, int min, int max) {{\n    return value {op} max;\n  }}\n}}\n"


BUGGY = "return value > min && value < max;"
FIXED = "return value >= min && value <= max;"
RANGE = "src/main/java/example/Range.java"


def _commit_map(out: Path) -> dict:
    return json.loads((out / "metadata" / "commit-map.json").read_text(encoding="utf-8"))


def _graph_map(out: Path) -> dict:
    return json.loads((out / "metadata" / "graph-map.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Task 1 (#9): deterministic author/date metadata
# ---------------------------------------------------------------------------


def test_deterministic_defaults_are_stable_and_role_independent():
    assert deterministic_date(None, 0) == "2024-01-01T10:00:00Z"
    assert deterministic_date(None, 3) == "2024-01-04T10:00:00Z"
    assert deterministic_date("2024-06-01T10:00:00Z", 1) == "2024-06-02T10:00:00Z"
    assert deterministic_date("2024-06-01T10:00:00+09:00", 1) == "2024-06-02T10:00:00+09:00"
    assert deterministic_author("SZZG-0001", 0) == deterministic_author("SZZG-0001", 0)
    assert all(deterministic_author("SZZG-0001", i) in DEFAULT_AUTHOR_POOL for i in range(20))
    # The author only depends on (scenario id, index); the role is irrelevant.
    scenario = {"meta": {"id": "SZZG-0001"}, "repository": {}}
    bic = resolve_commit_metadata(scenario, {"role": "bug_introducing"}, 2)
    other = resolve_commit_metadata(scenario, {"role": "intermediate"}, 2)
    assert bic.author == other.author
    assert bic.author_date == bic.committer_date == deterministic_date(None, 2, "SZZG-0001")
    assert bic.author_is_default and bic.author_date_is_default


def test_default_dates_are_irregular_weekday_timestamps_per_scenario():
    """Issue #9: default dates must not be one shared ramp at a single time."""
    from datetime import datetime

    def parsed(sid, i):
        return datetime.fromisoformat(deterministic_date(None, i, sid).replace("Z", "+00:00"))

    for sid in ("SZZG-0001", "SZZG-0050", "SZZ-0123"):
        stamps = [parsed(sid, i) for i in range(8)]
        assert stamps == sorted(stamps) and len(set(stamps)) == 8   # strictly increasing
        assert all(s.weekday() < 5 for s in stamps)                 # weekdays only
        assert all(8 <= s.hour <= 18 for s in stamps[1:])           # working hours
        gaps = {(b - a).days for a, b in zip(stamps, stamps[1:])}
        assert len(gaps) > 1                                        # not a fixed ramp
        assert deterministic_date(None, 3, sid) == deterministic_date(None, 3, sid)

    # Different scenarios start on different days and use different times.
    first = {deterministic_date(None, 0, f"SZZG-{i:04d}") for i in range(1, 40)}
    assert len(first) > 30
    times = {deterministic_date(None, 2, f"SZZG-{i:04d}")[11:] for i in range(1, 40)}
    assert len(times) > 20

    # An explicit base_date is reproduced verbatim by the first commit.
    assert deterministic_date("2024-03-01T10:00:00Z", 0, "SZZ-9900") == "2024-03-01T10:00:00Z"


def test_resolve_commit_metadata_preserves_explicit_values_and_separate_dates():
    scenario = {"meta": {"id": "SZZG-0001"}, "repository": {"base_date": "2025-02-01T00:00:00Z"}}
    explicit = resolve_commit_metadata(scenario, {"author": "Bob <bob@example.com>", "date": "2024-01-02T10:00:00Z"}, 5)
    assert explicit.author == "Bob <bob@example.com>"
    assert explicit.author_date == "2024-01-02T10:00:00Z"
    assert explicit.committer_date == "2024-01-02T10:00:00Z"
    assert not explicit.author_is_default
    split = resolve_commit_metadata(scenario, {"date": "2024-01-02T10:00:00Z", "committer_date": "2024-01-09T12:00:00Z"}, 1)
    assert split.author_date == "2024-01-02T10:00:00Z"
    assert split.committer_date == "2024-01-09T12:00:00Z"
    only_author_date = resolve_commit_metadata(scenario, {"author_date": "2024-01-02T10:00:00Z"}, 1)
    assert only_author_date.author_date == "2024-01-02T10:00:00Z"
    assert only_author_date.committer_date == deterministic_date("2025-02-01T00:00:00Z", 1, "SZZG-0001")
    assert only_author_date.committer_date_is_default


def test_classic_generator_assigns_deterministic_metadata_and_records_it(tmp_path):
    scenario = _write_classic_scenario(tmp_path / "SZZ-9900" / "scenario.yml", _classic_commits(c1={"author_date": "2024-05-05T05:05:05Z"}), repository={"base_date": "2024-03-01T10:00:00Z"})
    out = tmp_path / "out"
    commit_map, verify = generate_repository(scenario, out, force=True)
    assert verify is not None and not verify.has_errors()
    repo = out / "repo"
    c0, c1 = commit_map["c0"], commit_map["c1"]
    assert c0["author"] == deterministic_author("SZZ-9900", 0)
    assert c0["author_date"] == c0["committer_date"] == "2024-03-01T10:00:00Z"
    assert _log_line(repo, c0["hash"], "%an <%ae>|%aI|%cI") == f"{c0['author']}|2024-03-01T10:00:00Z|2024-03-01T10:00:00Z"
    assert c1["author_date"] == "2024-05-05T05:05:05Z"
    # the scenario pins c1's author date, so it keeps the plain schedule
    assert c1["committer_date"] == "2024-03-02T10:00:00Z"
    assert _log_line(repo, c1["hash"], "%aI|%cI") == "2024-05-05T05:05:05Z|2024-03-02T10:00:00Z"
    assert c1["date"] is None

    # Generating twice yields identical hashes: nothing depends on wall-clock time.
    again, _ = generate_repository(scenario, tmp_path / "out2", force=True)
    assert again["c0"]["hash"] == c0["hash"] and again["c1"]["hash"] == c1["hash"]


def test_classic_generator_keeps_explicit_author_and_date(tmp_path):
    commits = _classic_commits(
        c0={"author": "Alice <alice@example.com>", "date": "2024-01-01T10:00:00Z"},
        c1={"author": "Bob <bob@example.com>", "date": "2024-01-02T10:00:00Z"},
    )
    scenario = _write_classic_scenario(tmp_path / "SZZ-9901" / "scenario.yml", commits, scenario_id="SZZ-9901")
    out = tmp_path / "out"
    commit_map, _ = generate_repository(scenario, out, force=True)
    assert _log_line(out / "repo", commit_map["c1"]["hash"], "%an|%ae|%aI|%cI") == "Bob|bob@example.com|2024-01-02T10:00:00Z|2024-01-02T10:00:00Z"
    assert commit_map["c1"]["author"] == "Bob <bob@example.com>"
    assert commit_map["c1"]["date"] == "2024-01-02T10:00:00Z"


def test_graph_generator_assigns_deterministic_metadata(tmp_path):
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0", "role": "bug_introducing", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(True)}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1", "role": "bug_fixing", "author_date": "2024-02-02T02:02:02Z", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits)
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert verify is not None and not verify.has_errors()
    repo = out / "repo"
    assert commit_map["c0"]["author"] == deterministic_author("SZZG-9900", 0)
    # the scenario pins c1's author date, so it keeps the plain schedule
    assert commit_map["c0"]["author_date"] == "2024-01-01T10:00:00Z"
    assert _log_line(repo, commit_map["c0"]["hash"], "%aI|%cI") == "2024-01-01T10:00:00Z|2024-01-01T10:00:00Z"
    assert _log_line(repo, commit_map["c1"]["hash"], "%aI|%cI") == "2024-02-02T02:02:02Z|2024-01-02T10:00:00Z"
    assert commit_map["c1"]["committer_date"] == "2024-01-02T10:00:00Z"


# ---------------------------------------------------------------------------
# Task 2 (#18): filemode, line endings, header/footer, commit_generator
# ---------------------------------------------------------------------------


def test_chmod_scenario_enables_filemode_and_records_mode(tmp_path):
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0", "role": "bug_introducing", "operations": [
            {"type": "write_file", "path": "scripts/run.sh", "content": "#!/bin/sh\necho hi\n"},
            {"type": "write_file", "path": RANGE, "content": _range_java(True)},
        ]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1", "role": "intermediate", "operations": [{"type": "chmod", "path": "scripts/run.sh", "mode": "755"}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "c2", "role": "bug_fixing", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits)
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors()
    repo = out / "repo"
    assert _git(repo, "config", "core.filemode").strip() == "true"
    assert _git(repo, "ls-tree", commit_map["c0"]["hash"], "scripts/run.sh").startswith("100644")
    assert _git(repo, "ls-tree", commit_map["c1"]["hash"], "scripts/run.sh").startswith("100755")
    # No chmod -> filemode stays off (Windows compatibility).
    plain = _write_graph_scenario(tmp_path / "plain.graph.yml", commits[:1] + [commits[2] | {"parents": ["c0"]}], scenario_id="SZZG-9901")
    generate_graph_repository(plain, tmp_path / "plain", force=True)
    assert _git(tmp_path / "plain" / "repo", "config", "core.filemode").strip() == "false"


def test_line_ending_option_in_graph_operations(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    apply_graph_operation_to_filesystem(repo, {"type": "write_file", "path": "a.txt", "content": "one\ntwo\nthree\n", "line_ending": "crlf"})
    assert (repo / "a.txt").read_bytes() == b"one\r\ntwo\r\nthree\r\n"
    # Without the key an existing CRLF file keeps CRLF.
    apply_graph_operation_to_filesystem(repo, {"type": "replace", "path": "a.txt", "old": "two", "new": "2"})
    assert (repo / "a.txt").read_bytes() == b"one\r\n2\r\nthree\r\n"
    apply_graph_operation_to_filesystem(repo, {"type": "insert_after", "path": "a.txt", "anchor": "one\n", "content": "1.5\n"})
    assert (repo / "a.txt").read_bytes() == b"one\r\n1.5\r\n2\r\nthree\r\n"
    # An explicit line_ending re-encodes the whole file.
    apply_graph_operation_to_filesystem(repo, {"type": "replace", "path": "a.txt", "old": "three", "new": "3", "line_ending": "lf"})
    assert (repo / "a.txt").read_bytes() == b"one\n1.5\n2\n3\n"
    apply_graph_operation_to_filesystem(repo, {"type": "insert_after", "path": "a.txt", "anchor": "3\n", "content": "4\n", "line_ending": "crlf"})
    assert (repo / "a.txt").read_bytes() == b"one\r\n1.5\r\n2\r\n3\r\n4\r\n"
    # Default stays LF.
    apply_graph_operation_to_filesystem(repo, {"type": "write_file", "path": "b.txt", "content": "x\r\ny\n"})
    assert (repo / "b.txt").read_bytes() == b"x\ny\n"
    with pytest.raises(Exception):
        apply_graph_operation_to_filesystem(repo, {"type": "write_file", "path": "c.txt", "content": "x\n", "line_ending": "cr"})


def test_line_ending_option_in_classic_operations(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    apply_operation_to_filesystem(repo, {"type": "write_file", "path": "a.txt", "content": "one\ntwo\n", "line_ending": "crlf"})
    assert (repo / "a.txt").read_bytes() == b"one\r\ntwo\r\n"
    apply_operation_to_filesystem(repo, {"type": "replace", "path": "a.txt", "old": "two", "new": "2"})
    assert (repo / "a.txt").read_bytes() == b"one\r\n2\r\n"
    apply_operation_to_filesystem(repo, {"type": "replace", "path": "a.txt", "old": "one", "new": "1", "line_ending": "lf"})
    assert (repo / "a.txt").read_bytes() == b"1\n2\n"
    apply_operation_to_filesystem(repo, {"type": "write_file", "path": "b.txt", "content": "x\n"})
    assert (repo / "b.txt").read_bytes() == b"x\n"


def test_classic_scenario_with_crlf_generates_and_verifies(tmp_path):
    commits = _classic_commits(c0={"operations": [{"type": "write_file", "path": "src/example.txt", "content": "state=buggy\nother=1\n", "line_ending": "crlf"}]})
    scenario = _write_classic_scenario(tmp_path / "SZZ-9902" / "scenario.yml", commits, scenario_id="SZZ-9902")
    out = tmp_path / "out"
    commit_map, verify = generate_repository(scenario, out, force=True)
    assert not verify.has_errors()
    blob = subprocess.run(["git", "show", f"{commit_map['c1']['hash']}:src/example.txt"], cwd=out / "repo", stdout=subprocess.PIPE, check=True).stdout
    assert blob == b"state=fixed\r\nother=1\r\n"


def test_write_generated_text_file_header_and_footer(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    apply_graph_operation_to_filesystem(
        repo,
        {
            "type": "write_generated_text_file",
            "path": "Large.java",
            "lines": 3,
            "template": "  public int value_${line} = ${line};",
            "header": "package example;\npublic class Large {",
            "footer": "}\n",
        },
    )
    assert (repo / "Large.java").read_text(encoding="utf-8") == (
        "package example;\npublic class Large {\n  public int value_1 = 1;\n  public int value_2 = 2;\n  public int value_3 = 3;\n}\n"
    )
    apply_graph_operation_to_filesystem(repo, {"type": "write_generated_text_file", "path": "plain.txt", "lines": 2, "template": "l{line}"})
    assert (repo / "plain.txt").read_text(encoding="utf-8") == "l1\nl2\n"


def test_commit_generator_directory_backward_compatibility():
    assert commit_generator_directory(None) == "generated"
    assert commit_generator_directory("generated/unrelated-batch-1.txt") == "generated"
    assert commit_generator_directory("generated/batch") == "generated/batch"
    assert commit_generator_directory("generated/batch/") == "generated/batch"
    assert commit_generator_directory("notes.txt") == ""


def _commit_generator_commits(count: int, files: int = 2, path: str = "generated/unrelated-batch-1.txt") -> list[dict]:
    return [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1: bug", "role": "bug_introducing", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "c2: unrelated batch", "role": "intermediate", "operations": [{"type": "commit_generator", "generator": "unrelated_changes", "count": count, "files": files, "path": path}]},
        {"id": "c3", "branch": "main", "parents": ["c2"], "message": "c3: fix", "role": "bug_fixing", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]


def _commit_generator_bugs() -> list[dict]:
    return [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
            "bug_fixing_commits": [{"commit": "c3", "role": "complete_fix"}],
            "faults": [{"commit": "c1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "c3", "file": RANGE, "statement": FIXED}],
        }
    ]


def test_commit_generator_expands_into_real_commits_and_verifies(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _commit_generator_commits(5), bugs=_commit_generator_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    assert _git(repo, "rev-list", "--count", "HEAD").strip() == "9"  # 4 logical + 5 generated

    generated = commit_map["c2"]["generated_commits"]
    assert generated == [f"c2.g{i}" for i in range(1, 6)]
    assert _graph_map(out)["generated_commits"] == {"c2": generated}
    for gid in generated:
        assert commit_map[gid]["role"] == "generated"
        assert commit_map[gid]["generated_by"] == "c2"
    # Linear chain: c1 <- c2.g1 <- ... <- c2.g5 <- c2 (empty) <- c3
    assert _log_line(repo, commit_map["c2.g1"]["hash"], "%P") == commit_map["c1"]["hash"]
    assert _log_line(repo, commit_map["c2.g3"]["hash"], "%P") == commit_map["c2.g2"]["hash"]
    assert _log_line(repo, commit_map["c2"]["hash"], "%P") == commit_map["c2.g5"]["hash"]
    assert _log_line(repo, commit_map["c3"]["hash"], "%P") == commit_map["c2"]["hash"]
    assert _log_line(repo, commit_map["c2"]["hash"], "%s") == "c2: unrelated batch"
    assert _git(repo, "show", "--stat", "--format=", commit_map["c2"]["hash"]).strip() == ""  # owner is empty
    # Each generated commit touches exactly one file under the directory of the legacy path.
    for gid in generated:
        changed = _git(repo, "show", "--name-only", "--format=", commit_map[gid]["hash"]).split()
        assert len(changed) == 1 and changed[0].startswith("generated/unrelated_changes-")
    assert sorted(_git(repo, "ls-tree", "--name-only", commit_map["c2"]["hash"], "generated/").split()) == [
        "generated/unrelated_changes-01.txt",
        "generated/unrelated_changes-02.txt",
    ]
    # Dates are chronological: c1 < g1 < ... < g5 < c2, and authors come from the pool.
    dates = [_log_line(repo, commit_map[cid]["hash"], "%at") for cid in ["c1", *generated, "c2"]]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    assert all(commit_map[gid]["author"] in DEFAULT_AUTHOR_POOL for gid in generated)
    # The blame-based basic check still reaches the BIC through the generated history.
    assert any(item["code"] == "GI703" for item in verify.to_dict()["findings"])


def test_commit_generator_is_deterministic_and_capped(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _commit_generator_commits(3, files=1, path="history"), bugs=_commit_generator_bugs())
    first, _ = generate_graph_repository(scenario, tmp_path / "a", force=True)
    second, _ = generate_graph_repository(scenario, tmp_path / "b", force=True)
    assert first["c3"]["hash"] == second["c3"]["hash"]
    assert _git(tmp_path / "a" / "repo", "ls-tree", "--name-only", first["c2"]["hash"], "history/").split() == ["history/unrelated_changes-01.txt"]

    big = _write_graph_scenario(tmp_path / "big.graph.yml", _commit_generator_commits(MAX_GENERATED_COMMITS + 7, files=10), bugs=_commit_generator_bugs(), scenario_id="SZZG-9903")
    out = tmp_path / "big"
    commit_map, verify = generate_graph_repository(big, out, force=True)
    assert not verify.has_errors()
    assert len(commit_map["c2"]["generated_commits"]) == MAX_GENERATED_COMMITS
    assert _git(out / "repo", "rev-list", "--count", "HEAD").strip() == str(4 + MAX_GENERATED_COMMITS)


# ---------------------------------------------------------------------------
# Task 3 (#17): rebase fidelity, ref lifecycle, trailers, reverts, conflicts
# ---------------------------------------------------------------------------


def _rebase_commits() -> list[dict]:
    return [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "date": "2024-01-01T10:00:00Z", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "f1: introduce boundary bug", "role": "origin_bug_introducing", "date": "2024-01-02T10:00:00Z", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1: unrelated", "role": "intermediate", "operations": [{"type": "write_file", "path": "README.md", "content": "# demo\n"}]},
        {"id": "r1", "branch": "main", "parents": ["c1"], "role": "bug_introducing", "rebase_of": "f1", "inherit_message": True, "inherit_author_date": True, "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "c2", "branch": "main", "parents": ["r1"], "message": "c2: fix", "role": "bug_fixing", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]


def _rebase_bugs() -> list[dict]:
    return [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "r1", "role": "direct"}, {"commit": "f1", "role": "origin"}],
            "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
            "faults": [{"commit": "r1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "c2", "file": RANGE, "statement": FIXED}],
        }
    ]


def test_rebase_of_inherit_message_and_author_date(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _rebase_commits(), bugs=_rebase_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    r1 = commit_map["r1"]
    assert _log_line(repo, r1["hash"], "%s") == "f1: introduce boundary bug"
    assert _log_line(repo, r1["hash"], "%aI") == "2024-01-02T10:00:00Z"  # inherited from f1
    # the scenario pins dates, so the defaults stay on the plain schedule
    assert _log_line(repo, r1["hash"], "%cI") == "2024-01-04T10:00:00Z"  # base + index 3
    assert r1["message"] == "f1: introduce boundary bug"
    assert r1["author_date"] == "2024-01-02T10:00:00Z"
    assert r1["committer_date"] == "2024-01-04T10:00:00Z"
    assert r1["inherits"] == {"source": "f1", "source_hash": commit_map["f1"]["hash"], "message": True, "author_date": True, "subject": "f1: introduce boundary bug"}
    assert _graph_map(out)["commits"]["r1"]["rebase_of"] == "f1"
    # Without options nothing is inherited (existing behaviour).
    assert "inherits" not in commit_map["c1"]


def test_rebase_of_inherit_message_keeps_explicit_message(tmp_path):
    commits = _rebase_commits()
    commits[3]["message"] = "r1: rebased explicitly"
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_rebase_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors()
    assert _log_line(out / "repo", commit_map["r1"]["hash"], "%s") == "r1: rebased explicitly"
    assert commit_map["r1"]["inherits"]["message"] is False
    assert commit_map["r1"]["inherits"]["author_date"] is True


def test_ref_lifecycle_deletes_branch_and_creates_tag(tmp_path):
    extra = {"graph": {"model": "commit_dag", "ref_lifecycle": {"delete_branches": ["feature"], "tags": [{"name": "v1.0", "commit": "c0"}, {"name": "pre-rebase/feature", "commit": "f1"}]}}}
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _rebase_commits(), bugs=_rebase_bugs(), extra=extra)
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    refs = _git(repo, "for-each-ref", "--format=%(refname) %(objectname)").split("\n")
    refs = dict(line.split() for line in refs if line)
    assert refs == {
        "refs/heads/main": commit_map["c2"]["hash"],
        "refs/tags/v1.0": commit_map["c0"]["hash"],
        "refs/tags/pre-rebase/feature": commit_map["f1"]["hash"],
    }
    graph_map = _graph_map(out)
    assert graph_map["refs"] == {
        "branches": {"main": commit_map["c2"]["hash"]},
        "tags": {"v1.0": commit_map["c0"]["hash"], "pre-rebase/feature": commit_map["f1"]["hash"]},
    }
    assert graph_map["ref_lifecycle"]["deleted_branches"] == ["feature"]
    assert graph_map["ref_lifecycle"]["tags"]["v1.0"] == {"commit": "c0", "hash": commit_map["c0"]["hash"]}
    assert graph_map["branches"] == {"main": commit_map["c2"]["hash"]}


def test_graph_map_records_refs_without_ref_lifecycle(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _rebase_commits(), bugs=_rebase_bugs())
    out = tmp_path / "out"
    commit_map, _ = generate_graph_repository(scenario, out, force=True)
    graph_map = _graph_map(out)
    assert graph_map["refs"] == {"branches": {"main": commit_map["c2"]["hash"], "feature": commit_map["f1"]["hash"]}, "tags": {}}
    assert "ref_lifecycle" not in graph_map


def test_ref_lifecycle_can_delete_the_checked_out_branch(tmp_path):
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0", "role": "bug_introducing", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(True)}]},
        {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "f1", "role": "bug_fixing", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]
    extra = {"graph": {"ref_lifecycle": {"delete_branches": ["feature"]}}}
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, extra=extra)
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors()
    assert _git(out / "repo", "for-each-ref", "--format=%(refname)").split() == ["refs/heads/main"]
    assert _git(out / "repo", "rev-parse", "HEAD").strip() == commit_map["c0"]["hash"]


def test_ref_lifecycle_rejects_unknown_targets(tmp_path):
    commits = _rebase_commits()
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_rebase_bugs(), extra={"graph": {"ref_lifecycle": {"delete_branches": ["nope"]}}})
    with pytest.raises(GraphGenerationError, match="unknown branch 'nope'"):
        generate_graph_repository(scenario, tmp_path / "out", force=True)
    scenario = _write_graph_scenario(tmp_path / "t.graph.yml", commits, bugs=_rebase_bugs(), extra={"graph": {"ref_lifecycle": {"tags": [{"name": "v1", "commit": "zz"}]}}})
    with pytest.raises(GraphGenerationError, match="unknown logical commit 'zz'"):
        generate_graph_repository(scenario, tmp_path / "out2", force=True)


def _cherry_pick_commits(*, trailer: bool, with_operations: bool = False) -> list[dict]:
    r1: dict = {"id": "r1", "branch": "release", "parents": ["c0"], "message": "r1: backport boundary bug", "role": "cherry_pick", "cherry_pick_of": "c1", "cherry_pick_trailer": trailer}
    if with_operations:
        r1["operations"] = [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]
    return [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1: introduce boundary bug", "role": "bug_introducing", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        r1,
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "c2: fix", "role": "bug_fixing", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]


def _cherry_pick_bugs() -> list[dict]:
    return [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
            "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
            "faults": [{"commit": "c1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "c2", "file": RANGE, "statement": FIXED}],
        }
    ]


def test_cherry_pick_trailer_is_appended_to_body_only(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _cherry_pick_commits(trailer=True), bugs=_cherry_pick_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    r1_hash, c1_hash = commit_map["r1"]["hash"], commit_map["c1"]["hash"]
    assert _log_line(repo, r1_hash, "%s") == "r1: backport boundary bug"
    assert _log_line(repo, r1_hash, "%b").strip() == f"(cherry picked from commit {c1_hash})"
    assert _git(repo, "log", "-1", "--format=%B", r1_hash) == f"r1: backport boundary bug\n\n(cherry picked from commit {c1_hash})\n\n"
    assert commit_map["r1"]["body"] == f"(cherry picked from commit {c1_hash})"
    assert BUGGY in _git(repo, "show", f"{r1_hash}:{RANGE}")

    # With explicit operations (hand-written replay) the trailer still names the source.
    scenario2 = _write_graph_scenario(tmp_path / "t.graph.yml", _cherry_pick_commits(trailer=True, with_operations=True), bugs=_cherry_pick_bugs(), scenario_id="SZZG-9904")
    commit_map2, _ = generate_graph_repository(scenario2, tmp_path / "out2", force=True)
    assert _log_line(tmp_path / "out2" / "repo", commit_map2["r1"]["hash"], "%b").strip() == f"(cherry picked from commit {commit_map2['c1']['hash']})"


def test_cherry_pick_without_trailer_has_empty_body(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _cherry_pick_commits(trailer=False), bugs=_cherry_pick_bugs())
    out = tmp_path / "out"
    commit_map, _ = generate_graph_repository(scenario, out, force=True)
    assert _log_line(out / "repo", commit_map["r1"]["hash"], "%b") == ""
    assert "body" not in commit_map["r1"]


def _revert_commits(*, message: str | None = None, extra_ops: list[dict] | None = None, apply_revert: bool | None = None) -> list[dict]:
    revert: dict = {"id": "c2", "branch": "main", "parents": ["c1"], "role": "bug_fixing", "revert_of": "c1"}
    if message is not None:
        revert["message"] = message
    if extra_ops:
        revert["operations"] = extra_ops
    if apply_revert is not None:
        revert["apply_revert"] = apply_revert
    return [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}, {"type": "write_file", "path": "README.md", "content": "# demo\n"}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1: introduce boundary bug", "role": "bug_introducing", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        revert,
    ]


def _revert_bugs() -> list[dict]:
    return [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
            "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}],
            "faults": [{"commit": "c1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "c2", "file": RANGE, "statement": FIXED}],
        }
    ]


def test_revert_of_restores_tree_and_writes_standard_message(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _revert_commits(), bugs=_revert_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    c1_hash, c2_hash = commit_map["c1"]["hash"], commit_map["c2"]["hash"]
    assert _git(repo, "show", f"{c2_hash}:{RANGE}") == _range_java(False)
    assert _git(repo, "rev-parse", f"{c2_hash}^{{tree}}") == _git(repo, "rev-parse", f"{commit_map['c0']['hash']}^{{tree}}")
    assert _log_line(repo, c2_hash, "%s") == 'Revert "c1: introduce boundary bug"'
    assert _log_line(repo, c2_hash, "%b").strip() == f"This reverts commit {c1_hash}."
    assert commit_map["c2"]["message"] == 'Revert "c1: introduce boundary bug"'
    assert commit_map["c2"]["body"] == f"This reverts commit {c1_hash}."
    assert _graph_map(out)["commits"]["c2"]["revert_of"] == "c1"


def test_revert_of_with_explicit_message_and_extra_operations(tmp_path):
    extra_ops = [{"type": "replace", "path": "README.md", "old": "# demo", "new": "# demo (reverted)"}]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _revert_commits(message="c2: back out boundary change", extra_ops=extra_ops, apply_revert=True), bugs=_revert_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    c2_hash = commit_map["c2"]["hash"]
    assert _log_line(repo, c2_hash, "%s") == "c2: back out boundary change"
    assert _log_line(repo, c2_hash, "%b").strip() == f"This reverts commit {commit_map['c1']['hash']}."
    assert _git(repo, "show", f"{c2_hash}:{RANGE}") == _range_java(False)
    assert _git(repo, "show", f"{c2_hash}:README.md") == "# demo (reverted)\n"


def test_revert_of_with_operations_is_hand_written_and_keeps_footer(tmp_path):
    # Backward compatibility with SZZG-0084/0085: operations describe a partial
    # revert by hand; git revert is not run, but the footer is still added.
    partial = [{"type": "replace", "path": RANGE, "old": BUGGY, "new": "return value >= min && value < max;"}]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _revert_commits(message="c2: partially revert c1", extra_ops=partial), bugs=[
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "c1", "role": "direct"}],
            "bug_fixing_commits": [{"commit": "c2", "role": "partial_fix"}],
            "faults": [{"commit": "c1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "c2", "file": RANGE, "statement": "return value >= min && value < max;"}],
        }
    ])
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    c2_hash = commit_map["c2"]["hash"]
    assert "return value >= min && value < max;" in _git(repo, "show", f"{c2_hash}:{RANGE}")
    assert _log_line(repo, c2_hash, "%s") == "c2: partially revert c1"
    assert _log_line(repo, c2_hash, "%b").strip() == f"This reverts commit {commit_map['c1']['hash']}."


def test_revert_of_merge_with_mainline(tmp_path):
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "f1: bug on feature", "role": "bug_introducing", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "m1", "branch": "main", "parents": ["c0", "f1"], "message": "m1: merge feature", "role": "merge"},
        {"id": "c1", "branch": "main", "parents": ["m1"], "role": "bug_fixing", "revert_of": "m1", "mainline": 1},
    ]
    bugs = [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "f1", "role": "direct"}],
            "bug_fixing_commits": [{"commit": "c1", "role": "complete_fix"}],
            "faults": [{"commit": "f1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "c1", "file": RANGE, "statement": FIXED}],
        }
    ]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=bugs)
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    assert _git(repo, "show", f"{commit_map['c1']['hash']}:{RANGE}") == _range_java(False)
    assert _log_line(repo, commit_map["c1"]["hash"], "%s") == 'Revert "m1: merge feature"'
    assert _log_line(repo, commit_map["c1"]["hash"], "%b").strip() == f"This reverts commit {commit_map['m1']['hash']}."


def _conflict_commits(*, resolution: dict | None) -> list[dict]:
    merge: dict = {"id": "m1", "branch": "main", "parents": ["c1", "f1"], "message": "m1: merge feature", "role": "bug_fixing"}
    if resolution is not None:
        merge["resolution"] = resolution
    return [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "f1: strict bounds", "role": "bug_introducing", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1: inclusive bounds with comment", "role": "intermediate", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": "return value >= min && value <= max; // inclusive"}]},
        merge,
    ]


def _conflict_bugs() -> list[dict]:
    return [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "f1", "role": "direct"}],
            "bug_fixing_commits": [{"commit": "m1", "role": "complete_fix"}],
            "faults": [{"commit": "f1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "m1", "file": RANGE, "statement": "return value >= min && value <= max; // resolved"}],
        }
    ]


def test_conflicting_merge_is_resolved_with_resolution(tmp_path):
    resolved = _range_java(False).replace(FIXED, "return value >= min && value <= max; // resolved")
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _conflict_commits(resolution={RANGE: resolved}), bugs=_conflict_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    m1 = commit_map["m1"]["hash"]
    assert _log_line(repo, m1, "%P").split() == [commit_map["c1"]["hash"], commit_map["f1"]["hash"]]
    assert _git(repo, "show", f"{m1}:{RANGE}") == resolved
    assert "<<<<<<<" not in _git(repo, "show", f"{m1}:{RANGE}")
    assert commit_map["m1"]["resolved_conflicts"] == [RANGE]
    assert _git(repo, "status", "--porcelain").strip() == ""


def test_conflicting_merge_without_resolution_raises(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _conflict_commits(resolution=None), bugs=_conflict_bugs())
    out = tmp_path / "out"
    with pytest.raises(GraphGenerationError, match=r"reported conflicts in \['src/main/java/example/Range.java'\].*resolution"):
        generate_graph_repository(scenario, out, force=True)
    error = json.loads((out / "metadata" / "generation-error.json").read_text(encoding="utf-8"))
    assert "resolution" in error["error"]


def test_resolution_must_cover_all_conflicted_paths(tmp_path):
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", _conflict_commits(resolution={"docs/NOTE.md": "unrelated\n"}), bugs=_conflict_bugs())
    with pytest.raises(GraphGenerationError, match="does not cover conflicted paths"):
        generate_graph_repository(scenario, tmp_path / "out", force=True)


def test_conflicting_cherry_pick_is_resolved_with_resolution(tmp_path):
    resolved = _range_java(False).replace(FIXED, "return value > min && value < max; // picked")
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1: bug", "role": "bug_introducing", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "r0", "branch": "release", "parents": ["c0"], "message": "r0: comment", "role": "intermediate", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": "return value >= min && value <= max; // release"}]},
        {"id": "r1", "branch": "release", "parents": ["r0"], "message": "r1: pick bug", "role": "cherry_pick", "cherry_pick_of": "c1", "cherry_pick_trailer": True, "resolution": {RANGE: resolved}},
        {"id": "c2", "branch": "main", "parents": ["c1"], "message": "c2: fix", "role": "bug_fixing", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_cherry_pick_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    r1 = commit_map["r1"]["hash"]
    assert _git(repo, "show", f"{r1}:{RANGE}") == resolved
    assert _log_line(repo, r1, "%P") == commit_map["r0"]["hash"]
    assert _log_line(repo, r1, "%b").strip() == f"(cherry picked from commit {commit_map['c1']['hash']})"
    assert not (repo / ".git" / "CHERRY_PICK_HEAD").exists()
    assert commit_map["r1"]["resolved_conflicts"] == [RANGE]


# ---------------------------------------------------------------------------
# PR #31 review follow-up: reserved generated ids, root-level legacy path,
# parent/owner timestamp interval, non-ASCII conflict paths
# ---------------------------------------------------------------------------


def _colliding_commits(colliding_id: str, position: str) -> tuple[list[dict], list[dict]]:
    """A commit_generator owner `c2` plus a scenario commit that already uses one of its generated ids."""
    c0 = {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]}
    bic = {"id": "c1", "branch": "main", "parents": ["c0"], "message": "c1: bug", "role": "bug_introducing", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]}
    owner = {"id": "c2", "branch": "main", "parents": ["c1"], "message": "c2: churn", "role": "intermediate", "operations": [{"type": "commit_generator", "generator": "unrelated_changes", "count": 2, "path": "generated"}]}
    fix = {"id": "c3", "branch": "main", "parents": ["c2"], "message": "c3: fix", "role": "bug_fixing", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]}
    if position == "before":
        bic["id"] = colliding_id
        owner["parents"] = [colliding_id]
    else:
        fix["id"] = colliding_id
    commits = [c0, bic, owner, fix]
    bugs = [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": bic["id"], "role": "direct"}],
            "bug_fixing_commits": [{"commit": fix["id"], "role": "complete_fix"}],
            "faults": [{"commit": bic["id"], "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": fix["id"], "file": RANGE, "statement": FIXED}],
        }
    ]
    return commits, bugs


@pytest.mark.parametrize("position", ["before", "after"])
def test_commit_generator_refuses_ids_that_collide_with_scenario_commits(tmp_path, position):
    commits, bugs = _colliding_commits("c2.g1", position)
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=bugs)
    out = tmp_path / "out"
    with pytest.raises(GraphGenerationError, match=r"c2\.g1.*reserved"):
        generate_graph_repository(scenario, out, force=True)
    # Nothing was generated and nothing was overwritten: no commit map was written.
    assert not (out / "metadata" / "commit-map.json").exists()


def test_commit_generator_does_not_collide_with_unrelated_dotted_ids(tmp_path):
    # An id in another owner's namespace (c1.g1) is fine; both maps stay consistent.
    commits, bugs = _colliding_commits("c1.g1", "before")
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=bugs)
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    assert commit_map["c2"]["generated_commits"] == ["c2.g1", "c2.g2"]
    assert commit_map["c1.g1"]["role"] == "bug_introducing"
    assert _graph_map(out)["commits"]["c1.g1"]["hash"] == commit_map["c1.g1"]["hash"]
    assert _log_line(repo, commit_map["c2.g1"]["hash"], "%P") == commit_map["c1.g1"]["hash"]


def test_commit_generator_legacy_root_level_path_generates_and_verifies(tmp_path):
    commits = _commit_generator_commits(2, files=1, path="notes.txt")
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_commit_generator_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    for gid in commit_map["c2"]["generated_commits"]:
        assert _git(repo, "show", "--name-only", "--format=", commit_map[gid]["hash"]).split() == ["unrelated_changes-01.txt"]
        assert commit_map[gid]["path"] == "unrelated_changes-01.txt"
    assert "unrelated_changes-01.txt" in _git(repo, "ls-tree", "--name-only", commit_map["c2"]["hash"]).split()


def test_commit_generator_dates_stay_inside_the_parent_owner_interval(tmp_path):
    commits = _commit_generator_commits(2)
    commits[1]["date"] = "2024-01-01T10:01:00Z"
    commits[2]["date"] = "2024-01-01T10:02:00Z"
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_commit_generator_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    ids = ["c1", "c2.g1", "c2.g2", "c2"]
    for fmt in ("%at", "%ct"):
        stamps = [int(_log_line(repo, commit_map[cid]["hash"], fmt)) for cid in ids]
        assert stamps == sorted(stamps) and len(set(stamps)) == len(stamps), (fmt, stamps)
        assert stamps[0] == 1704103260 and stamps[-1] == 1704103320  # 10:01:00Z .. 10:02:00Z
    assert commit_map["c2.g1"]["timestamp_placement"] == "spaced"


def test_commit_generator_dates_are_clamped_when_the_interval_is_too_short(tmp_path):
    commits = _commit_generator_commits(3)
    commits[1]["date"] = "2024-01-01T10:00:00Z"
    commits[2]["date"] = "2024-01-01T10:00:01Z"
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_commit_generator_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    ids = ["c1", "c2.g1", "c2.g2", "c2.g3", "c2"]
    stamps = [int(_log_line(repo, commit_map[cid]["hash"], "%at")) for cid in ids]
    assert stamps == sorted(stamps), stamps  # non-decreasing, never before the parent or after the owner
    assert stamps[0] == 1704103200 and stamps[-1] == 1704103201
    assert all(commit_map[gid]["timestamp_placement"] == "clamped" for gid in commit_map["c2"]["generated_commits"])
    assert "dates clamped to the parent" in (out / "metadata" / "generation.log").read_text(encoding="utf-8")


def test_conflicting_merge_with_non_ascii_path_is_resolved(tmp_path):
    path = "src/main/java/example/範囲.java"
    resolved = _range_java(False).replace(FIXED, "return value >= min && value <= max; // resolved")
    commits = _conflict_commits(resolution={path: resolved})
    for commit in commits:
        for op in commit.get("operations", []):
            if op.get("path") == RANGE:
                op["path"] = path
    bugs = _conflict_bugs()
    for bug in bugs:
        for entry in bug["faults"] + bug["fixes"]:
            entry["file"] = path
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=bugs)
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    m1 = commit_map["m1"]["hash"]
    assert commit_map["m1"]["resolved_conflicts"] == [path]
    assert _git(repo, "show", f"{m1}:{path}") == resolved
    assert _git(repo, "status", "--porcelain").strip() == ""


def _stamps(repo: Path, commit_map: dict, ids: list[str], fmt: str) -> list[int]:
    return [int(_log_line(repo, commit_map[cid]["hash"], fmt)) for cid in ids]


def test_commit_generator_places_author_and_committer_dates_in_their_own_intervals(tmp_path):
    # Reviewer case: the author and committer intervals do not overlap (parent 10:01/11:01, owner 10:02/11:02).
    commits = _commit_generator_commits(2)
    commits[1]["author_date"] = "2024-01-01T10:01:00Z"
    commits[1]["committer_date"] = "2024-01-01T11:01:00Z"
    commits[2]["author_date"] = "2024-01-01T10:02:00Z"
    commits[2]["committer_date"] = "2024-01-01T11:02:00Z"
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_commit_generator_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    ids = ["c1", "c2.g1", "c2.g2", "c2"]
    author = _stamps(repo, commit_map, ids, "%at")
    committer = _stamps(repo, commit_map, ids, "%ct")
    assert author == sorted(author) and len(set(author)) == 4, author
    assert committer == sorted(committer) and len(set(committer)) == 4, committer
    assert author[0] == 1704103260 and author[-1] == 1704103320  # 10:01:00Z .. 10:02:00Z
    assert committer[0] == 1704106860 and committer[-1] == 1704106920  # 11:01:00Z .. 11:02:00Z
    assert commit_map["c2.g1"]["timestamp_placement"] == "spaced"
    assert commit_map["c2.g1"]["timestamp_placement_detail"] == {"author": "spaced", "committer": "spaced"}
    assert "clamped" not in (out / "metadata" / "generation.log").read_text(encoding="utf-8")


def test_commit_generator_uses_the_inherited_author_date_of_the_owner(tmp_path):
    # The owner is a rebased commit whose author date is inherited from f1 (10:01:00Z)
    # while its committer date is explicit (12:00:00Z); the parent c0 is at 09:00:00Z.
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "c0: initial", "role": "initial", "date": "2024-01-01T09:00:00Z", "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "f1: strict bounds", "role": "origin_bug_introducing", "date": "2024-01-01T10:01:00Z", "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "r1", "branch": "main", "parents": ["c0"], "message": "r1: replayed strict bounds", "role": "bug_introducing", "rebase_of": "f1", "inherit_author_date": True, "committer_date": "2024-01-01T12:00:00Z",
         "operations": [{"type": "commit_generator", "generator": "unrelated_changes", "count": 2, "path": "generated"}, {"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "c3", "branch": "main", "parents": ["r1"], "message": "c3: fix", "role": "bug_fixing", "date": "2024-01-01T13:00:00Z", "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]
    bugs = [
        {
            "id": "B001",
            "bug_introducing_commits": [{"commit": "r1", "role": "direct"}, {"commit": "f1", "role": "origin"}],
            "bug_fixing_commits": [{"commit": "c3", "role": "complete_fix"}],
            "faults": [{"commit": "r1", "file": RANGE, "statement": BUGGY}],
            "fixes": [{"commit": "c3", "file": RANGE, "statement": FIXED}],
        }
    ]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=bugs, extra={"expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["r1"]}}})
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    assert _log_line(repo, commit_map["r1"]["hash"], "%at") == "1704103260"  # inherited 10:01:00Z
    assert _log_line(repo, commit_map["r1"]["hash"], "%ct") == "1704110400"  # explicit 12:00:00Z
    ids = ["c0", "r1.g1", "r1.g2", "r1"]
    author = _stamps(repo, commit_map, ids, "%at")
    committer = _stamps(repo, commit_map, ids, "%ct")
    assert author == sorted(author) and len(set(author)) == 4, author  # 09:00 < g1 < g2 < 10:01 (inherited)
    assert committer == sorted(committer) and len(set(committer)) == 4, committer  # 09:00 < g1 < g2 < 12:00
    assert commit_map["r1.g1"]["timestamp_placement_detail"] == {"author": "spaced", "committer": "spaced"}


def test_commit_generator_ignores_an_overridden_parent_date_fallback(tmp_path):
    # The parent's original `date` is overridden by explicit author/committer dates and must not act as a bound.
    commits = _commit_generator_commits(2)
    commits[1]["date"] = "2024-01-10T10:01:00Z"
    commits[1]["author_date"] = "2024-01-01T10:01:00Z"
    commits[1]["committer_date"] = "2024-01-01T10:01:00Z"
    commits[2]["date"] = "2024-01-01T10:02:00Z"
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=_commit_generator_bugs())
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    repo = out / "repo"
    assert _stamps(repo, commit_map, ["c1"], "%at") == [1704103260]  # the effective parent date, not 2024-01-10
    assert _stamps(repo, commit_map, ["c2.g1", "c2.g2"], "%at") == [1704103280, 1704103300]  # 10:01:20Z, 10:01:40Z
    assert _stamps(repo, commit_map, ["c2.g1", "c2.g2"], "%ct") == [1704103280, 1704103300]
    assert commit_map["c2.g1"]["timestamp_placement"] == "spaced"


# ---------------------------------------------------------------------------
# Mixed explicit / default timelines (#9, PR #34 re-review)
# ---------------------------------------------------------------------------


def test_mixed_explicit_and_default_timelines_stay_ordered(tmp_path):
    """A scenario that pins only some timestamps must not invert its history.

    Four shipped rebase scenarios pinned the replay date and left the earlier
    commits to the generator; when the defaults moved to a per-scenario base
    date, the parents landed a year *after* the pinned children. Such scenarios
    keep the plain one-day-per-commit schedule, and the pinned values are still
    reproduced verbatim.
    """
    commits = [
        {"id": "c0", "branch": "main", "parents": [], "message": "add the range check", "role": "initial",
         "operations": [{"type": "write_file", "path": RANGE, "content": _range_java(False)}]},
        {"id": "f1", "branch": "feature", "parents": ["c0"], "message": "make the range check exclusive",
         "role": "origin_bug_introducing",
         "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "r1", "branch": "main", "parents": ["c0"], "role": "bug_introducing", "rebase_of": "f1",
         "inherit_message": True, "inherit_author_date": True, "committer_date": "2024-01-05T09:30:00Z",
         "operations": [{"type": "replace", "path": RANGE, "old": FIXED, "new": BUGGY}]},
        {"id": "c2", "branch": "main", "parents": ["r1"], "message": "accept the range bounds again",
         "role": "bug_fixing", "date": "2024-01-08T10:00:00Z",
         "operations": [{"type": "replace", "path": RANGE, "old": BUGGY, "new": FIXED}]},
    ]
    bugs = [{"id": "B001",
             "bug_introducing_commits": [{"commit": "r1", "role": "direct"}],
             "bug_fixing_commits": [{"commit": "c2", "role": "complete_fix"}]}]
    scenario = _write_graph_scenario(tmp_path / "s.graph.yml", commits, bugs=bugs, scenario_id="SZZG-9901")
    out = tmp_path / "out"
    commit_map, verify = generate_graph_repository(scenario, out, force=True)
    assert verify is not None and not verify.has_errors()
    assert [f.code for f in verify.findings if f.code in ("GE630", "GW631")] == []

    repo = out / "repo"
    committer = {cid: _log_line(repo, entry["hash"], "%cI") for cid, entry in commit_map.items()}
    author = {cid: _log_line(repo, entry["hash"], "%aI") for cid, entry in commit_map.items()}

    # the pinned values survive
    assert committer["r1"] == "2024-01-05T09:30:00Z"
    assert committer["c2"] == author["c2"] == "2024-01-08T10:00:00Z"
    # the generated parents come first, and the inherited author date is not in the future
    assert committer["c0"] < committer["r1"] < committer["c2"]
    assert committer["c0"] <= committer["f1"]
    assert author["r1"] == author["f1"] <= committer["r1"], "the replayed commit keeps f1's author date"

    # a scenario with no pinned timestamps still gets the spread-out schedule
    plain = [dict(c) for c in commits]
    for c in plain:
        c.pop("committer_date", None)
        c.pop("date", None)
    plain[2]["message"] = "make the range check exclusive"
    plain[2].pop("inherit_message", None)
    plain[2].pop("inherit_author_date", None)
    scenario2 = _write_graph_scenario(tmp_path / "s2.graph.yml", plain, bugs=bugs, scenario_id="SZZG-9902")
    map2, verify2 = generate_graph_repository(scenario2, tmp_path / "out2", force=True)
    assert verify2 is not None and not verify2.has_errors()
    repo2 = tmp_path / "out2" / "repo"
    stamps = [_log_line(repo2, map2[cid]["hash"], "%cI") for cid in ("c0", "f1", "r1", "c2")]
    assert stamps == sorted(stamps)
    assert len({s[:10] for s in stamps}) == 4          # four distinct days
    assert len({s[11:] for s in stamps}) > 1           # not a single time of day


def test_every_shipped_scenario_resolves_to_an_ordered_timeline():
    """No scenario in either suite may resolve to a child older than a parent."""
    import yaml
    from szzbench.gitutils import resolve_commit_metadata

    root = Path(__file__).resolve().parents[1]
    offenders = []
    for pattern in ("scenarios/SZZ-*/scenario.yml", "advanced-scenarios/SZZG-*/scenario.graph.yml"):
        for path in sorted(root.glob(pattern)):
            data = yaml.safe_load(path.read_text())
            commits = data.get("commits") or []
            meta = {c.get("id"): resolve_commit_metadata(data, c, i) for i, c in enumerate(commits)}
            order = [c.get("id") for c in commits]
            for i, commit in enumerate(commits):
                cid = commit.get("id")
                parents = commit.get("parents")
                if not isinstance(parents, list):          # classic suite: the previous commit
                    parents = [order[i - 1]] if i else []
                for parent in parents:
                    if parent in meta and meta[parent].committer_date > meta[cid].committer_date:
                        offenders.append(
                            f"{data['meta']['id']}: {cid} {meta[cid].committer_date} < {parent} {meta[parent].committer_date}"
                        )
    assert offenders == []
