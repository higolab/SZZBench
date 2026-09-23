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

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from szzbench.generator import generate_repository  # noqa: E402
from szzbench.graph_generator import generate_graph_repository  # noqa: E402

needs_jdk = pytest.mark.skipif(shutil.which("javac") is None or shutil.which("java") is None, reason="needs a JDK")

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
    bare = full.lstrip("^")
    return next(cid for cid, h in hashes.items() if h.startswith(bare[:40]) or bare.startswith(h[:40]))


def _snapshot(repo: Path, commit: str, into: Path) -> None:
    into.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(["git", "archive", commit], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(into)], input=tar, check=True)


def _run_driver(work: Path, sid: str) -> str:
    (work / "Drive.java").write_text(DRIVERS[sid])
    sources = [str(p) for p in work.rglob("*.java")]
    subprocess.run(["javac", "-d", str(work / "out"), *sources], check=True, capture_output=True)
    return subprocess.run(["java", "-cp", str(work / "out"), "Drive"], cwd=work, capture_output=True, text=True, check=True).stdout.strip()


def _blame_owners(repo: Path, hashes: dict[str, str]) -> dict[str, tuple[str, str, str]]:
    bfc = hashes[_bfc(hashes)]
    seen: dict[str, tuple[str, str, str]] = {}
    for path in _git(repo, "diff", "--name-only", f"{bfc}^", bfc).split():
        line_no = None
        for line in _git(repo, "diff", "-U0", f"{bfc}^", bfc, "--", path).splitlines():
            if line.startswith("@@"):
                line_no = int(line.split()[1].lstrip("-").split(",")[0])
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


def test_szz_0218_blame_returns_a_strict_superset_of_the_answer(generated):
    """The new mechanism: the scenario fails on a false positive, not a false negative."""
    sid, hashes, repo = generated
    if sid != "SZZ-0218":
        pytest.skip("only SZZ-0218 makes blame over-report")
    blamed = {owners[0] for owners in _blame_owners(repo, hashes).values()}
    assert REQUIRED[sid] < blamed, f"blame {blamed} is not a strict superset of {REQUIRED[sid]}"
    assert blamed - REQUIRED[sid] == {"c2"}


def test_szzg_0148_blame_falls_short_of_the_threshold(generated):
    """The new mechanism: one true positive, no false positive, below minimum_required."""
    sid, hashes, repo = generated
    if sid != "SZZG-0148":
        pytest.skip("only SZZG-0148 is scored against a threshold")
    blamed = {owners[0] for owners in _blame_owners(repo, hashes).values()}
    assert blamed < REQUIRED[sid] and len(blamed) == 1
    data = yaml.safe_load((ROOT / "advanced-scenarios" / sid / "scenario.graph.yml").read_text())
    level = data["expected_szz"]["commit_level"]
    assert level["evaluation_policy"] == "partial_credit"
    assert level["minimum_required"] == 2 and len(level["required"]) == 3
    assert len(blamed) < level["minimum_required"]
    bfc = hashes[_bfc(hashes)]
    diff = _git(repo, "diff", "-U0", f"{bfc}^", bfc).splitlines()
    assert len([l for l in diff if l.startswith("-") and not l.startswith("---")]) == 1
    assert len([l for l in diff if l.startswith("+") and not l.startswith("+++")]) == 6


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
def test_szz_0218_both_faults_are_necessary_and_the_counter_is_not_one(generated, tmp_path):
    sid, hashes, repo = generated
    if sid != "SZZ-0218":
        pytest.skip("only SZZ-0218 has the counter")
    only_boxes = tmp_path / "only-boxes"
    _snapshot(repo, hashes["c3"], only_boxes)
    _edit(only_boxes, "src/main/java/example/BatchSummary.java",
          ("return items / PER_BOX;", "return (int) (((long) items + PER_BOX - 1) / PER_BOX);"))
    assert _run_driver(only_boxes, sid) == "boxes24=2 boxes25=3 boxesMax=178956971 d24=24 boxes d25=25 boxes"
    only_label = tmp_path / "only-label"
    _snapshot(repo, hashes["c3"], only_label)
    _edit(only_label, "src/main/java/example/BatchSummary.java",
          ('return items + " boxes";', 'return boxes(items) + " boxes";'))
    assert _run_driver(only_label, sid) == "boxes24=2 boxes25=2 boxesMax=178956970 d24=2 boxes d25=2 boxes"
    # removing c2's counter alone changes nothing: it is written and never read
    without_counter = tmp_path / "without-counter"
    _snapshot(repo, hashes["c3"], without_counter)
    _edit(without_counter, "src/main/java/example/BatchSummary.java",
          ("        described++;\n", ""), ("    private int described;\n\n", ""))
    assert _run_driver(without_counter, sid) == EXPECTED[sid]["c3"]


def test_neither_new_scenario_overflows_on_a_supported_input(generated, tmp_path):
    """The reference and the fixed expression must be right across the declared int domain, not
    only on the small probes: a conversion that overflows makes the scenario's own premise false
    (PR #81 review). The boundary probes are part of EXPECTED, so this test states what they guard."""
    sid, hashes, repo = generated
    if shutil.which("javac") is None or shutil.which("java") is None:
        pytest.skip("needs a JDK")
    fixed = max(EXPECTED[sid])
    work = tmp_path / "boundary"
    _snapshot(repo, hashes[fixed], work)
    answers = dict(part.split("=", 1) for part in _run_driver(work, sid).split(" ") if "=" in part)
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
    assert offenders == [], "a cheap rule solves these by construction: " + "; ".join(offenders)
