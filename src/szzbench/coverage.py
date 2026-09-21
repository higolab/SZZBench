"""What does each scenario contribute that no other scenario does?

The 2026-09-17 review proposed merging or deleting 51 scenarios, but every one
of them has since been rebuilt, so the proposals no longer describe the suite
(issue #12). This module replaces that list with a measurement of the current
scenarios along the dimensions that decide how hard the bug-introducing commit
is to find, and groups the scenarios that agree on all of them.

A large group is redundancy. An empty combination is a gap.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .baselines import GitProbe, Scenario, _load_scenarios
from .evaluator import _commit_level_policy, _load_scenario_for_evaluation

#: The dimensions a scenario is grouped by.  ``category`` keeps scenarios that
#: test different failure modes apart even when their shape agrees.
SIGNATURE_FIELDS = ("suite", "category", "oracle_size", "bic_depth",
                    "fault_file_distractors", "commit_count", "ref_count")


@dataclass
class ScenarioShape:
    scenario_id: str
    suite: str
    category: str | None
    tier: str | None
    commit_count: int
    ref_count: int
    oracle_size: int
    bic_depth: int | None
    fault_file_distractors: int
    factors: list[str]

    def signature(self) -> tuple[Any, ...]:
        return tuple(getattr(self, field) for field in SIGNATURE_FIELDS)

    def to_dict(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in
                ("scenario_id", "tier", *SIGNATURE_FIELDS, "factors")}


def _oracle_ids(data: dict[str, Any], suite: str) -> set[str]:
    """The required set the evaluator would use.

    Reading the YAML fields directly is not enough: a graph scenario can select
    its required set through a default evaluation variant, and a scenario that
    omits ``required`` has its direct BICs inferred.  Four shipped scenarios
    looked like empty oracles that way (PR #38 review).
    """
    return set(_commit_level_policy(data, suite, None).required)


def _fault_files(data: dict[str, Any]) -> set[str]:
    files: set[str] = set()
    for bug in data.get("bugs") or []:
        for key in ("fault", "fix"):
            entry = bug.get(key)
            if isinstance(entry, dict) and entry.get("file"):
                files.add(entry["file"])
        for key in ("faults", "fixes", "origin_faults"):
            for entry in bug.get(key) or []:
                if isinstance(entry, dict) and entry.get("file"):
                    files.add(entry["file"])
    return files


def _shape(scenario: Scenario, data: dict[str, Any], git: GitProbe) -> ScenarioShape:
    required = _oracle_ids(data, scenario.suite)
    files = _fault_files(data)
    order = scenario.hashes
    index_of = {h: i for i, h in enumerate(order)}
    bfc_positions = [index_of[h] for h in scenario.bfc_hashes if h in index_of]
    last_bfc = max(bfc_positions) if bfc_positions else len(order) - 1
    hash_of_id = {c.logical_id: c.hash for c in scenario.commits if c.logical_id}
    bic_positions = [index_of[hash_of_id[r]] for r in required if r in hash_of_id]

    # How many *wrong* answers a blame-style tool has to choose between: commits
    # before the fix that touch a file the fault lives in and are not the answer.
    required_hashes = {hash_of_id[r] for r in required if r in hash_of_id}
    distractors = 0
    for position, commit in enumerate(scenario.commits):
        if position >= last_bfc or commit.hash in scenario.bfc_hashes or commit.hash in required_hashes:
            continue
        if set(git.paths_touched(scenario.repo_dir, commit.hash)) & files:
            distractors += 1
    refs = [r for r in git(scenario.repo_dir, "for-each-ref", "--format=%(refname)").splitlines() if r]
    return ScenarioShape(
        scenario_id=scenario.scenario_id,
        suite=scenario.suite,
        category=scenario.category,
        tier=(data.get("meta") or {}).get("tier"),
        commit_count=len(order),
        ref_count=len(refs),
        oracle_size=len(required),
        # the *farthest* required BIC: the deepest one a tool has to reach
        bic_depth=(last_bfc - min(bic_positions)) if bic_positions else None,
        fault_file_distractors=distractors,
        factors=sorted((data.get("meta") or {}).get("factors") or []),
    )


def run_coverage(
    *,
    generated_root: Path,
    scenarios_root: Path,
    advanced_scenarios_root: Path,
    variant: str = "default",
) -> dict[str, Any]:
    git = GitProbe()
    warnings: list[str] = []
    scenarios, errors = _load_scenarios(generated_root, scenarios_root, advanced_scenarios_root,
                                        variant, git, warnings=warnings)
    shapes: list[ScenarioShape] = []
    for scenario in scenarios:
        path = scenarios_root / scenario.scenario_id / "scenario.yml"
        if not path.exists():
            path = advanced_scenarios_root / scenario.scenario_id / "scenario.graph.yml"
        data, _ = _load_scenario_for_evaluation(path, scenario.suite)
        if data is None:
            errors.append(f"{scenario.scenario_id}: cannot read the scenario for coverage.")
            continue
        shapes.append(_shape(scenario, data, git))

    groups: dict[tuple[Any, ...], list[str]] = collections.defaultdict(list)
    for shape in shapes:
        groups[shape.signature()].append(shape.scenario_id)

    distributions = {
        field: dict(sorted(collections.Counter(getattr(s, field) for s in shapes).items(),
                           key=lambda kv: (kv[0] is None, str(kv[0]))))
        for field in ("tier", "oracle_size", "bic_depth", "fault_file_distractors",
                      "commit_count", "ref_count")
    }
    redundant = sorted((sorted(v) for v in groups.values() if len(v) > 1), key=len, reverse=True)
    return {
        "scenario_count": len(shapes),
        "distinct_signatures": len(groups),
        "signature_fields": list(SIGNATURE_FIELDS),
        "distributions": distributions,
        "redundant_groups": [
            {"size": len(members),
             "signature": dict(zip(SIGNATURE_FIELDS, next(k for k, v in groups.items() if sorted(v) == members))),
             "scenarios": members}
            for members in redundant
        ],
        "unique_scenarios": sorted(v[0] for v in groups.values() if len(v) == 1),
        "shapes": [s.to_dict() for s in shapes],
        "errors": errors + git.failures,
        "warnings": warnings,
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [f"Coverage over {report['scenario_count']} generated scenario(s)", ""]
    lines.append("  distribution of each difficulty dimension")
    for field, counts in report["distributions"].items():
        pairs = ", ".join(f"{k}:{v}" for k, v in counts.items())
        lines.append(f"      {field:22s} {pairs}")
    lines.append("")
    groups = report["redundant_groups"]
    covered = sum(g["size"] for g in groups)
    lines.append(f"  {report['distinct_signatures']} distinct signatures; "
                 f"{len(groups)} group(s) of two or more, covering {covered} scenarios")
    lines.append(f"  signature = {', '.join(report['signature_fields'])}")
    for group in groups[:15]:
        signature = group["signature"]
        shown = ", ".join(group["scenarios"][:8])
        more = " ..." if group["size"] > 8 else ""
        lines.append(f"      {group['size']:3d}x  " + "  ".join(f"{k}={v}" for k, v in signature.items()))
        lines.append(f"           {shown}{more}")
    if len(groups) > 15:
        lines.append(f"      ... and {len(groups) - 15} more group(s)")
    lines.append("")
    lines.append(f"  scenarios with a unique signature: {len(report['unique_scenarios'])}")
    for warning in report.get("warnings", []):
        lines.append(f"  [WARNING] {warning}")
    for error in report["errors"]:
        lines.append(f"  [ERROR] {error}")
    return "\n".join(lines)
