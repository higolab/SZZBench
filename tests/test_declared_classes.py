"""A scenario must belong to the class it declares (issue #7).

Seven scenarios declared an addition-only fix or a deletion-only
bug-introducing commit while a template indentation artefact re-indented the
surviving line, so the fix deleted it and plain blame reached the intended
"ghost" commit after all. `--lint` already detects that (W420 / W421); this
test keeps the shipped suite free of it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from szzbench.validator import validate_scenario_file

REPO_ROOT = Path(__file__).resolve().parents[1]
GHOST_CODES = {"W420", "W421"}


@pytest.mark.parametrize("path", sorted(REPO_ROOT.glob("scenarios/SZZ-*/scenario.yml")),
                         ids=lambda p: p.parent.name)
def test_declared_ghost_class_holds(path):
    _, result, _ = validate_scenario_file(path, simulate=True, lint=True)
    offenders = [f"{f.code}: {f.message}" for f in result.findings if f.code in GHOST_CODES]
    assert offenders == []


def test_the_ghost_classes_are_actually_exercised():
    """The guard above is only meaningful if some scenario declares a ghost class."""
    add_only = delete_only = 0
    for path in sorted(REPO_ROOT.glob("scenarios/SZZ-*/scenario.yml")):
        import yaml

        data = yaml.safe_load(path.read_text())
        factors = {f for f in (data.get("meta") or {}).get("factors") or [] if isinstance(f, str)}
        for bug in data.get("bugs") or []:
            fault = bug.get("fault") or {}
            fix = bug.get("fix") or {}
            if fault.get("change_type") == "omission" and fix.get("fix_type") in {"line_addition", "file_creation"}:
                add_only += 1
            if factors & {"deletion-only-bic", "line-deletion-bic"}:
                delete_only += 1
    assert add_only >= 6, "no scenario declares an addition-only fix any more"
    assert delete_only >= 3, "no scenario declares a deletion-only BIC any more"
