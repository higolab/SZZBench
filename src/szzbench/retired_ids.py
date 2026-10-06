"""The ids of withdrawn scenarios, as ``docs/retired-ids.md`` records them (issue #112).

Scenario ids are never renumbered, so a withdrawn scenario leaves a gap that
must stay one.  The table in ``docs/retired-ids.md`` records every gap, and
nothing that assigned or accepted an id read it: retiring the highest id of a
suite made it the next one issued.  The skeleton builders and
``validate-index`` read the table's first column here; the Scenario Editor's
backend reads the same column (``tools/scenario-editor/server/index.js``).
"""
from __future__ import annotations

from pathlib import Path
import re

_ROW = re.compile(r"\|\s*(SZZG?-\d+)\s*\|")


def retired_ids_path(root: Path) -> Path:
    """The table for the suite at ``root``: ``docs/`` beside the suite, as in a checkout."""
    return root.resolve().parent / "docs" / "retired-ids.md"


def read_retired_ids(root: Path) -> set[str]:
    """Every id in the first column of the table, of either suite.  A copy of
    the suites without the document has no retired ids."""
    path = retired_ids_path(root)
    if not path.is_file():
        return set()
    return {match.group(1) for line in path.read_text(encoding="utf-8").splitlines() if (match := _ROW.match(line))}
