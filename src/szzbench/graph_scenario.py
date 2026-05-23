from __future__ import annotations

from pathlib import Path
from typing import Any

from .scenario import load_yaml
from .findings import ValidationResult


def load_graph_scenario(path: Path) -> tuple[dict[str, Any] | None, ValidationResult]:
    data, result = load_yaml(path)
    if data is None:
        return None, result
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str) or "graph" not in schema_version:
        result.error("GE001", "scenario.graph.yml must use a graph schema_version such as 'graph-0.1-draft'.", "schema_version")
    return data, result


def commit_id_of(entry: Any) -> str | None:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict) and isinstance(entry.get("commit"), str):
        return entry["commit"]
    return None


def graph_bic_entries(bug: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for raw in bug.get("bug_introducing_commits", []) or []:
        if isinstance(raw, str):
            entries.append({"commit": raw, "role": "direct"})
        elif isinstance(raw, dict):
            entries.append(raw)
    return entries


def graph_bfc_entries(bug: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(bug.get("bug_fixing_commits"), list):
        entries = []
        for raw in bug.get("bug_fixing_commits", []) or []:
            if isinstance(raw, str):
                entries.append({"commit": raw, "role": "complete_fix"})
            elif isinstance(raw, dict):
                entries.append(raw)
        return entries
    if isinstance(bug.get("bug_fixing_commit"), str):
        return [{"commit": bug["bug_fixing_commit"], "role": "complete_fix"}]
    return []


def graph_faults(bug: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(bug.get("faults"), list):
        return [f for f in bug["faults"] if isinstance(f, dict)]
    if isinstance(bug.get("fault"), dict):
        return [bug["fault"]]
    return []


def graph_fixes(bug: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(bug.get("fixes"), list):
        return [f for f in bug["fixes"] if isinstance(f, dict)]
    if isinstance(bug.get("fix"), dict):
        return [bug["fix"]]
    return []
