"""The English and Japanese halves of README.md describe the same thing (issue #68).

`README.md` is one file: the English text, a rule, then `# 日本語版` and the
Japanese text. Three sections added to the English half between 2026-09-19
and 2026-09-21 never reached the Japanese half, because nothing compared the
two. These tests do: both halves must have the same sequence of heading
levels, the same code blocks in the same order (commands, paths and file
layouts are language-independent), and the same set of `docs/` references.
Prose is not compared -- a translation is not a copy -- so a section added
to one half without the other is what fails.

What prose carries that a translation keeps is compared too (issue #189): the
numbers, and the link targets. A Japanese paragraph saying `PASS: 162` next
to an English one saying 161 passed the checks above.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

README = Path(__file__).resolve().parents[1] / "README.md"
DIVIDER = "# 日本語版"

#: English spells out numbers that the Japanese half writes in digits.
_UNITS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
_TEENS = ("ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
          "nineteen")
_TENS = ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
SPELLED = re.compile(rf"\b(?:({'|'.join(_TENS)})(?:-({'|'.join(_UNITS)}))?|({'|'.join(_TEENS)}))\b", re.IGNORECASE)
LINK = re.compile(r"\]\(([^)\s]+)\)")


def _halves() -> tuple[list[str], list[str]]:
    lines = README.read_text(encoding="utf-8").split("\n")
    split = lines.index(DIVIDER)
    return lines[:split], lines[split + 1:]


def _outline(lines: list[str]) -> tuple[list[str], list[str]]:
    """Heading lines in order, and fenced code blocks in order, skipping
    headings that appear inside a fence."""
    headings: list[str] = []
    blocks: list[str] = []
    fence: str | None = None
    current: list[str] = []
    for line in lines:
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence is None:
            if marker:
                fence = marker.group(1)
                current = []
            elif re.match(r"^#{1,6} ", line):
                headings.append(line)
            continue
        if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) \
                and line.strip() == marker.group(1):
            blocks.append("\n".join(current).strip())
            fence = None
        else:
            current.append(line)
    assert fence is None, "unclosed code fence"
    return headings, blocks


def _level(heading: str) -> int:
    return len(heading) - len(heading.lstrip("#"))


def _numbers(lines: list[str]) -> Counter[str]:
    """Every number of two or more characters, the spelled-out ones from ten to
    ninety-nine included. A single digit is left out: English writes it as a
    word that is also a pronoun, an ordinal or an adverb ("one of", "the
    second", "twice"), and Japanese as a digit or in kanji (一つ, 二つ), so the
    two halves cannot be paired on it."""
    text = "\n".join(lines)
    numbers = Counter(number for number in re.findall(r"\d+(?:\.\d+)?", text) if len(number) > 1)
    for tens, unit, teen in SPELLED.findall(text):
        value = _TEENS.index(teen.lower()) + 10 if teen else \
            (_TENS.index(tens.lower()) + 2) * 10 + (_UNITS.index(unit.lower()) + 1 if unit else 0)
        numbers[str(value)] += 1
    return numbers


def _anchor(heading: str) -> str:
    """GitHub's id for a heading: lower case, punctuation dropped, spaces as hyphens."""
    return re.sub(r"[^\w\- ]", "", heading.lstrip("#").strip().lower()).replace(" ", "-")


def _anchors() -> dict[str, tuple[str, int]]:
    """Each heading id, and the half and position of its heading. GitHub renders
    the file as one page, so the second heading with the same text gets `-1`."""
    anchors: dict[str, tuple[str, int]] = {}
    seen: Counter[str] = Counter()
    for half, lines in zip(("English", "Japanese"), _halves()):
        headings, _ = _outline(lines)
        for position, heading in enumerate(headings):
            anchor = _anchor(heading)
            anchors[f"{anchor}-{seen[anchor]}" if seen[anchor] else anchor] = (half, position)
            seen[anchor] += 1
    return anchors


def _link_targets(lines: list[str], anchors: dict[str, tuple[str, int]]) -> dict[str, str]:
    """The targets of the links, each as compared and as written. An in-page
    anchor is compared as the English anchor of the heading at the same
    position, because a Japanese heading has a Japanese id; an anchor that
    names no heading is compared as written."""
    english = {where: anchor for anchor, where in anchors.items() if where[0] == "English"}
    targets: dict[str, str] = {}
    for target in LINK.findall("\n".join(lines)):
        where = anchors.get(target[1:]) if target.startswith("#") else None
        compared = f"#{english[('English', where[1])]}" if where else target
        targets.setdefault(compared, target if target == compared else f"{target} (the heading of {compared})")
    return targets


def test_both_halves_have_the_same_heading_structure():
    en, ja = _halves()
    en_levels = [_level(heading) for heading in _outline(en)[0]]
    ja_levels = [_level(heading) for heading in _outline(ja)[0]]
    assert len(en_levels) == len(ja_levels), (
        f"the English half has {len(en_levels)} headings and the Japanese half {len(ja_levels)}; "
        "a section was added to one half only")
    assert en_levels == ja_levels


def test_both_halves_have_the_same_code_blocks_in_the_same_order():
    en, ja = _halves()
    _, en_blocks = _outline(en)
    _, ja_blocks = _outline(ja)
    assert len(en_blocks) == len(ja_blocks)
    for index, (a, b) in enumerate(zip(en_blocks, ja_blocks)):
        assert a == b, f"code block {index} differs between the halves:\n{a}\n---\n{b}"


def test_both_halves_reference_the_same_documents():
    en, ja = _halves()
    pattern = re.compile(r"docs/[A-Za-z0-9_./-]+\.md")
    en_docs = set(pattern.findall("\n".join(en)))
    ja_docs = set(pattern.findall("\n".join(ja)))
    assert en_docs == ja_docs, (
        f"referenced only in English: {sorted(en_docs - ja_docs)}; only in Japanese: {sorted(ja_docs - en_docs)}")


def test_both_halves_quote_the_same_numbers():
    en, ja = _halves()
    en_numbers, ja_numbers = _numbers(en), _numbers(ja)
    assert en_numbers == ja_numbers, (
        f"only in English: {sorted((en_numbers - ja_numbers).elements())}; "
        f"only in Japanese: {sorted((ja_numbers - en_numbers).elements())}")


def test_both_halves_link_the_same_targets():
    anchors = _anchors()
    en, ja = (_link_targets(lines, anchors) for lines in _halves())
    assert en.keys() == ja.keys(), (
        f"linked only in English: {sorted(en[key] for key in en.keys() - ja.keys())}; "
        f"only in Japanese: {sorted(ja[key] for key in ja.keys() - en.keys())}")


@pytest.mark.xfail(strict=True, reason=(
    "README.md: the Japanese Quickstart's [evaluate](#evaluate) opens the English `## evaluate`, because GitHub "
    "gives the Japanese heading the id evaluate-1; README.md is to be fixed separately (issue #189)"))
def test_each_half_links_to_its_own_headings():
    anchors = _anchors()
    halves = dict(zip(("English", "Japanese"), _halves()))
    problems = []
    for half, lines in halves.items():
        for target in LINK.findall("\n".join(lines)):
            where = anchors.get(target[1:]) if target.startswith("#") else (half, None)
            if where is None:
                problems.append(f"the {half} half links {target}, which names no heading")
            elif where[0] != half:
                heading = _outline(halves[where[0]])[0][where[1]]
                problems.append(f"the {half} half links {target}, which opens `{heading}` of the {where[0]} half")
    assert problems == []
