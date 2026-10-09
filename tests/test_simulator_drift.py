"""``validate-graph --simulate`` models what ``generate-graph`` writes (issue #175).

The in-memory simulator, which ``--simulate`` runs for every scenario without
Git-computed commits, modelled six operation shapes differently from the
generator.  Two rejected a scenario that generates: a commit that edits a file
an earlier ``commit_generator`` wrote (the simulator wrote one placeholder file
where the generator writes ``<path>/<generator>-NN.txt``), and a ``chmod``-only
commit (the simulator kept no mode, although the generator enables
``core.filemode`` for a scenario that uses ``chmod``).  Four accepted a
scenario that generation then refused: ``commit_generator`` with ``count: 0``,
``move_entity`` with ``overwrite: false`` onto an existing file, a ``write_file``
onto a directory (refused with the bare OS message), and a rename that changes
only the letter case, which failed on macOS and succeeded on Linux.

The simulator now writes the generator's files with the generator's own
expansion, keeps the mode Git records, honours ``overwrite``, and refuses a
file over a directory; the generator names the operation and the path of an OS
error; and a case-only rename is GE060.  No test compared a simulated snapshot
with a generated tree, so the drift went unnoticed: the last tests here do, for
a scenario that exercises every file operation and for every shipped one.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

import szzbench.graph_simulator as graph_simulator
from szzbench.findings import ValidationResult
from szzbench.graph_generator import GraphGenerationError, generate_graph_repository
from szzbench.graph_operations import _block_text, apply_graph_operation_to_filesystem
from szzbench.graph_simulator import git_performed_features
from szzbench.graph_validator import validate_graph_scenario_file, validate_graph_static
from szzbench.gitutils import run_git_with_input
from szzbench.operations import OperationError, normalize_newlines

from support import git_bytes, git_stdout

ROOT = Path(__file__).resolve().parents[1]
GRAPH_SCENARIOS = sorted((ROOT / "advanced-scenarios").glob("SZZG-*/scenario.graph.yml"))


def _write_file(path: str, content: str) -> dict:
    return {"type": "write_file", "path": path, "content": content}


def _replace(path: str, old: str, new: str) -> dict:
    return {"type": "replace", "path": path, "old": old, "new": new}


def _chmod(path: str, mode: str) -> dict:
    return {"type": "chmod", "path": path, "mode": mode}


def _commit(cid: str, parents: list[str], *operations: dict) -> dict:
    return {"id": cid, "branch": "main", "parents": parents, "message": f"Update the sources ({cid})",
            "role": "intermediate", "operations": list(operations)}


def _scenario(*commits: dict) -> dict:
    return {"schema_version": "graph-1.0",
            "meta": {"id": "SZZG-9900", "title": "probe", "category": "probe", "factors": ["single-bic"]},
            "repository": {"name": "probe", "default_branch": "main"}, "graph": {"model": "commit_dag"},
            "commits": list(commits),
            "bugs": [{"id": "B001", "bug_introducing_commits": [{"commit": "c0", "role": "direct"}],
                      "bug_fixing_commits": [{"commit": commits[-1]["id"], "role": "complete_fix"}]}],
            "expected_szz": {"commit_level": {"evaluation_policy": "exact_set", "required": ["c0"]}}}


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "SZZG-9900" / "scenario.graph.yml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _errors(result: ValidationResult) -> list[tuple[str, str, str]]:
    return [(f.code, f.location, f.message) for f in result.findings if f.severity == "ERROR"]


GENERATOR = {"type": "commit_generator", "generator": "noise", "count": 2, "path": "generated"}

#: name: (scenario, the errors of validate-graph --simulate as (code, location, message part),
#:        the error generate-graph stops with, or None)
SHAPES = {
    "generator-then-edit": (
        _scenario(_commit("c0", [], _write_file("a.txt", "a\n")), _commit("c1", ["c0"], GENERATOR),
                  _commit("c2", ["c1"], _replace("generated/noise-01.txt", "noise change 1", "edited"))),
        [], None),
    "generator-count-0": (
        _scenario(_commit("c0", [], _write_file("a.txt", "a\n")), _commit("c1", ["c0"], dict(GENERATOR, count=0)),
                  _commit("c2", ["c1"], _replace("a.txt", "a", "b"))),
        [("GE202", "commits[1]", "Commit 'c1' would be empty")], "commit would be empty"),
    "chmod-only": (
        _scenario(_commit("c0", [], _write_file("run.sh", "#!/bin/sh\necho hi\n")),
                  _commit("c1", ["c0"], _chmod("run.sh", "755")),
                  _commit("c2", ["c1"], _replace("run.sh", "hi", "bye"))),
        [], None),
    "move-entity-overwrite": (
        _scenario(_commit("c0", [], _write_file("A.java", "class A {}\n"), _write_file("B.java", "class B {}\n")),
                  _commit("c1", ["c0"], {"type": "move_entity", "entity": {"name": "A"}, "from_file": "A.java",
                                         "to_file": "B.java", "overwrite": False})),
        [("GE201", "commits[1].operations[0]", "move_entity target file already exists: B.java")],
        "move_entity target file already exists: B.java"),
    "file-over-directory": (
        _scenario(_commit("c0", [], _write_file("lib/a.txt", "a\n")), _commit("c1", ["c0"], _write_file("lib", "now a file\n"))),
        [("GE201", "commits[1].operations[0]", "write_file target is a directory: lib")],
        "write_file 'lib': Is a directory: lib"),
    "case-only-rename": (
        _scenario(_commit("c0", [], _write_file("a.txt", "a\n")),
                  _commit("c1", ["c0"], {"type": "rename_file", "from": "a.txt", "to": "A.txt"})),
        [("GE060", "commits[1].operations[0].to", "rename_file from 'a.txt' to 'A.txt' changes only the letter case")],
        "Graph scenario validation failed"),
    # four more of the same kind
    "file-below-a-file": (
        _scenario(_commit("c0", [], _write_file("lib", "a file\n")), _commit("c1", ["c0"], _write_file("lib/a.txt", "a\n"))),
        [("GE201", "commits[1].operations[0]", "write_file target lies below the file lib: lib/a.txt")],
        "write_file 'lib/a.txt': File exists: lib"),
    "generator-below-a-file": (
        _scenario(_commit("c0", [], _write_file("generated", "a file\n")), _commit("c1", ["c0"], GENERATOR),
                  _commit("c2", ["c1"], _write_file("a.txt", "a\n"))),
        [("GE201", "commits[1].operations[0]", "commit_generator target lies below the file generated")],
        "commit_generator of commit 'c1' cannot write 'generated/noise-01.txt': generated is a file"),
    "copy-onto-a-directory": (
        _scenario(_commit("c0", [], _write_file("a.txt", "a\n"), _write_file("lib/b.txt", "b\n")),
                  _commit("c1", ["c0"], {"type": "copy_file", "from": "a.txt", "to": "lib", "overwrite": True})),
        [("GE201", "commits[1].operations[0]", "copy_file target is a directory: lib")],
        "copy target is a directory: lib"),
    "chmod-that-keeps-the-mode": (
        _scenario(_commit("c0", [], _write_file("run.sh", "#!/bin/sh\n")), _commit("c1", ["c0"], _chmod("run.sh", "644")),
                  _commit("c2", ["c1"], _write_file("a.txt", "a\n"))),
        [("GE202", "commits[1]", "Commit 'c1' would be empty")], "commit would be empty"),
}


@pytest.mark.parametrize("name", SHAPES)
def test_simulation_and_generation_give_one_verdict(tmp_path, name):
    data, simulated, generation_error = SHAPES[name]
    scenario = _write(tmp_path, data)
    _, result = validate_graph_scenario_file(scenario, simulate=True, strict_paths=True)
    errors = _errors(result)
    assert [(code, location) for code, location, _ in errors] == [(code, location) for code, location, _ in simulated], errors
    for (_, _, message), (_, _, part) in zip(errors, simulated):
        assert part in message
    if generation_error is None:
        generate_graph_repository(scenario, tmp_path / "out", force=True)
    else:
        with pytest.raises(GraphGenerationError) as raised:
            generate_graph_repository(scenario, tmp_path / "out", force=True)
        assert generation_error in str(raised.value)


def test_a_chmod_only_commit_records_the_mode_change(tmp_path):
    data = SHAPES["chmod-only"][0]
    commit_map, _ = generate_graph_repository(_write(tmp_path, data), tmp_path / "out", force=True)
    assert git_stdout(tmp_path / "out/repo", "ls-tree", commit_map["c1"]["hash"], "run.sh").split()[0] == "100755"
    assert graph_simulator.simulated_snapshots(data)["c1"]["run.sh"].mode == "100755"


def test_szzg_0111_passes_the_simulation_without_its_allow_empty(tmp_path):
    """Its chmod-only c2 keeps allow_empty for file systems without an executable bit only."""
    data = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0111/scenario.graph.yml").read_text(encoding="utf-8"))
    [c2] = [commit for commit in data["commits"] if commit["id"] == "c2"]
    assert c2.pop("allow_empty") is True and [op["type"] for op in c2["operations"]] == ["chmod"]
    _, result = validate_graph_scenario_file(_write(tmp_path, data), simulate=True, strict_paths=True)
    assert _errors(result) == []


@pytest.mark.parametrize("op", ["rename_file", "move_file", "copy_file", "move_entity", "copy_entity"])
def test_a_case_only_rename_is_ge060(op):
    source, target = ("from_file", "to_file") if op.endswith("entity") else ("from", "to")
    operation = {"type": op, source: "src/Range.java", target: "src/range.java"}
    if op.endswith("entity"):
        operation["entity"] = {"name": "Range"}
    data = _scenario(_commit("c0", [], _write_file("src/Range.java", "class Range {}\n")), _commit("c1", ["c0"], operation))
    assert [(f.code, f.location) for f in validate_graph_static(data).findings if f.severity == "ERROR"] == \
        [("GE060", f"commits[1].operations[0].{target}")]


@pytest.mark.parametrize("target", ["src/Range.java", "src/Other.java", "SRC/Other.java"])
def test_a_rename_that_changes_more_than_the_case_is_not_ge060(target):
    data = _scenario(_commit("c0", [], _write_file("src/Range.java", "class Range {}\n")),
                     _commit("c1", ["c0"], {"type": "rename_file", "from": "src/Range.java", "to": target}))
    assert "GE060" not in {f.code for f in validate_graph_static(data).findings}


@pytest.mark.parametrize("op, message", [
    (_write_file("lib", "x\n"), "write_file 'lib': Is a directory: lib"),
    (_write_file("a.txt/b.txt", "x\n"), "write_file 'a.txt/b.txt': File exists: a.txt"),
    ({"type": "delete_file", "path": "lib"}, "delete_file 'lib': "),
], ids=["onto-a-directory", "below-a-file", "delete-a-directory"])
def test_an_os_error_names_the_operation_and_the_path(tmp_path, op, message):
    apply_graph_operation_to_filesystem(tmp_path, _write_file("lib/a.txt", "a\n"))
    apply_graph_operation_to_filesystem(tmp_path, _write_file("a.txt", "a\n"))
    with pytest.raises(OperationError) as raised:
        apply_graph_operation_to_filesystem(tmp_path, op)
    assert str(raised.value).startswith(message)
    assert str(tmp_path) not in str(raised.value)


# --- simulated snapshots against generated trees ------------------------------------------

def _tree(repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    """``path: (mode, blob id)`` of every file of ``commit``."""
    entries = {}
    for record in git_stdout(repo, "ls-tree", "-r", "-z", commit).split("\0"):
        if record:
            meta, path = record.split("\t", 1)
            mode, _, blob = meta.split()
            entries[path] = (mode, blob)
    return entries


def _blob_id(content: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()


def _simulated_bytes(file: graph_simulator.SimFile) -> bytes:
    return file.content.encode("utf-8") if isinstance(file.content, str) else file.content


def _given_snapshot(repo: Path, tree: dict[str, tuple[str, str]]) -> dict[str, graph_simulator.SimFile]:
    """A generated tree in the simulator's terms: LF text, or bytes when it is not UTF-8."""
    blobs = sorted({blob for _, blob in tree.values()})
    stream = run_git_with_input(repo, ["cat-file", "--batch"], "".join(f"{b}\n" for b in blobs).encode()).stdout
    contents, position = {}, 0
    for blob in blobs:
        header_end = stream.index(b"\n", position)
        size = int(stream[position:header_end].split()[2])
        contents[blob] = stream[header_end + 1:header_end + 1 + size]
        position = header_end + 1 + size + 1
    snapshot = {}
    for path, (mode, blob) in tree.items():
        try:
            content: str | bytes = normalize_newlines(contents[blob].decode("utf-8"))
        except UnicodeDecodeError:
            content = contents[blob]
        snapshot[path] = graph_simulator.SimFile(content, "100755" if mode == "100755" else None)
    return snapshot


def _documented_difference(data: dict, path: str, generated: bytes, simulated: bytes) -> bool:
    """The two differences docs/generator-options.md §2 states: the simulator works on LF text,
    and it leaves out ``write_generated_text_file``'s ``header`` and ``footer``."""
    if generated.replace(b"\r\n", b"\n") == simulated:
        return True
    for commit in data["commits"]:
        for op in commit.get("operations") or []:
            if op.get("type") == "write_generated_text_file" and op.get("path") == path:
                header, footer = _block_text(op.get("header")).encode(), _block_text(op.get("footer")).encode()
                if (header or footer) and generated.startswith(header) and generated.endswith(footer) \
                        and generated[len(header):len(generated) - len(footer)] == simulated:
                    return True
    return False


def _drift(data: dict, repo: Path, commit_map: dict[str, dict]) -> list[str]:
    """Where a simulated snapshot differs from the generated tree of its commit.

    The commits Git computes (merges, reverts, cherry-picks, patches, resolutions)
    are not modelled in memory: their generated trees are given to the simulator,
    which models every other commit from them.
    """
    ids = [commit["id"] for commit in data["commits"]]
    trees = {cid: _tree(repo, commit_map[cid]["hash"]) for cid in ids}
    computed = {feature.split(": ", 1)[0] for feature in git_performed_features(data)}
    result = ValidationResult()
    snapshots = graph_simulator.simulated_snapshots(data, result, given={cid: _given_snapshot(repo, trees[cid]) for cid in computed})
    drift = [f"{code} at {location}: {message}" for code, location, message in _errors(result)]
    for cid in ids:
        if cid in computed:
            continue
        simulated = snapshots[cid]
        for path in sorted(set(trees[cid]) | set(simulated)):
            if path not in simulated or path not in trees[cid]:
                drift.append(f"{cid}: {path} only {'generated' if path in trees[cid] else 'simulated'}")
                continue
            mode, blob = trees[cid][path]
            content = _simulated_bytes(simulated[path])
            if mode != (simulated[path].mode or "100644"):
                drift.append(f"{cid}: {path} is {mode} in Git, {simulated[path].mode or '100644'} simulated")
            if blob != _blob_id(content) and not _documented_difference(data, path, git_bytes(repo, "cat-file", "blob", blob), content):
                drift.append(f"{cid}: {path} differs")
    return drift


def test_every_file_operation_is_simulated_as_generated(tmp_path):
    """One scenario that uses every file operation, and the shapes around modes and generated files."""
    data = _scenario(
        _commit("c0", [], _write_file("a.txt", "a\n"), _write_file("run.sh", "#!/bin/sh\necho hi\n"),
                _write_file("src/A.java", "class A {}\n"), _write_file("src/B.java", "class B {}\n"),
                _write_file("fmt.txt", "x  \ny\n"), _write_file("readme.txt", "r\n"),
                {"type": "write_binary_file", "path": "bin/logo.bin", "content_base64": "/wD/AA=="},
                {"type": "write_generated_text_file", "path": "gen/data.txt", "lines": 3, "template": "row {line}"}),
        _commit("c1", ["c0"], _chmod("run.sh", "755")),
        _commit("c2", ["c1"], _write_file("run.sh", "#!/bin/sh\necho bye\n"),             # keeps 100755
                {"type": "copy_file", "from": "run.sh", "to": "tools/run-copy.sh"}),         # so does the copy
        _commit("c3", ["c2"], {"type": "rename_file", "from": "tools/run-copy.sh", "to": "tools/run2.sh"},
                _chmod("tools/run2.sh", "644")),
        _commit("c4", ["c3"], dict(GENERATOR, count=3, files=2, path="generated/old-placeholder.txt"),
                {"type": "commit_generator", "generator": "other", "count": 2, "path": "notes.txt"},   # the root
                _replace("a.txt", "a", "b")),
        _commit("c5", ["c4"], _replace("generated/noise-01.txt", "noise change 1", "edited")),
        _commit("c6", ["c5"], _chmod("generated/noise-01.txt", "0755")),
        _commit("c7", ["c6"], dict(GENERATOR, count=2001, path="generated")),      # capped at 2000; 50 lines; 100644
        _commit("c8", ["c7"], {"type": "move_entity", "entity": {"name": "A"}, "from_file": "src/A.java",
                               "to_file": "src/B.java", "append": True, "remove_source_file": True},
                _chmod("src/B.java", "4755")),
        _commit("c9", ["c8"], {"type": "copy_entity", "entity": {"name": "B"}, "from_file": "src/B.java",
                               "to_file": "src/C.java"},
                {"type": "format_file", "path": "fmt.txt"},
                {"type": "insert_after", "path": "a.txt", "anchor": "b\n", "content": "c\n"}),
        _commit("c10", ["c9"], _write_file("src/D.java", "class D {}\n"), _chmod("src/D.java", "700"),
                {"type": "delete_file", "path": "run.sh"}),
        _commit("c11", ["c10"], {"type": "copy_entity", "entity": {"name": "C"}, "from_file": "src/C.java",
                                 "to_file": "src/D.java"},                           # keeps D's 100755
                _write_file("run.sh", "new\n"),                                      # a new file: 100644
                {"type": "move_file", "from": "gen/data.txt", "to": "gen/moved/data.txt"}),
    )
    commit_map, _ = generate_graph_repository(_write(tmp_path, data), tmp_path / "out", force=True, verify=False)
    assert len(commit_map) == 12 + 5 + 2000
    assert _drift(data, tmp_path / "out/repo", commit_map) == []
    modes = {path: mode for path, (mode, _) in _tree(tmp_path / "out/repo", commit_map["c11"]["hash"]).items()}
    assert {path for path, mode in modes.items() if mode == "100755"} == {"src/B.java", "src/D.java"}


@pytest.mark.parametrize("path", GRAPH_SCENARIOS, ids=lambda p: p.parent.name)
def test_the_simulation_of_a_shipped_scenario_is_its_generated_history(tmp_path, path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    commit_map, _ = generate_graph_repository(path, tmp_path / "out", force=True, verify=False)
    assert _drift(data, tmp_path / "out/repo", commit_map) == []
