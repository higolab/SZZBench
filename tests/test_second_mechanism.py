"""A discriminating scenario needs a multi-commit oracle, and two ways to be one (issue #80).

The declared baseline family makes the first half of that a theorem rather than
a design choice: ``position_indices`` enumerates ``position-k`` for the index of
every answer in the suite, so a one-commit oracle is always named exactly by one
positional rule, and ``abstain`` passes every ``expect_no_bic`` scenario by
definition.  ``test_only_a_multi_commit_oracle_can_discriminate`` states that
over the shipped suite.

The other tests cover the two mechanisms added for the second half: SZZ-0218,
where blame returns a strict superset of the answer, and SZZG-0148, where blame
returns one of three required commits and fails a ``minimum_required`` of two.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from support import GeneratedScenarios, blame_owners, export_tree, git_stdout, needs_jdk, run_driver

ROOT = Path(__file__).resolve().parents[1]

DRIVERS = {
    "SZZ-0218": """
public class Drive { public static void main(String[] a) {
    example.BatchSummary b = new example.BatchSummary(); StringBuilder out = new StringBuilder();
    out.append("boxes24=").append(b.boxes(24)).append(" boxes25=").append(b.boxes(25));
    out.append(" boxesMax=").append(b.boxes(Integer.MAX_VALUE));
    out.append(" d24=").append(b.describe(24)).append(" d25=").append(b.describe(25));
    System.out.print(out); } }
""",
    "SZZG-0148": """
import java.lang.reflect.Method;
public class Drive { public static void main(String[] a) throws Exception {
    example.payroll.Payslip p = new example.payroll.Payslip(); StringBuilder out = new StringBuilder();
    out.append("net=").append(p.netCents(19999, 20)).append(" netBig=").append(p.netCents(999999999, 33));
    try { Method m = p.getClass().getMethod("allowanceCents", Integer.class);
          out.append(" allow50=").append(m.invoke(p, Integer.valueOf(50)));
          String an; try { an = String.valueOf(m.invoke(p, (Object) null)); }
          catch (java.lang.reflect.InvocationTargetException e) { an = e.getCause().getClass().getSimpleName(); }
          out.append(" allowNull=").append(an); }
    catch (NoSuchMethodException e) { out.append(" allow=absent"); }
    try { Method m = p.getClass().getMethod("contributionCents", String.class, int.class);
          out.append(" perm=").append(m.invoke(p, "PERMANENT", 100000));
          out.append(" contractor=").append(m.invoke(p, "CONTRACTOR", 100000)); }
    catch (NoSuchMethodException e) { out.append(" contrib=absent"); }
    System.out.print(out); } }
""",
}

EXPECTED = {
    "SZZ-0218": {
        "c0": "boxes24=2 boxes25=3 boxesMax=178956971 d24=2 boxes d25=3 boxes",
        "c1": "boxes24=2 boxes25=2 boxesMax=178956970 d24=2 boxes d25=2 boxes",
        "c2": "boxes24=2 boxes25=2 boxesMax=178956970 d24=2 boxes d25=2 boxes",
        "c3": "boxes24=2 boxes25=2 boxesMax=178956970 d24=24 boxes d25=25 boxes",
        "c4": "boxes24=2 boxes25=3 boxesMax=178956971 d24=2 boxes d25=3 boxes",
    },
    "SZZG-0148": {
        "c0": "net=16000 netBig=670000000 allow=absent contrib=absent",
        "c1": "net=16019 netBig=670000032 allow=absent contrib=absent",
        "c2": "net=16019 netBig=670000032 allow=absent contrib=absent",
        "c3": "net=16019 netBig=670000032 allow50=5000 allowNull=NullPointerException contrib=absent",
        "c4": "net=16019 netBig=670000032 allow50=5000 allowNull=NullPointerException perm=10000 contractor=0",
        "c5": "net=16000 netBig=670000000 allow50=5000 allowNull=0 perm=10000 contractor=6666",
    },
}

#: stripped deleted line -> its blame owner at BFC^, under plain / -w / -w -C -C
BLAME = {
    "SZZ-0218": {
        "private int described;": ("c2", "c2", "c2"),
        "": ("c2", "c2", "c2"),
        "return items / PER_BOX;": ("c1", "c1", "c1"),
        "described++;": ("c2", "c2", "c2"),
        'return items + " boxes";': ("c3", "c3", "c3"),
    },
    "SZZG-0148": {
        "return grossCents - (int) ((long) grossCents / 100 * taxPercent);": ("c1", "c1", "c1"),
    },
}

REQUIRED = {"SZZ-0218": {"c1", "c3"}, "SZZG-0148": {"c1", "c3", "c4"}}


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory):
    return GeneratedScenarios(tmp_path_factory)


@pytest.fixture(scope="module", params=sorted(EXPECTED), ids=sorted(EXPECTED))
def generated(request, scenarios):
    return scenarios(request.param)


def _bfc(hashes: dict[str, str]) -> str:
    return max(hashes, key=lambda cid: int(cid[1:]))


def test_every_deleted_line_blames_as_the_readme_says(generated):
    sid, hashes, repo = generated
    assert blame_owners(repo, hashes) == BLAME[sid]


@pytest.mark.parametrize("sid", ['SZZ-0218'])
def test_szz_0218_blame_returns_a_strict_superset_of_the_answer(scenarios, sid):
    """The new mechanism: the scenario fails on a false positive, not a false negative."""
    _, hashes, repo = scenarios(sid)
    blamed = {owners[0] for owners in blame_owners(repo, hashes).values()}
    assert REQUIRED[sid] < blamed, f"blame {blamed} is not a strict superset of {REQUIRED[sid]}"
    assert blamed - REQUIRED[sid] == {"c2"}


@pytest.mark.parametrize("sid", ['SZZG-0148'])
def test_szzg_0148_blame_falls_short_of_the_threshold(scenarios, sid):
    """The new mechanism: one true positive, no false positive, below minimum_required."""
    _, hashes, repo = scenarios(sid)
    blamed = {owners[0] for owners in blame_owners(repo, hashes).values()}
    assert blamed < REQUIRED[sid] and len(blamed) == 1
    data = yaml.safe_load((ROOT / "advanced-scenarios" / sid / "scenario.graph.yml").read_text())
    level = data["expected_szz"]["commit_level"]
    assert level["evaluation_policy"] == "partial_credit"
    assert level["minimum_required"] == 2 and len(level["required"]) == 3
    assert len(blamed) < level["minimum_required"]
    bfc = hashes[_bfc(hashes)]
    diff = git_stdout(repo, "diff", "-U0", f"{bfc}^", bfc).splitlines()
    assert len([l for l in diff if l.startswith("-") and not l.startswith("---")]) == 1
    assert len([l for l in diff if l.startswith("+") and not l.startswith("+++")]) == 6


@needs_jdk
def test_the_probe_answers_move_exactly_where_the_readme_says(generated, tmp_path):
    sid, hashes, repo = generated
    observed = {}
    for cid in EXPECTED[sid]:
        work = tmp_path / cid
        export_tree(repo, hashes[cid], work)
        observed[cid] = run_driver(work, DRIVERS[sid])
    assert observed == EXPECTED[sid], sid


def _edit(work: Path, rel: str, *pairs: tuple[str, str]) -> None:
    p = work / rel
    text = p.read_text()
    for old, new in pairs:
        assert text.count(old) == 1, (rel, old)
        text = text.replace(old, new)
    p.write_text(text)


@needs_jdk
@pytest.mark.parametrize("sid", ['SZZ-0218'])
def test_szz_0218_both_faults_are_necessary_and_the_counter_is_not_one(scenarios, sid, tmp_path):
    _, hashes, repo = scenarios(sid)
    only_boxes = tmp_path / "only-boxes"
    export_tree(repo, hashes["c3"], only_boxes)
    _edit(only_boxes, "src/main/java/example/BatchSummary.java",
          ("return items / PER_BOX;", "return (int) (((long) items + PER_BOX - 1) / PER_BOX);"))
    assert run_driver(only_boxes, DRIVERS[sid]) == "boxes24=2 boxes25=3 boxesMax=178956971 d24=24 boxes d25=25 boxes"
    only_label = tmp_path / "only-label"
    export_tree(repo, hashes["c3"], only_label)
    _edit(only_label, "src/main/java/example/BatchSummary.java",
          ('return items + " boxes";', 'return boxes(items) + " boxes";'))
    assert run_driver(only_label, DRIVERS[sid]) == "boxes24=2 boxes25=2 boxesMax=178956970 d24=2 boxes d25=2 boxes"
    # removing c2's counter alone changes nothing: it is written and never read
    without_counter = tmp_path / "without-counter"
    export_tree(repo, hashes["c3"], without_counter)
    _edit(without_counter, "src/main/java/example/BatchSummary.java",
          ("        described++;\n", ""), ("    private int described;\n\n", ""))
    assert run_driver(without_counter, DRIVERS[sid]) == EXPECTED[sid]["c3"]


@needs_jdk
def test_neither_new_scenario_overflows_on_a_supported_input(generated, tmp_path):
    """The reference and the fixed expression must be right across the declared int domain, not
    only on the small probes: a conversion that overflows makes the scenario's own premise false
    (PR #81 review). The boundary probes are part of EXPECTED, so this test states what they guard."""
    sid, hashes, repo = generated
    fixed = max(EXPECTED[sid])
    work = tmp_path / "boundary"
    export_tree(repo, hashes[fixed], work)
    answers = dict(part.split("=", 1) for part in run_driver(work, DRIVERS[sid]).split(" ") if "=" in part)
    if sid == "SZZ-0218":
        # ceiling of Integer.MAX_VALUE / 12, computed in 64 bits; an int sum wraps negative
        assert answers["boxesMax"] == "178956971"
    else:
        # 999999999 * 33 leaves the int range; the correct net is the gross less a third of it
        assert answers["netBig"] == "670000000"


def test_only_a_multi_commit_oracle_can_discriminate():
    """A one-commit oracle is named by exactly one `position-k`, and `position_indices`
    enumerates k because an answer sits there; an empty oracle is what `abstain` predicts.
    So `discriminating` needs at least two required commits — a property of the declared
    family, not a design choice, and the reason every scenario of the tier has one."""
    from szzbench.evaluator import _commit_level_policy, _load_scenario_for_evaluation

    offenders = []
    for pattern, suite in (("scenarios/SZZ-*/scenario.yml", "scenarios"),
                           ("advanced-scenarios/SZZG-*/scenario.graph.yml", "advanced-scenarios")):
        for path in sorted(ROOT.glob(pattern)):
            data = yaml.safe_load(path.read_text())
            if (data.get("meta") or {}).get("tier") != "discriminating":
                continue
            scenario, _ = _load_scenario_for_evaluation(path, suite)
            policy = _commit_level_policy(scenario, suite, None)
            if policy.expect_no_bic or len(policy.required) < 2:
                offenders.append(f"{path.parent.name}: required={policy.required} expect_no_bic={policy.expect_no_bic}")
    assert offenders == [], "a naive rule solves these by construction: " + "; ".join(offenders)
