"""A file ``write_binary_file`` wrote stays binary: a text operation on it is GE065 (issue #277).

The replay of ``validate-graph --simulate`` keeps such a file as bytes and
refused a ``replace`` on it (GE201), while ``generate-graph`` read the bytes
as UTF-8 and committed the edit: the reverse of the usual drift, in which a
valid scenario failed strict simulated validation.  The text operations the
replay refuses on bytes are now refused statically, so ``generate-graph``
stops at validation too, and the replay never reaches them.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest
import yaml

from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_simulator import simulate_graph_scenario
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static

ROOT = Path(__file__).resolve().parents[1]


def _binary(path: str, data: bytes = b"limit=5\n") -> dict:
    return {"type": "write_binary_file", "path": path, "content_base64": base64.b64encode(data).decode()}


def _text(path: str, content: str = "limit=5\n") -> dict:
    return {"type": "write_file", "path": path, "content": content}


def _replace(path: str) -> dict:
    return {"type": "replace", "path": path, "old": "limit=5", "new": "limit=6"}


def _commit(cid: str, parents: list[str], *operations: dict, branch: str = "main", **keys) -> dict:
    return {"id": cid, "branch": branch, "parents": parents, "message": f"Update the limits ({cid})",
            "role": "merge" if len(parents) > 1 else "intermediate", "operations": list(operations), **keys}


def _scenario(*commits: dict) -> dict:
    return {"schema_version": "graph-1.0",
            "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
            "repository": {"name": "probe", "default_branch": "main"}, "graph": {"model": "commit_dag"},
            "commits": list(commits),
            "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                      "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}]}],
            "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}}


def _ge065(data: dict) -> list[str]:
    return [f.location for f in validate_graph_static(data).findings if f.code == "GE065"]


def test_the_issues_replace_is_refused_by_validate_graph_simulate_and_generate_graph_alike(tmp_path):
    """The issue's reproduction: GE201 with --simulate, a commit in generation."""
    data = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0001/scenario.graph.yml").read_text(encoding="utf-8"))
    data["commits"][0]["operations"].append(_binary("notes/data.txt"))
    data["commits"][1]["operations"].append(_replace("notes/data.txt"))
    scenario = tmp_path / "SZZG-0001" / "scenario.graph.yml"
    scenario.parent.mkdir()
    scenario.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    _, result = validate_graph_scenario_file(scenario, simulate=True, strict_paths=True)
    [error] = result.error_findings()
    assert (error.code, error.location) == ("GE065", "commits[1].operations[1].path")
    assert "write_binary_file wrote it in commit 'c0' (commits[0].operations[1])" in error.message
    with pytest.raises(GraphGenerationError, match="validation failed"):
        generate_graph_repository(scenario, tmp_path / "out")


def test_a_file_written_as_bytes_stays_binary_until_it_is_written_as_text():
    """GE065 refuses exactly the operations the replay refuses on bytes, through a rename and two text writes."""
    data = _scenario(
        _commit("c0", [], _binary("data.bin"), _binary("other.bin"), _text("a.txt")),
        _commit("c1", ["c0"], {"type": "rename_file", "from": "data.bin", "to": "moved.bin"},
                {"type": "insert_after", "path": "moved.bin", "anchor": "limit=5", "content": "x\n"},
                {"type": "copy_entity", "entity": {"name": "A"}, "from_file": "a.txt", "to_file": "moved.bin",
                 "append": True},
                {"type": "move_entity", "entity": {"name": "M"}, "from_file": "moved.bin", "to_file": "b.txt"},
                {"type": "copy_entity", "entity": {"name": "A"}, "from_file": "a.txt", "to_file": "other.bin"}),
        _commit("c2", ["c1"], _text("moved.bin"), {"type": "format_file", "path": "moved.bin"}, _replace("other.bin")))
    assert _ge065(data) == ["commits[1].operations[1].path", "commits[1].operations[2].to_file",
                            "commits[1].operations[3].from_file"]
    refused = [f.location for f in simulate_graph_scenario(data).error_findings() if "binary file" in f.message]
    assert refused == ["commits[1].operations[1]", "commits[1].operations[2]", "commits[1].operations[3]"]


#: f1 rewrites the bytes of c0, and p1 on main picks it.
PICKED = (_commit("c0", [], _binary("data.txt")),
          _commit("f1", ["c0"], _binary("data.txt", b"limit=6\n"), branch="feature"),
          _commit("p1", ["c0"], cherry_pick_of="f1"))
#: data.txt is a copy of source.txt's bytes; p1 picks f1's text over it, and r1 copies the bytes back.
COPY = {"type": "copy_file", "from": "source.txt", "to": "data.txt", "overwrite": True}
RECOPIED = (_commit("c0", [], _binary("source.txt"), COPY),
            _commit("f1", ["c0"], _text("data.txt", "limit=6\n"), branch="feature"),
            _commit("p1", ["c0"], cherry_pick_of="f1"), _commit("r1", ["p1"], COPY),
            _commit("t1", ["f1"], _text("data.txt", "limit=6\n"), branch="other", allow_empty=True))


@pytest.mark.parametrize("commits, refused", [
    # the binary file comes in with the second parent
    ((_commit("c0", [], _text("a.txt")), _commit("f1", ["c0"], _binary("data.txt"), branch="feature"),
      _commit("m1", ["c0", "f1"]), _commit("c2", ["m1"], _replace("data.txt"))),
     ["commits[3].operations[0].path"]),
    # the cherry-picked commit does not touch data.txt, which the branch rewrote as text
    ((_commit("c0", [], _binary("data.txt"), _text("a.txt")),
      _commit("f1", ["c0"], _text("data.txt", "limit=5\nunit=kb\n"), branch="feature"),
      _commit("c1", ["c0"], {"type": "replace", "path": "a.txt", "old": "5", "new": "6"}),
      _commit("p1", ["f1"], branch="feature", cherry_pick_of="c1"),
      _commit("p2", ["p1"], _replace("data.txt"), branch="feature")),
     []),
    # a pick of p1, and a revert of it, bring what a pick of f1 does (PR #281 review)
    ((*PICKED, _commit("t1", ["c0"], _text("data.txt"), branch="other", allow_empty=True),
      _commit("p2", ["t1"], branch="other", cherry_pick_of="p1"),
      _commit("t2", ["p2"], {"type": "replace", "path": "data.txt", "old": "limit=6", "new": "limit=7"},
              branch="other")),
     ["commits[5].operations[0].path"]),
    ((*PICKED, _commit("t1", ["c0"], _text("data.txt", "limit=6\n"), branch="other"),
      _commit("p2", ["t1"], branch="other", revert_of="p1"),
      _commit("t2", ["p2"], _replace("data.txt"), branch="other")),
     ["commits[5].operations[0].path"]),
    # a pick of r1 brings the bytes back, though the writer of data.txt at p1 was still c0's (PR #281 review)
    ((*RECOPIED, _commit("p2", ["t1"], branch="other", cherry_pick_of="r1"),
      _commit("t2", ["p2"], _replace("data.txt"), branch="other")),
     ["commits[6].operations[0].path"]),
    ((*RECOPIED, _commit("p2", ["t1"], {"type": "apply_patch_from", "commit": "r1"}, branch="other"),
      _commit("t2", ["p2"], _replace("data.txt"), branch="other")),
     ["commits[6].operations[0].path"]),
], ids=["merge-keeps-the-binary-file", "cherry-pick-of-another-file", "pick-of-a-pick", "revert-of-a-pick",
        "pick-of-a-copy-after-a-picked-text", "patch-of-a-copy-after-a-picked-text"])
def test_what_git_computes_brings_the_binary_files_it_may_carry(commits, refused):
    assert _ge065(_scenario(*commits)) == refused
