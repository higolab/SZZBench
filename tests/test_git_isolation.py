"""Generation must not depend on the caller's Git configuration (issue #96).

Until 2026-09-29 every Git subprocess inherited the caller's environment and
read the system and global configuration, so a developer's own Git setup
decided what a scenario generated.  Some settings made valid scenarios fail
(an unavailable signing program, a global ignore of ``*.java``, a global
clean filter).  Others were worse because nothing failed: a default ignore of
``build/`` dropped the generated file that SZZG-0107 is about, a global
commit-msg hook rewrote every message, a working signing key changed every
hash, and ``GIT_DIR`` sent every commit into another repository -- each time
with 0 errors and 0 warnings from verification.

Each vector below is injected only through this test process's environment
and files under ``tmp_path``, so no test reads or writes a developer's real
Git configuration, signing keys or hooks.  Every generation must succeed,
verify, and produce exactly the commit hashes of an uninfluenced generation.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from szzbench import gitutils  # noqa: E402
from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402

pytestmark = pytest.mark.skipif(os.name == "nt", reason="the vectors are POSIX shell scripts")

SCENARIOS = {
    # the classic path (gitutils.commit_all)
    "SZZ-0006": ROOT / "scenarios/SZZ-0006/scenario.yml",
    # the graph path; the BFC also writes build/generated/retention-table.txt
    "SZZG-0107": ROOT / "advanced-scenarios/SZZG-0107/scenario.graph.yml",
    # the graph path through git cherry-pick, a conflict and its resolution
    "SZZG-0124": ROOT / "advanced-scenarios/SZZG-0124/scenario.graph.yml",
}


def _generate(scenario_id: str, out: Path) -> dict[str, str]:
    path = SCENARIOS[scenario_id]
    generate = generate_repository if path.name == "scenario.yml" else generate_graph_repository
    commit_map, verify = generate(path, out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    return {cid: entry["hash"] for cid, entry in commit_map.items()}


def _script(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _inject(monkeypatch, *pairs: tuple[str, str]) -> None:
    """Configuration through GIT_CONFIG_COUNT, which outranks even a repository's own config."""
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(pairs)))
    for index, (key, value) in enumerate(pairs):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{index}", key)
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{index}", value)


def _signing_program_that_fails(tmp_path, monkeypatch):
    _inject(monkeypatch, ("commit.gpgsign", "true"), ("gpg.program", str(_script(tmp_path / "gpg", "exit 1\n"))))


def _working_ssh_signing_key(tmp_path, monkeypatch):
    if shutil.which("ssh-keygen") is None:
        pytest.skip("needs ssh-keygen")
    key = tmp_path / "signing-key"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "throwaway", "-f", str(key)],
                   check=True, capture_output=True)
    _inject(monkeypatch, ("commit.gpgsign", "true"), ("gpg.format", "ssh"), ("user.signingkey", str(key)))


def _ignore_file_listing_java(tmp_path, monkeypatch):
    (tmp_path / "ignore").write_text("*.java\n", encoding="utf-8")
    _inject(monkeypatch, ("core.excludesFile", str(tmp_path / "ignore")))


def _default_xdg_ignore_of_build(tmp_path, monkeypatch):
    # read by Git without any configuration: core.excludesFile defaults to $XDG_CONFIG_HOME/git/ignore
    (tmp_path / "xdg/git").mkdir(parents=True)
    (tmp_path / "xdg/git/ignore").write_text("build/\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))


def _global_commit_msg_hook(tmp_path, monkeypatch):
    hook = _script(tmp_path / "hooks/commit-msg",
                   'printf "\\nChange-Id: I0000000000000000000000000000000000000000\\n" >> "$1"\n')
    (tmp_path / "home").mkdir()
    (tmp_path / "home/.gitconfig").write_text(f"[core]\n\thooksPath = {hook.parent}\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))


def _clean_filter_from_global_attributes(tmp_path, monkeypatch):
    (tmp_path / "attributes").write_text("*.java filter=upper\n", encoding="utf-8")
    (tmp_path / "gitconfig").write_text(
        f"[core]\n\tattributesFile = {tmp_path / 'attributes'}\n[filter \"upper\"]\n\tclean = tr a-z A-Z\n",
        encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))


def _init_template_with_a_hook(tmp_path, monkeypatch):
    _script(tmp_path / "template/hooks/commit-msg", 'echo "Signed-off-by: Template <t@example.com>" >> "$1"\n')
    monkeypatch.setenv("GIT_TEMPLATE_DIR", str(tmp_path / "template"))


def _repository_redirected(tmp_path, monkeypatch):
    other = tmp_path / "other"
    subprocess.run(["git", "init", "-q", str(other)], check=True, capture_output=True)
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))

    def untouched():
        found = subprocess.run(["git", "--git-dir", str(other / ".git"), "rev-list", "--all"],
                               capture_output=True, text=True, check=True).stdout
        assert found == "", "commits were written into the repository GIT_DIR pointed at"
    return untouched


def _identity_and_dates(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Mallory")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "mallory@example.com")
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2001-01-01T00:00:00Z")


VECTORS = {
    "signing-program-fails": _signing_program_that_fails,
    "working-ssh-signing-key": _working_ssh_signing_key,
    "ignore-file-lists-java": _ignore_file_listing_java,
    "default-xdg-ignore-of-build": _default_xdg_ignore_of_build,
    "global-commit-msg-hook": _global_commit_msg_hook,
    "clean-filter-from-global-attributes": _clean_filter_from_global_attributes,
    "init-template-with-a-hook": _init_template_with_a_hook,
    "repository-redirected": _repository_redirected,
    "identity-and-dates": _identity_and_dates,
}


@pytest.fixture(scope="module")
def reference(tmp_path_factory) -> dict[str, dict[str, str]]:
    """Hashes of an uninfluenced generation.  Its own environment is emptied of Git
    configuration explicitly, so the reference does not depend on the machine either."""
    empty = tmp_path_factory.mktemp("empty-home")
    with pytest.MonkeyPatch.context() as monkeypatch:
        for key in list(os.environ):
            if key.startswith("GIT_"):
                monkeypatch.delenv(key)
        monkeypatch.setenv("HOME", str(empty))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(empty))
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        out = tmp_path_factory.mktemp("reference")
        return {sid: _generate(sid, out / sid) for sid in SCENARIOS}


@pytest.mark.parametrize("scenario_id", SCENARIOS)
@pytest.mark.parametrize("vector", VECTORS)
def test_ambient_git_configuration_changes_nothing(vector, scenario_id, reference, tmp_path, monkeypatch):
    check = VECTORS[vector](tmp_path, monkeypatch)
    assert _generate(scenario_id, tmp_path / "out") == reference[scenario_id]
    if check is not None:
        check()


def test_the_generated_file_of_szzg_0107_is_committed_despite_a_build_ignore(tmp_path, monkeypatch):
    _default_xdg_ignore_of_build(tmp_path, monkeypatch)
    _generate("SZZG-0107", tmp_path / "out")
    tracked = gitutils.run_git(tmp_path / "out/repo", ["ls-files", "build"]).stdout.split()
    assert tracked == ["build/generated/retention-table.txt"]


def test_git_env_withholds_what_redirects_or_reconfigures_git(monkeypatch):
    injected = ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_CONFIG_COUNT",
                "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_GLOBAL",
                "GIT_CONFIG_SYSTEM", "GIT_TEMPLATE_DIR", "GIT_COMMITTER_NAME", "GIT_AUTHOR_DATE"]
    for key in injected:
        monkeypatch.setenv(key, "ambient")
    monkeypatch.setenv("HOME", "/ambient/home")
    monkeypatch.setenv("XDG_CONFIG_HOME", "/ambient/xdg")
    env = gitutils._git_env()
    assert [key for key in injected if key in env] == []
    assert env["GIT_CONFIG_NOSYSTEM"] == "1" and env["GIT_ATTR_NOSYSTEM"] == "1"
    assert env["HOME"] == env["XDG_CONFIG_HOME"] != "/ambient/home"
    assert list(Path(env["HOME"]).iterdir()) == []
    # what a caller sets on purpose still reaches Git
    assert gitutils._git_env({"GIT_COMMITTER_NAME": "SZZ Benchmark"})["GIT_COMMITTER_NAME"] == "SZZ Benchmark"


def test_every_repository_variable_git_lists_is_withheld():
    listed = subprocess.run(["git", "rev-parse", "--local-env-vars"], capture_output=True, text=True,
                            check=True).stdout.split()
    assert listed, "git rev-parse --local-env-vars printed nothing"
    assert sorted(set(listed) - gitutils.ISOLATED_GIT_ENV) == []
