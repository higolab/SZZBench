"""Every finding code has a row in docs/validation.md, and every row a check that emits it (issue #154).

The document is the reference for a ``--json`` report.  Nothing compared the
two: E021 (duplicate bug id) and GI086 were emitted without a row, and so were
eighteen codes of the graph verifier (GE600, GE620-GE624, GI660, GW664, ...).  The
replay failure of ``validate --simulate`` carried the placeholder ``E2XX``,
which named no check, and had a row under that name.

The validators and verifiers write their codes as string literals
(``"E021"``); the lint helpers both suites share build theirs from the family
they run for (``f"{prefix}413"``).  A struck-through row (``~~GW441~~``) is a
retired code, which nothing may emit.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "validation.md"

#: A code: E, W or I (G before it for the graph suite, I for the index) and three digits.
CODE = re.compile(r"(?:G|I)?[EWI]\d{3}")
#: Anything shaped like a code, a placeholder such as ``E2XX`` included.
CODE_LIKE = r"(?:G|I)?[EWI]\d[0-9A-Z]{2}"
#: A code in a string literal of the source: ``"E021"``.
LITERAL = re.compile(rf"""["']({CODE_LIKE})["']""")
#: A code built at run time from a family: ``f"{prefix}413"``.
BUILT = re.compile(r"""f["']\{(\w+)\}(\d{3})["']""")
#: The families of the lint helpers in validator.py: ``prefix`` is W for
#: ``validate`` and GW for ``validate-graph``, ``error_prefix`` makes E / GE of
#: it, and ``lint_author_coincidence`` I / GI.
FAMILIES = {"prefix": ("W", "GW"), "code": ("E", "GE"), "info_prefix": ("I", "GI")}


def _emitted() -> set[str]:
    codes: set[str] = set()
    for path in sorted((ROOT / "src" / "szzbench").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        codes.update(LITERAL.findall(text))
        for name, number in BUILT.findall(text):
            assert name in FAMILIES, f"{path.name} builds a code from {{{name}}}; add its families to FAMILIES"
            codes.update(family + number for family in FAMILIES[name])
    return codes


def _documented() -> tuple[set[str], set[str]]:
    """The codes in the first column of the tables: (current, retired).

    A cell may hold a bold code (``**GE046**``), or two codes (``I700 / GI703``)."""
    current: set[str] = set()
    retired: set[str] = set()
    for line in DOC.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        (retired if cell.startswith("~~") else current).update(re.findall(CODE_LIKE, cell))
    return current, retired


def test_every_emitted_code_is_a_number_with_a_row():
    current, _ = _documented()
    emitted = _emitted()
    assert {"E000", "GE001", "IE001", "W410", "GW410", "GE400", "GI413"} <= emitted, "the scan finds both kinds"
    assert sorted(code for code in emitted if not CODE.fullmatch(code)) == [], "not a code"
    assert sorted(emitted - current) == [], "emitted without a row in docs/validation.md, or with a retired one"


def test_every_documented_code_is_a_number_that_is_emitted():
    current, retired = _documented()
    assert {"E000", "GE001", "IE001", "I700", "GI703", "GE046"} <= current and {"GW441", "IE010"} <= retired
    assert sorted(code for code in current | retired if not CODE.fullmatch(code)) == [], "a row that is not a code"
    assert sorted(current - _emitted()) == [], "a row in docs/validation.md that no check emits; strike a retired one through"
