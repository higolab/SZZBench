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
    "SZZG-0069": ("wrong-constant", 'example.Backoff b = new example.Backoff(); System.out.print(b.delayMillis(0) + " " + b.delayMillis(10));',
                  {"c0": "100 30000", "f1": "10 3000", "r1": "10 10240", "r2": "10 3000", "c3": "100 30000"}),
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
}

#: SZZG-0081's reformatting commit owns the faulty line under plain blame by design (GW703);
#: `git blame -w` is what reaches the BIC there.
BLAME_NEEDS_W = {"SZZG-0081"}


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


@pytest.mark.parametrize("sid", sorted(REWRITES))
def test_fix_deletes_a_line_that_blames_to_the_declared_bic(tmp_path, sid):
    scenario, cmap, repo = _generate(tmp_path, sid)
    by_hash = {e["hash"]: c for c, e in cmap.items()}
    bug = scenario["bugs"][0]
    required = set(scenario["expected_szz"]["commit_level"]["required"])
    for fix in bug["bug_fixing_commits"]:
        bfc = cmap[fix["commit"]]["hash"]
        diff = _git(repo, "diff", "-U0", f"{bfc}^", bfc)
        deleted = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
        assert len(deleted) == 1, (sid, fix["commit"], deleted)
        path = next(l[6:] for l in diff.splitlines() if l.startswith("--- a/"))
        start = next(l for l in diff.splitlines() if l.startswith("@@")).split()[1][1:].split(",")[0]
        options = ["-w"] if sid in BLAME_NEEDS_W else []
        blamed = _git(repo, "blame", "-l", "-s", *options, "-L", f"{start},{start}", f"{bfc}^", "--", path).split()[0].lstrip("^")
        assert by_hash[blamed] in required, (sid, fix["commit"], by_hash[blamed], required)
        if sid in BLAME_NEEDS_W:
            plain = _git(repo, "blame", "-l", "-s", "-L", f"{start},{start}", f"{bfc}^", "--", path).split()[0].lstrip("^")
            assert by_hash[plain] not in required, (sid, "plain blame was expected to stop at the reformatting commit")


@NEEDS_JDK
@pytest.mark.parametrize("sid", sorted(REWRITES))
def test_fault_is_observed_exactly_where_the_readme_says(tmp_path, sid):
    _, driver_body, expected = REWRITES[sid]
    _, cmap, repo = _generate(tmp_path, sid)
    assert set(expected) == set(cmap), (sid, sorted(cmap))
    driver = f"public class Driver {{ public static void main(String[] a) {{ {driver_body} }} }}"
    for cid, want in expected.items():
        work = tmp_path / f"run-{sid}-{cid}"
        work.mkdir()
        tar = subprocess.run(["git", "archive", cmap[cid]["hash"]], cwd=repo, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
        (work / "Driver.java").write_text(driver)
        subprocess.run(["javac", "-d", str(work / "out"), *[str(p) for p in work.rglob("*.java")]], check=True, capture_output=True)
        out = subprocess.run(["java", "-cp", str(work / "out"), "Driver"], capture_output=True, text=True, check=True).stdout
        assert out == want, (sid, cid, out)
