"""Multi-hop line histories (issue #24): SZZ-0209, SZZ-0210, SZZ-0211.

Each scenario rewrites its faulty line three or four times between the BIC
and the BFC without changing behaviour.  These tests generate the
repositories and check what the READMEs claim: the fault is observable from
the BIC through every rewrite and gone at the BFC; blame at the BFC parent
stops at the last rewrite; following the line the last rewrite replaced, and
so on, reaches the BIC in exactly the declared number of hops; and `-w` helps
exactly where the README says it does.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from support import GeneratedScenarios, export_tree, git_stdout, needs_jdk

ROOT = Path(__file__).resolve().parents[1]

CASES = {
    # id: (driver, expected output per commit, markers that together single out the faulty line, expected hop chain from BFC^, blame -w at BFC^)
    "SZZ-0209": (
        "public class Drive { public static void main(String[] a) { example.UploadPathPolicy p = new example.UploadPathPolicy(); "
        "System.out.print(p.accepts(\"uploads/report.txt\") + \" \" + p.accepts(\"../etc/passwd\") + \" \" + p.accepts(\"uploads/../etc/passwd\")); } }",
        {"c0": "true false false", "c1": "true false true", "c2": "true false true", "c3": "true false true",
         "c4": "true false true", "c5": "true false false"},
        ("if (", "startsWith("), ["c4", "c3", "c2", "c1"], "c4"),
    "SZZ-0210": (
        "public class Drive { public static void main(String[] a) { example.UploadLimit l = new example.UploadLimit(); "
        "System.out.print(l.accepts(1000, 4096) + \" \" + l.accepts(3000000, 1024)); } }",
        {"c0": "true false", "c1": "true true", "c2": "true true", "c3": "true true", "c4": "true true", "c5": "true false"},
        ("declaredBlocks * blockSize",), ["c4", "c3", "c2", "c1"], "c4"),
    "SZZ-0211": (
        "public class Drive { public static void main(String[] a) { example.ReportAccess r = new example.ReportAccess(); "
        "System.out.print(r.mayOpen(new example.Account(true), \"r1\") + \" \" + r.mayOpen(new example.Account(false), \"r1\") + \" \" + r.mayOpen(null, \"r1\")); } }",
        {"c0": "true false false", "c1": "true true false", "c2": "true true false", "c3": "true true false",
         "c4": "true true false", "c5": "true true false", "c6": "true false false"},
        ("if (", "== null"), ["c5", "c4", "c3", "c2", "c1"], "c5"),
}


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory):
    return GeneratedScenarios(tmp_path_factory)


@pytest.fixture(scope="module", params=sorted(CASES), ids=sorted(CASES))
def generated(request, scenarios):
    return scenarios(request.param)


def _carries(line: str, markers: tuple[str, ...]) -> bool:
    return all(marker in line for marker in markers)


def _deleted_lines(repo: Path, commit: str, path: str) -> list[str]:
    diff = git_stdout(repo, "diff", "-U0", f"{commit}^", commit, "--", path)
    return [line[1:] for line in diff.split("\n") if line.startswith("-") and not line.startswith("---")]


def _blame_owner(repo: Path, commit: str, path: str, line_text: str, hashes: dict[str, str], *flags: str) -> str:
    lines = git_stdout(repo, "show", f"{commit}:{path}").split("\n")
    number = lines.index(line_text) + 1
    blamed = git_stdout(repo, "blame", "-l", *flags, "-L", f"{number},{number}", commit, "--", path).split()[0].lstrip("^")
    return next(cid for cid, full in hashes.items() if full.startswith(blamed))


def test_the_faulty_line_is_rewritten_by_every_intermediate_commit(generated):
    """Each commit between the BIC and the BFC deletes exactly one line carrying the faulty expression."""
    sid, hashes, repo = generated
    _, _, markers, chain, _ = CASES[sid]
    path = git_stdout(repo, "diff", "--name-only", f"{hashes['c1']}^", hashes["c1"]).strip()
    for cid in chain[:-1]:                                 # the rewrites, not the BIC
        carrying = [line for line in _deleted_lines(repo, hashes[cid], path) if _carries(line, markers)]
        assert len(carrying) == 1, (sid, cid, carrying)


def test_plain_blame_stops_at_the_last_rewrite_and_the_line_history_reaches_the_bic(generated):
    sid, hashes, repo = generated
    _, _, markers, expected_chain, w_owner = CASES[sid]
    bfc = max(hashes, key=lambda cid: int(cid[1:]))
    path = git_stdout(repo, "diff", "--name-only", f"{hashes[bfc]}^", hashes[bfc]).strip()
    current = next(line for line in _deleted_lines(repo, hashes[bfc], path) if _carries(line, markers))
    parent = f"{hashes[bfc]}^"
    chain = []
    while True:
        owner = _blame_owner(repo, parent, path, current, hashes)
        chain.append(owner)
        if owner == "c1" or len(chain) > 10:
            break
        current = next(line for line in _deleted_lines(repo, hashes[owner], path) if _carries(line, markers))
        parent = f"{hashes[owner]}^"
    assert chain == expected_chain, f"{sid}: line history {chain}"
    # -w at the BFC parent: only a whitespace-only last rewrite would be skipped, and none of these is
    first_deleted = next(line for line in _deleted_lines(repo, hashes[bfc], path) if _carries(line, markers))
    assert _blame_owner(repo, f"{hashes[bfc]}^", path, first_deleted, hashes, "-w") == w_owner


@pytest.mark.parametrize("sid", ['SZZ-0211'])
def test_szz_0211_whitespace_hop_is_the_only_one_that_w_skips(scenarios, sid):
    _, hashes, repo = scenarios(sid)
    path = "src/main/java/example/ReportAccess.java"
    # c2 re-indented the file: at c3^ (= c2) the guard line blames to c2 plainly and to c1 with -w
    guard_at_c2 = "        if (user == null) {"
    assert _blame_owner(repo, hashes["c2"], path, guard_at_c2, hashes) == "c2"
    assert _blame_owner(repo, hashes["c2"], path, guard_at_c2, hashes, "-w") == "c1"
    assert git_stdout(repo, "diff", "-w", f"{hashes['c2']}^", hashes["c2"]).strip() == "", "c2 is whitespace-only"


@needs_jdk
def test_the_fault_is_visible_from_the_bic_through_every_rewrite_and_gone_at_the_bfc(generated, tmp_path):
    sid, hashes, repo = generated
    driver, expected, _, _, _ = CASES[sid]
    observed = {}
    for cid in expected:
        work = export_tree(repo, hashes[cid], tmp_path / cid)
        (work / "Drive.java").write_text(driver)
        sources = [str(p) for p in work.rglob("*.java")]
        subprocess.run(["javac", "-d", str(work / "out"), *sources], check=True, capture_output=True)
        observed[cid] = subprocess.run(["java", "-cp", str(work / "out"), "Drive"], capture_output=True, text=True, check=True).stdout
    assert observed == expected, sid
