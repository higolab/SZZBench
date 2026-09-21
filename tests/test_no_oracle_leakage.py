"""Suite-wide guards against oracle leakage (issues #8 and #9).

These tests run over the shipped scenarios rather than over fixtures: they are
the machine-checkable form of the policy in ``docs/decisions/oracle-leakage.md``.
A new scenario that announces its own answer, or that ties the author or the
date to the commit role, fails here.
"""
from __future__ import annotations

import collections
import random
import re
from pathlib import Path

import yaml

from szzbench.gitutils import resolve_commit_metadata, resolved_commit_authors
from szzbench.validator import LEAK_CONTENT_FIELDS, LEAK_ROLE_RE, logical_id_reference

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The attack's own vocabulary. It is deliberately *not* the lint's pattern:
#: the first version of this guard reused the lint regex, so it reported zero
#: leaks for the messages the lint could not see (PR #34 re-review).
ATTACK_WORDS = re.compile(r"\b(bugs?|buggy|faulty|faults?|defects?|broken|BIC|distractor|noise)\b", re.I)
PATTERNS = ("scenarios/SZZ-*/scenario.yml", "advanced-scenarios/SZZG-*/scenario.graph.yml")


def _scenarios():
    for pattern in PATTERNS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            yield path, yaml.safe_load(path.read_text())


def _bfc_ids(data):
    ids = set()
    for bug in data.get("bugs") or []:
        if bug.get("bug_fixing_commit"):
            ids.add(bug["bug_fixing_commit"])
        for entry in bug.get("bug_fixing_commits") or []:
            ids.add(entry.get("commit") if isinstance(entry, dict) else entry)
    return {i for i in ids if i}


def _required(data):
    """Union of the commit-level required sets over all bugs."""
    required = set()
    for bug in data.get("bugs") or []:
        level = (bug.get("expected_szz") or {}).get("commit_level") or {}
        required |= set(level.get("true_positives") or [])
        required |= set(level.get("required") or [])
    level = (data.get("expected_szz") or {}).get("commit_level") or {}
    required |= set(level.get("required") or [])
    return required


def test_no_message_announces_its_role_or_logical_id():
    offenders = []
    for path, data in _scenarios():
        bfcs = _bfc_ids(data)
        for commit in data.get("commits") or []:
            message = commit.get("message")
            if not isinstance(message, str):
                continue
            exposed = logical_id_reference(message, [c.get("id") for c in data.get("commits") or []])
            if exposed:
                offenders.append(f"{path.parent.name}/{commit.get('id')}: logical id {exposed!r} in {message!r}")
            if commit.get("id") not in bfcs and LEAK_ROLE_RE.search(message):
                offenders.append(f"{path.parent.name}/{commit.get('id')}: role wording in {message!r}")
    assert offenders == []


def test_no_commit_writes_its_role_into_the_repository():
    offenders = []
    for path, data in _scenarios():
        for commit in data.get("commits") or []:
            for op in commit.get("operations") or []:
                field = LEAK_CONTENT_FIELDS.get(op.get("type"))
                text = op.get(field) if field else None
                if isinstance(text, str) and LEAK_ROLE_RE.search(text):
                    offenders.append(f"{path.parent.name}/{commit.get('id')}: {op.get('path')}")
                target = str(op.get("path") or "")
                if LEAK_ROLE_RE.search(Path(target).name):
                    offenders.append(f"{path.parent.name}/{commit.get('id')}: path {target}")
    assert offenders == []


def test_message_only_predictor_wins_nothing():
    """"Return the non-BFC commits whose subject admits a bug" must score 0.

    The predictor uses ``ATTACK_WORDS``, not the lint's pattern, so a hole in
    the lint cannot make this test pass: before the PR #34 re-review it found
    SZZ-0146, SZZ-0158, SZZ-0159, SZZ-0160, SZZ-0166 and SZZG-0093, all of
    which the lint's own regex considered clean.
    """
    wins, solved, total = 0, [], 0
    for path, data in _scenarios():
        required = _required(data)
        if not required:
            continue
        total += 1
        bfcs = _bfc_ids(data)
        guess = {c.get("id") for c in data.get("commits") or []
                 if isinstance(c.get("message"), str)
                 and c.get("id") not in bfcs
                 and ATTACK_WORDS.search(c["message"])}
        if guess and guess == required:
            wins += 1
            solved.append(path.parent.name)
    assert total > 150, "the suite scan found too few scenarios"
    assert wins == 0, f"message-only predictor solved {wins}/{total} scenarios: {solved}"


def _author_sets(data):
    """(canonical author per commit, commit ids) for the history the generated repository will have:
    explicit or deterministic default authors as Git records them, plus the commits `commit_generator`
    expands (PR #64 review) - the same model the W413 lint uses."""
    rows = resolved_commit_authors(data)
    return [author for _, author in rows], [cid for cid, _ in rows]


def _best_single_author(rows):
    """The statistic of #36: over all scenarios, the largest number of scenarios whose oracle
    is exactly one author's set of commits, for one author fixed across the suite."""
    wins = collections.Counter()
    for labels, ids, required in rows:
        by_author = collections.defaultdict(set)
        for author, cid in zip(labels, ids):
            by_author[author].add(cid)
        for author, owned in by_author.items():
            if owned == required:
                wins[author] += 1
    return max(wins.values()) if wins else 0


def test_no_single_author_predicts_the_oracle():
    """One author fixed across the suite must not identify the BICs.

    The threat is a rule chosen once and applied everywhere ("report the
    commits written by Bob"), which passed 70/101 normal scenarios before the
    sweep. Picking the matching author per scenario is not an attack: it needs
    the oracle, and most oracles are a single commit.

    The bound is not a constant (#36): the statistic is a maximum over authors,
    so its chance level is the distribution of that maximum when the labels
    carry no information. That null is drawn here by shuffling the author labels
    *inside* each scenario — the multiset of authors and the commit count of
    every scenario are kept — and recomputing the maximum; the observed value
    must not exceed the null's 95th percentile. The old constant (10%) sat
    inside this null on the 206-scenario suite.
    """
    from szzbench.evaluator import _commit_level_policy

    rows = []
    for path, data in _scenarios():
        suite = "scenarios" if path.parent.parent.name == "scenarios" else "advanced-scenarios"
        required = set(_commit_level_policy(data, suite, None).required)
        if not required:
            continue
        labels, ids = _author_sets(data)
        rows.append((labels, ids, required))
    total = len(rows)
    assert total > 150, "the suite scan found too few scenarios"
    observed = _best_single_author(rows)

    rng = random.Random(36)
    draws = []
    for _ in range(500):
        shuffled = []
        for labels, ids, required in rows:
            permuted = list(labels)
            rng.shuffle(permuted)
            shuffled.append((permuted, ids, required))
        draws.append(_best_single_author(shuffled))
    draws.sort()
    bound = draws[int(0.95 * len(draws))]
    assert observed <= bound, (
        f"the best fixed author solves {observed}/{total} scenarios, above the permutation null's "
        f"95th percentile of {bound} (null mean {sum(draws) / len(draws):.1f}, max {draws[-1]})")


def test_author_and_date_do_not_encode_the_role():
    authors_by_role = collections.defaultdict(collections.Counter)
    missing = []
    for path, data in _scenarios():
        for index, commit in enumerate(commits := data.get("commits") or []):
            meta = resolve_commit_metadata(data, commit, index)
            if not meta.author or not meta.author_date:
                missing.append(f"{path.parent.name}/{commit.get('id')}")
            authors_by_role[commit.get("role")][meta.author] += 1
        assert commits, f"{path} has no commits"
    assert missing == []
    for role in ("bug_introducing", "initial", "distractor"):
        counter = authors_by_role.get(role)
        if not counter or sum(counter.values()) < 20:
            continue
        top, count = counter.most_common(1)[0]
        share = count / sum(counter.values())
        assert share < 0.45, f"author {top!r} holds {share:.0%} of role {role!r}"
