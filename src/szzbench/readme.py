"""The generated header of a scenario README (issue #19).

Every scenario README opens with a header that is **rendered from the scenario
file**: the ``# <id>: <title>`` line and a metadata table between two marker
comments.  The header is the only part of a README a tool writes.  Everything
after the end marker is the author's prose -- purpose, evidence, what a tool
must do -- and is never touched.

The header replaces the hand-written copies that drifted: ``## Factors`` lists
that no longer matched ``meta.factors`` (8 of 251 on 2026-09-22), ``## Source``
sections naming a category vocabulary the index had abandoned (35), and, in the
graph suite, a boilerplate sentence about "graph-aware semantics" in place of
the features a scenario actually uses.

``szzbench readme`` checks every README against its scenario (exit 1 when a
header is missing or stale) and ``--write`` regenerates them; ``validate
--lint`` reports the same disagreement as ``W455`` / ``GW455``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .operations import SUPPORTED_OPERATIONS
from .scenario import load_yaml

HEADER_BEGIN = ("<!-- szzbench:header (generated from the scenario file: edit the YAML "
                "and run `szzbench readme --write`) -->")
HEADER_END = "<!-- /szzbench:header -->"

#: Hand-written copies of header data.  ``## Factors`` repeated ``meta.factors``
#: and ``## Source`` carried a ``- Category:`` label; both are removed when the
#: header is written and reported by the lint while they remain.
LEGACY_SECTION_RE = re.compile(r"^## (?:Factors|Source)[ \t]*\n(?:(?!^#).*\n?)*", re.M)

#: ``expected_szz`` sections the classic schema does not have.
GRAPH_ONLY_ORACLE_LEVELS = ("entity_level", "branch_level", "work_item_level", "bug_level")

#: Top-level context sections the classic schema does not have.
GRAPH_CONTEXT_SECTIONS = ("issues", "work_items", "developer_hints", "clone_relationships",
                          "copy_relationships", "bug_instances", "bug_groups", "semantic_rewrites",
                          "fix_series", "context")

#: Per-commit keys that record a replayed or rewritten commit.
REPLAY_KEYS = (("rebase_of", "rebase"), ("cherry_pick_of", "cherry-pick"), ("backport_of", "backport"),
               ("revert_of", "revert"), ("squash_of", "squash"), ("apply_squash", "squash"),
               ("apply_patch_from", "patch replay"))


def suite_of(scenario_path: Path) -> str:
    """The evaluator's suite name for a scenario file."""
    return "advanced-scenarios" if scenario_path.name == "scenario.graph.yml" else "scenarios"


# --- rendering -----------------------------------------------------------------

def _code(value: Any) -> str:
    return f"`{value}`"


def _codes(values: list[str]) -> str:
    return ", ".join(_code(v) for v in values)


def _policy_phrase(policy: Any) -> str:
    parts = [_code(policy.evaluation_policy)]
    if policy.expect_no_bic:
        parts.append("expects no BIC")
    elif policy.evaluation_policy == "top_k":
        parts.append("relevant " + (_codes(policy.relevant) if policy.relevant else _codes(policy.required)))
        if policy.k_values:
            parts.append("k = " + ", ".join(str(k) for k in policy.k_values))
        if policy.status_k is not None:
            parts.append(f"status at k = {policy.status_k}")
    else:
        parts.append("required " + (_codes(policy.required) if policy.required else "none"))
    if policy.minimum_required is not None:
        parts.append(f"minimum {policy.minimum_required}")
    if policy.acceptable_related:
        parts.append("acceptable " + ", ".join(
            _code(entry.commit) + (f" (credit {entry.credit:g})" if entry.credit else "")
            for entry in policy.acceptable_related))
    if policy.related_origins:
        parts.append("related origins " + _codes(policy.related_origins))
    if policy.related_but_not_correct:
        parts.append("related but not correct " + _codes(policy.related_but_not_correct))
    if policy.known_distractors:
        parts.append("known distractors " + _codes(policy.known_distractors))
    return "; ".join(parts)


def oracle_summary(data: dict[str, Any], suite: str) -> str:
    """The commit-level oracle the evaluator resolves, variant by variant.

    Read through ``_commit_level_policy`` so a default variant, an inferred
    direct BIC or a ``top_k`` oracle appears exactly as a scored run sees it.
    """
    from .evaluator import _commit_level_policy, _scenario_bfc_ids

    default = _commit_level_policy(data, suite, None)
    expected_szz = data.get("expected_szz") if isinstance(data.get("expected_szz"), dict) else {}
    variants = [v for v in (expected_szz.get("evaluation_variants") or []) if isinstance(v, dict) and v.get("name")]
    if variants:
        label = "default"
        if default.evaluation_variant:
            label += f" ({_code(default.evaluation_variant)})"
        pieces = [f"{label}: {_policy_phrase(default)}"]
        for variant in variants:
            if variant["name"] == default.evaluation_variant:
                continue
            pieces.append(f"{_code(variant['name'])}: {_policy_phrase(_commit_level_policy(data, suite, variant['name']))}")
        summary = " · ".join(pieces)
    else:
        summary = _policy_phrase(default)
    bfcs = _scenario_bfc_ids(data)
    if bfcs:
        summary += f" · {'BFC' if len(bfcs) == 1 else 'BFCs'} {_codes(bfcs)}"
    return summary


def graph_features(data: dict[str, Any]) -> list[str]:
    """What a graph scenario uses that the classic schema cannot express.

    The classic schema is a linear ``main`` history of ``write_file`` /
    ``replace`` operations with one bug per scenario and a commit-level
    exact-set oracle; everything else is a reason for a scenario to live in
    the graph suite, and this lists the ones a scenario actually has.
    """
    commits = [c for c in (data.get("commits") or []) if isinstance(c, dict)]
    features: list[str] = []

    branches: list[str] = []
    for commit in commits:
        branch = commit.get("branch")
        if isinstance(branch, str) and branch not in branches:
            branches.append(branch)
    if len(branches) > 1:
        features.append(f"{len(branches)} branches")
    merges = [str(c.get("id")) for c in commits if len(c.get("parents") or []) > 1]
    if merges:
        features.append(("merge commit " if len(merges) == 1 else "merge commits ") + _codes(merges))
    for key, label in REPLAY_KEYS:
        ids = [str(c.get("id")) for c in commits if key in c]
        if ids:
            features.append(f"{label} {_codes(ids)}")
    operations: list[str] = []
    for commit in commits:
        for op in commit.get("operations") or []:
            kind = op.get("type") if isinstance(op, dict) else None
            if isinstance(kind, str) and kind not in SUPPORTED_OPERATIONS and kind not in operations:
                operations.append(kind)
    generated = (data.get("commit_generators") or any("commit_generator" in c for c in commits)
                 or "commit_generator" in operations)
    operations = [kind for kind in operations if kind != "commit_generator"]
    if generated:
        features.append("generated commits (`commit_generator`)")
    graph = data.get("graph") if isinstance(data.get("graph"), dict) else {}
    if graph.get("ref_lifecycle"):
        features.append("ref lifecycle")
    if operations:
        features.append(("operation " if len(operations) == 1 else "operations ") + _codes(operations))

    from .graph_scenario import graph_bfc_entries, graph_bic_entries, graph_faults

    bugs = [b for b in (data.get("bugs") or []) if isinstance(b, dict)]
    if len(bugs) > 1:
        features.append(f"{len(bugs)} bugs")
    most_bics = max((len(graph_bic_entries(b)) for b in bugs), default=0)
    if most_bics > 1:
        features.append(f"{most_bics} BICs")
    most_bfcs = max((len(graph_bfc_entries(b)) for b in bugs), default=0)
    if most_bfcs > 1:
        features.append(f"{most_bfcs} BFCs")
    if any(b.get("origin_faults") for b in bugs):
        features.append("origin faults")
    most_faults = max((len(graph_faults(b)) for b in bugs), default=0)
    if most_faults > 1:
        features.append(f"{most_faults} fault sites")

    expected_szz = data.get("expected_szz") if isinstance(data.get("expected_szz"), dict) else {}
    commit_level = expected_szz.get("commit_level") if isinstance(expected_szz.get("commit_level"), dict) else {}
    policy = commit_level.get("evaluation_policy")
    if isinstance(policy, str) and policy != "exact_set":
        features.append(f"policy {_code(policy)}")
    variants = [v.get("name") for v in (expected_szz.get("evaluation_variants") or []) if isinstance(v, dict)]
    if variants:
        noun = "evaluation variant" if len(variants) == 1 else "evaluation variants"
        features.append(f"{len(variants)} {noun} ({_codes([str(v) for v in variants])})")
    for level in GRAPH_ONLY_ORACLE_LEVELS:
        if expected_szz.get(level):
            features.append(f"{_code(level)} oracle")
    for section in GRAPH_CONTEXT_SECTIONS:
        if data.get(section):
            features.append(_code(section))
    return features


NO_GRAPH_FEATURE = ("none: a linear history with one bug and an exact-set oracle, "
                    "kept in the graph suite for its category")


def header_rows(data: dict[str, Any], suite: str) -> list[tuple[str, str]]:
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else {}
    code = meta.get("category_code")
    name = meta.get("category")
    category = " ".join(part for part in (_code(code) if code else "", str(name) if name else "") if part) or "—"
    factors = [f for f in (meta.get("factors") or []) if isinstance(f, str)]
    rows = [
        ("category", category),
        ("tier", _code(meta.get("tier")) if meta.get("tier") else "—"),
        ("status", _code(meta.get("status")) if meta.get("status") else "—"),
        ("difficulty", _code(meta.get("difficulty")) if meta.get("difficulty") else "—"),
        ("language", _code(repository.get("language")) if repository.get("language") else "—"),
        ("factors", _codes(factors) if factors else "—"),
        ("oracle", oracle_summary(data, suite)),
    ]
    if suite == "advanced-scenarios":
        features = graph_features(data)
        rows.append(("graph features", "; ".join(features) if features else NO_GRAPH_FEATURE))
    return rows


def render_header(data: dict[str, Any], suite: str) -> str:
    """The exact text a README must start with."""
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    lines = [f"# {meta.get('id')}: {str(meta.get('title', '')).strip()}", "", HEADER_BEGIN, "| | |", "|---|---|"]
    for key, value in header_rows(data, suite):
        lines.append(f"| {key} | {value} |")
    lines.append(HEADER_END)
    return "\n".join(lines) + "\n"


# --- checking and applying -----------------------------------------------------

def split_header(text: str) -> tuple[str | None, str]:
    """``(header, rest)``: the generated header a README carries, or ``None``."""
    begin = text.find(HEADER_BEGIN)
    end = text.find(HEADER_END)
    if begin < 0 or end < begin:
        return None, text
    end += len(HEADER_END)
    if end < len(text) and text[end] == "\n":
        end += 1
    return text[:end], text[end:]


def check_readme(text: str, header: str) -> list[str]:
    """Why a README disagrees with its scenario; empty when it agrees."""
    problems: list[str] = []
    existing, _ = split_header(text)
    if existing is None:
        problems.append("has no generated header")
    elif existing != header:
        for have, want in zip(existing.splitlines(), header.splitlines()):
            if have != want:
                problems.append(f"header is stale: {have!r} should read {want!r}")
                break
        else:
            problems.append("header is stale: the two differ in length")
    for match in LEGACY_SECTION_RE.finditer(text):
        title = match.group(0).splitlines()[0].strip()
        problems.append(f"carries a `{title}` section, a hand-written copy of what the header states")
    return problems


def _strip_leading_title(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return "\n".join(lines)


def apply_header(text: str, header: str) -> str:
    """The README with ``header`` in place and the legacy copies removed."""
    existing, rest = split_header(text)
    if existing is None:
        rest = _strip_leading_title(text)
    rest = LEGACY_SECTION_RE.sub("", rest)
    rest = re.sub(r"\n{3,}", "\n\n", rest).strip("\n")
    return header + ("\n" + rest + "\n" if rest else "")


# --- running over the suites ------------------------------------------------

@dataclass
class ReadmeStatus:
    scenario_id: str
    readme: Path
    problems: list[str] = field(default_factory=list)
    written: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"scenario_id": self.scenario_id, "readme": str(self.readme), "problems": self.problems,
                "written": self.written, "error": self.error}


def scenario_files(scenarios_root: Path, advanced_scenarios_root: Path) -> list[Path]:
    files = sorted(scenarios_root.glob("SZZ-*/scenario.yml"))
    files += sorted(advanced_scenarios_root.glob("SZZG-*/scenario.graph.yml"))
    return files


def resolve_targets(targets: list[str]) -> list[Path]:
    """Scenario files named on the command line, directly or by directory."""
    files: list[Path] = []
    for raw in targets:
        path = Path(raw)
        if path.is_dir():
            for name in ("scenario.yml", "scenario.graph.yml"):
                if (path / name).exists():
                    files.append(path / name)
        else:
            files.append(path)
    return files


def sync_readme(scenario_path: Path, *, write: bool) -> ReadmeStatus:
    """Check one README against its scenario; rewrite it when ``write``."""
    readme = scenario_path.with_name("README.md")
    status = ReadmeStatus(scenario_id=scenario_path.parent.name, readme=readme)
    data, result = load_yaml(scenario_path)
    if data is None:
        status.error = "; ".join(f.message for f in result.findings)
        return status
    header = render_header(data, suite_of(scenario_path))
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    status.problems = check_readme(text, header) if text else ["is missing"]
    if status.problems and write:
        readme.write_text(apply_header(text, header), encoding="utf-8")
        status.written = True
    return status


def run_readme(files: list[Path], *, write: bool) -> dict[str, Any]:
    statuses = [sync_readme(path, write=write) for path in files]
    return {
        "scenario_count": len(statuses),
        "current": sum(1 for s in statuses if not s.problems and s.error is None),
        "written": sum(1 for s in statuses if s.written),
        "stale": [s.to_dict() for s in statuses if s.problems],
        "errors": [s.to_dict() for s in statuses if s.error],
    }


def format_readme_report(report: dict[str, Any], *, write: bool) -> str:
    lines = []
    for item in report["stale"]:
        verb = "rewrote" if item["written"] else "stale"
        lines.append(f"{verb}: {item['readme']}")
        for problem in item["problems"]:
            lines.append(f"    {problem}")
    for item in report["errors"]:
        lines.append(f"error: {item['scenario_id']}: {item['error']}")
    lines.append(
        f"{report['scenario_count']} scenario(s): {report['current']} README header(s) current, "
        f"{len(report['stale'])} {'rewritten' if write else 'stale or missing'}, {len(report['errors'])} unreadable"
    )
    return "\n".join(lines)
