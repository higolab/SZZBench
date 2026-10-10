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
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .baselines import GitProbe, History, Scenario, _bfc_hashes, _load_scenarios, blame_deleted_lines
from .evaluator import _commit_level_policy, _load_scenario_for_evaluation, classify_diff_text

#: What plain first-parent blame on the lines the fix deletes does with the
#: oracle (``decisions/vocabulary.md`` section 4).  Measured, never hand-edited.
BLAME_CLASSES = ("exact", "extra", "miss", "addition-only", "empty-first-parent")

#: The difficulty a scenario must declare at least, given what plain blame does
#: with its oracle (``decisions/vocabulary.md`` section 4, decided 2026-09-22).
#: A scenario may declare more when its README names another failure mode; it
#: may never declare less.
DIFFICULTY_FLOOR = {"exact": "easy", "extra": "medium", "addition-only": "medium",
                    "miss": "hard", "empty-first-parent": "hard"}
DIFFICULTIES = ("easy", "medium", "hard")

#: The dimensions a scenario is grouped by.  ``category`` keeps scenarios that
#: test different failure modes apart even when their shape agrees.
SIGNATURE_FIELDS = ("suite", "category", "oracle_size", "bic_depth",
                    "fault_file_distractors", "commit_count", "ref_count")

#: How the report spells a dimension with no value, such as the ``bic_depth``
#: of an empty oracle, in ``coverage.md`` and ``coverage.json`` alike (issue #185).
NO_VALUE = "none"


@dataclass
class ScenarioShape:
    scenario_id: str
    suite: str
    category: str | None
    tier: str | None
    difficulty: str | None
    blame_class: str | None
    commit_count: int
    ref_count: int
    oracle_size: int
    bic_depth: int | None
    fault_file_distractors: int
    factors: list[str]
    fault_statements: list[str]

    def signature(self) -> tuple[Any, ...]:
        return tuple(getattr(self, field) for field in SIGNATURE_FIELDS)

    @property
    def difficulty_floor(self) -> str | None:
        return DIFFICULTY_FLOOR.get(self.blame_class or "")

    def to_dict(self) -> dict[str, Any]:
        data = {field: getattr(self, field) for field in
                ("scenario_id", "tier", "difficulty", "blame_class", *SIGNATURE_FIELDS, "factors", "fault_statements")}
        data["difficulty_floor"] = self.difficulty_floor
        return data


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


def _fault_statements(data: dict[str, Any]) -> list[str]:
    """Every fault statement a scenario declares (``fault.statement``,
    ``faults[].statement``, ``origin_faults[].statement``), whitespace-normalised
    and without duplicates, in declaration order.

    This is the text issue #13 counts: the same statement in many scenarios is
    the template monoculture, and a scenario that repeats one statement in two
    fault entries (a copy and its origin) counts it once.
    """
    found: list[str] = []
    for bug in data.get("bugs") or []:
        if not isinstance(bug, dict):
            continue
        entries: list[Any] = [bug.get("fault")]
        for key in ("faults", "origin_faults"):
            value = bug.get(key)
            entries.extend(value if isinstance(value, list) else [])
        for entry in entries:
            statement = entry.get("statement") if isinstance(entry, dict) else None
            if isinstance(statement, str) and statement.strip():
                normalized = re.sub(r"\s+", " ", statement.strip())
                if normalized not in found:
                    found.append(normalized)
    return found


def _fault_reuse(shapes: list[ScenarioShape]) -> dict[str, Any]:
    """How many scenarios share each fault statement, overall and per category."""
    carriers: dict[str, list[str]] = collections.defaultdict(list)
    suite_of = {s.scenario_id: s.suite for s in shapes}
    for shape in shapes:
        for statement in shape.fault_statements:
            carriers[statement].append(shape.scenario_id)
    shared = []
    for statement, ids in sorted(carriers.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(ids) < 2:
            break
        shared.append({
            "statement": statement,
            "scenarios": len(ids),
            "by_suite": dict(sorted(collections.Counter(suite_of[i] for i in ids).items())),
            "scenario_ids": sorted(ids),
        })
    per_category: dict[str, Any] = {}
    for category in sorted({str(s.category) for s in shapes}):
        members = [s for s in shapes if str(s.category) == category]
        counter = collections.Counter(st for s in members for st in s.fault_statements)
        top = counter.most_common(1)
        per_category[category] = {
            "scenarios": len(members),
            "distinct_statements": len(counter),
            "most_reused": top[0][0] if top else None,
            "most_reused_scenarios": top[0][1] if top else 0,
        }
    return {
        "scenarios_with_a_statement": sum(1 for s in shapes if s.fault_statements),
        "distinct_statements": len(carriers),
        "shared": shared,
        "per_category": per_category,
    }


def _blame_class(history: History, git: GitProbe, required_hashes: set[str]) -> str | None:
    """Classify what naive blame does with this scenario's oracle.

    ``empty-first-parent``: no bug-fixing commit changes anything against its
    first parent (a merge that only records the fix arriving).
    ``addition-only``: the fixes only add lines, so there is nothing to blame.
    Otherwise the lines every fix deletes are blamed at the fix's first parent
    and the set of commits compared with the required set: ``exact`` when they
    are the same, ``extra`` when every required commit is blamed and others
    besides, ``miss`` when a required commit is not blamed at all.  An empty
    oracle (``expect_no_bic``) with any blamed commit is ``extra``.
    """
    bfcs = _bfc_hashes(history)
    if not bfcs:
        return None
    # The first parent, or the empty tree for a root fix: a root commit has no
    # ``<hash>^``, and a failed Git call must not read as an empty merge diff.
    shapes = [classify_diff_text(git(history.repo_dir, "diff", "--no-color", "--no-ext-diff", "-U0",
                                     "--no-renames", git.parent_of(history.repo_dir, bfc), bfc))
              for bfc in bfcs]
    if all(shape == "empty_first_parent" for shape in shapes):
        return "empty-first-parent"
    if all(shape in ("empty_first_parent", "addition_only") for shape in shapes):
        return "addition-only"
    blamed = set(blame_deleted_lines(git, history))
    if blamed == required_hashes:
        return "exact"
    if required_hashes <= blamed:
        return "extra"
    return "miss"


def _shape(scenario: Scenario, data: dict[str, Any], git: GitProbe) -> ScenarioShape:
    required = _oracle_ids(data, scenario.suite)
    files = _fault_files(data)
    history = scenario.history
    order = history.hashes
    index_of = {h: i for i, h in enumerate(order)}
    bfc_positions = [index_of[h] for h in history.bfc_hashes if h in index_of]
    last_bfc = max(bfc_positions) if bfc_positions else len(order) - 1
    hash_of_id = scenario.hash_of_id
    bic_positions = [index_of[hash_of_id[r]] for r in required if r in hash_of_id]

    # How many *wrong* answers a blame-style tool has to choose between: commits
    # before the fix that touch a file the fault lives in and are not the answer.
    required_hashes = {hash_of_id[r] for r in required if r in hash_of_id}
    distractors = 0
    for position, commit in enumerate(history.commits):
        if position >= last_bfc or commit.hash in history.bfc_hashes or commit.hash in required_hashes:
            continue
        if set(git.paths_touched(history.repo_dir, commit.hash)) & files:
            distractors += 1
    refs = [r for r in git(history.repo_dir, "for-each-ref", "--format=%(refname)").splitlines() if r]
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    return ScenarioShape(
        scenario_id=scenario.scenario_id,
        suite=scenario.suite,
        category=scenario.category,
        tier=meta.get("tier"),
        difficulty=str(meta["difficulty"]) if meta.get("difficulty") is not None else None,
        blame_class=_blame_class(history, git, required_hashes),
        commit_count=len(order),
        ref_count=len(refs),
        oracle_size=len(required),
        # the *farthest* required BIC: the deepest one a tool has to reach
        bic_depth=(last_bfc - min(bic_positions)) if bic_positions else None,
        fault_file_distractors=distractors,
        factors=sorted(meta.get("factors") or []),
        fault_statements=_fault_statements(data),
    )


def _difficulty_check(shapes: list[ScenarioShape]) -> dict[str, list[dict[str, Any]]]:
    """Declared ``difficulty`` against the floor its ``blame_class`` sets.

    ``below_floor`` is a contradiction to fix (a scenario claims to be easier
    than plain blame shows it is); ``above_floor`` is an allowed override,
    listed so the reason can be looked for in the README; ``ungraded`` is a
    declaration outside ``easy``/``medium``/``hard`` (the graph suite's old
    ``advanced``) or a scenario without a measurable class.
    """
    below: list[dict[str, Any]] = []
    above: list[dict[str, Any]] = []
    ungraded: list[dict[str, Any]] = []
    for shape in shapes:
        floor = shape.difficulty_floor
        entry = {"scenario_id": shape.scenario_id, "declared": shape.difficulty, "floor": floor,
                 "blame_class": shape.blame_class}
        if floor is None or shape.difficulty not in DIFFICULTIES:
            ungraded.append(entry)
        elif DIFFICULTIES.index(shape.difficulty) < DIFFICULTIES.index(floor):
            below.append(entry)
        elif DIFFICULTIES.index(shape.difficulty) > DIFFICULTIES.index(floor):
            above.append(entry)
    return {"below_floor": below, "above_floor": above, "ungraded": ungraded}


def _difficulty_by_blame_class(shapes: list[ScenarioShape]) -> dict[str, dict[str, dict[str, int]]]:
    """Per suite, how many scenarios declare each ``difficulty`` for each measured
    ``blame_class`` -- the table the grading rule of ``decisions/vocabulary.md``
    section 4 is checked against."""
    table: dict[str, dict[str, dict[str, int]]] = {}
    for shape in shapes:
        by_class = table.setdefault(shape.suite, {})
        row = by_class.setdefault(str(shape.blame_class), {})
        row[str(shape.difficulty)] = row.get(str(shape.difficulty), 0) + 1
    return {suite: {cls: dict(sorted(row.items())) for cls, row in sorted(by_class.items())}
            for suite, by_class in sorted(table.items())}


def _distribution(values: Iterable[Any]) -> dict[Any, int]:
    """How many scenarios take each value: integers in numeric order, then
    strings, then the missing value as :data:`NO_VALUE`.

    Ordering by the string form put ``1003`` between ``1`` and ``2``, and the
    missing value came out as ``None`` in ``coverage.md`` and ``null`` in
    ``coverage.json`` (issue #185).
    """
    counts = collections.Counter(values)
    order = sorted(counts, key=lambda k: (k is None, not isinstance(k, int), k if isinstance(k, int) else str(k)))
    return {NO_VALUE if k is None else k: counts[k] for k in order}


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
        field: _distribution(getattr(s, field) for s in shapes)
        for field in ("tier", "blame_class", "oracle_size", "bic_depth", "fault_file_distractors",
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
        "fault_reuse": _fault_reuse(shapes),
        "difficulty_by_blame_class": _difficulty_by_blame_class(shapes),
        "difficulty_check": _difficulty_check(shapes),
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
    reuse = report.get("fault_reuse")
    if reuse:
        lines.append("  fault statement reuse (fault.statement, faults[].statement, origin_faults[].statement; whitespace-normalised)")
        lines.append(f"      {reuse['distinct_statements']} distinct statement(s) over {reuse['scenarios_with_a_statement']} scenario(s); "
                     f"{len(reuse['shared'])} shared by two or more")
        for item in reuse["shared"][:8]:
            suites = ", ".join(f"{k} {v}" for k, v in item["by_suite"].items())
            lines.append(f"      {item['scenarios']:3d}x  {item['statement']}   ({suites})")
        if len(reuse["shared"]) > 8:
            lines.append(f"      ... and {len(reuse['shared']) - 8} more shared statement(s)")
        shares = ", ".join(f"{cat} {v['most_reused_scenarios']}/{v['scenarios']}"
                           for cat, v in reuse["per_category"].items() if v["most_reused_scenarios"] > 1)
        lines.append(f"      most reused statement per category: {shares or 'none shared'}")
        lines.append("")
    cross = report.get("difficulty_by_blame_class")
    if cross:
        lines.append("  declared difficulty by measured blame class (decisions/vocabulary.md section 4)")
        for suite, by_class in cross.items():
            for cls, row in by_class.items():
                cells = ", ".join(f"{difficulty}:{count}" for difficulty, count in row.items())
                lines.append(f"      {suite:19s} {cls:19s} {cells}")
        lines.append("")
    check = report.get("difficulty_check")
    if check is not None:
        floor = ", ".join(f"{cls}->{level}" for cls, level in DIFFICULTY_FLOOR.items())
        lines.append(f"  difficulty floor ({floor}): {len(check['below_floor'])} below, "
                     f"{len(check['above_floor'])} above (allowed overrides), {len(check['ungraded'])} ungraded")
        for entry in check["below_floor"]:
            lines.append(f"      [BELOW FLOOR] {entry['scenario_id']} declares {entry['declared']} but blame is "
                         f"{entry['blame_class']}, so at least {entry['floor']}")
        for entry in check["ungraded"][:10]:
            lines.append(f"      [UNGRADED] {entry['scenario_id']} declares {entry['declared']!r}")
        if len(check["ungraded"]) > 10:
            lines.append(f"      ... and {len(check['ungraded']) - 10} more ungraded")
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
        lines.append(f"      {group['size']:3d}x  " + "  ".join(f"{k}={NO_VALUE if v is None else v}"
                                                             for k, v in signature.items()))
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
