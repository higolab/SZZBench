"""The Python scenarios (SZZ-0200–SZZ-0206, issue #24).

The Java bar of `decisions/vocabulary.md` §4 is "every Java snapshot compiles";
the Python bar is "every Python snapshot byte-compiles", and it is checked
here on every test run because the interpreter running the tests is all it
needs. The behaviour checks do what `test_twins_and_transitions.py` does for
Java: run the module at every commit and require the fault to appear at the
BIC, persist through the noise commit, and vanish at the BFC.
"""
from __future__ import annotations

import py_compile
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from szzbench.generator import generate_repository  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLASSIC = ROOT / "scenarios"

PYTHON_SCENARIOS = sorted(
    p.parent.name for p in CLASSIC.glob("SZZ-*/scenario.yml")
    if (yaml.safe_load(p.read_text()).get("repository") or {}).get("language") == "python"
)

# driver, then the expected stdout per commit (the fault must be visible at
# every commit between the BIC and the BFC, and at no other)
BEHAVIOUR: dict[str, tuple[str, list[str]]] = {
    "SZZ-0200": (
        "from grading.scores import passes; print([passes(s) for s in (79, 80, 85, 89, 90)])",
        ["[False, True, True, True, True]", "[False, False, False, False, True]", "[False, True, True, True, True]"],
    ),
    "SZZ-0201": (
        "from search.midpoint import middle, bisect_index\n"
        "try: print('middle', middle([1, 2, 3]))\n"
        "except TypeError as e: print('middle raises TypeError:', e)\n"
        "print('bisect', bisect_index([1, 3, 5], 4))",
        ["middle 2\nbisect 2", "middle raises TypeError: list indices must be integers or slices, not float\nbisect 2", "middle 2\nbisect 2"],
    ),
    "SZZ-0202": (
        "from tagging.tags import with_tag; print(with_tag('a')); print(with_tag('b')); print(with_tag('c', ['x']))",
        ["['a']\n['b']\n['x', 'c']", "['a']\n['a', 'b']\n['x', 'c']", "['a']\n['b']\n['x', 'c']"],
    ),
    "SZZ-0203": (
        "import carriers.names as n\n"
        "print(hasattr(n, 'carrier_name') and n.carrier_name('UPS'))\n"
        "try: print(n.carrier_name('XYZ'))\n"
        "except (AttributeError, KeyError) as e: print('raises', type(e).__name__)",
        ["False\nraises AttributeError", "United Parcel Service\nraises KeyError", "United Parcel Service\nunknown carrier"],
    ),
    "SZZ-0204": (
        "from cache.expiry import is_expired; print([is_expired(a, 10) for a in (9, 10, 11)])",
        ["[False, False, True]", "[False, True, True]", "[False, True, True]", "[False, False, True]"],
    ),
    "SZZ-0205": (
        "from shipping.summary import progress_line\n"
        "try: print(progress_line(3, 12))\n"
        "except TypeError: print('one-argument signature')",
        ["one-argument signature", "12 of 3 items shipped", "12 of 3 items shipped", "3 of 12 items shipped"],
    ),
    "SZZ-0206": (
        "from limits.upload import accepts, MAX_UPLOAD_KB; print(MAX_UPLOAD_KB, [accepts(k, 'a.pdf') for k in (6144, 6145, 20480, 61440, 61441)])",
        ["20480 [True, True, True, False, False]", "6144 [True, False, False, False, False]",
         "6144 [True, False, False, False, False]", "61440 [True, True, True, True, False]"],
    ),
}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


def _generate(tmp_path: Path, sid: str) -> tuple[dict, Path]:
    out = tmp_path / sid
    commit_map, verify = generate_repository(CLASSIC / sid / "scenario.yml", out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict() if verify else None
    return commit_map, out / "repo"


def _snapshot(repo: Path, commit_hash: str, work: Path) -> Path:
    work.mkdir()
    tar = subprocess.run(["git", "archive", commit_hash], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
    return work


def _ordered(commit_map: dict) -> list[tuple[str, str]]:
    return [(cid, commit_map[cid]["hash"]) for cid in sorted(commit_map, key=lambda c: int(c[1:]))]


def test_the_python_scenarios_are_the_seven_of_issue_24():
    assert PYTHON_SCENARIOS == [f"SZZ-{n:04d}" for n in range(200, 207)]
    assert set(BEHAVIOUR) == set(PYTHON_SCENARIOS)


@pytest.mark.parametrize("sid", PYTHON_SCENARIOS)
def test_every_python_snapshot_byte_compiles(tmp_path, sid):
    commit_map, repo = _generate(tmp_path, sid)
    compiled = 0
    for cid, commit_hash in _ordered(commit_map):
        work = _snapshot(repo, commit_hash, tmp_path / f"snap-{cid}")
        sources = sorted(work.rglob("*.py"))
        assert sources, f"{sid} {cid}: snapshot carries no Python"
        for source in sources:
            py_compile.compile(str(source), doraise=True)   # raises PyCompileError on a syntax error
            compiled += 1
    assert compiled >= len(commit_map)


@pytest.mark.parametrize("sid", PYTHON_SCENARIOS)
def test_fault_is_visible_exactly_between_bic_and_bfc(tmp_path, sid):
    driver, expected = BEHAVIOUR[sid]
    commit_map, repo = _generate(tmp_path, sid)
    ordered = _ordered(commit_map)
    assert len(ordered) == len(expected)
    for (cid, commit_hash), want in zip(ordered, expected):
        work = _snapshot(repo, commit_hash, tmp_path / f"run-{cid}")
        run = subprocess.run([sys.executable, "-c", driver], cwd=work / "src", text=True, capture_output=True)
        assert run.returncode == 0, (sid, cid, run.stderr)
        assert run.stdout.strip() == want, (sid, cid, run.stdout)


def test_wrong_threshold_twin_differs_from_szz_0021_in_language_only(tmp_path):
    """SZZ-0200 mirrors SZZ-0021: same authors, dates and messages at every position."""
    java, _ = generate_repository(CLASSIC / "SZZ-0021" / "scenario.yml", tmp_path / "java", force=True)
    python, _ = _generate(tmp_path, "SZZ-0200")
    assert set(java) == set(python) == {"c0", "c1", "c2"}
    for cid in java:
        for key in ("author", "author_date", "committer_date", "message"):
            assert java[cid][key] == python[cid][key], (cid, key)
    scenario = yaml.safe_load((CLASSIC / "SZZ-0200" / "scenario.yml").read_text())
    assert scenario["repository"]["language"] == "python"


def _blamed_ids(repo: Path, commit_map: dict, bfc: str, path: str, line: int, *options: str) -> set[str]:
    by_hash = {entry["hash"]: cid for cid, entry in commit_map.items()}
    out = _git(repo, "blame", "-l", "-s", *options, "-L", f"{line},{line}", f"{commit_map[bfc]['hash']}^", "--", path)
    return {by_hash[token.lstrip("^")] for token in (line_.split()[0] for line_ in out.splitlines())}


@pytest.mark.parametrize("sid,path,line", [
    ("SZZ-0204", "src/cache/expiry.py", 11),
    ("SZZ-0205", "src/shipping/summary.py", 5),
    ("SZZ-0206", "src/limits/upload.py", 1),
])
def test_noise_commit_owns_the_deleted_line_even_under_blame_w(tmp_path, sid, path, line):
    """The S3 Python scenarios claim plain blame and `blame -w` both return c2, not the BIC c1."""
    commit_map, repo = _generate(tmp_path, sid)
    deleted = _git(repo, "diff", "-U0", f"{commit_map['c3']['hash']}^", commit_map["c3"]["hash"])
    assert f"@@ -{line}" in deleted, deleted
    assert _blamed_ids(repo, commit_map, "c3", path, line) == {"c2"}
    assert _blamed_ids(repo, commit_map, "c3", path, line, "-w") == {"c2"}


def test_bom_scenario_changes_only_the_three_bom_bytes(tmp_path):
    """SZZ-0206: c2 prepends EF BB BF and nothing else; c3 keeps the BOM and changes the constant."""
    commit_map, repo = _generate(tmp_path, "SZZ-0206")
    blobs = {cid: subprocess.run(["git", "show", f"{commit_map[cid]['hash']}:src/limits/upload.py"], cwd=repo,
                                 capture_output=True, check=True).stdout for cid in commit_map}
    assert not blobs["c1"].startswith(b"\xef\xbb\xbf")
    assert blobs["c2"] == b"\xef\xbb\xbf" + blobs["c1"]
    assert blobs["c3"].startswith(b"\xef\xbb\xbfMAX_UPLOAD_KB = 61440\n")
    assert blobs["c3"][3:].splitlines()[1:] == blobs["c1"].splitlines()[1:]
    assert _git(repo, "diff", "--numstat", commit_map["c1"]["hash"], commit_map["c2"]["hash"]).split("\t")[:2] == ["1", "1"]
