"""The token-bszz image's tokenize-repos.sh stops at a step that fails (issue #194).

It ran with `set -u` alone and took the BFG jar from `ls ... | head -n 1`, so an image without
the jar ran java with an empty jar path for every repository, and the loop went on past any other
step that failed. The rewrite of one repository is still allowed to fail: its status goes to that
repository's tokenize.status, which the adapter reports as the scenario's tool error.

The script runs here under bash, without Docker: IN_ROOT, OUT_ROOT and BFG_CHECKOUT stand in for
the image's /in, /out and /opt/bfg-repo-cleaner, and BFG (java), timeout, git and, in one test,
cp are stand-ins on PATH that record how they were called.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/adapters/token-bszz/tokenize-repos.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

#: the stand-ins; each appends its command line to $CALLS
STAND_INS = {
    # BFG: fails for a repository whose path contains $FAIL_BFG_FOR, and otherwise says it ran
    "java": 'echo "java $*" >> "$CALLS"\n'
            'for last; do :; done\n'
            'case "$last" in *"${FAIL_BFG_FOR:-no repository}"*) echo "BFG stopped"; exit 1;; esac\n'
            'echo "BFG run is complete"\n',
    "timeout": 'echo "timeout $1" >> "$CALLS"\nshift\nexec "$@"\n',
    "git": 'echo "git $* in $PWD" >> "$CALLS"\n',
}
JAR = "bfg-1.12.16-SNAPSHOT.jar"
FAILING_CP = 'echo "cp $*" >> "$CALLS"\necho "cp: no space left on device" >&2\nexit 1\n'


def _setup(tmp_path: Path, jars: tuple[str, ...] = (JAR,),
           scenarios: tuple[str, ...] = ("SZZ-0001",), stand_ins: dict[str, str] | None = None) -> dict[str, str]:
    """Generated repositories, a BFG checkout with ``jars``, and the environment to run the script in."""
    for scenario in scenarios:
        repo = tmp_path / "in" / scenario / "default/repo"
        repo.mkdir(parents=True)
        (repo / "A.java").write_text("class A {}\n", encoding="utf-8")
    target = tmp_path / "bfg/bfg/target"
    target.mkdir(parents=True)
    for jar in jars:
        (target / jar).write_bytes(b"")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in {**STAND_INS, **(stand_ins or {})}.items():
        (bin_dir / name).write_text("#!/bin/sh\n" + body, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    # only what the script reads, so a VARIANT or BFG_TIMEOUT of the caller's does not reach it
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "IN_ROOT": str(tmp_path / "in"),
            "OUT_ROOT": str(tmp_path / "out"), "BFG_CHECKOUT": str(tmp_path / "bfg"),
            "CALLS": str(tmp_path / "calls.log")}


def _run(environment: dict[str, str], cwd: Path | None = None, **extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT)], cwd=cwd, env={**environment, **extra}, capture_output=True,
                          text=True)


def _calls(tmp_path: Path) -> list[str]:
    calls = tmp_path / "calls.log"
    return calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []


def test_a_repository_is_rewritten_into_its_copy_with_its_log_and_status_0(tmp_path):
    completed = _run(_setup(tmp_path))
    assert completed.returncode == 0, completed.stderr
    out = tmp_path / "out/SZZ-0001/default"
    assert (out / "repo/A.java").read_text(encoding="utf-8") == "class A {}\n"
    assert (out / "tokenize.log").read_text(encoding="utf-8") == "BFG run is complete\n"
    assert (out / "tokenize.status").read_text(encoding="utf-8") == "0\n"
    assert (tmp_path / "out/.memo-window-1").is_dir()
    jar = tmp_path / "bfg/bfg/target" / JAR
    assert _calls(tmp_path) == [
        "timeout 600",
        f"java -XX:ActiveProcessorCount=1 -jar {jar} --blob-exec:/opt/cregit/tokenizeByBlobId/tokenBySha.pl=\\.java$ "
        f"--no-blob-protection {out / 'repo'}",
        f"git reset --quiet --hard HEAD in {out / 'repo'}",
    ]


@pytest.mark.parametrize("jars, extra, message", [
    ((), {}, "no BFG jar matches {target}/bfg-*.jar"),
    ((JAR, "bfg-1.12.17.jar"), {}, "2 BFG jars match {target}/bfg-*.jar, so it is not clear"),
    # BFG runs from its own checkout, where the relative path would name another directory
    ((JAR,), {"OUT_ROOT": "out"}, "OUT_ROOT must be an absolute path, not out"),
])
def test_a_setup_failure_stops_the_script_before_any_repository(tmp_path, jars, extra, message):
    completed = _run(_setup(tmp_path, jars=jars), cwd=tmp_path, **extra)
    assert completed.returncode != 0
    assert message.format(target=tmp_path / "bfg/bfg/target") in completed.stderr
    assert not (tmp_path / "out").exists()
    assert _calls(tmp_path) == []


def test_a_failed_rewrite_is_recorded_in_its_status_and_the_others_go_on(tmp_path):
    completed = _run(_setup(tmp_path, scenarios=("SZZ-0001", "SZZ-0002")), FAIL_BFG_FOR="SZZ-0001")
    assert completed.returncode == 0, completed.stderr
    first, second = tmp_path / "out/SZZ-0001/default", tmp_path / "out/SZZ-0002/default"
    assert (first / "tokenize.status").read_text(encoding="utf-8") == "1\n"
    assert (first / "tokenize.log").read_text(encoding="utf-8") == "BFG stopped\n"
    assert (second / "tokenize.status").read_text(encoding="utf-8") == "0\n"


def test_any_other_failed_step_stops_the_script(tmp_path):
    completed = _run(_setup(tmp_path, scenarios=("SZZ-0001", "SZZ-0002"), stand_ins={"cp": FAILING_CP}))
    assert completed.returncode != 0
    assert "cp: no space left on device" in completed.stderr
    # the first copy failed, and nothing ran after it: no BFG, no status, no second repository
    assert [call.split()[0] for call in _calls(tmp_path)] == ["cp"]
    assert not (tmp_path / "out/SZZ-0001/default/tokenize.status").exists()
    assert not (tmp_path / "out/SZZ-0002").exists()
