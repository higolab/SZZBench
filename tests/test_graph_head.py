"""graph-map.json records where generate-graph left HEAD (issue #201).

HEAD stays on the branch of the scenario's last commit, which need not be the
default branch, and ``graph.ref_lifecycle`` may detach it.  Eleven shipped
graph repositories end on ``release``, and in some of them a bug-fixing commit
on ``main`` is not reachable from HEAD, so a tool that walks history from HEAD
(``git log`` without ``--all``) does not see it.  Nothing in ``metadata/`` said
where HEAD was; ``graph-map.json`` now records it as ``head``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from support import git, scenario_file
from szzbench.graph_generator import generate_graph_repository


def _commit(cid: str, parents: list[str], *, branch: str = "main") -> dict:
    return {"id": cid, "branch": branch, "parents": parents, "message": f"Edit the notes ({cid})",
            "role": "intermediate", "operations": [{"type": "write_file", "path": f"{cid}.txt", "content": f"{cid}\n"}]}


def _scenario(tmp_path: Path, ref_lifecycle: dict | None) -> Path:
    """main (c0 <- c1, the bug-fixing commit) and release (c0 <- r1), declared last."""
    graph: dict = {"model": "commit_dag"}
    if ref_lifecycle is not None:
        graph["ref_lifecycle"] = ref_lifecycle
    data = {
        "schema_version": "graph-1.0",
        "meta": {"id": "SZZG-9900", "title": "Where HEAD is", "category": "fixture", "factors": ["single-bic"]},
        "repository": {"name": "where-head-is", "default_branch": "main"},
        "graph": graph,
        "commits": [_commit("c0", []), _commit("c1", ["c0"]), _commit("r1", ["c0"], branch="release")],
        "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                  "bug_fixing_commits": [{"commit": "c1", "role": "complete_fix"}]}],
        "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}},
    }
    path = tmp_path / "scenario.graph.yml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _head(out: Path) -> dict:
    return json.loads((out / "metadata/graph-map.json").read_text(encoding="utf-8"))["head"]


@pytest.mark.parametrize("ref_lifecycle, branch", [
    (None, "release"),                                        # the last commit's branch, not main
    # both branches deleted: detached at the last commit; the tag keeps c1
    ({"delete_branches": ["release", "main"], "tags": [{"name": "v1", "commit": "c1"}]}, None),
], ids=["on the last commit's branch", "detached"])
def test_graph_map_records_where_head_is(tmp_path, ref_lifecycle, branch):
    out = tmp_path / "out"
    commit_map, result = generate_graph_repository(_scenario(tmp_path, ref_lifecycle), out)
    assert result is not None and not result.has_errors()
    repo = out / "repo"
    assert _head(out) == {"branch": branch, "hash": commit_map["r1"]["hash"]}
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == (branch or "HEAD")
    assert git(repo, "rev-parse", "HEAD") == commit_map["r1"]["hash"]
    # the bug-fixing commit is in the repository, but not in the history of HEAD
    assert commit_map["c1"]["hash"] not in git(repo, "rev-list", "HEAD").split()
    assert commit_map["c1"]["hash"] in git(repo, "rev-list", "--all").split()
    log = (out / "metadata/generation.log").read_text(encoding="utf-8").splitlines()
    assert (f"HEAD is on branch release ({commit_map['r1']['hash']})" if branch
            else f"HEAD is detached at {commit_map['r1']['hash']}") in log


def test_shipped_szzg_0054_leaves_its_bug_fixing_commit_out_of_head(tmp_path):
    """The example README.md and docs/generator-options.md give: HEAD on release, c3 on main unreachable."""
    scenario = scenario_file("SZZG-0054")
    data = yaml.safe_load(scenario.read_text(encoding="utf-8"))
    assert data["repository"]["default_branch"] == "main"
    assert [f["commit"] for b in data["bugs"] for f in b["bug_fixing_commits"]] == ["c3"]
    out = tmp_path / "out"
    commit_map, _ = generate_graph_repository(scenario, out)
    head = _head(out)
    assert head == {"branch": "release", "hash": commit_map["c4"]["hash"]}
    from_head = git(out / "repo", "rev-list", head["hash"]).split()
    assert commit_map["c3"]["hash"] not in from_head        # the only bug-fixing commit
    assert commit_map["c1"]["hash"] in from_head            # the bug-introducing commit is there
