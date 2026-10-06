"""Add a new scenario's entry to an index.yml by editing its text (issue #111).

The skeleton builders used to append a two-space-indented entry to the end of
the file.  The shipped indexes list their entries at column 0, and
``advanced-scenarios/index.yml`` ends with a top-level ``notes:`` block, so the
appended entry left both files unreadable.  Like the Scenario Editor's
``spliceIndexEntry``, the entry now goes into the ``scenarios:`` list itself,
at the list's own indentation, and every other line stays byte for byte,
except ``scenario_count``, which follows the list.  The result is loaded
before anything is written: unless it reads back as the old index plus the
new entry, the builder writes nothing.
"""
from __future__ import annotations

from pathlib import Path
import re

import yaml

from .scenario import UniqueKeyLoader

_LINE = re.compile(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+\Z")
_SCENARIOS_KEY = re.compile(r"scenarios:[ \t]*(\[[ \t]*\]|~|null|Null|NULL)?[ \t]*(?:#.*)?")
_SCENARIO_COUNT = re.compile(r"(scenario_count:[ \t]*)\d+([ \t]*(?:#.*)?)")


class IndexSpliceError(ValueError):
    pass


def read_index_text(index_path: Path, empty: str) -> str:
    """The index as stored, or ``empty`` for a root that has none yet.
    ``newline=""`` keeps CRLF line ends, so that the lines the splice leaves
    alone are written back byte for byte."""
    if not index_path.exists():
        return empty
    with index_path.open(encoding="utf-8", newline="") as fh:
        return fh.read()


def write_index_text(index_path: Path, text: str) -> None:
    with index_path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def splice_index_entry(text: str, data: dict, entry: dict) -> str:
    """``text`` with ``entry`` added as the last item of its ``scenarios:`` list.

    ``data`` is ``text`` as loaded, with ``scenarios`` a list.  The builders
    number a new scenario after every id in use, so the end of the list is
    its place in id order.  The entry is rendered the way PyYAML writes the
    shipped indexes, and indented like the list's first item.
    """
    lines = _LINE.findall(text)
    eol = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += eol
    key = next((i for i, line in enumerate(lines) if _SCENARIOS_KEY.fullmatch(_body(line))), None)
    if key is None:
        lines.append("scenarios:" + eol)
        key = len(lines) - 1
    elif _SCENARIOS_KEY.fullmatch(_body(lines[key])).group(1):      # scenarios: [] or null
        lines[key] = "scenarios:" + eol
    end = next((i for i in range(key + 1, len(lines)) if _is_top_level(lines[i])), len(lines))
    items = [i for i in range(key + 1, end) if _body(lines[i]).strip() and not _body(lines[i]).lstrip().startswith("#")]
    indent = re.match(r" *", lines[items[0]]).group() if items else ""
    rendered = yaml.safe_dump([entry], sort_keys=False, allow_unicode=True, width=float("inf"))
    at = items[-1] + 1 if items else key + 1
    lines[at:at] = [indent + line + eol for line in rendered.rstrip("\n").split("\n")]

    expected = {**data, "scenarios": [*data["scenarios"], entry]}
    if data.get("scenario_count") is not None:
        count = next((i for i, line in enumerate(lines) if _SCENARIO_COUNT.fullmatch(_body(line))), None)
        if count is None:
            raise IndexSpliceError("its scenario_count is not a plain number on a line of its own")
        expected["scenario_count"] = len(expected["scenarios"])
        line = lines[count]
        lines[count] = _SCENARIO_COUNT.sub(rf"\g<1>{expected['scenario_count']}\g<2>", _body(line)) + line[len(_body(line)):]

    spliced = "".join(lines)
    try:
        loaded = yaml.load(spliced, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise IndexSpliceError(f"the edited index would not load: {exc}") from exc
    if loaded != expected:
        raise IndexSpliceError("the edited index would not read back as the old one plus the new entry")
    return spliced


def _body(line: str) -> str:
    return line.rstrip("\r\n")


def _is_top_level(line: str) -> bool:
    """A key at column 0: not indented, not a comment, and not an item of a
    list written at column 0, as the shipped indexes write ``scenarios:``."""
    return line[:1] not in ("", " ", "\t", "#", "\r", "\n") and not re.match(r"-(?:\s|$)", line)
