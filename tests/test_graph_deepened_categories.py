"""Second discriminating scenarios for the graph categories that rested on one (issue #80, proposal 2).

G1, G6, G7 and G8 each had a single discriminating history, so a method could
pass the category by overfitting to one example.  These are their seconds, and
each fails the naive rules for a reason its category's first one does not: a
merge resolution owns the rewrite, a merge reintroduces a reverted change, the
evidence is a release tag and a changelog, and the unreachable commit touches
nothing but a binary file.

Every test measures the scenario against its generated repository: the probe
answers at each commit, the blame owner of every line the fix deletes, and the
structural claim its README makes about the graph.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from support import GeneratedScenarios, blame_owners, export_tree, git_bytes, git_stdout, logical_id, needs_jdk, run_driver

ROOT = Path(__file__).resolve().parents[1]

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


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory):
    return GeneratedScenarios(tmp_path_factory)


@pytest.fixture(scope="module", params=sorted(EXPECTED), ids=sorted(EXPECTED))
def generated(request, scenarios):
    return scenarios(request.param)


def _blame_of(repo: Path, hashes: dict[str, str], at: str, path: str, needle: str) -> str:
    head = hashes[at]
    for i, line in enumerate(git_stdout(repo, "show", f"{head}:{path}").splitlines(), 1):
        if needle in line:
            return logical_id(hashes, git_stdout(repo, "blame", "-l", "-L", f"{i},{i}", head, "--", path).split()[0])
    raise AssertionError(f"{needle!r} is not in {path} at {at}")


def test_every_deleted_line_blames_as_the_readme_says(generated):
    sid, hashes, repo = generated
    assert blame_owners(repo, hashes, BFC[sid]) == BLAME[sid]


def test_blame_misses_exactly_one_required_commit(generated):
    sid, hashes, repo = generated
    blamed = {owners[0] for owners in blame_owners(repo, hashes, BFC[sid]).values()}
    assert UNREACHABLE[sid] not in blamed, "the unreachable commit must not be blamed"
    assert blamed & REQUIRED[sid] == REQUIRED[sid] - {UNREACHABLE[sid]}
    assert blamed <= REQUIRED[sid], "blame must name no commit outside the oracle here"


@needs_jdk
def test_the_probe_answers_move_exactly_where_the_readme_says(generated, tmp_path):
    sid, hashes, repo = generated
    observed = {}
    for cid in EXPECTED[sid]:
        work = tmp_path / cid
        export_tree(repo, hashes[cid], work)
        observed[cid] = run_driver(work, DRIVERS[sid])
    assert observed == EXPECTED[sid], sid


def test_the_unreachable_commit_moved_no_answer_when_it_landed(generated):
    """Every probe answers the same before and after the commit blame cannot reach."""
    sid, hashes, repo = generated
    order = list(EXPECTED[sid])
    before = order[order.index(UNREACHABLE[sid]) - 1]
    assert EXPECTED[sid][UNREACHABLE[sid]] == EXPECTED[sid][before], "the unreachable commit must move no answer"
    observable = OBSERVABLE_AT[sid]
    assert EXPECTED[sid][observable] != EXPECTED[sid][order[order.index(observable) - 1]]


@pytest.mark.parametrize("sid", ['SZZG-0150'])
def test_the_merge_resolution_owns_the_boundary(scenarios, sid):
    """SZZG-0150: both lines the resolution wrote differ from both parents, and c1 is off the first parent."""
    _, hashes, repo = scenarios(sid)
    path = "src/main/java/example/Bands.java"
    assert _blame_of(repo, hashes, "c4", path, "static final int HEAVY_FROM_KILOGRAMS") == "c3"
    assert _blame_of(repo, hashes, "c4", path, "return kilograms > HEAVY_FROM_KILOGRAMS;") == "c3"
    walk = [logical_id(hashes, h) for h in git_stdout(repo, "log", "--first-parent", "--format=%H", hashes["c5"]).split()]
    assert "c1" not in walk and "c3" in walk


@pytest.mark.parametrize("sid", ['SZZG-0151'])
def test_the_merge_reintroduces_what_the_revert_undid(scenarios, sid):
    """SZZG-0151: c2 is a real revert, c4 is a merge, and blame leads to the origin instead."""
    _, hashes, repo = scenarios(sid)
    assert git_stdout(repo, "log", "--format=%s", "-1", hashes["c2"]).startswith('Revert "')
    assert len(git_stdout(repo, "log", "--format=%P", "-1", hashes["c4"]).split()) == 2
    path = "src/main/java/example/RateCard.java"
    assert _blame_of(repo, hashes, "c5", path, "static final int DAILY = 5;") == "c1", "blame reaches the origin"
    assert "c1" not in REQUIRED[sid], "and the origin is not part of the answer"


@pytest.mark.parametrize("sid", ['SZZG-0152'])
def test_the_release_tag_and_changelog_lead_to_the_unit_change(scenarios, sid):
    """SZZG-0152: the range the fix's message names contains c1, and the changelog says what it did."""
    _, hashes, repo = scenarios(sid)
    released = [logical_id(hashes, h) for h in git_stdout(repo, "log", "--format=%H", "v2.3.0..v2.4.0").split()]
    assert set(released) == {"c1", "c2", "c3"}
    changelog = git_stdout(repo, "show", f"{hashes['c4']}:CHANGELOG.md")
    assert "## 2.4.0" in changelog and "tenths of a cent" in changelog
    # the entry belongs to the release, not to the commit it describes, so it names no commit
    assert "## 2.4.0" not in git_stdout(repo, "show", f"{hashes['c1']}:CHANGELOG.md")
    wrote_entry = [logical_id(hashes, h) for h in git_stdout(repo, "log", "-S", "tenths", "--format=%H").split()]
    assert wrote_entry == ["c3"], wrote_entry
    assert "v2.4.0" in git_stdout(repo, "log", "--format=%s", "-1", hashes["c5"])
    path = "src/main/java/example/Metering.java"
    assert _blame_of(repo, hashes, "c4", path, "static final int METERED_UNIT_PRICE") == "c2", "the rename owns it"


@pytest.mark.parametrize("sid", ['SZZG-0153'])
def test_the_binary_change_carries_no_diff(scenarios, sid):
    """SZZG-0153: the commit adds and deletes no line, and blaming the file names it for all of it."""
    _, hashes, repo = scenarios(sid)
    table = "src/main/resources/zone-rates.bin"
    numstat = git_stdout(repo, "diff", "--numstat", hashes["c0"], hashes["c1"], "--", table).split()
    assert numstat[:2] == ["-", "-"], f"a binary diff has no line counts: {numstat}"
    shortstat = git_stdout(repo, "diff", "--shortstat", hashes["c0"], hashes["c1"]).strip()
    assert shortstat == "1 file changed, 0 insertions(+), 0 deletions(-)", shortstat
    # the file's own bytes come back in the blame output, so read it as bytes
    raw = git_bytes(repo, "blame", "-l", hashes["c1"], "--", table)
    blame = raw.splitlines()
    assert len(blame) == 1, "git treats the whole binary file as one line"
    assert logical_id(hashes, blame[0].split()[0].decode()) == "c1"
    assert git_stdout(repo, "diff", "--name-only", f"{hashes['c1']}^", hashes["c1"]).split() == [table]


#: words that would give the unit away if a commit message carried them (PR #87 review).  The
#: bug-fixing commit is exempt: its own message is where a tool starts.
UNIT_WORDS = {"SZZG-0152": ("cent", "tenth"), "SZZG-0153": ("cent", "dollar", "usd")}


@pytest.mark.parametrize("sid", sorted(UNIT_WORDS))
def test_no_commit_message_gives_the_unit_away(scenarios, sid):
    """The evidence these two scenarios claim is the only one: greping the log must not shortcut it."""
    _, hashes, repo = scenarios(sid)
    telling = []
    for cid, sha in hashes.items():
        if cid == BFC[sid]:
            continue
        message = git_stdout(repo, "log", "--format=%B", "-1", sha).lower()
        telling += [f"{cid}: {word}" for word in UNIT_WORDS[sid] if word in message]
    assert telling == [], f"{sid} names the unit in a commit message: {telling}"
    for word in UNIT_WORDS[sid]:
        found = {logical_id(hashes, h) for h in git_stdout(repo, "log", "--all", "-i", f"--grep={word}", "--format=%H").split()}
        assert found <= {BFC[sid]}, f"git log --grep={word} reaches {sorted(found)}"
