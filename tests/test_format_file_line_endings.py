"""``format_file``, ``move_entity`` and ``copy_entity`` keep a file's CRLF line endings (issue #181).

The three graph operations read their files with ``Path.read_text``, whose
universal-newline mode turns every ``\\r\\n`` into ``\\n``, and wrote them back
with LF.  A ``format_file`` on a CRLF file was therefore no whitespace-only
commit: it also rewrote every line ending, which ``git blame -w`` does not skip,
and ``validate-graph --simulate``, whose simulator works on LF text, could not
see it.  The operations now keep the convention by the rule ``replace`` follows
without a ``line_ending`` key: a file whose every newline is CRLF stays CRLF,
anything else is written with LF.  An entity operation writes the source
file's convention, or, with ``append``, the destination's own.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_operations import apply_graph_operation_to_filesystem
from szzbench.graph_validator import validate_graph_scenario_file


def _repo(tmp_path: Path, files: dict[str, bytes]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for name, data in files.items():
        (repo / name).write_bytes(data)
    return repo


@pytest.mark.parametrize("before, after", [
    (b"a  \r\nb\t\r\nc", b"a\r\nb\r\nc\r\n"),     # the newline added at the end is CRLF too
    (b"a  \nb\t\nc", b"a\nb\nc\n"),
    (b"a  \r\nb\t\nc\n", b"a\nb\nc\n"),           # mixed is written as LF, as replace writes it
], ids=["crlf", "lf", "mixed"])
def test_format_file_strips_trailing_whitespace_in_the_files_line_endings(tmp_path, before, after):
    repo = _repo(tmp_path, {"a.txt": before})
    apply_graph_operation_to_filesystem(repo, {"type": "format_file", "path": "a.txt"})
    assert (repo / "a.txt").read_bytes() == after


def test_copy_entity_writes_the_source_files_line_endings(tmp_path):
    repo = _repo(tmp_path, {"A.java": b"class A {\r\n}\r\n"})
    apply_graph_operation_to_filesystem(repo, {"type": "copy_entity", "entity": {"name": "A"},
                                               "from_file": "A.java", "to_file": "B.java"})
    assert (repo / "B.java").read_bytes() == b"// SZZBench copy_entity: A\r\nclass A {\r\n}\r\n"


def test_an_appended_destination_keeps_its_own_line_endings(tmp_path):
    repo = _repo(tmp_path, {"A.java": b"class A {}\n", "B.java": b"class B {}\r\n\r\n"})
    apply_graph_operation_to_filesystem(repo, {"type": "move_entity", "entity": {"name": "A"}, "from_file": "A.java",
                                               "to_file": "B.java", "append": True, "remove_source_file": True})
    assert (repo / "B.java").read_bytes() == b"class B {}\r\n\r\n// SZZBench move_entity: A\r\nclass A {}\r\n"


def test_formatting_a_clean_crlf_file_is_empty_in_generation_as_in_the_simulation(tmp_path):
    """--simulate found nothing to format (GE202), and generation committed an LF rewrite of the file."""
    data = {"schema_version": "graph-1.0",
            "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
            "repository": {"name": "probe", "default_branch": "main"}, "graph": {"model": "commit_dag"},
            "commits": [{"id": "c0", "branch": "main", "parents": [], "message": "Add the notes", "role": "initial",
                         "operations": [{"type": "write_file", "path": "a.txt", "line_ending": "crlf", "content": "a\nb\n"}]},
                        {"id": "c1", "branch": "main", "parents": ["c0"], "message": "Format the notes",
                         "role": "formatting", "operations": [{"type": "format_file", "path": "a.txt"}]}],
            "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                      "bug_fixing_commits": [{"commit": "c1", "role": "complete_fix"}]}],
            "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}}
    path = tmp_path / "SZZG-9900" / "scenario.graph.yml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    _, result = validate_graph_scenario_file(path, simulate=True)
    assert [(f.code, f.location) for f in result.findings if f.severity == "ERROR"] == [("GE202", "commits[1]")]
    with pytest.raises(GraphGenerationError, match="commit would be empty"):
        generate_graph_repository(path, tmp_path / "out", force=True)
