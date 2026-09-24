"""Second discriminating scenarios for the graph categories that rested on one (issue #80, proposal 2).

G1, G6, G7 and G8 each had a single discriminating history, so a method could
pass the category by overfitting to one example.  These are their seconds, and
each fails the cheap rules for a reason its category's first one does not: a
merge resolution owns the rewrite, a merge reintroduces a reverted change, the
evidence is a release tag and a changelog, and the unreachable commit touches
nothing but a binary file.

Every test measures the scenario against its generated repository: the probe
answers at each commit, the blame owner of every line the fix deletes, and the
structural claim its README makes about the graph.
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

from szzbench.graph_generator import generate_graph_repository  # noqa: E402

needs_jdk = pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")

DRIVERS = {
    # the constant is package-private, so the two methods below are the package's whole
    # public surface until c4 adds the label (fault-library rule 7)
    "SZZG-0150": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    int[] xs = {Integer.MIN_VALUE, 0, 18, 19, 20, 21, Integer.MAX_VALUE};
    example.Bands b = new example.Bands(); example.Quote q = new example.Quote();
    StringBuilder s = new StringBuilder("heavy=");
    for (int x : xs) s.append(b.heavy(x) ? "T" : "F");
    s.append(" surcharge=");
    for (int x : xs) s.append(q.surchargeCents(x)).append(",");
    try { Method m = q.getClass().getMethod("heavyFrom"); s.append(" label=").append(m.invoke(q)); }
    catch (NoSuchMethodException e) { s.append(" label=absent"); }
    System.out.print(s); } }
""",
    "SZZG-0151": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.RateCard r = new example.RateCard(); StringBuilder s = new StringBuilder();
    s.append("total1=").append(r.totalCents(1)).append(" total7=").append(r.totalCents(7));
    s.append(" totalMax=").append(r.totalCents(4294967));
    try { Method m = r.getClass().getMethod("dailyLabel"); s.append(" label=").append(m.invoke(r)); }
    catch (NoSuchMethodException e) { s.append(" label=absent"); }
    try { Method m = r.getClass().getMethod("expressCents"); s.append(" express=").append(m.invoke(r)); }
    catch (NoSuchMethodException e) { s.append(" express=absent"); }
    System.out.print(s); } }
""",
    "SZZG-0152": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.Metering m = new example.Metering(); StringBuilder s = new StringBuilder();
    s.append("cost1=").append(m.costCents(1)).append(" cost25=").append(m.costCents(25));
    s.append(" costMax=").append(m.costCents(17895697));
    try { Method p = m.getClass().getMethod("priceLabel"); s.append(" label=").append(p.invoke(m)); }
    catch (NoSuchMethodException e) { s.append(" label=absent"); }
    System.out.print(s); } }
""",
    "SZZG-0153": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.Quote q = new example.Quote(); StringBuilder s = new StringBuilder("ship=");
    for (int z = 0; z < 4; z++) s.append(q.shippingCents(z)).append(",");
    try { Method m = q.getClass().getMethod("rateLabel", int.class);
          s.append(" label0=").append(m.invoke(q, 0)).append(" label3=").append(m.invoke(q, 3)); }
    catch (NoSuchMethodException e) { s.append(" label=absent"); }
    System.out.print(s); } }
""",
}

_G150 = "heavy=FFFFTTT surcharge=0,0,0,0,500,500,500,"
_G151 = "total1=500 total7=3500 totalMax=2147483500"
_G152 = "cost1=12 cost25=300 costMax=214748364"
_G153 = "ship=900,1200,1500,2000,"

EXPECTED = {
    "SZZG-0150": {
        "c0": f"{_G150} label=absent",
        "c2": f"{_G150} label=absent",
        "c1": f"{_G150} label=absent",
        "c3": f"{_G150} label=absent",
        "c4": f"{_G150} label=19 kg and over",
        "c5": f"{_G150} label=20 kg and over",
    },
    "SZZG-0151": {
        "c0": f"{_G151} label=absent express=absent",
        "c1": f"{_G151} label=absent express=absent",
        "c2": f"{_G151} label=absent express=absent",
        "c3": f"{_G151} label=5 EUR express=absent",
        "c4": f"{_G151} label=5 EUR express=absent",
        "c5": f"{_G151} label=5 EUR express=55",
        "c6": f"{_G151} label=5 EUR express=550",
    },
    "SZZG-0152": {
        "c0": f"{_G152} label=absent",
        "c1": f"{_G152} label=absent",
        "c2": f"{_G152} label=absent",
        "c3": f"{_G152} label=absent",
        "c4": f"{_G152} label=120 cents per unit",
        "c5": f"{_G152} label=12 cents per unit",
    },
    "SZZG-0153": {
        "c0": f"{_G153} label=absent",
        "c1": f"{_G153} label=absent",
        "c2": f"{_G153} label=absent",
        "c3": f"{_G153} label0=900 USD label3=2000 USD",
        "c4": f"{_G153} label0=9 USD label3=20 USD",
    },
}

#: the line the fix deletes -> its blame owner under plain, ``-w`` and ``-w -C -C``
BLAME = {
    "SZZG-0150": {'return Bands.HEAVY_FROM_KILOGRAMS + " kg and over";': ("c4", "c4", "c4")},
    "SZZG-0151": {"return DAILY + 50;": ("c5", "c5", "c5")},
    "SZZG-0152": {'return METERED_UNIT_PRICE + " cents per unit";': ("c4", "c4", "c4")},
    "SZZG-0153": {'return rates.rawValue(zone) + " USD";': ("c3", "c3", "c3")},
}

REQUIRED = {"SZZG-0150": {"c1", "c4"}, "SZZG-0151": {"c4", "c5"},
            "SZZG-0152": {"c1", "c4"}, "SZZG-0153": {"c1", "c3"}}

#: the required commit blame does not reach, and the commit where the fault becomes observable
UNREACHABLE = {"SZZG-0150": "c1", "SZZG-0151": "c4", "SZZG-0152": "c1", "SZZG-0153": "c1"}
OBSERVABLE_AT = {"SZZG-0150": "c4", "SZZG-0151": "c5", "SZZG-0152": "c4", "SZZG-0153": "c3"}
BFC = {"SZZG-0150": "c5", "SZZG-0151": "c6", "SZZG-0152": "c5", "SZZG-0153": "c4"}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout


@pytest.fixture(scope="module", params=sorted(EXPECTED), ids=sorted(EXPECTED))
def generated(request, tmp_path_factory):
    sid = request.param
    out = tmp_path_factory.mktemp(sid.lower()) / sid
    commit_map, verify = generate_graph_repository(
        ROOT / "advanced-scenarios" / sid / "scenario.graph.yml", out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    entries = commit_map.get("commits", commit_map) if isinstance(commit_map, dict) else commit_map
    return sid, {c: (e["hash"] if isinstance(e, dict) else e) for c, e in entries.items()}, out / "repo"


def _owner(hashes: dict[str, str], full: str) -> str:
    bare = full.lstrip("^")
    return next(cid for cid, h in hashes.items() if h.startswith(bare[:40]) or bare.startswith(h[:40]))


def _blame_owners(repo: Path, hashes: dict[str, str], bfc: str) -> dict[str, tuple[str, str, str]]:
    head = hashes[bfc]
    seen: dict[str, tuple[str, str, str]] = {}
    for path in _git(repo, "diff", "--name-only", f"{head}^", head).split():
        line_no = None
        for line in _git(repo, "diff", "-U0", f"{head}^", head, "--", path).splitlines():
            if line.startswith("@@"):
                line_no = int(re.match(r"@@ -(\d+)", line).group(1))
            elif line.startswith("-") and not line.startswith("---") and line_no is not None:
                seen[line[1:].strip()] = tuple(
                    _owner(hashes, _git(repo, "blame", "-l", *flags, "-L", f"{line_no},{line_no}",
                                        f"{head}^", "--", path).split()[0])
                    for flags in ((), ("-w",), ("-w", "-C", "-C")))
                line_no += 1
            elif line.startswith(" ") and line_no is not None:
                line_no += 1
    return seen


def _blame_of(repo: Path, hashes: dict[str, str], at: str, path: str, needle: str) -> str:
    head = hashes[at]
    for i, line in enumerate(_git(repo, "show", f"{head}:{path}").splitlines(), 1):
        if needle in line:
            return _owner(hashes, _git(repo, "blame", "-l", "-L", f"{i},{i}", head, "--", path).split()[0])
    raise AssertionError(f"{needle!r} is not in {path} at {at}")


def test_every_deleted_line_blames_as_the_readme_says(generated):
    sid, hashes, repo = generated
    assert _blame_owners(repo, hashes, BFC[sid]) == BLAME[sid]


def test_blame_misses_exactly_one_required_commit(generated):
    sid, hashes, repo = generated
    blamed = {owners[0] for owners in _blame_owners(repo, hashes, BFC[sid]).values()}
    assert UNREACHABLE[sid] not in blamed, "the unreachable commit must not be blamed"
    assert blamed & REQUIRED[sid] == REQUIRED[sid] - {UNREACHABLE[sid]}
    assert blamed <= REQUIRED[sid], "blame must name no commit outside the oracle here"


@needs_jdk
def test_the_probe_answers_move_exactly_where_the_readme_says(generated, tmp_path):
    sid, hashes, repo = generated
    observed = {}
    for cid in EXPECTED[sid]:
        work = tmp_path / cid
        work.mkdir(parents=True, exist_ok=True)
        tar = subprocess.run(["git", "archive", hashes[cid]], cwd=repo, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
        (work / "Drive.java").write_text(DRIVERS[sid])
        sources = [str(p) for p in work.rglob("*.java")]
        subprocess.run(["javac", "-nowarn", "-d", str(work / "out"), *sources], check=True, capture_output=True)
        observed[cid] = subprocess.run(["java", "-cp", str(work / "out"), "Drive"], cwd=work,
                                       capture_output=True, text=True, check=True).stdout.strip()
    assert observed == EXPECTED[sid], sid


def test_the_unreachable_commit_moved_no_answer_when_it_landed(generated):
    """Every probe answers the same before and after the commit blame cannot reach."""
    sid, hashes, repo = generated
    order = list(EXPECTED[sid])
    before = order[order.index(UNREACHABLE[sid]) - 1]
    assert EXPECTED[sid][UNREACHABLE[sid]] == EXPECTED[sid][before], "the unreachable commit must move no answer"
    observable = OBSERVABLE_AT[sid]
    assert EXPECTED[sid][observable] != EXPECTED[sid][order[order.index(observable) - 1]]


def test_the_merge_resolution_owns_the_boundary(generated):
    """SZZG-0150: both lines the resolution wrote differ from both parents, and c1 is off the first parent."""
    sid, hashes, repo = generated
    if sid != "SZZG-0150":
        pytest.skip("only SZZG-0150 resolves a conflict by inlining")
    path = "src/main/java/example/Bands.java"
    assert _blame_of(repo, hashes, "c4", path, "static final int HEAVY_FROM_KILOGRAMS") == "c3"
    assert _blame_of(repo, hashes, "c4", path, "return kilograms > HEAVY_FROM_KILOGRAMS;") == "c3"
    walk = [_owner(hashes, h) for h in _git(repo, "log", "--first-parent", "--format=%H", hashes["c5"]).split()]
    assert "c1" not in walk and "c3" in walk


def test_the_merge_reintroduces_what_the_revert_undid(generated):
    """SZZG-0151: c2 is a real revert, c4 is a merge, and blame leads to the origin instead."""
    sid, hashes, repo = generated
    if sid != "SZZG-0151":
        pytest.skip("only SZZG-0151 reintroduces by merging")
    assert _git(repo, "log", "--format=%s", "-1", hashes["c2"]).startswith('Revert "')
    assert len(_git(repo, "log", "--format=%P", "-1", hashes["c4"]).split()) == 2
    path = "src/main/java/example/RateCard.java"
    assert _blame_of(repo, hashes, "c5", path, "static final int DAILY = 5;") == "c1", "blame reaches the origin"
    assert "c1" not in REQUIRED[sid], "and the origin is not part of the answer"


def test_the_release_tag_and_changelog_lead_to_the_unit_change(generated):
    """SZZG-0152: the range the fix's message names contains c1, and the changelog says what it did."""
    sid, hashes, repo = generated
    if sid != "SZZG-0152":
        pytest.skip("only SZZG-0152 carries release tags")
    released = [_owner(hashes, h) for h in _git(repo, "log", "--format=%H", "v2.3.0..v2.4.0").split()]
    assert set(released) == {"c1", "c2", "c3"}
    changelog = _git(repo, "show", f"{hashes['c4']}:CHANGELOG.md")
    assert "## 2.4.0" in changelog and "tenths of a cent" in changelog
    # the entry belongs to the release, not to the commit it describes, so it names no commit
    assert "## 2.4.0" not in _git(repo, "show", f"{hashes['c1']}:CHANGELOG.md")
    wrote_entry = [_owner(hashes, h) for h in _git(repo, "log", "-S", "tenths", "--format=%H").split()]
    assert wrote_entry == ["c3"], wrote_entry
    assert "v2.4.0" in _git(repo, "log", "--format=%s", "-1", hashes["c5"])
    path = "src/main/java/example/Metering.java"
    assert _blame_of(repo, hashes, "c4", path, "static final int METERED_UNIT_PRICE") == "c2", "the rename owns it"


def test_the_binary_change_carries_no_diff(generated):
    """SZZG-0153: the commit adds and deletes no line, and blaming the file names it for all of it."""
    sid, hashes, repo = generated
    if sid != "SZZG-0153":
        pytest.skip("only SZZG-0153 hides the unit in a binary file")
    table = "src/main/resources/zone-rates.bin"
    numstat = _git(repo, "diff", "--numstat", hashes["c0"], hashes["c1"], "--", table).split()
    assert numstat[:2] == ["-", "-"], f"a binary diff has no line counts: {numstat}"
    shortstat = _git(repo, "diff", "--shortstat", hashes["c0"], hashes["c1"]).strip()
    assert shortstat == "1 file changed, 0 insertions(+), 0 deletions(-)", shortstat
    # the file's own bytes come back in the blame output, so read it as bytes
    raw = subprocess.run(["git", "blame", "-l", hashes["c1"], "--", table],
                         cwd=repo, capture_output=True, check=True).stdout
    blame = raw.splitlines()
    assert len(blame) == 1, "git treats the whole binary file as one line"
    assert _owner(hashes, blame[0].split()[0].decode()) == "c1"
    assert _git(repo, "diff", "--name-only", f"{hashes['c1']}^", hashes["c1"]).split() == [table]


#: words that would give the unit away if a commit message carried them (PR #87 review).  The
#: bug-fixing commit is exempt: its own message is where a tool starts.
UNIT_WORDS = {"SZZG-0152": ("cent", "tenth"), "SZZG-0153": ("cent", "dollar", "usd")}


def test_no_commit_message_gives_the_unit_away(generated):
    """The evidence these two scenarios claim is the only one: greping the log must not shortcut it."""
    sid, hashes, repo = generated
    if sid not in UNIT_WORDS:
        pytest.skip("only SZZG-0152 and SZZG-0153 rest on evidence outside the commit messages")
    telling = []
    for cid, sha in hashes.items():
        if cid == BFC[sid]:
            continue
        message = _git(repo, "log", "--format=%B", "-1", sha).lower()
        telling += [f"{cid}: {word}" for word in UNIT_WORDS[sid] if word in message]
    assert telling == [], f"{sid} names the unit in a commit message: {telling}"
    for word in UNIT_WORDS[sid]:
        found = {_owner(hashes, h) for h in _git(repo, "log", "--all", "-i", f"--grep={word}", "--format=%H").split()}
        assert found <= {BFC[sid]}, f"git log --grep={word} reaches {sorted(found)}"
