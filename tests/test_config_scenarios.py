"""Configuration scenarios whose code really reads the configuration (issue #23).

SZZ-0172 (config BIC, code fix) already had this property.  These are the three
the issue was still missing on 2026-09-22: the mirror case SZZ-0207 (code BIC,
config fix), the key rename SZZ-0208 (config BIC that changes no value, code
fix) and the repaired SZZG-0112 (non-UTF-8 config, BIC and BFC both in it).
Each test compiles every commit snapshot with a small driver, runs it from the
snapshot root so the relative `config/` path resolves, and checks that the
fault appears at the BIC, survives the distractor and is gone at the BFC; then
it checks the blame claim the README makes about the line the fix deletes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402

needs_jdk = pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")

RETRY_DRIVER = ("public class Drive { public static void main(String[] a) { "
                "System.out.print(new example.RetryPolicy().delayMillis()); } }")
RANGE_DRIVER = ("public class Drive { public static void main(String[] a) { "
                "example.ConfigBackedRange r = new example.ConfigBackedRange(); "
                "System.out.print(r.contains(0) + \" \" + r.contains(1) + \" \" + r.contains(9) + \" \" + r.contains(10)"
                " + \" \" + r.label().length() + \" \" + (int) r.label().charAt(3)); } }")

CASES = [
    # id, driver, expected output per commit, (file the fix touches, line it deletes, commit blame must name)
    ("SZZ-0207", RETRY_DRIVER, {"c0": "2000", "c1": "2", "c2": "2", "c3": "2000"},
     ("config/retry.properties", "retry.delay.unit=seconds", "c0")),
    ("SZZ-0208", RETRY_DRIVER, {"c0": "2000", "c1": "2", "c2": "2", "c3": "2000"},
     ("src/main/java/example/RetryPolicy.java", '    this.unit = properties.getProperty("retry.delay.unit", "milliseconds");', "c0")),
    ("SZZG-0112", RANGE_DRIVER, {"c0": "true true true true 4 233", "c1": "false true true false 4 233",
                                 "c2": "true true true true 4 233"}, None),
]


def _generate(tmp_path: Path, sid: str) -> tuple[dict[str, str], Path]:
    out = tmp_path / sid
    if sid.startswith("SZZG-"):
        commit_map, verify = generate_graph_repository(ROOT / "advanced-scenarios" / sid / "scenario.graph.yml", out, force=True)
    else:
        commit_map, verify = generate_repository(ROOT / "scenarios" / sid / "scenario.yml", out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict() if verify else "no verification"
    entries = commit_map.get("commits", commit_map) if isinstance(commit_map, dict) else commit_map
    hashes = {cid: (entry["hash"] if isinstance(entry, dict) else entry) for cid, entry in entries.items()}
    return hashes, out / "repo"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


def _run(repo: Path, commit: str, work: Path, driver: str) -> str:
    work.mkdir(parents=True)
    tar = subprocess.run(["git", "archive", commit], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
    (work / "Drive.java").write_text(driver)
    sources = [str(p) for p in work.rglob("*.java")]
    subprocess.run(["javac", "-d", str(work / "out"), *sources], check=True, capture_output=True)
    return subprocess.run(["java", "-cp", str(work / "out"), "Drive"], cwd=work, capture_output=True, text=True,
                          check=True).stdout.strip()


@needs_jdk
@pytest.mark.parametrize("sid, driver, expected, blame", CASES, ids=[c[0] for c in CASES])
def test_the_configuration_reaches_the_code_and_the_fix_undoes_the_fault(tmp_path, sid, driver, expected, blame):
    hashes, repo = _generate(tmp_path, sid)
    observed = {cid: _run(repo, hashes[cid], tmp_path / "w" / cid, driver) for cid in expected}
    assert observed == expected
    if blame is None:
        return
    path, deleted, owner = blame
    bfc = hashes[max(expected)]                       # the last commit is the BFC in all three histories
    diff = _git(repo, "diff", "-U0", f"{bfc}^", bfc, "--", path)
    assert f"-{deleted}" in diff, diff
    parent_lines = _git(repo, "show", f"{bfc}^:{path}").split("\n")
    line_no = parent_lines.index(deleted) + 1
    for flags in ((), ("-w",), ("-w", "-C", "-C")):
        blamed = _git(repo, "blame", "-l", *flags, "-L", f"{line_no},{line_no}", f"{bfc}^", "--", path).split()[0].lstrip("^")
        assert hashes[owner].startswith(blamed), f"{sid}: blame {flags} names {blamed[:7]}, README says {owner}"


def test_szz_0207_mirrors_szz_0172():
    """The pair is the point: same file names, same interpreter, fault and fix on opposite sides."""
    import yaml

    a = yaml.safe_load((ROOT / "scenarios/SZZ-0172/scenario.yml").read_text())
    b = yaml.safe_load((ROOT / "scenarios/SZZ-0207/scenario.yml").read_text())
    fault_a, fix_a = a["bugs"][0]["fault"]["file"], a["bugs"][0]["fix"]["file"]
    fault_b, fix_b = b["bugs"][0]["fault"]["file"], b["bugs"][0]["fix"]["file"]
    assert (fault_a, fix_a) == ("config/retry.properties", "src/main/java/example/RetryPolicy.java")
    assert (fault_b, fix_b) == ("src/main/java/example/RetryPolicy.java", "config/retry.properties")


def test_szz_0208_bic_changes_a_key_and_no_value(tmp_path):
    hashes, repo = _generate(tmp_path, "SZZ-0208")
    before = dict(line.split("=", 1) for line in _git(repo, "show", f"{hashes['c1']}^:config/retry.properties").split("\n"))
    after = dict(line.split("=", 1) for line in _git(repo, "show", f"{hashes['c1']}:config/retry.properties").split("\n"))
    assert sorted(before.values()) == sorted(after.values()), "the BIC must change no value"
    assert set(before) ^ set(after) == {"retry.delay.unit", "retry.delayUnit"}
    assert _git(repo, "diff", "--name-only", f"{hashes['c1']}^", hashes["c1"]) == "config/retry.properties"


def test_szzg_0112_config_is_not_utf8(tmp_path):
    hashes, repo = _generate(tmp_path, "SZZG-0112")
    raw = subprocess.run(["git", "show", f"{hashes['c2']}:config/range-limits.properties"], cwd=repo,
                         capture_output=True, check=True).stdout
    assert b"\xe9" in raw
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8")
    assert json.loads(json.dumps(raw.decode("cp1252"))) == "min=0\nmax=10\nlabel=café\n"


def test_szzg_0112_git_sees_text_lines_and_blame_reaches_the_bic(tmp_path):
    """The file is non-UTF-8, but Git diffs and blames it as text (PR #70 review)."""
    hashes, repo = _generate(tmp_path, "SZZG-0112")
    path = "config/range-limits.properties"
    assert _git(repo, "diff", "--numstat", hashes["c1"], hashes["c2"]) == f"2\t2\t{path}"
    hunk = [line for line in _git(repo, "diff", "-U0", hashes["c1"], hashes["c2"]).split("\n") if line[:1] in "+-" and line[:3] not in ("---", "+++")]
    assert hunk == ["-min=1", "-max=9", "+min=0", "+max=10"]
    # the file is CP1252 -- reading it through a UTF-8 text pipe is exactly the trap the README describes
    raw = subprocess.run(["git", "show", f"{hashes['c2']}^:{path}"], cwd=repo, capture_output=True, check=True).stdout
    parent = raw.decode("cp1252").split("\n")
    for deleted in ("min=1", "max=9"):
        no = parent.index(deleted) + 1
        blamed = _git(repo, "blame", "-l", "-L", f"{no},{no}", f"{hashes['c2']}^", "--", path).split()[0].lstrip("^")
        assert hashes["c1"].startswith(blamed), (deleted, blamed[:7])
