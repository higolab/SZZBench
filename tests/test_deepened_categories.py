"""Second discriminating scenarios for the categories that rested on one (issue #80, proposal 2).

A category whose claim to discriminate rests on a single history gives a method
one example to overfit to.  Nine categories were in that position after #84;
these are the five for S1, S2, S5, S7 and S8, each using a reason the category's
first one does not.

Each test measures the scenario against its generated repository: the probe
answers at every commit, the blame owner of every deleted line, and how blame's
answer relates to the oracle — which is the point of each design.
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

needs_jdk = pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")

DRIVERS = {
    "SZZ-0221": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.Order o = new example.Order(); StringBuilder b = new StringBuilder();
    b.append("total=").append(o.roundedTotal(1234, 66));
    b.append(" totalMax=").append(o.roundedTotal(2147483643, 0));
    try { o.roundedTotal(-8, 0); b.append(" negTotal=accepted"); }
    catch (IllegalArgumentException e) { b.append(" negTotal=refused"); }
    try { Method m = o.getClass().getMethod("roundedRefund", int.class, int.class);
          b.append(" refund3=").append(m.invoke(o, 3, 3)).append(" refund8=").append(m.invoke(o, 8, 8));
          b.append(" refundMax=").append(m.invoke(o, 2147483643, 0)); }
    catch (NoSuchMethodException e) { b.append(" refund=absent"); }
    System.out.print(b); } }
""",
    "SZZ-0222": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.Uploads u = new example.Uploads(); StringBuilder b = new StringBuilder();
    b.append("small=").append(u.accept("a.txt", 1000) ? "T" : "F");
    b.append(" huge=").append(u.accept("a.txt", 2000000) ? "T" : "F");
    try { Method m = u.getClass().getMethod("acceptBatch", String[].class, int[].class);
          b.append(" batchHugeItem=").append(m.invoke(u, new String[]{"a","b"}, new int[]{1000, 2000000}));
          b.append(" batchOverTotal=").append(m.invoke(u, new String[]{"a","b","c"}, new int[]{1000000, 1000000, 1000000}));
          String[] n = new String[2048]; int[] s = new int[2048];
          for (int i = 0; i < 2048; i++) { n[i] = "f" + i; s[i] = 1048576; }
          b.append(" batch2048=").append(m.invoke(u, n, s)); }
    catch (NoSuchMethodException e) { b.append(" batch=absent"); }
    System.out.print(b); } }
""",
    "SZZ-0223": """
public class Drive { public static void main(String[] a) {
    example.Quote q = new example.Quote();
    System.out.print("q2000=" + q.totalCents(2000, 5000) + " q500=" + q.totalCents(500, 1000)); } }
""",
    "SZZ-0224": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.ImportRunner ir = new example.ImportRunner(); StringBuilder b = new StringBuilder();
    b.append("import0=").append(ir.runsFor(0)).append(" import5=").append(ir.runsFor(5));
    try { Object er = Class.forName("example.ExportRunner").getConstructor().newInstance();
          Method m = er.getClass().getMethod("runsFor", int.class);
          b.append(" export0=").append(m.invoke(er, 0)).append(" export5=").append(m.invoke(er, 5)); }
    catch (ClassNotFoundException e) { b.append(" export=absent"); }
    System.out.print(b); } }
""",
    "SZZ-0225": """
public class Drive { public static void main(String[] a) {
    example.LateFee f = new example.LateFee();
    System.out.print("d1=" + f.cents(1) + " d3=" + f.cents(3) + " d10=" + f.cents(10)); } }
""",
}

EXPECTED = {
    "SZZ-0221": {
        "c0": "total=1300 totalMax=2147483640 negTotal=refused refund=absent",
        "c1": "total=1300 totalMax=2147483640 negTotal=refused refund=absent",
        "c2": "total=1300 totalMax=2147483640 negTotal=refused refund=absent",
        "c3": "total=1300 totalMax=2147483640 negTotal=refused refund3=0 refund8=-20 refundMax=-2147483640",
        "c4": "total=1300 totalMax=2147483640 negTotal=refused refund3=-10 refund8=-20 refundMax=-2147483640",
    },
    "SZZ-0222": {
        "c0": "small=T huge=F batch=absent",
        "c1": "small=T huge=T batch=absent",
        "c2": "small=T huge=T batch=absent",
        "c3": "small=T huge=T batchHugeItem=true batchOverTotal=true batch2048=true",
        "c4": "small=T huge=F batchHugeItem=false batchOverTotal=false batch2048=false",
    },
    "SZZ-0224": {
        "c0": "import0=1 import5=3 export=absent",
        "c1": "import0=1 import5=3 export=absent",
        "c2": "import0=1 import5=3 export=absent",
        "c3": "import0=1 import5=3 export0=1 export5=2",
        "c4": "import0=1 import5=3 export0=1 export5=3",
    },
    "SZZ-0225": {
        "c0": "d1=50 d3=150 d10=500",
        "c1": "d1=50 d3=150 d10=500",
        "c2": "d1=50 d3=150 d10=500",
        "c3": "d1=0 d3=100 d10=450",
        "c4": "d1=50 d3=150 d10=500",
    },
    "SZZ-0223": {
        "c0": "q2000=5600 q500=1150",
        "c1": "q2000=5060 q500=1015",
        "c2": "q2000=5060 q500=1015",
        "c3": "q2000=4910 q500=865",
        "c4": "q2000=5750 q500=1300",
    },
}

BLAME = {
    "SZZ-0221": {"if (value < -10) {": ("c1", "c1", "c1")},
    "SZZ-0222": {"if (name == null) {": ("c0", "c0", "c0")},
    "SZZ-0223": {"return goodsCents + shipping.feeCents(grams, 30) - HANDLING_CENTS;": ("c3", "c3", "c3")},
    "SZZ-0224": {"for (int i = 0; i < limit.attempts(); i++) {": ("c3", "c3", "c3")},
    "SZZ-0225": {"return (daysLate - 1) * CENTS_PER_DAY;": ("c3", "c3", "c3"),
                 "assertCents(fee.cents(3), 100);": ("c2", "c2", "c2")},
}

REQUIRED = {sid: {"c1", "c3"} for sid in EXPECTED}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout


@pytest.fixture(scope="module", params=sorted(EXPECTED), ids=sorted(EXPECTED))
def generated(request, tmp_path_factory):
    sid = request.param
    out = tmp_path_factory.mktemp(sid.lower()) / sid
    commit_map, verify = generate_repository(ROOT / "scenarios" / sid / "scenario.yml", out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    entries = commit_map.get("commits", commit_map) if isinstance(commit_map, dict) else commit_map
    return sid, {c: (e["hash"] if isinstance(e, dict) else e) for c, e in entries.items()}, out / "repo"


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
                    _owner(repo, hashes, _git(repo, "blame", "-l", *f, "-L", f"{line_no},{line_no}", f"{bfc}^", "--", path).split()[0])
                    for f in ((), ("-w",), ("-w", "-C", "-C")))
                line_no += 1
            elif line.startswith(" ") and line_no is not None:
                line_no += 1
    return seen


def test_every_deleted_line_blames_as_the_readme_says(generated):
    sid, hashes, repo = generated
    assert _blame_owners(repo, hashes) == BLAME[sid]


def test_blame_relates_to_the_oracle_as_the_design_says(generated):
    """SZZ-0221 and SZZ-0223 each reach one required commit; SZZ-0222 reaches none."""
    sid, hashes, repo = generated
    blamed = {owners[0] for owners in _blame_owners(repo, hashes).values()}
    if sid == "SZZ-0222":
        assert not (blamed & REQUIRED[sid]), "blame's answer must contain no required commit"
        assert blamed == {"c0"}
    elif sid == "SZZ-0221":
        assert blamed == {"c1"} and "c3" not in blamed
    elif sid == "SZZ-0225":
        # the product change, plus the rename that owns the expectation's line
        assert blamed == {"c2", "c3"} and "c1" not in blamed
    else:
        assert blamed == {"c3"} and "c1" not in blamed


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
    observed = {}
    for cid in EXPECTED[sid]:
        work = tmp_path / cid
        _snapshot(repo, hashes[cid], work)
        observed[cid] = _run_driver(work, sid)
    assert observed == EXPECTED[sid], sid


@needs_jdk
def test_the_unreachable_commit_moved_no_answer_when_it_landed(generated, tmp_path):
    """The first fault is invisible until a later commit reaches it, except in SZZ-0222."""
    sid, hashes, repo = generated
    if sid == "SZZ-0222":
        pytest.skip("both of this scenario's faults are visible as soon as they land")
    if sid == "SZZ-0221":
        # every probe of the package's public surface, including a negative total and both
        # ends of the supported domain, answers the same at c1 as at c0 (PR #85 review)
        assert EXPECTED[sid]["c1"] == EXPECTED[sid]["c0"], "c1 must move no probe answer"
        assert "negTotal=refused" in EXPECTED[sid]["c1"], "the only route to the helper must refuse a negative"
    elif sid in ("SZZ-0224", "SZZ-0225"):
        # c1 halves what a Javadoc'd constant means (0224) or writes a wrong expectation
        # into a test (0225); neither moves a product answer until c3 reaches it
        assert EXPECTED[sid]["c1"] == EXPECTED[sid]["c0"], "c1 must move no probe answer"
        assert EXPECTED[sid]["c2"] == EXPECTED[sid]["c1"], "the distractor must move no probe answer"
        assert EXPECTED[sid]["c3"] != EXPECTED[sid]["c2"], "c3 must be where the fault becomes observable"
    else:
        assert EXPECTED[sid]["c2"] == EXPECTED[sid]["c1"], "the refactoring must move no probe answer"
