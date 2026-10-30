"""Discriminating scenarios for the categories a naive rule almost always solved (issue #80, proposal 3).

Naive rules solved 39 of S3's 40 scenarios and 27 of G4's 29, the two
largest such pockets in the suite.  By the rule of
``tests/test_second_mechanism.py`` every one of those had a one-commit oracle, so
the pocket can only shrink by adding scenarios whose oracle names more than one
commit.  These are S3's two and G4's one.

Each test measures the scenario against its generated repository: the probe
answers at every commit, the blame owner of every deleted line, and the evidence
that both required commits are necessary.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from support import GeneratedScenarios, blame_owners, export_tree, git_stdout, logical_id, needs_jdk, run_driver

ROOT = Path(__file__).resolve().parents[1]

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


@pytest.fixture(scope="module")
def scenarios(tmp_path_factory):
    return GeneratedScenarios(tmp_path_factory)


@pytest.fixture(scope="module", params=sorted(EXPECTED), ids=sorted(EXPECTED))
def generated(request, scenarios):
    return scenarios(request.param)


def test_every_deleted_line_blames_as_the_readme_says(generated):
    sid, hashes, repo = generated
    assert blame_owners(repo, hashes) == BLAME[sid]


def test_neither_scenario_is_reachable_by_blaming_what_the_fix_deletes(generated):
    """SZZ-0219 misses a required commit; SZZ-0220 names two that are not required."""
    sid, hashes, repo = generated
    blamed = {owners[0] for owners in blame_owners(repo, hashes).values()}
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
        for path in git_stdout(repo, "diff", "--name-only", f"{bfc}^", bfc).split():
            newest = git_stdout(repo, "log", "-1", "--format=%H", f"{bfc}^", "--", path).strip()
            assert logical_id(hashes, newest) == "c6"
        level = yaml.safe_load((ROOT / "advanced-scenarios" / sid / "scenario.graph.yml").read_text())["expected_szz"]["commit_level"]
        assert blamed == {"c1"} and blamed < REQUIRED[sid]
        assert level["evaluation_policy"] == "partial_credit" and level["minimum_required"] == 2
        assert len(blamed) < level["minimum_required"]


@needs_jdk
def test_the_probe_answers_move_exactly_where_the_readme_says(generated, tmp_path):
    sid, hashes, repo = generated
    observed = {cid: run_driver(tmp_path / cid, DRIVERS[sid]) for cid in EXPECTED[sid]
                if (export_tree(repo, hashes[cid], tmp_path / cid) or True)}
    assert observed == EXPECTED[sid], sid


def _edit(work: Path, rel: str, old: str, new: str) -> None:
    p = work / rel
    text = p.read_text()
    assert text.count(old) == 1, (rel, old)
    p.write_text(text.replace(old, new))


# SZZG-0149 is left out: it has three independent causes, and the per-commit table already
# shows that each moves its own answers
@needs_jdk
@pytest.mark.parametrize("sid", [sid for sid in sorted(EXPECTED) if sid != "SZZG-0149"])
def test_both_faults_are_necessary_and_the_noise_commit_is_not_one(scenarios, sid, tmp_path):
    _, hashes, repo = scenarios(sid)
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
        export_tree(repo, hashes[last_faulty], work)
        _edit(work, rel, old, new)
        assert run_driver(work, DRIVERS[sid]) == expected, (sid, work.name)
