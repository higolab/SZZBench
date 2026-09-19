"""Every scenario field path the documentation names must exist in a scenario.

`docs/decisions/vocabulary.md` has three times described something that was not
there: a `szzbench stats` command that writes `blame_class` (corrected in #49),
and a compilation exemption keyed on `meta.build_system` when the schema field
is `repository.build_system` (corrected here, found in review of #52).  Prose is
not validated by anything else, so a documented field path that occurs in no
scenario is the cheapest form of that mistake to catch.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

#: Top-level scenario keys; a dotted token rooted elsewhere is not a field path.
SCENARIO_ROOTS = frozenset({
    "meta", "repository", "commits", "bugs", "expected_szz", "clone_relationships",
    "scenario_design", "graph_extensions", "evaluation_points", "notes", "checks",
})

#: `notes.txt` and friends are filenames that happen to match the shape.
FILE_SUFFIXES = (".txt", ".md", ".yml", ".yaml", ".json", ".java", ".xml", ".py", ".log")

DOTTED = re.compile(r"`([a-z_]+(?:\.[a-z_0-9]+)+)`")


def _occurring_paths() -> set[str]:
    paths: set[str] = set()

    def walk(node: object, prefix: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                child = f"{prefix}.{key}" if prefix else str(key)
                paths.add(child)
                walk(value, child)
        elif isinstance(node, list):
            for item in node:
                walk(item, prefix)

    for pattern in ("scenarios/SZZ-*/scenario.yml", "advanced-scenarios/SZZG-*/scenario.graph.yml"):
        for path in ROOT.glob(pattern):
            walk(yaml.safe_load(path.read_text(encoding="utf-8")), "")
    return paths


def test_documented_field_paths_exist():
    occurring = _occurring_paths()
    assert "repository.build_system" in occurring, "fixture sanity: the suite declares build_system"

    unknown = []
    for doc in sorted((ROOT / "docs").rglob("*.md")):
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            for match in DOTTED.finditer(line):
                field = match.group(1)
                if field.split(".")[0] not in SCENARIO_ROOTS or field.endswith(FILE_SUFFIXES):
                    continue
                if field not in occurring:
                    unknown.append(f"{doc.relative_to(ROOT)}:{lineno} names `{field}`")

    assert not unknown, (
        "documentation names scenario fields that occur in no scenario:\n  "
        + "\n  ".join(unknown)
    )
