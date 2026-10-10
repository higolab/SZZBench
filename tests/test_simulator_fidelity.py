"""The in-memory replay of ``validate-graph --simulate`` and what it does not model.

Issue #183: since issue #94 ``validate-graph --simulate`` generates every
scenario with a commit Git computes (a merge, a real revert or cherry-pick,
``apply_patch_from``, ``apply_squash``, a ``resolution``) with Git, so the
replay's file-level model of merges and patches was reached by no command.
Called directly, it still answered for a merge with an approximation of its
own (``GE200 ... merge conflict for path: a.txt`` where the command says
GE203).  The model is gone, and such a commit is refused instead.

Issue #240: the replay ignored an operation's ``encoding``, which
``validate-graph`` accepted as any text encoding Python knows.  A file written
in UTF-16 and edited without the key, UTF-8 text read as latin-1, or text
latin-1 cannot encode passed ``--simulate`` and failed generation, and a
commit that only added a byte order mark was GE202 there and a commit in Git.
The key is now ``utf-8`` or ``utf-8-sig``, as in the classic suite (E042 /
GE061), and the replay applies it as the classic replay does.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from szzbench.graph_generator import generate_graph_repository
from szzbench.graph_simulator import SimFile, simulate_graph_scenario, simulated_snapshots
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static

from support import git_bytes


def _write_file(path: str, content: str, **keys) -> dict:
    return {"type": "write_file", "path": path, "content": content, **keys}


def _replace(path: str, old: str, new: str, **keys) -> dict:
    return {"type": "replace", "path": path, "old": old, "new": new, **keys}


def _commit(cid: str, parents: list[str], *operations: dict, branch: str = "main") -> dict:
    commit = {"id": cid, "branch": branch, "parents": parents, "message": f"Update the sources ({cid})",
              "role": "merge" if len(parents) > 1 else "intermediate"}
    if operations:
        commit["operations"] = list(operations)
    return commit


def _scenario(*commits: dict, bug: dict | None = None) -> dict:
    return {"schema_version": "graph-1.0",
            "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
            "repository": {"name": "probe", "default_branch": "main"}, "graph": {"model": "commit_dag"},
            "commits": list(commits),
            "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                      "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}], **(bug or {})}],
            "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}}


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "SZZG-9900" / "scenario.graph.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _findings(result) -> list[tuple[str, str]]:
    return [(f.code, f.location) for f in result.findings]


# --- issue #183: no file-level model of what Git computes ----------------------------------

#: The issue's two scenarios: a merge that conflicts, and an apply_patch_from of a merge.
CONFLICT = _scenario(_commit("c0", [], _write_file("a.txt", "a\n")), _commit("c1", ["c0"], _replace("a.txt", "a", "left")),
                     _commit("f1", ["c0"], _replace("a.txt", "a", "right"), branch="feature"),
                     _commit("m1", ["c1", "f1"]))
PATCH = _scenario(_commit("c0", [], _write_file("a.txt", "a\n")),
                  _commit("f1", ["c0"], _write_file("f.txt", "f\n"), branch="feature"), _commit("m1", ["c0", "f1"]),
                  _commit("rel", ["c0"], _write_file("r.txt", "r\n"), branch="release"),
                  _commit("a1", ["rel"], {"type": "apply_patch_from", "commit": "m1", "mainline": 1}, branch="release"))


@pytest.mark.parametrize("data, refused", [
    (CONFLICT, [("GE200", "commits[3]")]),
    (PATCH, [("GE200", "commits[2]"), ("GE200", "commits[4]")]),
], ids=["conflicting-merge", "patch-of-a-merge"])
def test_the_replay_refuses_a_commit_git_computes_instead_of_approximating_it(data, refused):
    result = simulate_graph_scenario(data)
    assert _findings(result) == refused
    assert all("validate-graph --simulate generates such a scenario with Git" in f.message for f in result.findings)


def test_the_snapshots_of_a_commit_git_computes_must_be_given():
    with pytest.raises(ValueError, match="does not model commit 'm1', whose content Git computes \\(merge\\)"):
        simulated_snapshots(CONFLICT)
    merged = {"a.txt": SimFile("resolved\n")}
    assert simulated_snapshots(CONFLICT, given={"m1": merged})["m1"] == merged


# --- issue #240: encoding is utf-8 or utf-8-sig, and the replay applies it ------------------

LIMITS = "src/Limits.java"
V1 = "class Limits { int max = 10; }\n"
CAFE = "class Limits { String unit = \"café\"; int max = 10; }\n"
LIMITS_FAULT = {"faults": [{"id": "F001", "commit": "c0", "file": LIMITS, "statement": "int max = 10;"}]}


def _limits(c0: dict, c1: dict) -> dict:
    return _scenario(_commit("c0", [], c0), _commit("c1", ["c0"], c1), bug=LIMITS_FAULT)


#: The first four rows of the issue's table: each passed --simulate and failed generate-graph.
@pytest.mark.parametrize("data, refused", [
    (_limits(_write_file(LIMITS, V1, encoding="utf-16"), _replace(LIMITS, "10", "9")),
     ["commits[0].operations[0].encoding"]),
    (_limits(_write_file(LIMITS, CAFE), _replace(LIMITS, "café", "cafe", encoding="latin-1")),
     ["commits[1].operations[0].encoding"]),
    (_limits(_write_file(LIMITS, V1), _write_file(LIMITS, V1.replace("int", "String unit = \"日本\"; int"), encoding="latin-1")),
     ["commits[1].operations[0].encoding"]),
    (_limits(_write_file(LIMITS, V1, encoding="utf-16"), _replace(LIMITS, "10", "9", encoding="utf-16")),
     ["commits[0].operations[0].encoding", "commits[1].operations[0].encoding"]),
], ids=["utf16-then-replace", "utf8-then-latin1-replace", "latin1-unencodable", "utf16-fault-statement"])
def test_a_codec_the_replay_does_not_model_is_ge061_at_the_operation(data, refused):
    errors = [f for f in validate_graph_static(data).findings if f.severity == "ERROR"]
    assert [(f.code, f.location) for f in errors] == [("GE061", location) for location in refused]
    assert "encoding must be 'utf-8' or 'utf-8-sig'" in errors[0].message


def test_a_bom_only_commit_passes_the_simulation_as_generation_commits_it(tmp_path):
    """The issue's last row: GE202 in the replay, a commit in Git."""
    data = _limits(_write_file(LIMITS, V1), _write_file(LIMITS, V1, encoding="utf-8-sig"))
    scenario = _write(tmp_path, data)
    _, result = validate_graph_scenario_file(scenario, simulate=True, strict_paths=True)
    assert [f for f in result.findings if f.severity == "ERROR"] == []
    commit_map, verification = generate_graph_repository(scenario, tmp_path / "out", force=True)
    assert not verification.has_errors()
    blob = git_bytes(tmp_path / "out/repo", "cat-file", "blob", f"{commit_map['c1']['hash']}:{LIMITS}")
    assert blob.startswith(b"\xef\xbb\xbf")
    assert simulated_snapshots(data)["c1"][LIMITS].content.encode("utf-8") == blob
