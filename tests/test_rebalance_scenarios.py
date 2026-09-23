"""The discriminating scenarios added for the categories that had none (issue #35).

Each scenario has a two-commit oracle of which plain blame on the fix's deleted
lines reaches at most one.  These tests generate the repositories and check what
the READMEs claim: the probe answers at every commit, the blame owner of every
deleted line under three variants, and the counterfactual or partial fix that
shows both commits are necessary.
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

DRIVERS = {
    "SZZ-0212": """
public class Drive { public static void main(String[] a) {
    example.ShippingFee f = new example.ShippingFee(); StringBuilder out = new StringBuilder();
    for (int w : new int[] {1999, 2000, 2001}) for (boolean e : new boolean[] {false, true})
        out.append(w).append(e ? "X" : "S").append('=').append(f.feeCents(w, e)).append(' ');
    System.out.print(out.toString().trim()); } }
""",
    "SZZ-0213": """
import java.lang.reflect.Method;
public class Drive { @SuppressWarnings({"unchecked", "rawtypes"}) public static void main(String[] a) throws Exception {
    example.InvoiceTotal t = new example.InvoiceTotal(); StringBuilder out = new StringBuilder();
    out.append("tax1999=").append(t.withTaxCents(1999)).append(" tax2000=").append(t.withTaxCents(2000));
    try {
        Class<?> cust = Class.forName("example.Customer"); Class<?> tier = Class.forName("example.Customer$Tier");
        Method m = t.getClass().getMethod("discountCents", cust, int.class);
        Object gold = cust.getConstructor(tier).newInstance(Enum.valueOf((Class<Enum>) tier, "GOLD"));
        Object std = cust.getConstructor(tier).newInstance(Enum.valueOf((Class<Enum>) tier, "STANDARD"));
        out.append(" gold=").append(m.invoke(t, gold, 1000)).append(" std=").append(m.invoke(t, std, 1000));
        String anon; try { anon = String.valueOf(m.invoke(t, null, 1000)); }
        catch (java.lang.reflect.InvocationTargetException e) { anon = e.getCause().getClass().getSimpleName(); }
        out.append(" anon=").append(anon);
    } catch (ClassNotFoundException | NoSuchMethodException e) { out.append(" discount=absent"); }
    System.out.print(out); } }
""",
    "SZZ-0214": """
import java.lang.reflect.Method;
public class Drive {
    static String call(Object target, String name, String arg) {
        try { return String.valueOf(target.getClass().getMethod(name, String.class).invoke(target, arg)); }
        catch (NoSuchMethodException e) { return "absent"; }
        catch (java.lang.reflect.InvocationTargetException e) { return e.getCause().getClass().getSimpleName(); }
        catch (Exception e) { return e.getClass().getSimpleName(); } }
    public static void main(String[] a) throws Exception {
        StringBuilder out = new StringBuilder(); Object g = new example.Greeting();
        out.append("greet=").append(call(g, "greet", " Ada ")).append(" farewell=").append(call(g, "farewell", " Ada "));
        try { Object p = Class.forName("example.Profile").getConstructor().newInstance();
              out.append(" display=").append(call(p, "displayName", " Ada ")).append(" displayNull=").append(call(p, "displayName", null)); }
        catch (ClassNotFoundException e) { out.append(" profile=absent"); }
        System.out.print(out); } }
""",
    "SZZG-0144": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.SessionPolicy p = new example.SessionPolicy(); StringBuilder out = new StringBuilder();
    for (int s : new int[] {899, 900, 901}) out.append("exp").append(s).append('=').append(p.expired(s)).append(' ');
    try { Method m = p.getClass().getMethod("remainingSeconds", int.class);
          out.append("rem20=").append(m.invoke(p, 20)).append(" rem600=").append(m.invoke(p, 600)); }
    catch (NoSuchMethodException e) { out.append("rem=absent"); }
    System.out.print(out.toString().trim()); } }
""",
    "SZZ-0215": """
public class Drive { public static void main(String[] a) {
    example.LoyaltyPoints p = new example.LoyaltyPoints(); StringBuilder out = new StringBuilder();
    for (int v : new int[] {4, 5, 6, 8, 9}) out.append("b").append(v).append('=').append(p.bonus(v) ? "T" : "F").append(' ');
    out.append("p250=").append(p.points(250)).append(" p199=").append(p.points(199));
    System.out.print(out); } }
""",
    "SZZG-0145": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.ZoneRates r = new example.ZoneRates(); StringBuilder out = new StringBuilder();
    out.append("cents3=").append(r.rateCents("zone-3")).append(" cents1250=").append(r.rateCents("zone-1250"));
    try { Method m = r.getClass().getMethod("rateLabel", String.class);
          out.append(" label3=").append(m.invoke(r, "zone-3")).append(" label1250=").append(m.invoke(r, "zone-1250")); }
    catch (NoSuchMethodException e) { out.append(" label=absent"); }
    System.out.print(out); } }
""",
    "SZZG-0146": """
public class Drive { public static void main(String[] a) throws Exception {
    StringBuilder out = new StringBuilder(); example.Discount d = new example.Discount();
    out.append("apply=").append(d.apply(2000, "15%")).append(" applyBig=").append(d.apply(2000000, "15%"));
    try { Object rc = Class.forName("example.Receipt").getConstructor().newInstance();
          java.lang.reflect.Method m = rc.getClass().getMethod("describe", String.class);
          out.append(" d15=").append(m.invoke(rc, "15%")).append(" d7=").append(m.invoke(rc, "7%")); }
    catch (ClassNotFoundException e) { out.append(" receipt=absent"); }
    System.out.print(out); } }
""",
    "SZZG-0147": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.RetryPolicy p = new example.RetryPolicy(); StringBuilder out = new StringBuilder();
    out.append("wait3=").append(p.waitSeconds(3));
    try { Method m = p.getClass().getMethod("firstWaitSeconds"); out.append(" first=").append(m.invoke(p)); }
    catch (NoSuchMethodException e) { out.append(" first=absent"); }
    System.out.print(out); } }
""",
    "SZZ-0216": """
public class Drive { public static void main(String[] a) {
    example.TicketPricing t = new example.TicketPricing(); StringBuilder out = new StringBuilder();
    for (int age : new int[] {11, 12, 13}) out.append("base").append(age).append('=').append(t.basePriceCents(age)).append(' ');
    out.append("group30x3=").append(t.groupPriceCents(30, 3));
    System.out.print(out); } }
""",
    "SZZ-0217": """
public class Drive { public static void main(String[] a) throws Exception {
    StringBuilder out = new StringBuilder(); example.RequestTimeout t = new example.RequestTimeout();
    out.append("timeout90s=").append(t.seconds("90s")).append(" timeout2m=").append(t.seconds("2m"));
    out.append(" timeoutBig=").append(t.seconds("1000000000s"));
    try { Object r = Class.forName("example.RetryDelay").getConstructor().newInstance();
          java.lang.reflect.Method m = r.getClass().getMethod("seconds", String.class);
          out.append(" retry90s=").append(m.invoke(r, "90s")).append(" retry2m=").append(m.invoke(r, "2m"));
          out.append(" retryBig=").append(m.invoke(r, "1000000000s")); }
    catch (ClassNotFoundException e) { out.append(" retry=absent"); }
    System.out.print(out); } }
""",
}

EXPECTED = {
    "SZZ-0212": {
        "c0": "1999S=0 1999X=500 2000S=0 2000X=500 2001S=300 2001X=800",
        "c1": "1999S=0 1999X=500 2000S=300 2000X=800 2001S=300 2001X=800",
        "c2": "1999S=0 1999X=500 2000S=300 2000X=800 2001S=300 2001X=800",
        "c3": "1999S=0 1999X=-500 2000S=300 2000X=-200 2001S=300 2001X=-200",
        "c4": "1999S=0 1999X=500 2000S=0 2000X=500 2001S=300 2001X=800",
    },
    "SZZ-0213": {
        "c0": "tax1999=2198 tax2000=2200 discount=absent",
        "c1": "tax1999=2189 tax2000=2200 discount=absent",
        "c2": "tax1999=2189 tax2000=2200 discount=absent",
        "c3": "tax1999=2189 tax2000=2200 gold=100 std=0 anon=NullPointerException",
        "c4": "tax1999=2198 tax2000=2200 gold=100 std=0 anon=0",
    },
    "SZZ-0214": {
        "c0": "greet=Hello, ada! farewell=absent profile=absent",
        "c1": "greet=Hello, ada! farewell=absent profile=absent",
        "c2": "greet=Hello, ada! farewell=Goodbye, ada. profile=absent",
        "c3": "greet=Hello, ada! farewell=Goodbye, ada. display=ada displayNull=NullPointerException",
        "c4": "greet=Hello, ada! farewell=Goodbye, ada. display=ada displayNull=",
    },
    "SZZG-0144": {
        "c0": "exp899=false exp900=false exp901=true rem=absent",
        "c1": "exp899=false exp900=false exp901=true rem=absent",
        "c2": "exp899=false exp900=false exp901=true rem=absent",
        "c3": "exp899=false exp900=false exp901=true rem=absent",
        "c4": "exp899=false exp900=false exp901=true rem20=-5 rem600=-585",
        "c5": "exp899=false exp900=false exp901=true rem20=-5 rem600=-585",
        "c6": "exp899=false exp900=false exp901=true rem20=880 rem600=300",
    },
    "SZZ-0215": {
        "c0": "b4=F b5=T b6=T b8=T b9=T p250=2 p199=1",
        "c1": "b4=F b5=F b6=T b8=T b9=T p250=2 p199=1",
        "c2": "b4=F b5=F b6=F b8=F b9=T p250=2 p199=1",
        "c3": "b4=F b5=F b6=F b8=F b9=T p250=50 p199=99",
        "c4": "b4=F b5=F b6=F b8=T b9=T p250=2 p199=1",
    },
    "SZZG-0145": {
        "c0": "cents3=300 cents1250=125000 label=absent",
        "c1": "cents3=300 cents1250=125000 label=absent",
        "c2": "cents3=300 cents1250=125000 label=absent",
        "c3": "cents3=300 cents1250=125000 label3=300 USD label1250=125000 USD",
        "c4": "cents3=300 cents1250=125000 label3=3 USD label1250=1250 USD",
    },
    "SZZG-0146": {
        "c0": "apply=1700 applyBig=1700000 receipt=absent",
        "c1": "apply=1700 applyBig=1700000 receipt=absent",
        "c2": "apply=1700 applyBig=1700000 receipt=absent",
        "c3": "apply=1700 applyBig=1700000 d15=1500 percent off d7=700 percent off",
        "c4": "apply=1700 applyBig=1700000 d15=15 percent off d7=7 percent off",
    },
    "SZZG-0147": {
        "c0": "wait3=6 first=absent",
        "c1": "wait3=6 first=absent",
        "c2": "wait3=6 first=absent",
        "c3": "wait3=6 first=absent",
        "c4": "wait3=6 first=2000",
        "c5": "wait3=6 first=2",
    },
    "SZZ-0216": {
        "c0": "base11=500 base12=1200 base13=1200 group30x3=3600",
        "c1": "base11=500 base12=500 base13=1200 group30x3=3600",
        "c2": "base11=500 base12=500 base13=1200 group30x3=3600",
        "c3": "base11=500 base12=500 base13=1200 group30x3=1203",
        "c4": "base11=500 base12=1200 base13=1200 group30x3=3600",
    },
    "SZZ-0217": {
        "c0": "timeout90s=90 timeout2m=120 timeoutBig=1000000000 retry=absent",
        "c1": "timeout90s=90 timeout2m=120 timeoutBig=1000000000 retry=absent",
        "c2": "timeout90s=90 timeout2m=120 timeoutBig=1000000000 retry=absent",
        "c3": "timeout90s=90 timeout2m=120 timeoutBig=1000000000 retry90s=90000 retry2m=120000 retryBig=1000000000000",
        "c4": "timeout90s=90 timeout2m=120 timeoutBig=1000000000 retry90s=90 retry2m=120 retryBig=1000000000",
    },
}

# deleted line (stripped) -> (plain, -w, -w -C -C) owner, at BFC^
BLAME = {
    "SZZ-0212": {"int base = weightGrams < FREE_UP_TO_GRAMS ? 0 : STANDARD_FEE_CENTS;": ("c2", "c1", "c1"),
                 "return base - surcharge;": ("c3", "c3", "c3")},
    "SZZ-0213": {"/** Rounding step of the 2023 statements; kept until the archive export is retired. */": ("c0", "c0", "c0"),
                 "static final int LEGACY_ROUNDING_CENTS = 5;": ("c0", "c0", "c0"),
                 "": ("c0", "c0", "c0"),
                 "return netCents + (int) ((long) netCents / 100 * TAX_PERCENT);": ("c1", "c1", "c1")},
    "SZZ-0214": {},
    "SZZG-0144": {"return IDLE_TIMEOUT - idleSeconds;": ("c4", "c4", "c4")},
    "SZZ-0215": {"return cents % 100;": ("c3", "c3", "c3"), "return visits > 8;": ("c2", "c2", "c2")},
    "SZZG-0145": {'return rawRate(zone) + " USD";': ("c3", "c3", "c3")},
    "SZZG-0146": {'return Percent.parse(percent) + " percent off";': ("c3", "c3", "c3")},
    "SZZG-0147": {"return BACKOFF;": ("c4", "c4", "c4")},
    "SZZ-0216": {"return age <= 12 ? CHILD_CENTS : ADULT_CENTS;": ("c2", "c2", "c2"),
                 "return basePriceCents(age) + count;": ("c3", "c3", "c3")},
    "SZZ-0217": {"return DurationText.parse(configured);": ("c3", "c3", "c3")},
}

REQUIRED = {"SZZ-0212": {"c1", "c3"}, "SZZ-0213": {"c1", "c3"}, "SZZ-0214": {"c1", "c3"}, "SZZG-0144": {"c2", "c4"},
            "SZZ-0215": {"c1", "c3"}, "SZZG-0145": {"c1", "c3"}, "SZZG-0146": {"c1", "c3"}, "SZZG-0147": {"c3", "c4"},
            "SZZ-0216": {"c1", "c3"}, "SZZ-0217": {"c1", "c3"}}


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
    hashes = {cid: (entry["hash"] if isinstance(entry, dict) else entry) for cid, entry in entries.items()}
    return sid, hashes, out / "repo"


def _bfc(hashes: dict[str, str]) -> str:
    return max(hashes, key=lambda cid: int(cid[1:]))


def _owner(repo: Path, hashes: dict[str, str], full: str) -> str:
    return next(cid for cid, h in hashes.items() if h.startswith(full.lstrip("^")[:40]) or full.lstrip("^").startswith(h[:40]))


def _snapshot(repo: Path, commit: str, into: Path) -> None:
    into.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(["git", "archive", commit], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(into)], input=tar, check=True)


def _run_driver(work: Path, sid: str) -> str:
    (work / "Drive.java").write_text(DRIVERS[sid])
    sources = [str(p) for p in work.rglob("*.java")]
    subprocess.run(["javac", "-d", str(work / "out"), *sources], check=True, capture_output=True)
    return subprocess.run(["java", "-cp", str(work / "out"), "Drive"], cwd=work, capture_output=True, text=True, check=True).stdout.strip()


def test_every_deleted_line_of_the_fix_blames_as_the_readme_says(generated):
    sid, hashes, repo = generated
    bfc = hashes[_bfc(hashes)]
    seen: dict[str, tuple[str, str, str]] = {}
    for path in _git(repo, "diff", "--name-only", f"{bfc}^", bfc).split():
        line_no = None
        for line in _git(repo, "diff", "-U0", f"{bfc}^", bfc, "--", path).splitlines():
            if line.startswith("@@"):
                line_no = int(line.split()[1].lstrip("-").split(",")[0])
            elif line.startswith("-") and not line.startswith("---") and line_no is not None:
                owners = tuple(_owner(repo, hashes, _git(repo, "blame", "-l", *flags, "-L", f"{line_no},{line_no}", f"{bfc}^", "--", path).split()[0])
                               for flags in ((), ("-w",), ("-w", "-C", "-C")))
                seen[line[1:].strip()] = owners
                line_no += 1
            elif line.startswith(" ") and line_no is not None:
                line_no += 1
    assert seen == BLAME[sid]
    plain = {owners[0] for owners in seen.values()}
    assert plain != REQUIRED[sid] and not REQUIRED[sid] <= plain, f"{sid}: plain blame {plain} reaches the whole oracle"


def test_the_two_required_commits_are_not_the_answer_of_any_single_position(generated):
    """Two required commits at different positions: no `position-N`, `position-before-fix` or
    last-toucher rule returns both, and `position-all-non-fix` returns more (there is always c0)."""
    sid, hashes, repo = generated
    order = sorted(hashes, key=lambda cid: int(cid[1:]))
    positions = {order.index(cid) for cid in REQUIRED[sid]}
    assert len(positions) == 2 and 0 not in positions
    assert len(order) - 1 not in positions            # the fix is last


@needs_jdk
def test_the_probe_answers_move_exactly_where_the_readme_says(generated, tmp_path):
    sid, hashes, repo = generated
    observed = {}
    for cid in EXPECTED[sid]:
        work = tmp_path / cid
        _snapshot(repo, hashes[cid], work)
        observed[cid] = _run_driver(work, sid)
    assert observed == EXPECTED[sid], sid


def _edit(work: Path, rel: str, *pairs: tuple[str, str]) -> None:
    p = work / rel
    text = p.read_text()
    for old, new in pairs:
        assert text.count(old) == 1, (rel, old)
        text = text.replace(old, new)
    p.write_text(text)


@needs_jdk
def test_both_commits_are_necessary(generated, tmp_path):
    """Interaction kinds: undoing the unreachable commit on top of the later one gives the fixed
    answers.  Independent kinds: fixing one fault at the last faulty commit leaves the other."""
    sid, hashes, repo = generated
    if sid == "SZZG-0144":
        work = tmp_path / "undo-c2-on-c4"
        _snapshot(repo, hashes["c4"], work)
        _edit(work, "src/main/java/example/SessionPolicy.java",
              ("IDLE_TIMEOUT = 15;", "IDLE_TIMEOUT = 900;"), ("idleSeconds > IDLE_TIMEOUT * 60;", "idleSeconds > IDLE_TIMEOUT;"))
        assert _run_driver(work, sid) == EXPECTED[sid]["c6"]
    elif sid == "SZZ-0214":
        # the check put back on top of c3 is the fix itself; c1 alone moves no probe of the entry points that exist
        assert EXPECTED[sid]["c1"] == EXPECTED[sid]["c0"]
        work = tmp_path / "check-back-on-c3"
        _snapshot(repo, hashes["c3"], work)
        _edit(work, "src/main/java/example/Nickname.java",
              ("        return raw.trim().toLowerCase();", '        if (raw == null) {\n            return "";\n        }\n        return raw.trim().toLowerCase();'))
        assert _run_driver(work, sid) == EXPECTED[sid]["c4"]
    elif sid == "SZZ-0212":
        only_weight = tmp_path / "only-weight"
        _snapshot(repo, hashes["c3"], only_weight)
        _edit(only_weight, "src/main/java/example/ShippingFee.java", ("weightGrams < FREE_UP_TO_GRAMS", "weightGrams <= FREE_UP_TO_GRAMS"))
        assert _run_driver(only_weight, sid) == "1999S=0 1999X=-500 2000S=0 2000X=-500 2001S=300 2001X=-200"
        only_surcharge = tmp_path / "only-surcharge"
        _snapshot(repo, hashes["c3"], only_surcharge)
        _edit(only_surcharge, "src/main/java/example/ShippingFee.java", ("return base - surcharge;", "return base + surcharge;"))
        assert _run_driver(only_surcharge, sid) == EXPECTED[sid]["c1"]
    elif sid == "SZZ-0215":
        only_bonus = tmp_path / "only-bonus"
        _snapshot(repo, hashes["c3"], only_bonus)
        _edit(only_bonus, "src/main/java/example/LoyaltyPoints.java", ("return visits > 8;", "return visits >= 8;"))
        assert _run_driver(only_bonus, sid) == "b4=F b5=F b6=F b8=T b9=T p250=50 p199=99"
        only_points = tmp_path / "only-points"
        _snapshot(repo, hashes["c3"], only_points)
        _edit(only_points, "src/main/java/example/LoyaltyPoints.java", ("return cents % 100;", "return cents / 100;"))
        assert _run_driver(only_points, sid) == "b4=F b5=F b6=F b8=F b9=T p250=2 p199=1"
    elif sid == "SZZG-0145":
        work = tmp_path / "undo-c1-on-c3"
        _snapshot(repo, hashes["c3"], work)
        _edit(work, "src/main/java/example/ZoneRates.java",
              ("return Integer.parseInt(rawRate(zone));", "return Integer.parseInt(rawRate(zone)) * 100;"))
        table = work / "src/main/resources/zone-rates.csv"
        table.write_text("zone,rate_dollars\n" + "".join(f"zone-{i},{i}\n" for i in range(1, 5001)))
        assert _run_driver(work, sid) == EXPECTED[sid]["c4"]
    elif sid == "SZZG-0146":
        work = tmp_path / "undo-c1-on-c3"
        _snapshot(repo, hashes["c3"], work)
        _edit(work, "src/main/java/example/Percent.java", ('.trim()) * 100;', '.trim());'))
        _edit(work, "src/main/java/example/Discount.java", ("/ 10000)", "/ 100)"))
        assert _run_driver(work, sid) == EXPECTED[sid]["c4"]
    elif sid == "SZZG-0147":
        work = tmp_path / "undo-c3-on-c4"
        _snapshot(repo, hashes["c4"], work)
        _edit(work, "src/main/java/example/RetryPolicy.java",
              ("BACKOFF = 2000;", "BACKOFF = 2;"), ("return BACKOFF * attempt / 1000;", "return BACKOFF * attempt;"))
        assert _run_driver(work, sid) == EXPECTED[sid]["c5"]
    elif sid == "SZZ-0216":
        only_fare = tmp_path / "only-fare"
        _snapshot(repo, hashes["c3"], only_fare)
        _edit(only_fare, "src/main/java/example/FareTable.java", ("age <= 12", "age < 12"))
        assert _run_driver(only_fare, sid) == "base11=500 base12=1200 base13=1200 group30x3=1203"
        only_group = tmp_path / "only-group"
        _snapshot(repo, hashes["c3"], only_group)
        _edit(only_group, "src/main/java/example/TicketPricing.java", ("basePriceCents(age) + count;", "basePriceCents(age) * count;"))
        assert _run_driver(only_group, sid) == EXPECTED[sid]["c1"]
    elif sid == "SZZ-0217":
        work = tmp_path / "undo-c1-on-c3"
        _snapshot(repo, hashes["c3"], work)
        _edit(work, "src/main/java/example/DurationText.java",
              ('return (text.endsWith("m") ? value * 60 : value) * 1000;', 'return text.endsWith("m") ? value * 60 : value;'))
        _edit(work, "src/main/java/example/RequestTimeout.java", ("parse(configured) / 1000;", "parse(configured);"))
        assert _run_driver(work, sid) == EXPECTED[sid]["c4"]
    elif sid == "SZZ-0213":
        only_tax = tmp_path / "only-tax"
        _snapshot(repo, hashes["c3"], only_tax)
        _edit(only_tax, "src/main/java/example/InvoiceTotal.java", ("(long) netCents / 100 * TAX_PERCENT", "(long) netCents * TAX_PERCENT / 100"))
        assert _run_driver(only_tax, sid) == "tax1999=2198 tax2000=2200 gold=100 std=0 anon=NullPointerException"
        only_check = tmp_path / "only-check"
        _snapshot(repo, hashes["c3"], only_check)
        _edit(only_check, "src/main/java/example/InvoiceTotal.java",
              ("        return customer.tier()", "        if (customer == null) {\n            return 0;\n        }\n        return customer.tier()"))
        assert _run_driver(only_check, sid) == "tax1999=2189 tax2000=2200 gold=100 std=0 anon=0"


def test_szz_0214_fix_adds_only_and_c1_deletes_only(generated):
    sid, hashes, repo = generated
    if sid != "SZZ-0214":
        pytest.skip("only SZZ-0214 is a ghost on both sides")
    fix = _git(repo, "diff", "-U0", f"{hashes['c4']}^", hashes["c4"]).splitlines()
    assert [l for l in fix if l.startswith("-") and not l.startswith("---")] == []
    assert len([l for l in fix if l.startswith("+") and not l.startswith("+++")]) == 3
    bic = _git(repo, "diff", "-U0", f"{hashes['c1']}^", hashes["c1"]).splitlines()
    assert [l for l in bic if l.startswith("+") and not l.startswith("+++")] == []
    assert len([l for l in bic if l.startswith("-") and not l.startswith("---")]) == 3


def test_szz_0212_reformat_is_whitespace_only(generated):
    sid, hashes, repo = generated
    if sid != "SZZ-0212":
        pytest.skip("only SZZ-0212 has the reformat")
    assert _git(repo, "diff", "-w", hashes["c1"], hashes["c2"]).strip() == ""
    assert _git(repo, "diff", "--stat", hashes["c1"], hashes["c2"]).strip() != ""


def test_szzg_0144_issue_documents_and_message_evidence(generated):
    sid, hashes, repo = generated
    if sid != "SZZG-0144":
        pytest.skip("only SZZG-0144 has issue documents")
    for issue in ("ISSUE-12", "ISSUE-19", "ISSUE-23"):
        assert f"# {issue}:" in _git(repo, "show", f"{hashes['c6']}:docs/issues/{issue}.md")
    fix_message = _git(repo, "log", "-1", "--format=%s", hashes["c6"])
    assert "ISSUE-12" in fix_message and "ISSUE-23" in fix_message
    mentioning = {cid for cid in hashes if "ISSUE-12" in _git(repo, "log", "-1", "--format=%s", hashes[cid])}
    assert mentioning == {"c1", "c2", "c6"}
    touching = {cid for cid in mentioning if "src/main/java/example/SessionPolicy.java" in _git(repo, "show", "--name-only", "--format=", hashes[cid])}
    assert touching == {"c2", "c6"}


def _changed_lines(repo: Path, commit: str) -> tuple[set[str], set[str]]:
    diff = _git(repo, "show", "--format=", "-U0", commit).splitlines()
    removed = {l[1:] for l in diff if l.startswith("-") and not l.startswith("---")}
    added = {l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")}
    return removed, added


def test_szzg_0147_reverts_are_real_and_the_second_restores_the_first_change(generated):
    sid, hashes, repo = generated
    if sid != "SZZG-0147":
        pytest.skip("only SZZG-0147 has the revert pair")
    c1_removed, c1_added = _changed_lines(repo, hashes["c1"])
    c2_removed, c2_added = _changed_lines(repo, hashes["c2"])
    c3_removed, c3_added = _changed_lines(repo, hashes["c3"])
    assert (c2_removed, c2_added) == (c1_added, c1_removed)            # c2 is the inverse of c1
    assert (c3_removed, c3_added) == (c1_removed, c1_added)            # c3 is c1 again
    subjects = {cid: _git(repo, "log", "-1", "--format=%s", hashes[cid]).strip() for cid in ("c1", "c2", "c3")}
    assert subjects["c2"] == f'Revert "{subjects["c1"]}"' and subjects["c3"] == f'Revert "{subjects["c2"]}"'
    assert _git(repo, "log", "--first-parent", "--format=%h").count("\n") + 1 == 6 or len(_git(repo, "log", "--first-parent", "--format=%h").split()) == 6


def test_szzg_0145_unit_change_rewrites_every_line_of_the_table(generated):
    sid, hashes, repo = generated
    if sid != "SZZG-0145":
        pytest.skip("only SZZG-0145 has the generated table")
    stat = _git(repo, "show", "--numstat", "--format=", hashes["c1"]).split("\n")
    rows = {line.split("\t")[2]: (int(line.split("\t")[0]), int(line.split("\t")[1])) for line in stat if line}
    assert rows["src/main/resources/zone-rates.csv"] == (5001, 5001)
    assert rows["src/main/java/example/ZoneRates.java"] == (1, 1)
    fix_files = _git(repo, "diff", "--name-only", f"{hashes['c4']}^", hashes["c4"]).split()
    assert fix_files == ["src/main/java/example/ZoneRates.java"]


def test_szzg_0146_default_variant_is_the_strict_one():
    from szzbench.evaluator import _commit_level_policy, _load_scenario_for_evaluation
    scenario, notes = _load_scenario_for_evaluation(ROOT / "advanced-scenarios" / "SZZG-0146" / "scenario.graph.yml", "advanced-scenarios")
    assert scenario is not None, notes
    default = _commit_level_policy(scenario, "advanced-scenarios", None)
    assert (default.evaluation_variant, default.evaluation_policy, set(default.required)) == ("full-cause", "exact_set", {"c1", "c3"})
    lenient = _commit_level_policy(scenario, "advanced-scenarios", "observable-only")
    assert (lenient.evaluation_variant, lenient.evaluation_policy, set(lenient.required)) == ("observable-only", "relaxed_with_related", {"c3"})
    assert set(lenient.related_origins) == {"c1"}


def test_szz_0216_the_move_is_reached_only_by_a_lower_copy_score_or_by_following_the_file(generated):
    sid, hashes, repo = generated
    if sid != "SZZ-0216":
        pytest.skip("only SZZ-0216 moves the method")
    path = "src/main/java/example/FareTable.java"
    parent = f"{hashes['c4']}^"
    lines = _git(repo, "show", f"{parent}:{path}").split("\n")
    number = next(i for i, l in enumerate(lines, 1) if "age <= 12" in l)
    def owner(*flags):
        return _owner(repo, hashes, _git(repo, "blame", "-l", *flags, "-L", f"{number},{number}", parent, "--", path).split()[0])
    assert (owner(), owner("-w"), owner("-M"), owner("-C"), owner("-C", "-C")) == ("c2", "c2", "c2", "c2", "c2")
    assert owner("-C10") == "c1"
    followed = _git(repo, "log", "--follow", "--format=%H", parent, "--", path).split()
    assert [ _owner(repo, hashes, h) for h in followed ] == ["c2", "c1", "c0"]
    assert _git(repo, "diff", "-w", hashes["c1"], hashes["c2"], "--", "src/main/java/example/TicketPricing.java").strip() != ""


def test_szz_0217_fix_message_quotes_the_callee_change(generated):
    sid, hashes, repo = generated
    if sid != "SZZ-0217":
        pytest.skip("only SZZ-0217 quotes a subject")
    subject_c1 = _git(repo, "log", "-1", "--format=%s", hashes["c1"]).strip()
    fix_message = _git(repo, "log", "-1", "--format=%s", hashes["c4"])
    assert f'"{subject_c1}"' in fix_message
    matching = _git(repo, "log", "--all", f"--grep={subject_c1}", "--fixed-strings", "--format=%H").split()
    assert {_owner(repo, hashes, h) for h in matching} == {"c1", "c4"}
