"""Helpers shared by the test modules (issue #107).

They were copied from file to file: fourteen ``_git()`` helpers, six fixtures
that generate a family of shipped scenarios, and the helpers that export a
commit's tree, attribute blamed lines and run a Java driver.  Every copy ran
Git with the developer's own configuration; the helpers here run it the way
SZZBench does, isolated from it (``szzbench.gitutils``, issue #96).
``tests/test_suite_conventions.py`` checks that no test runs Git otherwise.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from szzbench.generator import generate_repository
from szzbench.gitutils import _git_env, run_git, run_git_with_input
from szzbench.graph_generator import generate_graph_repository

ROOT = Path(__file__).resolve().parents[1]

needs_jdk = pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")


# --- Git ------------------------------------------------------------------------------------

def git(repo: Path, *args: str) -> str:
    """Git's output in ``repo``, stripped."""
    return git_stdout(repo, *args).strip()


def git_stdout(repo: Path, *args: str) -> str:
    """Git's output in ``repo``, as Git wrote it."""
    return run_git(Path(repo), list(args)).stdout


def git_bytes(repo: Path, *args: str) -> bytes:
    """Git's output in ``repo`` as bytes, for archives and blobs."""
    return run_git_with_input(Path(repo), list(args), b"").stdout


def git_env() -> dict[str, str]:
    """The environment SZZBench runs Git in, for a test that needs the exit status itself."""
    return _git_env()


def export_tree(repo: Path, commit: str, into: Path) -> Path:
    """Write the tree of ``commit`` into ``into`` (``git archive`` piped into ``tar -x``)."""
    into.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tar", "-x", "-C", str(into)], input=git_bytes(repo, "archive", commit), check=True)
    return into


# --- generated scenarios --------------------------------------------------------------------

def scenario_file(sid: str) -> Path:
    if sid.startswith("SZZG-"):
        return ROOT / "advanced-scenarios" / sid / "scenario.graph.yml"
    return ROOT / "scenarios" / sid / "scenario.yml"


class GeneratedScenarios:
    """Shipped scenarios generated at most once each: ``generated(sid)`` is ``(sid, hashes, repo)``.

    A test module holds one in a module-scoped fixture.  A family-wide test
    takes the scenarios through a parametrized fixture; a test about one
    scenario asks for that scenario, instead of running for the whole family
    and skipping the others.
    """

    def __init__(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        self._tmp = tmp_path_factory
        self._cache: dict[str, tuple[dict[str, dict], Path]] = {}

    def __call__(self, sid: str) -> tuple[str, dict[str, str], Path]:
        commit_map, repo = self._generated(sid)
        return sid, {cid: entry["hash"] for cid, entry in commit_map.items()}, repo

    def commit_map(self, sid: str) -> dict[str, dict]:
        """The generator's commit map, for a test that evaluates predictions against it."""
        return self._generated(sid)[0]

    def _generated(self, sid: str) -> tuple[dict[str, dict], Path]:
        if sid not in self._cache:
            out = self._tmp.mktemp(sid.lower()) / sid
            generate = generate_graph_repository if sid.startswith("SZZG-") else generate_repository
            commit_map, verify = generate(scenario_file(sid), out, force=True)
            assert verify is not None and not verify.has_errors(), verify.to_dict()
            self._cache[sid] = (commit_map, out / "repo")
        return self._cache[sid]


# --- blame and Java -------------------------------------------------------------------------

def logical_id(hashes: dict[str, str], full: str) -> str:
    """The logical commit a hash Git printed belongs to (a root commit is printed as ``^`` plus 39 characters)."""
    bare = full.lstrip("^")
    return next(cid for cid, h in hashes.items() if h.startswith(bare[:40]) or bare.startswith(h[:40]))


def last_commit(hashes: dict[str, str]) -> str:
    """The logical commit with the highest number: the bug-fixing commit of a linear scenario."""
    return max(hashes, key=lambda cid: int(cid[1:]))


def blame_owners(repo: Path, hashes: dict[str, str], bfc: str | None = None) -> dict[str, tuple[str, str, str]]:
    """For every line the fix deletes: who plain blame, ``-w`` and ``-w -C -C`` say wrote it.

    The fix is ``bfc``, or the scenario's last commit.
    """
    head = hashes[bfc if bfc is not None else last_commit(hashes)]
    seen: dict[str, tuple[str, str, str]] = {}
    for path in git(repo, "diff", "--name-only", f"{head}^", head).split():
        line_no = None
        for line in git(repo, "diff", "-U0", f"{head}^", head, "--", path).splitlines():
            if line.startswith("@@"):
                line_no = int(re.match(r"@@ -(\d+)", line).group(1))
            elif line.startswith("-") and not line.startswith("---") and line_no is not None:
                seen[line[1:].strip()] = tuple(
                    logical_id(hashes, git(repo, "blame", "-l", *flags, "-L", f"{line_no},{line_no}", f"{head}^",
                                      "--", path).split()[0])
                    for flags in ((), ("-w",), ("-w", "-C", "-C")))
                line_no += 1
            elif line.startswith(" ") and line_no is not None:
                line_no += 1
    return seen


def run_driver(work: Path, source: str) -> str:
    """Compile every Java file under ``work`` with ``source`` as ``Drive.java``, run ``Drive``, return its output."""
    (work / "Drive.java").write_text(source)
    sources = [str(p) for p in work.rglob("*.java")]
    subprocess.run(["javac", "-nowarn", "-d", str(work / "out"), *sources], check=True, capture_output=True)
    return subprocess.run(["java", "-cp", str(work / "out"), "Drive"], cwd=work, capture_output=True, text=True,
                          check=True).stdout.strip()
