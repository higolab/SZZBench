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

import subprocess
from pathlib import Path

import pytest

from support import export_tree, git, needs_jdk
from szzbench.graph_generator import generate_graph_repository

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "advanced-scenarios"


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
    assert git(repo_b, "for-each-ref", "--format=%(refname:short)").split() == ["main"]


def test_fast_forward_twin_shares_prefix_objects_and_the_fix_tree(tmp_path):
    """SZZG-0128 is SZZG-0043 integrated by fast-forward: c0..c2 identical objects, c4 same
    author/dates/message/tree, and only its parent differs (c2 instead of the merge c3)."""
    a, repo_a = _generate(tmp_path, "SZZG-0043")
    b, repo_b = _generate(tmp_path, "SZZG-0128")
    for cid in ("c0", "c1", "c2"):
        assert a[cid]["hash"] == b[cid]["hash"], cid
    fmt = "%an <%ae>|%aI|%cI|%s|%T"
    assert git(repo_a, "log", "-1", f"--format={fmt}", a["c4"]["hash"]) == git(repo_b, "log", "-1", f"--format={fmt}", b["c4"]["hash"])
    assert git(repo_b, "rev-list", "--parents", "-n", "1", b["c4"]["hash"]).split()[1:] == [b["c2"]["hash"]]
    assert git(repo_a, "rev-list", "--parents", "-n", "1", a["c4"]["hash"]).split()[1:] == [a["c3"]["hash"]]


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
    export_tree(repo, commit_hash, work)
    (work / "Drive.java").write_text(DRIVER)
    subprocess.run(["javac", "-d", str(work / "out"), str(work / "src/main/java/example/UploadWindow.java"), str(work / "Drive.java")], check=True, capture_output=True)
    return subprocess.run(["java", "-cp", str(work / "out"), "Drive"], capture_output=True, text=True, check=True).stdout


@needs_jdk
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


# --- non-source BICs: the code must really consume the artifact (issue #23) -----

def _run_java(repo: Path, commit_hash: str, work: Path, driver_name: str, driver_src: str, sources: list[str]) -> str:
    """Compile the snapshot's listed sources plus a driver, with src/main/resources on the classpath."""
    work.mkdir(parents=True, exist_ok=True)
    export_tree(repo, commit_hash, work)
    (work / f"{driver_name}.java").write_text(driver_src)
    subprocess.run(["javac", "-d", str(work / "out"), *[str(work / s) for s in sources], str(work / f"{driver_name}.java")], check=True, capture_output=True)
    cp = f"{work / 'out'}:{work / 'src' / 'main' / 'resources'}"
    return subprocess.run(["java", "-cp", cp, driver_name], capture_output=True, text=True, check=True).stdout.strip()


ARTIFACT_CASES = [
    # SZZG-0104: the trailing slash in app.properties reaches the URL the client builds
    ("SZZG-0104", "ApiDrive", "public class ApiDrive { public static void main(String[] a) { System.out.print(new example.ApiClient().apiUrl()); } }",
     ["src/main/java/example/Endpoint.java", "src/main/java/example/AppConfig.java", "src/main/java/example/ApiClient.java"],
     {"c0": "https://example.com/api", "c1": "https://example.com//api", "c2": "https://example.com/api"}),
    # SZZG-0133: the palette header decides whether the asset loads
    ("SZZG-0133", "PalDrive", "public class PalDrive { public static void main(String[] a) { example.Palette p = new example.Palette(); System.out.print(p.isValid() + \" \" + p.colours()); } }",
     ["src/main/java/example/Palette.java"],
     {"c0": "true 3", "c1": "false 0", "c2": "true 3"}),
    # SZZG-0134: the .gitattributes rule changes the bytes the reader sees
    ("SZZG-0134", "ModeDrive", "public class ModeDrive { public static void main(String[] a) { System.out.print(new example.ModeList().contains(\"strict\")); } }",
     ["src/main/java/example/ModeList.java"],
     {"c0": "true", "c1": "false", "c2": "true"}),
]


@needs_jdk
@pytest.mark.parametrize("sid, driver, src, sources, expected", ARTIFACT_CASES, ids=[c[0] for c in ARTIFACT_CASES])
def test_non_source_bic_reaches_the_code(tmp_path, sid, driver, src, sources, expected):
    commit_map, repo = _generate(tmp_path, sid)
    observed = {cid: _run_java(repo, commit_map[cid]["hash"], tmp_path / "w" / cid, driver, src, sources) for cid in expected}
    assert observed == expected


# --- report-date scenarios: the dates the READMEs reason about are the generated ones --

def test_report_date_scenarios_have_the_declared_timeline(tmp_path):
    """SZZG-0130: c1 < report < c3 < c4.  SZZG-0131: r1's author date < report < r1's committer date."""
    cm, repo = _generate(tmp_path, "SZZG-0130")
    committed = {cid: git(repo, "log", "-1", "--format=%cI", cm[cid]["hash"]) for cid in ("c1", "c3", "c4")}
    assert committed["c1"] < "2024-03-07T09:12:00Z" < committed["c3"] < committed["c4"], committed

    cm, repo = _generate(tmp_path, "SZZG-0131")
    authored = git(repo, "log", "-1", "--format=%aI", cm["r1"]["hash"])
    committed_r1 = git(repo, "log", "-1", "--format=%cI", cm["r1"]["hash"])
    assert authored < "2024-05-08T15:40:00Z" < committed_r1, (authored, committed_r1)
    assert authored == git(repo, "log", "-1", "--format=%aI", cm["f1"]["hash"]), "r1 inherits f1's author date"
