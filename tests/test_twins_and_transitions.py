"""Two things the structural checks do not establish (PR #55 review).

1. A twin pair must differ *only* in the history property it tests. The
   generator derives default authors and dates from ``meta.id``, so a twin that
   merely copies its pair's commit list gets different authors and timestamps,
   and a rule that reads nothing but metadata can tell the twins apart. The
   twins pin their metadata; these tests compare the generated objects.

2. A scenario that declares "commit X introduces this fault" must have the
   fault appear at X and not before. Blame ownership of a rewritten line does
   not show that; running the code does. SZZG-0124's first version failed this:
   the rejection it blamed on the adaptation was already there two commits
   earlier.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from szzbench.graph_generator import generate_graph_repository  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "advanced-scenarios"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


def _generate(tmp_path: Path, sid: str) -> tuple[dict, Path]:
    out = tmp_path / sid
    commit_map, verify = generate_graph_repository(GRAPH / sid / "scenario.graph.yml", out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    return commit_map, out / "repo"


# --- twins -------------------------------------------------------------------

def test_deleted_branch_twin_has_identical_commit_objects(tmp_path):
    """SZZG-0122 is SZZG-0057 with `feature` deleted: every commit object must be the same."""
    a, _ = _generate(tmp_path, "SZZG-0057")
    b, repo_b = _generate(tmp_path, "SZZG-0122")
    assert set(a) == set(b)
    for cid in a:
        assert a[cid]["hash"] == b[cid]["hash"], (cid, a[cid]["hash"], b[cid]["hash"])
    assert _git(repo_b, "for-each-ref", "--format=%(refname:short)").split() == ["main"]


def test_fast_forward_twin_shares_prefix_objects_and_the_fix_tree(tmp_path):
    """SZZG-0128 is SZZG-0043 integrated by fast-forward: c0..c2 identical objects, c4 same
    author/dates/message/tree, and only its parent differs (c2 instead of the merge c3)."""
    a, repo_a = _generate(tmp_path, "SZZG-0043")
    b, repo_b = _generate(tmp_path, "SZZG-0128")
    for cid in ("c0", "c1", "c2"):
        assert a[cid]["hash"] == b[cid]["hash"], cid
    fmt = "%an <%ae>|%aI|%cI|%s|%T"
    assert _git(repo_a, "log", "-1", f"--format={fmt}", a["c4"]["hash"]) == _git(repo_b, "log", "-1", f"--format={fmt}", b["c4"]["hash"])
    assert _git(repo_b, "rev-list", "--parents", "-n", "1", b["c4"]["hash"]).split()[1:] == [b["c2"]["hash"]]
    assert _git(repo_a, "rev-list", "--parents", "-n", "1", a["c4"]["hash"]).split()[1:] == [a["c3"]["hash"]]


# --- behavioural transitions ------------------------------------------------

DRIVER = """import example.UploadWindow;
public class Drive {
  public static void main(String[] a) {
    UploadWindow w = new UploadWindow();
    int[][] in = {{10,10,20},{15,10,20},{20,10,20},{9,10,20},{21,10,20},{15,10,0}};
    StringBuilder sb = new StringBuilder();
    for (int[] x : in) sb.append(w.accepts(x[0], x[1], x[2]) ? 'T' : 'F');
    System.out.print(sb);
  }
}
"""


def _behaviour(repo: Path, commit_hash: str, work: Path) -> str:
    work.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(["git", "archive", commit_hash], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
    (work / "Drive.java").write_text(DRIVER)
    subprocess.run(["javac", "-d", str(work / "out"), str(work / "src/main/java/example/UploadWindow.java"), str(work / "Drive.java")], check=True, capture_output=True)
    return subprocess.run(["java", "-cp", str(work / "out"), "Drive"], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")
@pytest.mark.parametrize("sid, expected", [
    # inputs: (10,10,20) (15,10,20) (20,10,20) (9,10,20) (21,10,20) (15,10,0)
    # SZZG-0124: the adaptation r1 introduces the fault; nothing before it rejects (15,10,20)
    ("SZZG-0124", {"c0": "TTTFFF", "rel1": "TTTFFF", "c1": "TTTFFT", "r1": "FFFFFF", "r2": "TTTFFT"}),
    # SZZG-0125: the source c1 introduces the fault; the adaptation r1 reproduces it faithfully
    ("SZZG-0125", {"c0": "TTTFFF", "rel1": "TTTFFF", "c1": "FTFFFF", "r1": "FTFFFF", "r2": "TTTFFF"}),
])
def test_cherry_pick_twins_fault_appears_where_declared(tmp_path, sid, expected):
    commit_map, repo = _generate(tmp_path, sid)
    observed = {cid: _behaviour(repo, commit_map[cid]["hash"], tmp_path / "w" / cid) for cid in expected}
    assert observed == expected
