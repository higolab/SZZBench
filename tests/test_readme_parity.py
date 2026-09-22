"""The English and Japanese halves of README.md describe the same thing (issue #68).

`README.md` is one file: the English text, a rule, then `# 日本語版` and the
Japanese text. Three sections added to the English half between 2026-09-19
and 2026-09-21 never reached the Japanese half, because nothing compared the
two. These tests do: both halves must have the same sequence of heading
levels, the same code blocks in the same order (commands, paths and file
layouts are language-independent), and the same set of `docs/` references.
Prose is not compared -- a translation is not a copy -- so a section added
to one half without the other is what fails.
"""
from __future__ import annotations

import re
from pathlib import Path

README = Path(__file__).resolve().parents[1] / "README.md"
DIVIDER = "# 日本語版"


def _halves() -> tuple[list[str], list[str]]:
    lines = README.read_text(encoding="utf-8").split("\n")
    split = lines.index(DIVIDER)
    return lines[:split], lines[split + 1:]


def _outline(lines: list[str]) -> tuple[list[int], list[str]]:
    """Heading levels in order, and fenced code blocks in order, skipping
    headings that appear inside a fence."""
    levels: list[int] = []
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
                levels.append(len(line) - len(line.lstrip("#")))
            continue
        if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) \
                and line.strip() == marker.group(1):
            blocks.append("\n".join(current).strip())
            fence = None
        else:
            current.append(line)
    assert fence is None, "unclosed code fence"
    return levels, blocks


def test_both_halves_have_the_same_heading_structure():
    en, ja = _halves()
    en_levels, _ = _outline(en)
    ja_levels, _ = _outline(ja)
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
