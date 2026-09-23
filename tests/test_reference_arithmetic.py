"""What a scenario calls correct must be correct across the inputs it admits (issue #82).

Four PR reviews in a row found the same defect: an expression the scenario
presents as the *reference* or the *fix* overflows Java ``int`` for an input
inside the declared type range, so the scenario's own premise is false there and
the faulty expression is the accurate one.  A README's behaviour table, a
counterfactual and the claim that the BFC is a fix all rest on that premise.

Each row below states a scenario's **supported domain** and the exact answer at
the top of it, evaluated against the bug-fixing snapshot of the generated
repository.  Writing the bound down is the point: a scenario either computes
correctly for every input its types admit, or it says where it stops, and either
way the boundary is measured rather than assumed.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402

needs_jdk = pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")

#: scenario -> (why the domain stops there, [(class, method, arguments at the top of it, expected answer)])
#:
#: A scenario's bound must clear **every** method that consumes the bounded quantity, not just the
#: one whose expression the grep flagged: SZZG-0139's base price fits int for one night longer than
#: the booking with its weekend surcharge does (PR #83 review).
CASES = {
    # repaired on 2026-09-23: the product is taken in 64 bits, so the whole int range is supported
    "SZZ-0093": ("any int order total: the discount is taken in 64 bits",
                 [("com.example.pricing.DiscountCalculator", "discountCents", [2147483647], 214748364)]),
    "SZZ-0213": ("a net whose taxed total still fits int, which bounds the input whatever the intermediate width",
                 [("example.InvoiceTotal", "withTaxCents", [1000000000], 1100000000)]),
    "SZZG-0138": ("any int amount and any percentage 0..100",
                  [("example.pricing.Discounts", "percentOf", [1000000000, 20], 200000000)]),
    "SZZG-0141": ("any int amount and any percentage 0..100",
                  [("example.invoice.InvoiceLine", "discountedCents", [1000000000, 20], 800000000)]),
    # left in int: the scenario probes its own overflow on purpose, so the domain is written down instead
    "SZZ-0100": ("a setting whose millisecond value fits int, from -2147483 upward; the probes beyond it "
                 "pin what the shared overflow does rather than claiming it is right",
                 [("com.example.config.TimeoutSetting", "timeoutMillis", ["-2147483"], -2147483000),
                  ("com.example.config.TimeoutSetting", "timeoutMillis", ["2147483"], 60000),
                  ("com.example.config.TimeoutSetting", "timeoutMillis", ["60"], 60000)]),
    # not repaired: the product leaves the int range only outside the domain the scenario describes
    "SZZG-0005": ("a parcel of at most 1000 cm a side, and a shipping cost that still fits int",
                  [("example.Shipping", "volumetricWeight", [1000, 1000, 1000], 200000000),
                   ("example.ShippingUtils", "cost", [200000000, 10, 0], 2000000)]),
    "SZZG-0007": ("a page index times a page size that still fits int",
                  [("example.Paging", "offset", [1000000, 1000], 1000000000)]),
    "SZZG-0070": ("a page index times a page size that still fits int",
                  [("example.Pagination", "lastIndex", [1000000, 1000], 999999999)]),
    "SZZG-0136": ("a late fee that still fits int: 2 000 000 chargeable days at 1000 cents",
                  [("example.billing.LateFee", "feeCents", [2000000, 0, 1000], 2000000000)]),
    "SZZG-0137": ("a late fee that still fits int: 2 000 000 chargeable days at 1000 cents",
                  [("example.billing.LateFee", "feeCents", [2000000, 0, 1000], 2000000000)]),
    "SZZG-0139": ("195 225 nights: the weekend surcharge adds a tenth, so the complete booking leaves the "
                  "int range one night before the base price alone does",
                  [("example.booking.Pricing", "basePrice", [195225], 1952250000),
                   ("example.booking.Surcharge", "weekend", [1952250000], 2147475000)]),
    "SZZG-0147": ("a million attempts at a 2000 ms backoff, the most that fits int",
                  [("example.RetryPolicy", "waitSeconds", [1000000], 2000000)]),
}

DRIVER = """
import java.lang.reflect.*;
public class Drive {
    public static void main(String[] a) throws Exception {
        Class<?> c = Class.forName(%(cls)s);
        Object inst = c.getDeclaredConstructor().newInstance();
        for (Method m : c.getDeclaredMethods()) {
            if (!m.getName().equals(%(method)s)) continue;
            Class<?>[] ps = m.getParameterTypes();
            Object[] args = new Object[] { %(args)s };
            if (ps.length != args.length) continue;
            System.out.print(m.invoke(inst, args));
            return;
        }
        throw new IllegalStateException("method not found");
    }
}
"""


def _java_args(values) -> str:
    out = []
    for v in values:
        out.append(json.dumps(v) if isinstance(v, str) else f"Integer.valueOf({v})")
    return ", ".join(out)


@pytest.fixture(scope="module", params=sorted(CASES), ids=sorted(CASES))
def fixed_snapshot(request, tmp_path_factory):
    sid = request.param
    out = tmp_path_factory.mktemp(sid.lower()) / sid
    if sid.startswith("SZZG-"):
        commit_map, verify = generate_graph_repository(ROOT / "advanced-scenarios" / sid / "scenario.graph.yml", out, force=True)
    else:
        commit_map, verify = generate_repository(ROOT / "scenarios" / sid / "scenario.yml", out, force=True)
    assert verify is not None and not verify.has_errors(), verify.to_dict()
    return sid, out / "repo"


@needs_jdk
def test_the_fixed_snapshot_is_exact_at_the_top_of_its_domain(fixed_snapshot, tmp_path):
    sid, repo = fixed_snapshot
    domain, probes = CASES[sid]
    work = tmp_path / sid
    work.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(["git", "archive", "HEAD"], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(work)], input=tar, check=True)
    wrong = []
    for cls, method, args, expected in probes:
        (work / "Drive.java").write_text(DRIVER % {"cls": json.dumps(cls), "method": json.dumps(method),
                                                   "args": _java_args(args)})
        sources = [str(p) for p in work.rglob("*.java")]
        subprocess.run(["javac", "-nowarn", "-d", str(work / "out"), *sources], check=True, capture_output=True)
        answer = subprocess.run(["java", "-cp", str(work / "out"), "Drive"], cwd=work,
                                capture_output=True, text=True, check=True).stdout.strip()
        if answer != str(expected):
            wrong.append(f"{cls}.{method}{tuple(args)} answered {answer}, not {expected}")
    assert wrong == [], textwrap.fill(
        f"{sid}: " + "; ".join(wrong) + f". The supported domain is {domain}; an answer that differs "
        f"here means the expression the scenario calls correct overflows inside it (issue #82).", 100)


def test_every_audited_scenario_is_still_in_the_suite():
    """The table is a list of scenarios to keep honest; a rename must not silently empty it."""
    missing = [sid for sid in CASES
               if not (ROOT / ("advanced-scenarios" if sid.startswith("SZZG-") else "scenarios") / sid).is_dir()]
    assert missing == []
    assert len(CASES) >= 12
