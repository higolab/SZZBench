"""Two generation options: ``inherit_author`` (issue #180) and ``line_ending`` on
``format_file``, ``move_entity`` and ``copy_entity`` (issue #181).

* #180: ``git cherry-pick`` and ``git rebase`` keep the author of the commit they
  replay, but a commit with ``cherry_pick_of``, ``backport_of`` or ``rebase_of``
  was authored by the pool author of its own position (SZZG-0065 ``r1``,
  SZZG-0124 ``r1``), and nothing could make it take its source's.
  ``inherit_author: true`` now does, the committer with it; the default keeps
  the pool author, so no shipped hash changes.  The author lint's history
  (``resolved_commit_authors``) follows it.
* #181: the three operations keep a file's line endings since PR #255, but took no
  ``line_ending`` key, so a formatting commit that also converts CRLF to LF could
  not be written.  The key now converts, as it does on ``replace``.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from support import git, git_bytes
from szzbench.gitutils import canonical_author, resolved_commit_authors
from szzbench.graph_generator import generate_graph_repository
from szzbench.graph_operations import apply_graph_operation_to_filesystem
from szzbench.graph_validator import validate_graph_scenario_file

ORIGINAL = "Orig Author <orig@example.com>"


def _scenario(tmp_path: Path, commits: list[dict]) -> Path:
    data = {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
        "repository": {"name": "probe", "default_branch": "main"},
        "commits": commits,
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }
    path = tmp_path / "SZZG-9900" / "scenario.graph.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _commit(cid: str, parents: list[str], branch: str = "main", **keys) -> dict:
    commit = {"id": cid, "branch": branch, "parents": parents, "message": f"Change {cid}", **keys}
    if not any(key in keys for key in ("cherry_pick_of", "backport_of")):    # a pick replays its source
        commit["operations"] = [{"type": "write_file", "path": f"{cid}.txt", "content": f"{cid}\n"}]
    return commit


# --- #180: inherit_author --------------------------------------------------------------------

def test_inherit_author_gives_the_commit_and_the_author_lint_the_sources_author(tmp_path):
    """p1 and p2 are picks, and b1 a backport of the pick p1; each would have the pool author of its position."""
    commits = [
        _commit("c0", []),
        _commit("c1", ["c0"], branch="feature", author=ORIGINAL),
        _commit("c2", ["c1"], branch="feature"),                                   # a pool author
        _commit("p1", ["c0"], branch="release", cherry_pick_of="c1", inherit_author=True),
        _commit("b1", ["c0"], branch="maint", backport_of="p1", inherit_author=True),   # through p1
        _commit("p2", ["p1"], branch="release", cherry_pick_of="c2", inherit_author=True),
    ]
    path = _scenario(tmp_path, commits)
    commit_map, _ = generate_graph_repository(path, tmp_path / "out")
    repo = tmp_path / "out" / "repo"

    def identities(cid: str) -> list[str]:
        return git(repo, "log", "-1", "--format=%an <%ae>%n%cn <%ce>", commit_map[cid]["hash"]).splitlines()

    assert identities("p1") == identities("b1") == [ORIGINAL, ORIGINAL]
    assert identities("p2") == [commit_map["c2"]["author"]] * 2
    assert commit_map["p2"]["author"] == commit_map["c2"]["author"] != commit_map["p1"]["author"]
    assert commit_map["p1"]["inherits"] == {"source": "c1", "source_hash": commit_map["c1"]["hash"],
                                            "message": False, "author_date": False, "author": True}
    # the history the author lint (W413 / GW413) reasons about is the one generated
    generated = [(cid, canonical_author(identities(cid)[0])) for cid in ("c0", "c1", "c2", "p1", "b1", "p2")]
    assert resolved_commit_authors(yaml.safe_load(path.read_text(encoding="utf-8"))) == generated


@pytest.mark.parametrize("keys, code, location, words", [
    ({"cherry_pick_of": "c1", "inherit_author": "yes"}, "GE076", "inherit_author",
     "inherit_author must be true or false, not 'yes'"),
    ({"cherry_pick_of": "c1", "inherit_author": True, "author": ORIGINAL}, "GE076", "inherit_author",
     "sets both author and inherit_author: true"),
    # a squash-rebase names two commits, and generation inherits from one (#179)
    ({"rebase_of": ["c1", "c2"], "inherit_author": True}, "GE074", "inherit_author",
     "its rebase_of is a list (a squash-rebase)"),
], ids=["not-a-boolean", "with-an-author", "rebase-of-a-list"])
def test_inherit_author_is_true_or_false_and_has_one_source(tmp_path, keys, code, location, words):
    commits = [_commit("c0", []), _commit("c1", ["c0"], branch="feature"), _commit("c2", ["c1"], branch="feature"),
               _commit("r1", ["c0"], branch="release", **keys)]
    _, result = validate_graph_scenario_file(_scenario(tmp_path, commits))
    errors = [f for f in result.findings if f.severity == "ERROR"]
    assert [(f.code, f.location) for f in errors] == [(code, f"commits[3].{location}")]
    assert words in errors[0].message


# --- #181: line_ending on format_file, move_entity and copy_entity ---------------------------

@pytest.mark.parametrize("files, op, written, expected", [
    ({"a.txt": b"a  \r\nb\r\n"}, {"type": "format_file", "path": "a.txt", "line_ending": "lf"}, "a.txt", b"a\nb\n"),
    ({"a.txt": b"a  \nb"}, {"type": "format_file", "path": "a.txt", "line_ending": "crlf"}, "a.txt", b"a\r\nb\r\n"),
    ({"A.java": b"class A {\r\n}\r\n"}, {"type": "copy_entity", "entity": {"name": "A"}, "from_file": "A.java",
                                         "to_file": "B.java", "line_ending": "lf"},
     "B.java", b"// SZZBench copy_entity: A\nclass A {\n}\n"),
], ids=["format-crlf-to-lf", "format-lf-to-crlf", "copy-entity-to-lf"])
def test_an_explicit_line_ending_converts_the_file_written(tmp_path, files, op, written, expected):
    repo = tmp_path / "repo"
    repo.mkdir()
    for name, data in files.items():
        (repo / name).write_bytes(data)
    apply_graph_operation_to_filesystem(repo, op)
    assert (repo / written).read_bytes() == expected


@pytest.mark.parametrize("op", [
    {"type": "format_file", "path": "c0.txt", "line_ending": "cr"},
    {"type": "move_entity", "entity": {"name": "A"}, "from_file": "c0.txt", "to_file": "B.java", "line_ending": "cr"},
], ids=["format_file", "move_entity"])
def test_a_line_ending_these_operations_cannot_write_is_ge061(tmp_path, op):
    commits = [_commit("c0", []), {**_commit("c1", ["c0"]), "operations": [op]}]
    _, result = validate_graph_scenario_file(_scenario(tmp_path, commits))
    assert [(f.code, f.location) for f in result.findings if f.severity == "ERROR"] == \
        [("GE061", "commits[1].operations[0].line_ending")]


def test_a_formatting_commit_that_converts_to_lf_simulates_and_generates_alike(tmp_path):
    """The simulator works on LF text and sees the whitespace go; generation writes the LF bytes."""
    commits = [{**_commit("c0", []), "operations": [{"type": "write_file", "path": "a.txt", "line_ending": "crlf",
                                                     "content": "a  \nb\n"}]},
               {**_commit("c1", ["c0"]), "operations": [{"type": "format_file", "path": "a.txt", "line_ending": "lf"}]}]
    path = _scenario(tmp_path, commits)
    _, result = validate_graph_scenario_file(path, simulate=True)
    assert not result.has_errors(), result.to_dict()
    commit_map, _ = generate_graph_repository(path, tmp_path / "out")
    assert git_bytes(tmp_path / "out" / "repo", "cat-file", "blob", f"{commit_map['c1']['hash']}:a.txt") == b"a\nb\n"
