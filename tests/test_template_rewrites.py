"""Issue #13: scenarios rewritten away from the `Range.contains` template.

A rewrite changes the code, not what the scenario tests, so these tests pin
three things for every rewritten scenario: the fault is observed exactly at the
commits the README says (Java, skipped without a JDK); the line the fix deletes
blames to the declared BIC; and the Range template is gone while the declared
fault kind is present in `meta.factors`.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from szzbench.graph_generator import generate_graph_repository  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "advanced-scenarios"
NEEDS_JDK = pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")

# scenario -> (fault kind factor, driver body, {commit: expected stdout})
REWRITES: dict[str, tuple[str, str, dict[str, str]]] = {
    "SZZG-0045": ("string-comparison",
                  'System.out.print(new example.RoleCheck().isAdmin(new String("admin")) + " " + new example.RoleCheck().isAdmin("admin"));',
                  {"c0": "true true", "c1": "true true", "c2": "true true", "c3": "false true", "c4": "true true"}),
    "SZZG-0047": ("exception-swallowed",
                  'example.PortParser p = new example.PortParser(); try { System.out.print(p.parse("http")); } catch (RuntimeException e) { System.out.print(e.getClass().getSimpleName()); }',
                  {"c0": "NumberFormatException", "c1": "0", "c2": "0", "c3": "0", "c4": "IllegalArgumentException"}),
    "SZZG-0049": ("off-by-one",
                  'example.Pager p = new example.Pager(); System.out.print(p.pageCount(20, 10) + " " + p.pageCount(21, 10));',
                  {"c0": "2 3", "c1": "3 3", "r1": "3 3", "c2": "2 3", "r2": "2 3"}),
    "SZZG-0050": ("null-check-omission",
                  'example.Greeting g = new example.Greeting(); try { System.out.print(g.forName(null)); } catch (RuntimeException e) { System.out.print(e.getClass().getSimpleName()); }',
                  {"c0": "Hello, guest!", "c1": "NullPointerException", "r0": "NullPointerException", "c2": "Hello, guest!",
                   "c3": "Hello, guest!", "r1": "NullPointerException", "r2": "Hello, guest!"}),
    "SZZG-0051": ("wrong-constant", 'System.out.print(new example.Retention().days());',
                  {"c0": "30", "c1": "30", "r1": "3", "r2": "30"}),
    "SZZG-0053": ("boolean-negation",
                  'example.Gate g = new example.Gate(); System.out.print(g.canServe(false, false) + " " + g.canServe(true, false));',
                  {"c0": "true false", "c1": "true false", "c2": "false true", "c3": "true false", "c4": "true false"}),
    "SZZG-0054": ("wrong-variable", 'System.out.print(new example.Totals().grand(100, 20, 15));',
                  {"c0": "135", "c1": "140", "c2": "140", "c3": "135", "c4": "140"}),
    "SZZG-0056": ("integer-overflow", 'System.out.print(new example.Bytes().toBits(1 << 28));',
                  {"c0": "2147483648", "c1": "-2147483648", "rel1": "-2147483648", "c2": "2147483648", "r2": "2147483648"}),
    # --- G5 ---
    "SZZG-0069": ("wrong-constant",
                  'example.Backoff b = new example.Backoff(); for (int n : new int[] {0, 10, 25, 31, 32}) System.out.print(b.delayMillis(n) + " ");',
                  # attempts 25, 31 and 32 saturate at the cap in every snapshot (PR #61 review: the first version overflowed)
                  {"c0": "100 30000 30000 30000 30000 ", "f1": "10 3000 3000 3000 3000 ", "r1": "10 10240 30000 30000 30000 ",
                   "r2": "10 3000 3000 3000 3000 ", "c3": "100 30000 30000 30000 30000 "}),
    "SZZG-0070": ("off-by-one", 'System.out.print(new example.Pagination().lastIndex(1, 10));',
                  {"c0": "9", "f1": "19", "f2": "20", "r1": "20", "c2": "9"}),
    "SZZG-0073": ("api-misuse", 'System.out.print(new example.InvoiceDates().dueMonth(java.time.LocalDate.of(2024, 3, 15)));',
                  {"c0": "3", "f1": "2", "f2": "2", "r1": "3", "r2": "2", "c3": "3"}),
    "SZZG-0076": ("integer-overflow", 'example.Elapsed e = new example.Elapsed(); System.out.print(e.minutesBetween(0, 120000) + " " + e.minutesBetween(0, 3000000000L));',
                  {"c0": "2 50000", "f1": "2 -21582", "f2": "7200000000 -77698037760000", "r1": "2 -21582", "r2": "7200000000 -77698037760000", "c3": "2 50000"}),
    "SZZG-0081": ("null-check-omission", 'try { System.out.print("[" + new example.Label().text(null) + "]"); } catch (RuntimeException e) { System.out.print(e.getClass().getSimpleName()); }',
                  {"c0": "[]", "f1": "NullPointerException", "r1": "NullPointerException", "r2": "NullPointerException", "c3": "[]"}),
    "SZZG-0082": ("boolean-negation", 'example.FeatureGate g = new example.FeatureGate(); System.out.print(g.isEnabled(true, false) + " " + g.isEnabled(true, true));',
                  {"c0": "true false", "f1": "false true", "r1": "false true", "r2": "false true", "c3": "true false"}),
    "SZZG-0083": ("wrong-variable", 'example.StatusText s = new example.StatusText(); System.out.print(s.describe("OK", "Unknown") + " " + s.describe(null, "Unknown"));',
                  {"c0": "OK Unknown", "f1": "Unknown null", "r1": "Unknown null", "c2": "OK Unknown"}),
    # --- G2 ---
    "SZZG-0016": ("null-check-omission",
                  'for (String n : new String[] {"example.TagNormalizer", "example.LabelNormalizer"}) { try { Class<?> c = Class.forName(n); '
                  'try { System.out.print("[" + c.getMethod("normalize", String.class).invoke(c.getDeclaredConstructor().newInstance(), (Object) null) + "]"); } '
                  'catch (java.lang.reflect.InvocationTargetException e) { System.out.print(e.getCause().getClass().getSimpleName()); } } '
                  'catch (ClassNotFoundException e) { System.out.print("absent"); } System.out.print(" "); }',
                  {"c0": "NullPointerException absent ", "c1": "NullPointerException NullPointerException ", "c2": "[] [] "}),
    "SZZG-0017": ("off-by-one",
                  'try { Class<?> c = Class.forName("example.Selection"); Object o = c.getDeclaredConstructor().newInstance(); '
                  'for (java.lang.reflect.Method m : c.getDeclaredMethods()) System.out.print(m.getName() + "=" + m.invoke(o, 10)); } '
                  'catch (ClassNotFoundException e) { System.out.print("absent"); }',
                  {"c0": "absent", "c1": "lastPosition=10", "c2": "endPosition=10", "c3": "endPosition=9"}),
    "SZZG-0019": ("wrong-constant",
                  'try { Class<?> c = Class.forName("generated.GeneratedLimits"); System.out.print(c.getMethod("maxRetries").invoke(c.getDeclaredConstructor().newInstance())); } '
                  'catch (ClassNotFoundException e) { System.out.print("absent"); }',
                  {"c0": "absent", "c1": "30", "c2": "3"}),
    "SZZG-0021": ("boolean-negation",
                  'try { Class<?> c = Class.forName("example.AccessCopy"); Object o = c.getDeclaredConstructor().newInstance(); java.lang.reflect.Method m = c.getMethod("canView", boolean.class, boolean.class); '
                  'System.out.print(m.invoke(o, true, false) + " " + m.invoke(o, false, false)); } catch (ClassNotFoundException e) { System.out.print("absent"); }',
                  {"c0": "absent", "c1": "false true", "c2": "absent"}),
    "SZZG-0024": ("wrong-operator",
                  'System.out.print(new example.Rate().percentOf(30000000, 100) + " "); '
                  'try { Class<?> c = Class.forName("example.RateClone"); java.lang.reflect.Method m = c.getMethod("percentOfClone", int.class, int.class); Object o = c.getDeclaredConstructor().newInstance(); '
                  'System.out.print(m.invoke(o, 199, 10) + " " + m.invoke(o, 30000000, 100)); } catch (ClassNotFoundException e) { System.out.print("absent"); }',
                  # the large input (PR #62 review) must not overflow in the original or in the fixed clone
                  {"c0": "30000000 absent", "f1": "30000000 10 30000000", "f2": "30000000 10 30000000", "r1": "30000000 10 30000000",
                   "r2": "30000000 10 30000000", "c4": "30000000 19 30000000"}),
    # --- G1, G8, G6, G3 ---
    "SZZG-0005": ("wrong-variable",
                  'for (String n : new String[] {"example.Shipping", "example.ShippingUtils"}) { try { Class<?> c = Class.forName(n); Object o = c.getDeclaredConstructor().newInstance(); '
                  'for (java.lang.reflect.Method m : c.getDeclaredMethods()) if (m.getName().equals("cost")) System.out.print(n.substring(8) + "=" + m.invoke(o, 500, 10, 8) + "/" + m.invoke(o, 30000, 100000, 8) + " "); } catch (ClassNotFoundException e) { } }',
                  # the second call (PR #63 review) would overflow an int product; the result must be 3000000 in every snapshot
                  {"c0": "Shipping=8/3000000 ", "c1": "Shipping=10/3000000 ", "c2": "ShippingUtils=10/3000000 ", "c3": "ShippingUtils=8/3000000 "}),
    "SZZG-0006": ("exception-swallowed",
                  'try { System.out.print(new example.OrderService().describeParsed("SKU-1", "x")); } catch (RuntimeException e) { System.out.print(e.getClass().getSimpleName()); }',
                  {"c0": "NumberFormatException", "c1": "SKU-1 x 0", "c2": "SKU-1 x 0", "c3": "IllegalArgumentException"}),
    "SZZG-0007": ("off-by-one",
                  'for (String n : new String[] {"example.Paging", "example.PagingUtils", "example.Batches"}) { try { Class<?> c = Class.forName(n); Object o = c.getDeclaredConstructor().newInstance(); '
                  'for (java.lang.reflect.Method m : c.getDeclaredMethods()) if (m.getName().endsWith("Count")) System.out.print(m.getName() + "=" + m.invoke(o, 20, 10) + "/" + m.invoke(o, Integer.MAX_VALUE, 100) + " "); } catch (ClassNotFoundException e) { } }',
                  # Integer.MAX_VALUE items (PR #63 review): the fixed ceiling division must not overflow
                  {"c1": "pageCount=3/21474837 ", "c2": "pageCount=3/21474837 batchCount=3/21474837 ", "c3": "pageCount=2/21474837 batchCount=2/21474837 "}),
    "SZZG-0107": ("boolean-negation",
                  'example.Retention r = new example.Retention(); System.out.print(r.shouldKeep(false, false) + " " + r.shouldKeep(false, true));',
                  {"c0": "true false", "c1": "false true", "c2": "true false"}),
    "SZZG-0108": ("wrong-constant", 'System.out.print(new example.Thumbnails().maxEdgePixels());',
                  {"c0": "256", "c1": "51", "c2": "512"}),
    "SZZG-0088": ("wrong-variable",
                  'example.Greeting g = new example.Greeting(); System.out.print(g.greet("Ada", true)); try { System.out.print(" " + g.greet(null, true)); } catch (RuntimeException e) { System.out.print(" " + e.getClass().getSimpleName()); }',
                  {"c0": "Dear Ada Dear guest", "c1": "Hi Ada NullPointerException", "c2": "Dear Ada Dear guest", "c3": "Hi Ada Hi guest", "c4": "Dear Ada Dear guest"}),
    "SZZG-0091": ("wrong-operator", 'System.out.print(new example.InvoiceSummary().summarize(100, 30, false));',
                  {"c0": "OPEN 70", "c1": "PAID 70", "c2": "PAID 130", "c3": "OPEN 70", "c4": "OPEN 130", "c5": "OPEN 70"}),
    "SZZG-0035": ("wrong-constant", 'example.Fees f = new example.Fees(); System.out.print(f.cardFee(1000) + " " + f.transferFee(1000) + " " + f.cardFee(1000000000));',
                  # 1e9 cents (PR #63 review): the 3 % fee must be 30000000, not an int overflow
                  {"c0": "30 30 30000000", "c1": "300 300 300000000", "c2": "30 300 30000000", "c3": "30 30 30000000"}),
}

#: SZZG-0081's reformatting commit owns the faulty line under plain blame by design (GW703);
#: `git blame -w` is what reaches the BIC there.
BLAME_NEEDS_W = {"SZZG-0081"}

#: Where plain blame of the fix's deleted lines is *designed* not to be exactly the required set,
#: the README says what it returns instead; these tests pin that statement.
#: SZZG-0016: the fix deletes one line per file; the copy blames to c1 (required), the original to c0 (origin).
#: SZZG-0021: the fix deletes the whole faulty file; all eight lines blame to c1.
#: SZZG-0024: the annotation commit r2 is the last touch of the line, so plain blame returns it (GW703 by design).
#: SZZG-0005/0006/0007: the fixed line lives in a file the move/extract commit c2 created, so plain blame returns c2
#: (required only in 0007, where c2 is also the BIC of the duplicated instance).
#: SZZG-0035: each fix deletes a `return fee(cents);` call written by the root commit c0, not the faulty helper line.
PLAIN_BLAME = {"SZZG-0016": {"c1", "c0"}, "SZZG-0021": {"c1"}, "SZZG-0024": {"r2"},
               "SZZG-0005": {"c2"}, "SZZG-0006": {"c2"}, "SZZG-0007": {"c2"}, "SZZG-0035": {"c0"}}


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


def _generate(tmp_path: Path, sid: str) -> tuple[dict, dict, Path]:
    path = GRAPH / sid / "scenario.graph.yml"
    commit_map, verify = generate_graph_repository(path, tmp_path / sid, force=True)
    assert not verify.has_errors(), verify.to_dict()
    return yaml.safe_load(path.read_text(encoding="utf-8")), commit_map, tmp_path / sid / "repo"


@pytest.mark.parametrize("sid", sorted(REWRITES))
def test_rewritten_scenario_left_the_range_template(sid):
    kind, _, _ = REWRITES[sid]
    scenario = yaml.safe_load((GRAPH / sid / "scenario.graph.yml").read_text(encoding="utf-8"))
    code = "\n".join(str(op.get(key, "")) for c in scenario["commits"] for op in (c.get("operations") or [])
                     for key in ("path", "content", "old", "new"))
    assert "Range" not in code and "value > min" not in code, f"{sid} still writes the Range template"
    statements = [f.get("statement", "") for b in scenario["bugs"] for f in (b.get("faults") or []) + (b.get("origin_faults") or [])]
    assert not any("value > min" in st for st in statements), f"{sid} still declares the Range fault"
    assert kind in scenario["meta"]["factors"], f"{sid} does not declare its fault kind {kind}"


def _deleted_lines(repo: Path, bfc: str) -> list[tuple[str, int]]:
    """(path, line number at BFC^) of every line the fix's first-parent diff deletes."""
    deleted: list[tuple[str, int]] = []
    path = None
    for line in _git(repo, "diff", "-U0", f"{bfc}^", bfc).splitlines():
        if line.startswith("--- a/"):
            path = line[6:]
        elif line.startswith("--- /dev/null"):
            path = None
        elif line.startswith("@@") and path is not None:
            old = line.split()[1][1:]
            start, _, count = old.partition(",")
            deleted.extend((path, int(start) + i) for i in range(int(count) if count else 1))
    return deleted


@pytest.mark.parametrize("sid", sorted(REWRITES))
def test_fix_deletes_lines_that_blame_as_the_readme_says(tmp_path, sid):
    scenario, cmap, repo = _generate(tmp_path, sid)
    by_hash = {e["hash"]: c for c, e in cmap.items()}
    required = set(scenario["expected_szz"]["commit_level"]["required"])
    for fix in scenario["bugs"][0]["bug_fixing_commits"]:
        bfc = cmap[fix["commit"]]["hash"]
        deleted = _deleted_lines(repo, bfc)
        assert deleted, (sid, fix["commit"], "the fix deletes nothing")
        def owner(token: str) -> str:
            # a root commit is printed as ^ plus 39 hash characters
            return next(c for h, c in by_hash.items() if h.startswith(token.lstrip("^")))

        def blame(*options: str) -> set[str]:
            return {owner(_git(repo, "blame", "-l", "-s", *options, "-L", f"{n},{n}", f"{bfc}^", "--", path).split()[0])
                    for path, n in deleted}
        plain = blame()
        if sid in PLAIN_BLAME:
            assert plain == PLAIN_BLAME[sid], (sid, fix["commit"], plain)
        elif sid in BLAME_NEEDS_W:
            assert not plain & required and blame("-w") <= required, (sid, fix["commit"], plain, blame("-w"))
        else:
            assert len(deleted) == 1 and plain <= required, (sid, fix["commit"], deleted, plain, required)


@NEEDS_JDK
@pytest.mark.parametrize("sid", sorted(REWRITES))
def test_fault_is_observed_exactly_where_the_readme_says(tmp_path, sid):
    _, driver_body, expected = REWRITES[sid]
    _, cmap, repo = _generate(tmp_path, sid)
    assert set(expected) == set(cmap), (sid, sorted(cmap))
    driver = f"public class Driver {{ public static void main(String[] a) throws Exception {{ {driver_body} }} }}"
    for cid, want in expected.items():
        work = tmp_path / f"run-{sid}-{cid}"
        work.mkdir()
        tar = subprocess.run(["git", "archive", cmap[cid]["hash"]], cwd=repo, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
        (work / "Driver.java").write_text(driver)
        subprocess.run(["javac", "-d", str(work / "out"), *[str(p) for p in work.rglob("*.java")]], check=True, capture_output=True)
        out = subprocess.run(["java", "-cp", str(work / "out"), "Driver"], capture_output=True, text=True, check=True).stdout
        assert out == want, (sid, cid, out)


# --- the oracle must survive the rewrite ------------------------------------------

#: main as it stood before the first #13 rewrite (the merge of PR #58); every rewritten scenario's
#: scoring-relevant oracle must be identical to what it declared there.
PRE_REWRITE_COMMIT = "b3369e8"

SCORING_KEYS = ("evaluation_policy", "required", "related_origins", "related_but_not_correct", "relevant",
                "k_values", "status_k", "minimum_required", "expect_no_bic", "known_distractors")


def _scoring_view(scenario: dict) -> dict:
    """Everything the evaluator reads, and nothing it does not (no notes, descriptions or statements)."""
    from szzbench.graph_scenario import normalize_bic_role

    def level(cl: dict) -> dict:
        view = {k: cl.get(k) for k in SCORING_KEYS if cl.get(k) is not None}
        if cl.get("acceptable_related"):
            view["acceptable_related"] = [
                (e.get("commit"), e.get("credit")) if isinstance(e, dict) else (e, None) for e in cl["acceptable_related"]]
        return view

    expected = scenario.get("expected_szz") or {}
    return {
        "commit_level": level(expected.get("commit_level") or {}),
        "variants": {v["name"]: level(v.get("commit_level") or {}) for v in expected.get("evaluation_variants") or []},
        "default_variant": expected.get("default_variant"),
        "bugs": [{"bics": sorted((e["commit"], normalize_bic_role(e.get("role"))) for e in b.get("bug_introducing_commits") or []),
                  "bfcs": sorted(e["commit"] for e in b.get("bug_fixing_commits") or [])} for b in scenario.get("bugs") or []],
    }


def _pre_rewrite(sid: str) -> dict | None:
    result = subprocess.run(["git", "show", f"{PRE_REWRITE_COMMIT}:advanced-scenarios/{sid}/scenario.graph.yml"],
                            cwd=ROOT, text=True, capture_output=True)
    return yaml.safe_load(result.stdout) if result.returncode == 0 else None


@pytest.mark.parametrize("sid", sorted(REWRITES))
def test_the_oracle_is_exactly_what_it_was_before_the_rewrite(sid):
    """PR #63 review: SZZG-0091's rewrite had moved the origin from c2 to c1, which changed the
    origin-aware variant's verdicts. A rewrite changes code, never what is scored (fault-library.md §3)."""
    before = _pre_rewrite(sid)
    if before is None:
        pytest.skip(f"{PRE_REWRITE_COMMIT} is not available in this clone")
    after = yaml.safe_load((GRAPH / sid / "scenario.graph.yml").read_text(encoding="utf-8"))
    assert _scoring_view(after) == _scoring_view(before)


def test_szzg_0091_origin_aware_variant_scores_as_before(tmp_path):
    """The verdicts the review measured: {c4, c2} passes and {c4, c1} fails under origin-aware."""
    from szzbench.evaluator import Prediction, evaluate_scenario

    scenario, cmap, _ = _generate(tmp_path, "SZZG-0091")

    def verdict(answer: list[str], variant: str | None) -> str:
        predictions = [Prediction(scenario_id="SZZG-0091", inducing_commit=c) for c in answer]
        return evaluate_scenario("SZZG-0091", scenario, GRAPH / "SZZG-0091" / "scenario.graph.yml", "advanced-scenarios",
                                 cmap, predictions, evaluation_variant=variant).status

    assert verdict(["c4", "c2"], "origin-aware") == "PASS"
    assert verdict(["c4", "c1"], "origin-aware") == "FAIL"
    assert verdict(["c4"], None) == "PASS" and verdict(["c4", "c2"], None) == "FAIL"

