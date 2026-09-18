"""Cheap baselines: how much of SZZBench is solved without doing SZZ.

A benchmark result only means something against a floor.  This module runs a
declared family of predictors over the generated repositories and scores them
with the ordinary evaluator, so the numbers are produced by exactly the
policies a real tool run is scored with.

The families are ordered by how much of the repository they read:

``metadata``
    author, date and commit message only.  These must stay at chance: a
    predictor that recovers the oracle from metadata means the oracle leaked
    (issues #8, #9, and ``docs/decisions/oracle-leakage.md``).
``position``
    the shape of the history only — a commit's index, or its distance from the
    bug-fixing commit.  No file is opened.
``shape``
    which files and lines the commits touch, without interpreting them.
``blame``
    the classic SZZ baseline: ``git blame`` on the lines the fix deletes.

``position`` and ``shape`` are legitimate signals rather than leaks, but they
are the floor a real SZZ variant has to beat, so they are reported and not
silenced.
"""
from __future__ import annotations

import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .evaluator import Prediction, evaluate_prediction_map
from .gitutils import GitError, run_git

#: Ordered families, cheapest first.
FAMILIES = ("metadata", "position", "shape", "blame")


@dataclass
class Scenario:
    """Everything a baseline predictor may look at."""

    scenario_id: str
    suite: str
    category: str | None
    commit_ids: list[str]
    bfc_ids: list[str]
    authors: dict[str, str]
    messages: dict[str, str]
    hash_of: dict[str, str]
    id_of: dict[str, str]
    repo_dir: Path


@dataclass
class BaselineResult:
    name: str
    family: str
    description: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.failed)

    @property
    def rate(self) -> float:
        return len(self.passed) / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family,
            "description": self.description,
            "passed": len(self.passed),
            "total": self.total,
            "rate": self.rate,
            "solved": sorted(self.passed),
        }


# ---------------------------------------------------------------------------
# predictors
# ---------------------------------------------------------------------------

Predictor = Callable[[Scenario], Iterable[str]]

#: Whole words that admit a fault.  Deliberately not the validator's lint
#: pattern: a guard must not be measured with the instrument it guards.
ADMITS_FAULT = re.compile(r"\b(bugs?|buggy|faulty|faults?|defects?|broken|BIC|distractor|noise)\b", re.I)


def _non_bfc(scenario: Scenario) -> list[str]:
    return [c for c in scenario.commit_ids if c not in scenario.bfc_ids]


def _by_author(author: str) -> Predictor:
    def predict(scenario: Scenario) -> list[str]:
        return [c for c in scenario.commit_ids if scenario.authors.get(c) == author]
    return predict


def _message_admits_fault(scenario: Scenario) -> list[str]:
    return [c for c in _non_bfc(scenario) if ADMITS_FAULT.search(scenario.messages.get(c, ""))]


def _at_index(index: int) -> Predictor:
    def predict(scenario: Scenario) -> list[str]:
        ids = scenario.commit_ids
        return [ids[index]] if len(ids) > index else []
    return predict


def _before_bfc(scenario: Scenario) -> list[str]:
    positions = [i for i, c in enumerate(scenario.commit_ids) if c in scenario.bfc_ids]
    if not positions or positions[-1] == 0:
        return []
    return [scenario.commit_ids[positions[-1] - 1]]


def _all_non_bfc(scenario: Scenario) -> list[str]:
    return _non_bfc(scenario)


def _git(repo: Path, *args: str) -> str:
    try:
        return run_git(repo, list(args)).stdout
    except GitError:
        return ""


def _bfc_hashes(scenario: Scenario) -> list[str]:
    return [scenario.hash_of[b] for b in scenario.bfc_ids if b in scenario.hash_of]


def _files_touched(repo: Path, commit: str) -> list[str]:
    out = _git(repo, "diff", "--name-only", "--no-renames", f"{commit}^", commit)
    return [line for line in out.splitlines() if line.strip()]


def _last_toucher(scenario: Scenario) -> list[str]:
    """The newest commit before the fix that touched any file the fix touches."""
    found: list[str] = []
    for bfc_hash in _bfc_hashes(scenario):
        for path in _files_touched(scenario.repo_dir, bfc_hash):
            out = _git(scenario.repo_dir, "log", "-1", "--format=%H", f"{bfc_hash}^", "--", path)
            commit_hash = out.strip()
            if commit_hash and scenario.id_of.get(commit_hash):
                found.append(scenario.id_of[commit_hash])
    return sorted(set(found))


_HUNK_RE = re.compile(r"@@ -(\d+)")


def _blame_deleted_lines(scenario: Scenario) -> list[str]:
    """Naive B-SZZ: blame every line the fix deletes, against its first parent."""
    found: list[str] = []
    for bfc_hash in _bfc_hashes(scenario):
        diff = _git(scenario.repo_dir, "diff", "-U0", "--no-renames", f"{bfc_hash}^", bfc_hash)
        path: str | None = None
        line_no: int | None = None
        for line in diff.splitlines():
            if line.startswith("--- a/"):
                path = line[6:]
            elif line.startswith("--- /dev/null"):
                path = None
            elif line.startswith("@@"):
                match = _HUNK_RE.match(line)
                line_no = int(match.group(1)) if match else None
            elif line.startswith("-") and not line.startswith("---") and path and line_no is not None:
                porcelain = _git(scenario.repo_dir, "blame", "--line-porcelain",
                                 "-L", f"{line_no},{line_no}", f"{bfc_hash}^", "--", path)
                if porcelain:
                    commit_hash = porcelain.split("\n", 1)[0].split()[0]
                    if scenario.id_of.get(commit_hash):
                        found.append(scenario.id_of[commit_hash])
                line_no += 1
            elif line.startswith(" ") and line_no is not None:
                line_no += 1
    return sorted(set(found))


def build_predictors(scenarios: list[Scenario]) -> list[tuple[str, str, str, Predictor]]:
    """(name, family, description, predictor), including one rule per author.

    The author rules are enumerated over the whole suite and only their best is
    reported: an attacker picks one rule and applies it everywhere, and
    choosing the matching author per scenario would need the oracle.
    """
    predictors: list[tuple[str, str, str, Predictor]] = []
    for author in sorted({a for s in scenarios for a in s.authors.values()}):
        name = author.split("<")[0].strip() or author
        predictors.append((f"author:{name}", "metadata",
                           f"report every commit written by {name}", _by_author(author)))
    predictors.append(("message-admits-fault", "metadata",
                       "report the non-fixing commits whose message admits a fault",
                       _message_admits_fault))
    for index, ordinal in ((0, "first"), (1, "second"), (2, "third")):
        predictors.append((f"position-{ordinal}", "position",
                           f"report the {ordinal} commit of the history", _at_index(index)))
    predictors.append(("position-before-fix", "position",
                       "report the commit listed immediately before the fix", _before_bfc))
    predictors.append(("position-all-non-fix", "position",
                       "report every commit that is not a fix", _all_non_bfc))
    predictors.append(("shape-last-toucher", "shape",
                       "report the newest commit before the fix that touched a file the fix touches",
                       _last_toucher))
    predictors.append(("blame-deleted-lines", "blame",
                       "naive B-SZZ: blame every line the fix deletes", _blame_deleted_lines))
    return predictors


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


def _load_scenarios(generated_root: Path, scenarios_root: Path, advanced_scenarios_root: Path,
                    variant: str) -> tuple[list[Scenario], list[str]]:
    from .evaluator import _find_scenario_path, _load_commit_map, _load_scenario_for_evaluation

    scenarios: list[Scenario] = []
    errors: list[str] = []
    for repo_dir in sorted(generated_root.glob(f"*/{variant}/repo")):
        if not (repo_dir / ".git").exists():
            continue
        scenario_id = repo_dir.parent.parent.name
        path, suite = _find_scenario_path(scenario_id, scenarios_root, advanced_scenarios_root)
        if path is None:
            errors.append(f"Cannot find scenario for '{scenario_id}'.")
            continue
        data, load_errors = _load_scenario_for_evaluation(path, suite)
        errors.extend(load_errors)
        if data is None:
            continue
        commit_map, map_errors = _load_commit_map(repo_dir.parent / "metadata" / "commit-map.json")
        errors.extend(map_errors)
        if commit_map is None:
            continue
        commits = data.get("commits") or []
        bfc_ids: list[str] = []
        for bug in data.get("bugs") or []:
            if bug.get("bug_fixing_commit"):
                bfc_ids.append(bug["bug_fixing_commit"])
            for entry in bug.get("bug_fixing_commits") or []:
                value = entry.get("commit") if isinstance(entry, dict) else entry
                if value:
                    bfc_ids.append(value)
        hash_of = {cid: entry["hash"] for cid, entry in commit_map.items()
                   if isinstance(entry, dict) and isinstance(entry.get("hash"), str)}
        authors = {cid: entry.get("author", "") for cid, entry in commit_map.items() if isinstance(entry, dict)}
        scenarios.append(Scenario(
            scenario_id=scenario_id,
            suite=suite,
            category=(data.get("meta") or {}).get("category_code"),
            commit_ids=[c.get("id") for c in commits if isinstance(c, dict) and c.get("id")],
            bfc_ids=list(dict.fromkeys(bfc_ids)),
            authors=authors,
            messages={c.get("id"): c.get("message") or "" for c in commits if isinstance(c, dict)},
            hash_of=hash_of,
            id_of={h: cid for cid, h in hash_of.items()},
            repo_dir=repo_dir,
        ))
    return scenarios, errors


def run_baselines(
    *,
    generated_root: Path,
    scenarios_root: Path,
    advanced_scenarios_root: Path,
    variant: str = "default",
    families: Iterable[str] = FAMILIES,
) -> dict[str, Any]:
    """Score every baseline and report the best of each family."""
    selected = [f for f in FAMILIES if f in set(families)]
    scenarios, errors = _load_scenarios(generated_root, scenarios_root, advanced_scenarios_root, variant)
    by_id = {s.scenario_id: s for s in scenarios}
    results: list[BaselineResult] = []
    for name, family, description, predictor in build_predictors(scenarios):
        if family not in selected:
            continue
        predictions: dict[str, list[Prediction]] = {}
        for scenario in scenarios:
            guessed = list(predictor(scenario))
            if guessed:
                predictions[scenario.scenario_id] = [
                    Prediction(scenario_id=scenario.scenario_id, inducing_commit=c, tool=f"baseline:{name}")
                    for c in guessed
                ]
        report = evaluate_prediction_map(
            predictions,
            generated_root=generated_root,
            scenarios_root=scenarios_root,
            advanced_scenarios_root=advanced_scenarios_root,
            variant=variant,
            include_generated=True,
        )
        result = BaselineResult(name=name, family=family, description=description)
        for item in report.scenarios:
            (result.passed if item.status == "PASS" else result.failed).append(item.scenario_id)
        results.append(result)

    results.sort(key=lambda r: (FAMILIES.index(r.family), -r.rate, r.name))
    solved_by_family: dict[str, set[str]] = defaultdict(set)
    for result in results:
        solved_by_family[result.family] |= set(result.passed)
    solved_any: set[str] = set().union(*solved_by_family.values()) if solved_by_family else set()
    unsolved = sorted(s.scenario_id for s in scenarios if s.scenario_id not in solved_any)

    per_category: dict[str, dict[str, int]] = {}
    for scenario in scenarios:
        bucket = per_category.setdefault(scenario.category or "?", {"total": 0, "solved": 0})
        bucket["total"] += 1
        if scenario.scenario_id in solved_any:
            bucket["solved"] += 1

    best_per_family = {}
    for family in selected:
        family_results = [r for r in results if r.family == family]
        if family_results:
            best = max(family_results, key=lambda r: r.rate)
            best_per_family[family] = {"name": best.name, "passed": len(best.passed), "total": best.total,
                                       "rate": best.rate}
    return {
        "scenario_count": len(scenarios),
        "baselines": [r.to_dict() for r in results],
        "best_per_family": best_per_family,
        "solved_by_any_baseline": len(solved_any),
        "unsolved": unsolved,
        "unsolved_detail": [
            {"scenario_id": sid, "category": by_id[sid].category, "commits": len(by_id[sid].commit_ids)}
            for sid in unsolved
        ],
        "per_category": per_category,
        "errors": errors,
    }


def format_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    total = report["scenario_count"]
    lines.append(f"Baselines over {total} generated scenario(s)")
    lines.append("")
    lines.append(f"  {'baseline':28s} {'family':9s} {'solves':>12s}")
    lines.append(f"  {'-' * 28} {'-' * 9} {'-' * 12}")
    for item in report["baselines"]:
        share = f"{item['passed']:3d}/{item['total']:<3d} {100 * item['rate']:5.1f}%"
        lines.append(f"  {item['name']:28s} {item['family']:9s} {share:>12s}")
    lines.append("")
    solved = report["solved_by_any_baseline"]
    lines.append(f"  solved by at least one baseline: {solved}/{total} = {100 * solved / total:.1f}%" if total else "")
    lines.append(f"  solved by none:                  {len(report['unsolved'])}")
    for item in report["unsolved_detail"]:
        lines.append(f"      {item['scenario_id']} [{item['category']}] {item['commits']} commits")
    lines.append("")
    lines.append("  per category (solved by any baseline / total)")
    for category in sorted(report["per_category"]):
        bucket = report["per_category"][category]
        rate = 100 * bucket["solved"] / bucket["total"] if bucket["total"] else 0.0
        lines.append(f"      {category:4s} {bucket['solved']:3d}/{bucket['total']:<3d} {rate:5.1f}%")
    for error in report["errors"]:
        lines.append(f"  [ERROR] {error}")
    return "\n".join(lines)
