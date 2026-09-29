"""SZZG-0089: a revert-of-revert whose reverts are real and whose conflict is real (issue #22).

Until 2026-09-22 its two reverts were prose subjects with hand-written
operations.  These tests generate the scenario and check what the README
claims: the reverts carry Git's footer naming the reverted hash, the
intervening commit rewrote exactly the reverted lines so the second revert
needed a resolution, the fault appears and disappears where declared, and the
lines the fix deletes blame to the rename, not to the BIC.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from support import export_tree, git, git_env, needs_jdk
from szzbench.graph_generator import generate_graph_repository

ROOT = Path(__file__).resolve().parents[1]

JAVA = "src/main/java/example/Range.java"
DRIVER = ("public class Drive { public static void main(String[] a) { example.Range r = new example.Range(); "
          "System.out.print(r.contains(0, 0, 10) + \" \" + r.contains(5, 0, 10) + \" \" + r.contains(10, 0, 10)); } }")


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> tuple[dict[str, str], Path]:
    out = tmp_path_factory.mktemp("szzg0089") / "SZZG-0089"
    commit_map, verify = generate_graph_repository(ROOT / "advanced-scenarios/SZZG-0089/scenario.graph.yml", out, force=True)
    assert not verify.has_errors(), verify.to_dict()
    return {cid: entry["hash"] for cid, entry in commit_map.items()}, out / "repo"


def test_both_reverts_are_real_and_carry_the_footer(generated):
    hashes, repo = generated
    body_c3 = git(repo, "log", "-1", "--format=%s%n%b", hashes["c3"])
    body_c5 = git(repo, "log", "-1", "--format=%s%n%b", hashes["c5"])
    assert body_c3.startswith('Revert "Accept both bounds again"\n') and f"This reverts commit {hashes['c2']}." in body_c3
    assert body_c5.startswith('Revert "Revert "Accept both bounds again""\n') and f"This reverts commit {hashes['c3']}." in body_c5
    # c3 is c2 undone exactly: the tree of c3 equals the tree of c1
    assert git(repo, "rev-parse", f"{hashes['c3']}^{{tree}}") == git(repo, "rev-parse", f"{hashes['c1']}^{{tree}}")


def test_the_second_revert_conflicts_and_the_resolution_keeps_the_rename(generated):
    hashes, repo = generated
    # replaying git revert c3 on c4 without the resolution must conflict
    scratch = repo.parent / "scratch"
    git(repo.parent, "clone", "-q", str(repo), str(scratch))
    git(scratch, "checkout", "-q", hashes["c4"])
    attempt = subprocess.run(["git", "revert", "--no-commit", "--no-edit", hashes["c3"]], cwd=scratch, capture_output=True, text=True,
                             env=git_env())
    assert attempt.returncode != 0 and "conflict" in (attempt.stdout + attempt.stderr).lower()
    final = git(repo, "show", f"{hashes['c5']}:{JAVA}")
    assert "boolean lowerOk = value >= min;" in final and "boolean upperOk = value <= max;" in final
    assert "aboveMin" not in final and '"inclusive range"' in final


@needs_jdk
def test_fault_appears_at_c1_returns_at_c3_and_is_gone_at_c5(generated, tmp_path):
    hashes, repo = generated
    expected = {"c0": "true true true", "c1": "false true false", "c2": "true true true",
                "c3": "false true false", "c4": "false true false", "c5": "true true true"}
    observed = {}
    for cid in expected:
        work = tmp_path / cid
        work.mkdir()
        export_tree(repo, hashes[cid], work)
        (work / "Drive.java").write_text(DRIVER)
        subprocess.run(["javac", "-d", str(work / "out"), str(work / JAVA), str(work / "Drive.java")], check=True, capture_output=True)
        observed[cid] = subprocess.run(["java", "-cp", str(work / "out"), "Drive"], capture_output=True, text=True, check=True).stdout
    assert observed == expected


def test_the_lines_the_fix_deletes_blame_to_the_rename_not_the_bic(generated):
    hashes, repo = generated
    parent = git(repo, "show", f"{hashes['c5']}^:{JAVA}").split("\n")
    for deleted in ("    boolean lowerOk = value > min;", "    boolean upperOk = value < max;"):
        line_no = parent.index(deleted) + 1
        blamed = git(repo, "blame", "-l", "-L", f"{line_no},{line_no}", f"{hashes['c5']}^", "--", JAVA).split()[0]
        assert blamed == hashes["c4"], f"{deleted!r} blames to {blamed[:7]}, expected c4"
