"""The token-level B-SZZ adapter names its answers by the original repository's commits.

B-SZZ runs on a token-level copy of each generated repository, which BFG rewrote, so the commits
it answers are the copy's. The adapter maps each back through the `Former-commit-id` footer BFG
adds to a rewritten commit, as cregit's remapCommits does. A commit BFG left alone keeps its hash.
A scenario whose tokenization failed, or whose answer names a commit the copy does not have, is a
tool error, not an answer (issue #95). Docker is not needed for any of this.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from support import git

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def adapter(monkeypatch):
    spec = importlib.util.spec_from_file_location("token_bszz_adapter",
                                                  ROOT / "tools/adapters/token_bszz_to_predictions.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def _commit(repo: Path, message: str) -> str:
    git(repo, "-c", "user.name=Token", "-c", "user.email=token@example.com", "commit", "-q", "-a", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def test_a_rewritten_commit_maps_back_through_its_footer_and_an_untouched_one_to_itself(adapter, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "README.md").write_text("no Java here\n", encoding="utf-8")
    git(repo, "add", "README.md")
    untouched = _commit(repo, "Describe the project")
    (repo / "README.md").write_text("still no Java\n", encoding="utf-8")
    rewritten = _commit(repo, "Reword the description\n\nFormer-commit-id: " + "a" * 40)
    environment = adapter.isolated_environment(dict(os.environ), str(tmp_path / "home"))
    assert adapter.former_commit_map(repo, environment) == {untouched: untouched, rewritten: "a" * 40}


def test_token_level_answers_are_named_by_the_original_commits(adapter, tmp_path):
    token_fix, token_bic = "1" * 40, "2" * 40
    original_fix, original_bic = "3" * 40, "4" * 40
    predictions = tmp_path / "b-szz-predictions.jsonl"
    predictions.write_text("\n".join(json.dumps(record) for record in [
        {"scenario_id": "SZZ-0006", "repository_id": "r6", "predictions": [{
            "fix_commit": token_fix, "fix_commit_id": "c2", "inducing_commit": token_bic, "inducing_commit_id": "c1",
            "tool": "b-szz", "file": "A.java", "line": 7, "line_content": "<=", "input_line": [7], "scenario_id": "SZZ-0006",
            "raw_file": "/tmp/raw/SZZ-0006.json"}]},
        {"scenario_id": "SZZ-0007", "predictions": [{"fix_commit": token_fix, "inducing_commit": "5" * 40}]},
    ]) + "\n", encoding="utf-8")
    mappings = {"SZZ-0006": {token_fix: original_fix, token_bic: original_bic}, "SZZ-0007": {token_fix: original_fix}}
    records = adapter.map_back(predictions, mappings, {"SZZ-0008": "tokenization failed (status 1)"})

    # the original hashes, the logical ids B-SZZ found, and none of the token-level file's positions
    assert records[0] == {"scenario_id": "SZZ-0006", "repository_id": "r6", "predictions": [{
        "fix_commit": original_fix, "fix_commit_id": "c2", "inducing_commit": original_bic,
        "inducing_commit_id": "c1", "tool": "token-b-szz", "file": "A.java"}]}
    # an answer the token-level repository cannot account for is not scored as a commit
    assert records[1]["status"] == "error"
    assert records[1]["errors"] == [f"inducing_commit {'5' * 10} is not a commit of the token-level repository"]
    # a scenario B-SZZ never ran on, because tokenization failed, still gets its record
    assert records[2] == {"scenario_id": "SZZ-0008", "status": "error",
                          "errors": ["tokenization failed (status 1)"], "predictions": []}


def _generated_output(tmp_path: Path) -> tuple[Path, str]:
    """A generated output of one commit, as the token-level side receives it."""
    original = tmp_path / "generated/SZZ-0006/default"
    (original / "repo").mkdir(parents=True)
    (original / "metadata").mkdir()
    git(original / "repo", "init", "-q")
    (original / "repo/A.java").write_text("class A {}\n", encoding="utf-8")
    git(original / "repo", "add", "A.java")
    return original, _commit(original / "repo", "Add A")


def _token_output(tmp_path: Path, original: Path) -> Path:
    """A token-level copy in which BFG changed nothing, so every commit keeps its hash."""
    token = tmp_path / "token/SZZ-0006/default"
    token.mkdir(parents=True)
    shutil.copytree(original / "repo", token / "repo")
    (token / "tokenize.status").write_text("0\n", encoding="utf-8")
    return token


def test_a_commit_no_ref_reaches_has_no_token_level_counterpart_and_is_left_out(adapter, tmp_path):
    """BFG rewrites what the refs reach: a deleted branch's commit (SZZG-0072, SZZG-0122) is not in the copy."""
    original, c0 = _generated_output(tmp_path)
    unreachable = "9" * 40
    (original / "metadata/commit-map.json").write_text(json.dumps(
        {"c0": {"hash": c0, "role": "bug_fixing"}, "f1": {"hash": unreachable, "role": "unrelated"}}), encoding="utf-8")
    token = _token_output(tmp_path, original)
    environment = adapter.isolated_environment(dict(os.environ), str(tmp_path / "home"))
    assert adapter.prepare_token_output(original, token, environment) == {c0: c0}
    rekeyed = json.loads((token / "metadata/commit-map.json").read_text(encoding="utf-8"))
    assert rekeyed == {"c0": {"hash": c0, "role": "bug_fixing"}}


def test_a_reachable_commit_without_a_token_level_counterpart_is_an_error(adapter, tmp_path):
    original, c0 = _generated_output(tmp_path)
    (original / "metadata/commit-map.json").write_text(json.dumps({"c0": {"hash": c0}}), encoding="utf-8")
    # a copy whose only commit was rewritten from some other commit, so nothing maps back to c0
    token = tmp_path / "token/SZZ-0006/default"
    (token / "repo").mkdir(parents=True)
    (token / "tokenize.status").write_text("0\n", encoding="utf-8")
    git(token / "repo", "init", "-q")
    (token / "repo/A.java").write_text("class|class\n", encoding="utf-8")
    git(token / "repo", "add", "A.java")
    _commit(token / "repo", "Add A\n\nFormer-commit-id: " + "8" * 40)
    environment = adapter.isolated_environment(dict(os.environ), str(tmp_path / "home"))
    with pytest.raises(ValueError, match="c0 .* has no token-level commit"):
        adapter.prepare_token_output(original, token, environment)


def test_a_generated_output_without_its_commit_map_is_a_tool_error_not_left_out(adapter, tmp_path):
    """The gap the PR #114 review found in the SZZ Unleashed adapter, closed here as well."""
    _generated_output(tmp_path)          # a repository, and a metadata directory without a commit map
    environment = adapter.isolated_environment(dict(os.environ), str(tmp_path / "home"))
    mappings, failures = adapter.prepare_token_outputs(tmp_path / "generated", tmp_path / "token", "default",
                                                       environment)
    assert mappings == {}
    assert failures["SZZ-0006"].endswith("commit-map.json is missing: the generated output is incomplete")


def test_a_failed_tokenization_gets_no_metadata(adapter, tmp_path):
    token = tmp_path / "token/SZZ-0006/default"
    (token / "repo").mkdir(parents=True)
    (token / "tokenize.status").write_text("1\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"tokenization failed \(status 1"):
        adapter.prepare_token_output(tmp_path / "generated/SZZ-0006/default", token, {})
    assert not (token / "metadata").exists()


def test_a_scenario_that_could_not_be_prepared_gets_its_failure_not_b_szz_record(adapter, tmp_path):
    """B-SZZ can still answer for such a scenario's copy, from an earlier run's metadata, or with the
    error of a copy without a commit map. The failure the preparation met names the cause."""
    predictions = tmp_path / "b-szz-predictions.jsonl"
    predictions.write_text("\n".join(json.dumps(record) for record in [
        {"scenario_id": "SZZ-0006", "predictions": [{"fix_commit": "1" * 40, "inducing_commit": "2" * 40}]},
        {"scenario_id": "SZZ-0007", "status": "error", "predictions": [],
         "errors": ["token/SZZ-0007/default/metadata/commit-map.json is missing: the generated output is incomplete"]},
    ]) + "\n", encoding="utf-8")
    failures = {"SZZ-0006": "tokenization failed (status 1; see token/SZZ-0006/default/tokenize.log)",
                "SZZ-0007": f"ValueError: c0 ({'3' * 10}) has no token-level commit"}
    assert adapter.map_back(predictions, {}, failures) == [
        {"scenario_id": scenario_id, "status": "error", "errors": [failure], "predictions": []}
        for scenario_id, failure in failures.items()]


def _prepared_scenario(tmp_path: Path) -> None:
    original, c0 = _generated_output(tmp_path)
    (original / "metadata/commit-map.json").write_text(json.dumps({"c0": {"hash": c0}}), encoding="utf-8")
    _token_output(tmp_path, original)


def _write_b_szz_records(output_root: Path, records: list[dict]) -> None:
    """Records where the PySZZ adapter writes B-SZZ's, under its --output-root."""
    (output_root / "b-szz").mkdir(parents=True, exist_ok=True)
    (output_root / "b-szz/b-szz-predictions.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def _run_main(adapter, tmp_path: Path, monkeypatch, b_szz) -> int:
    """main() with the tokenization skipped, and `b_szz` in place of the PySZZ adapter: it gets the
    adapter's --output-root, and returns the adapter's exit status."""
    run = subprocess.run

    def fake_run(command, *args, **kwargs):
        if command[0] != "pyszz-python":
            return run(command, *args, **kwargs)
        completed = subprocess.CompletedProcess(command, b_szz(Path(command[command.index("--output-root") + 1])))
        if kwargs.get("check"):
            completed.check_returncode()
        return completed

    monkeypatch.setattr(adapter.subprocess, "run", fake_run)
    return adapter.main(["--generated-root", str(tmp_path / "generated"), "--token-root", str(tmp_path / "token"),
                         "--cregit-root", str(tmp_path / "cregit"), "--pyszz-root", str(tmp_path / "pyszz"),
                         "--pyszz-python", "pyszz-python", "--docker", str(tmp_path / "no-docker"),
                         "--skip-tokenize", "--out", str(tmp_path / "out/predictions.jsonl")])


def test_records_with_tool_errors_are_mapped_back_although_the_pyszz_adapter_exits_1(adapter, tmp_path, monkeypatch):
    """The PySZZ adapter exits 1 when a record carries a tool error, and still writes every record."""
    _prepared_scenario(tmp_path)

    def b_szz(output_root: Path) -> int:
        _write_b_szz_records(output_root, [{"scenario_id": "SZZ-0006", "status": "error",
                                            "errors": ["No bug fixing commits found."], "predictions": []}])
        return 1

    assert _run_main(adapter, tmp_path, monkeypatch, b_szz) == 1
    lines = (tmp_path / "out/predictions.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line) for line in lines] == [
        {"scenario_id": "SZZ-0006", "predictions": [], "status": "error", "errors": ["No bug fixing commits found."]}]


@pytest.mark.parametrize("status", [1, 2])
def test_a_pyszz_run_that_writes_no_records_is_not_answered_by_an_earlier_runs(adapter, tmp_path, monkeypatch,
                                                                               capsys, status):
    """A crash exits 1 as well, but before B-SZZ starts it leaves the earlier run's records in place.
    The PySZZ adapter exits 2 when PySZZ cannot run at all."""
    _prepared_scenario(tmp_path)
    _write_b_szz_records(tmp_path / "out/pyszz", [{"scenario_id": "SZZ-0006", "predictions": []}])
    assert _run_main(adapter, tmp_path, monkeypatch, lambda output_root: status) == 2
    assert not (tmp_path / "out/predictions.jsonl").exists()
    assert f"exited with status {status} and wrote no records" in capsys.readouterr().err
