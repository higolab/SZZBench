"""What `docs/decisions/vocabulary.md` says about factors and roles holds for the suites (issues #187, #197, #198).

The factor vocabulary is open (§1.1), so no lint reports a word outside the
recommended lists. §1.4 still names old spellings that are replaced, and until
2026-10-10 twenty scenarios used them while the document called the vocabulary
closed (issue #197). §2.1 listed a BFC role, `attempted_fix`, that the validator
rejected (issue #187). These tests compare the document with the suites and
the validator, the way `test_docs_field_paths.py` does for field paths.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from szzbench.graph_validator import ALLOWED_BFC_ROLES
from szzbench.validator import ALLOWED_ROLES

ROOT = Path(__file__).resolve().parent.parent
VOCABULARY = (ROOT / "docs" / "decisions" / "vocabulary.md").read_text(encoding="utf-8")
CODE = re.compile(r"`([a-z0-9_-]+)`")


def _section(start: str, end: str) -> str:
    return VOCABULARY[VOCABULARY.index(start):VOCABULARY.index(end)]


def _spelling(word: str) -> str:
    """The table spells some words as the graph suite did before it became hyphen-case."""
    return word.replace("_", "-")


def _shipped_factors() -> dict[str, list[str]]:
    factors = {}
    for pattern in ("scenarios/SZZ-*/scenario.yml", "advanced-scenarios/SZZG-*/scenario.graph.yml"):
        for path in sorted(ROOT.glob(pattern)):
            factors[path.parent.name] = yaml.safe_load(path.read_text(encoding="utf-8"))["meta"]["factors"]
    return factors


def _old_spellings() -> tuple[set[str], set[str]]:
    """``(replaced, not_applied)``: the old spellings of §1.4 and those it says are still in use."""
    section = _section("### 1.4", "## 2. Roles")
    # the words §1.2 lists in its first column and §1.3 in its paragraph, not the ones they replace
    recommended = {w for line in _section("### 1.2", "### 1.3").splitlines() if line.startswith("| `")
                   for w in CODE.findall(line.split("|")[1])}
    recommended |= set(CODE.findall(_section("### 1.3", "### 1.4")))
    replaced = set()
    for row in (line for line in section.splitlines() if line.startswith("| `")):
        old, new = row.split("|")[1:3]
        replacements = {_spelling(w) for w in CODE.findall(re.sub(r"`[a-z0-9_-]+`→", "", new))}
        replaced |= {_spelling(w) for w in CODE.findall(old)} - replacements - recommended
    not_applied = next((line for line in section.splitlines() if line.startswith("- **Not applied.**")), "")
    return replaced, {_spelling(w) for w in CODE.findall(not_applied)}


def test_no_scenario_uses_an_old_spelling_the_synonym_table_replaced():
    replaced, not_applied = _old_spellings()
    assert {"context", "context-dependent", "comment-only-intermediate"} <= replaced, "fixture sanity: §1.4 parsed"
    offenders = [f"{sid}: {word}" for sid, words in _shipped_factors().items()
                 for word in words if word in replaced - not_applied]
    assert offenders == [], "§1.4 replaces these spellings; use the word it names instead"


def test_every_spelling_listed_as_not_applied_is_still_in_use():
    _, not_applied = _old_spellings()
    in_use = {word for words in _shipped_factors().values() for word in words}
    assert not_applied - in_use == set(), "§1.4 lists a spelling as not applied that no scenario uses any more"


def test_the_bfc_roles_of_the_vocabulary_are_the_ones_the_validator_accepts():
    section = _section("### 2.1", "### 2.2")
    paragraph = next(line for line in section.splitlines() if line.startswith("**BFC entries**"))
    named = set(CODE.findall(paragraph.split(". ")[0]))
    assert named == set(ALLOWED_BFC_ROLES)
    table = section[section.index("| canonical | today (scenarios) |"):]
    canonical = {match for row in table.splitlines()[2:] if row.startswith("| `")
                 for match in CODE.findall(row.split("|")[1])}
    assert canonical <= set(ALLOWED_BFC_ROLES), "a row of the §2.1 table maps onto a role GE404 rejects"


def test_szzg_0036_declares_its_test_only_commit():
    # SZZG-0029 plus a test-only commit inside the fix series (consolidation-matrix.md §7, issue #198)
    scenario = yaml.safe_load((ROOT / "advanced-scenarios/SZZG-0036/scenario.graph.yml").read_text(encoding="utf-8"))
    c2 = next(commit for commit in scenario["commits"] if commit["id"] == "c2")
    assert c2["role"] == "test_change" and c2["role"] in ALLOWED_ROLES
    assert [op["path"] for op in c2["operations"]] == ["src/test/java/example/RangeTest.java"]
    assert "test-file-added" in scenario["meta"]["factors"]
    bfcs = {entry["commit"] for bug in scenario["bugs"] for entry in bug["bug_fixing_commits"]}
    assert "c2" in scenario["fix_series"][0]["commits"] and "c2" not in bfcs
