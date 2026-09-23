"""Discriminating scenarios for the categories a cheap rule almost always solved (issue #80, proposal 3).

S3 held 39 of its 40 scenarios in the cheaply-solved set and G4 27 of 29, the two
largest such pockets in the suite.  By the rule of
``tests/test_second_mechanism.py`` every one of those had a one-commit oracle, so
the pocket can only shrink by adding scenarios whose oracle names more than one
commit.  These are S3's two and G4's one.

Each test measures the scenario against its generated repository: the probe
answers at every commit, the blame owner of every deleted line, and the evidence
that both required commits are necessary.
"""
from __future__ import annotations

import re
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

DRIVERS = {
    "SZZ-0219": """
public class Drive { public static void main(String[] a) {
    example.RateLimit r = new example.RateLimit(); StringBuilder o = new StringBuilder();
    for (int u : new int[]{9, 10, 11}) o.append("allow").append(u).append('=').append(r.allowed(u, 10) ? "T" : "F").append(' ');
    o.append("rem3=").append(r.remaining(3, 10)).append(" rem10=").append(r.remaining(10, 10));
    System.out.print(o); } }
""",
    "SZZ-0220": """
public class Drive { public static void main(String[] a) {
    example.PasswordPolicy p = new example.PasswordPolicy(); StringBuilder o = new StringBuilder();
    for (String s : new String[]{"1234567", "12345678", "123456789"})
        o.append("len").append(s.length()).append('=').append(p.longEnough(s) ? "T" : "F").append(' ');
    o.append("score8=").append(p.score("12345678"));
    System.out.print(o); } }
""",
    "SZZG-0149": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.quote.Quote q = new example.quote.Quote(); StringBuilder o = new StringBuilder();
    o.append("d1200=").append(q.deliveryDays(1200)).append(" d200=").append(q.deliveryDays(200));
    try { Method m = q.getClass().getMethod("expressDays", int.class);
          o.append(" x200=").append(m.invoke(q, 200)).append(" x1200=").append(m.invoke(q, 1200)); }
    catch (NoSuchMethodException e) { o.append(" express=absent"); }
    try { Object s = Class.forName("example.quote.Surcharge").getConstructor().newInstance();
          Method m = s.getClass().getMethod("cents", String.class);
          o.append(" rural=").append(m.invoke(s, "RURAL")).append(" remote=").append(m.invoke(s, "REMOTE")); }
    catch (ClassNotFoundException e) { o.append(" surcharge=absent"); }
    System.out.print(o); } }
""",
}

EXPECTED = {
    "SZZ-0219": {
        "c0": "allow9=T allow10=F allow11=F rem3=7 rem10=0",
        "c1": "allow9=T allow10=T allow11=F rem3=7 rem10=0",
        "c2": "allow9=T allow10=T allow11=F rem3=7 rem10=0",
        "c3": "allow9=T allow10=T allow11=F rem3=7 rem10=0",
        "c4": "allow9=T allow10=T allow11=F rem3=6 rem10=-1",
        "c5": "allow9=T allow10=F allow11=F rem3=7 rem10=0",
    },
    "SZZ-0220": {
        "c0": "len7=F len8=T len9=T score8=16",
        "c1": "len7=F len8=F len9=T score8=16",
        "c2": "len7=F len8=F len9=T score8=16",
        "c3": "len7=F len8=F len9=T score8=4",
        "c4": "len7=F len8=T len9=T score8=16",
    },
    "SZZG-0149": {
        "c0": "d1200=3 d200=1 express=absent surcharge=absent",
        "c1": "d1200=2 d200=0 express=absent surcharge=absent",
        "c2": "d1200=2 d200=0 express=absent surcharge=absent",
        "c3": "d1200=3 d200=1 express=absent rural=500 remote=0",
        "c4": "d1200=2 d200=0 express=absent rural=500 remote=0",
        "c5": "d1200=2 d200=0 x200=-1 x1200=1 rural=500 remote=0",
        "c6": "d1200=2 d200=0 x200=-1 x1200=1 rural=500 remote=0",
        "c7": "d1200=3 d200=1 x200=1 x1200=2 rural=500 remote=1500",
    },
}

#: stripped deleted line at BFC^ -> its blame owner under plain / -w / -w -C -C
BLAME = {
    "SZZ-0219": {
        "boolean withinQuota = used <= quota;": ("c3", "c3", "c3"),
        "return quota - used - 1;": ("c4", "c4", "c4"),
    },
    "SZZ-0220": {
        "return value.length() > 8;": ("c1", "c1", "c1"),
        "}": ("c0", "c0", "c0"),
        "": ("c0", "c0", "c0"),
        "/** @deprecated renamed to longEnough */": ("c2", "c2", "c2"),
        "@Deprecated": ("c2", "c2", "c2"),
        "public boolean isLongEnough(String value) {": ("c2", "c2", "c2"),
        "return longEnough(value);": ("c2", "c2", "c2"),
        "return value.length() / 2;": ("c3", "c3", "c3"),
    },
    "SZZG-0149": {"return distanceKm / 500;": ("c1", "c1", "c1")},
}

REQUIRED = {"SZZ-0219": {"c1", "c4"}, "SZZ-0220": {"c1", "c3"}, "SZZG-0149": {"c1", "c3", "c5"}}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout


@pytest.fixture(scope="module", params=sorted(EXPECTED), ids=sorted(EXPECTED))
def generated(request, tmp_path_factory):
    sid = request.param
    out = tmp_path_factory.mktemp(sid.lower()) / sid
    if sid.startswith("SZZG-"):
        commit_map, verify = generate_graph_repository(ROOT / "advanced-scenarios" / sid / "scenario.graph.yml", out, force=True)
    else:
        commit_map, verify = generate_repository(ROOT / "scenarios" / sid / "scenario.yml", out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    entries = commit_map.get("commits", commit_map) if isinstance(commit_map, dict) else commit_map
    hashes = {cid: (e["hash"] if isinstance(e, dict) else e) for cid, e in entries.items()}
    return sid, hashes, out / "repo"


def _owner(repo: Path, hashes: dict[str, str], full: str) -> str:
    bare = full.lstrip("^")
    return next(cid for cid, h in hashes.items() if h.startswith(bare[:40]) or bare.startswith(h[:40]))


def _blame_owners(repo: Path, hashes: dict[str, str]) -> dict[str, tuple[str, str, str]]:
    bfc = hashes[max(hashes, key=lambda cid: int(cid[1:]))]
    seen: dict[str, tuple[str, str, str]] = {}
    for path in _git(repo, "diff", "--name-only", f"{bfc}^", bfc).split():
        line_no = None
        for line in _git(repo, "diff", "-U0", f"{bfc}^", bfc, "--", path).splitlines():
            if line.startswith("@@"):
                line_no = int(re.match(r"@@ -(\d+)", line).group(1))
            elif line.startswith("-") and not line.startswith("---") and line_no is not None:
                seen[line[1:].strip()] = tuple(
                    _owner(repo, hashes, _git(repo, "blame", "-l", *flags, "-L", f"{line_no},{line_no}", f"{bfc}^", "--", path).split()[0])
                    for flags in ((), ("-w",), ("-w", "-C", "-C")))
                line_no += 1
            elif line.startswith(" ") and line_no is not None:
                line_no += 1
    return seen


def test_every_deleted_line_blames_as_the_readme_says(generated):
    sid, hashes, repo = generated
    assert _blame_owners(repo, hashes) == BLAME[sid]


def test_neither_scenario_is_reachable_by_blaming_what_the_fix_deletes(generated):
    """SZZ-0219 misses a required commit; SZZ-0220 names two that are not required."""
    sid, hashes, repo = generated
    blamed = {owners[0] for owners in _blame_owners(repo, hashes).values()}
    assert blamed != REQUIRED[sid]
    if sid == "SZZ-0219":
        assert "c1" not in blamed and "c3" in blamed        # the rename, two steps in front of the fault
    elif sid == "SZZ-0220":
        assert REQUIRED[sid] < blamed and blamed - REQUIRED[sid] == {"c0", "c2"}
    else:
        # one true positive, no false positive, below a minimum_required of two;
        # and the shape rule is kept out by c6, which touches both files the fix touches
        import yaml
        bfc = hashes[max(hashes, key=lambda cid: int(cid[1:]))]
        for path in _git(repo, "diff", "--name-only", f"{bfc}^", bfc).split():
            newest = _git(repo, "log", "-1", "--format=%H", f"{bfc}^", "--", path).strip()
            assert _owner(repo, hashes, newest) == "c6"
        level = yaml.safe_load((ROOT / "advanced-scenarios" / sid / "scenario.graph.yml").read_text())["expected_szz"]["commit_level"]
        assert blamed == {"c1"} and blamed < REQUIRED[sid]
        assert level["evaluation_policy"] == "partial_credit" and level["minimum_required"] == 2
        assert len(blamed) < level["minimum_required"]


def _snapshot(repo: Path, commit: str, into: Path) -> None:
    into.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(["git", "archive", commit], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(into)], input=tar, check=True)


def _run_driver(work: Path, sid: str) -> str:
    (work / "Drive.java").write_text(DRIVERS[sid])
    sources = [str(p) for p in work.rglob("*.java")]
    subprocess.run(["javac", "-nowarn", "-d", str(work / "out"), *sources], check=True, capture_output=True)
    return subprocess.run(["java", "-cp", str(work / "out"), "Drive"], cwd=work, capture_output=True, text=True, check=True).stdout.strip()


@needs_jdk
def test_the_probe_answers_move_exactly_where_the_readme_says(generated, tmp_path):
    sid, hashes, repo = generated
    observed = {cid: _run_driver(tmp_path / cid, sid) for cid in EXPECTED[sid]
                if (_snapshot(repo, hashes[cid], tmp_path / cid) or True)}
    assert observed == EXPECTED[sid], sid


def _edit(work: Path, rel: str, old: str, new: str) -> None:
    p = work / rel
    text = p.read_text()
    assert text.count(old) == 1, (rel, old)
    p.write_text(text.replace(old, new))


@needs_jdk
def test_both_faults_are_necessary_and_the_noise_commit_is_not_one(generated, tmp_path):
    sid, hashes, repo = generated
    if sid == "SZZG-0149":
        pytest.skip("three independent causes; the per-commit table already shows each moves its own answers")
    if sid == "SZZ-0219":
        last_faulty = "c4"
        first = (tmp_path / "only-quota", "src/main/java/example/RateLimit.java",
                 "boolean withinQuota = used <= quota;", "boolean withinQuota = used < quota;",
                 "allow9=T allow10=F allow11=F rem3=6 rem10=-1")
        second = (tmp_path / "only-remaining", "src/main/java/example/RateLimit.java",
                  "return quota - used - 1;", "return quota - used;", EXPECTED[sid]["c3"])
    else:
        last_faulty = "c3"
        first = (tmp_path / "only-length", "src/main/java/example/PasswordPolicy.java",
                 "return value.length() > 8;", "return value.length() >= 8;",
                 "len7=F len8=T len9=T score8=4")
        second = (tmp_path / "only-score", "src/main/java/example/PasswordPolicy.java",
                  "return value.length() / 2;", "return value.length() * 2;", EXPECTED[sid]["c1"])
    for work, rel, old, new, expected in (first, second):
        _snapshot(repo, hashes[last_faulty], work)
        _edit(work, rel, old, new)
        assert _run_driver(work, sid) == expected, (sid, work.name)
