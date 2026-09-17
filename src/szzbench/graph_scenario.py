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


#: Normalized BIC roles whose commits form the inferred `required` set when a
#: graph scenario declares no explicit commit-level oracle.
DIRECT_BIC_ROLES: frozenset[str] = frozenset({"direct", "reintroducing", "contributing"})


def normalize_bic_role(role: Any) -> str:
    """Map a bug-entry role spelling to one of the canonical role classes.

    Scenarios use many free-form spellings (``direct_squash_bic``,
    ``merge_introducing``, ``old_origin_bic``, ...). The evaluator and the
    verifier only need to know which class a role belongs to:

    - ``direct``: the commit itself introduced the fault (also the default
      when the role is missing);
    - ``origin``: the commit is where a copied/replayed fault first appeared;
    - ``reintroducing``: the commit brought a previously fixed fault back;
    - ``contributing``: the commit is one of several that jointly caused it;
    - ``other``: anything not covered above.
    """
    if role is None:
        return "direct"
    if not isinstance(role, str):
        return "other"
    value = role.strip().lower()
    if not value:
        return "direct"
    if "origin" in value:
        return "origin"
    if "reintroduc" in value:
        return "reintroducing"
    if "contribut" in value:
        return "contributing"
    if value.startswith("direct") or "introduc" in value:
        return "direct"
    return "other"


def graph_bic_entries(bug: dict[str, Any], *, roles: frozenset[str] | set[str] | None = None) -> list[dict[str, Any]]:
    """Return the bug's BIC entries as dicts.

    When ``roles`` is given, only entries whose normalized role (see
    :func:`normalize_bic_role`) is in that set are returned.
    """
    entries = []
    for raw in bug.get("bug_introducing_commits", []) or []:
        if isinstance(raw, str):
            entries.append({"commit": raw, "role": "direct"})
        elif isinstance(raw, dict):
            entries.append(raw)
    if roles is not None:
        entries = [entry for entry in entries if normalize_bic_role(entry.get("role")) in roles]
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
