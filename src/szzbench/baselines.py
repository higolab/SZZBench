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
class CommitInfo:
    """One materialized Git commit, as a predictor sees it."""

    hash: str
    logical_id: str | None
    author: str
    subject: str


@dataclass
class Scenario:
    """Everything a baseline predictor may look at.

    The commits are the **materialized** history, in
    ``git rev-list --all --topo-order --reverse`` order, so parents come before
    children and commits expanded by ``commit_generator`` are present.  A
    predictor names a commit by its hash; mapping that back to a logical id is
    the evaluator's job.
    """

    scenario_id: str
    suite: str
    category: str | None
    commits: list[CommitInfo]
    bfc_hashes: set[str]
    repo_dir: Path

    @property
    def hashes(self) -> list[str]:
        return [c.hash for c in self.commits]


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


def _non_bfc(scenario: Scenario) -> list[CommitInfo]:
    return [c for c in scenario.commits if c.hash not in scenario.bfc_hashes]


def _by_author(author: str) -> Predictor:
    def predict(scenario: Scenario) -> list[str]:
        return [c.hash for c in scenario.commits if c.author == author]
    return predict


def _message_admits_fault(scenario: Scenario) -> list[str]:
    return [c.hash for c in _non_bfc(scenario) if ADMITS_FAULT.search(c.subject)]


def _at_index(index: int) -> Predictor:
    def predict(scenario: Scenario) -> list[str]:
        hashes = scenario.hashes
        return [hashes[index]] if len(hashes) > index else []
    return predict


def _before_bfc(scenario: Scenario) -> list[str]:
    positions = [i for i, c in enumerate(scenario.commits) if c.hash in scenario.bfc_hashes]
    if not positions or positions[-1] == 0:
        return []
    return [scenario.commits[positions[-1] - 1].hash]


def _all_non_bfc(scenario: Scenario) -> list[str]:
    return [c.hash for c in _non_bfc(scenario)]


class GitProbe:
    """Runs Git for the predictors and keeps every failure visible.

    A failed Git call must not look like "this baseline found nothing": that
    would silently lower the published floor.
    """

    def __init__(self) -> None:
        self.failures: list[str] = []

    def __call__(self, repo: Path, *args: str) -> str:
        try:
            return run_git(repo, list(args)).stdout
        except GitError as exc:
            self.failures.append(f"{repo.parent.parent.name}: git {' '.join(args[:2])} failed: {exc}")
            return ""

    def paths_touched(self, repo: Path, commit: str) -> list[str]:
        """Paths a commit changes, read NUL-delimited so no quoting is involved."""
        out = self(repo, "diff", "--name-only", "--no-renames", "-z", f"{commit}^", commit)
        return [p for p in out.split("\0") if p]


def _bfc_hashes(scenario: Scenario) -> list[str]:
    return [h for h in scenario.hashes if h in scenario.bfc_hashes]


def _last_toucher(git: GitProbe) -> Predictor:
    """The newest commit before the fix that touched any file the fix touches."""
    def predict(scenario: Scenario) -> list[str]:
        found: list[str] = []
        for bfc_hash in _bfc_hashes(scenario):
            for path in git.paths_touched(scenario.repo_dir, bfc_hash):
                out = git(scenario.repo_dir, "log", "-1", "--format=%H", f"{bfc_hash}^", "--", path)
                if out.strip():
                    found.append(out.strip())
        return sorted(set(found))
    return predict


_HUNK_RE = re.compile(r"@@ -(\d+)")


def _blame_deleted_lines(git: GitProbe) -> Predictor:
    """Naive B-SZZ: blame every line the fix deletes, against its first parent.

    The diff is taken one file at a time, with the path coming from the
    NUL-delimited file list rather than from a ``--- a/`` header: Git
    terminates that header with a tab when the path contains a space and
    quotes paths with special characters.
    """
    def predict(scenario: Scenario) -> list[str]:
        found: list[str] = []
        for bfc_hash in _bfc_hashes(scenario):
            for path in git.paths_touched(scenario.repo_dir, bfc_hash):
                diff = git(scenario.repo_dir, "diff", "-U0", "--no-renames",
                           f"{bfc_hash}^", bfc_hash, "--", path)
                line_no: int | None = None
                for line in diff.splitlines():
                    if line.startswith("@@"):
                        match = _HUNK_RE.match(line)
                        line_no = int(match.group(1)) if match else None
                    elif line.startswith("-") and not line.startswith("---") and line_no is not None:
                        porcelain = git(scenario.repo_dir, "blame", "--line-porcelain",
                                        "-L", f"{line_no},{line_no}", f"{bfc_hash}^", "--", path)
                        if porcelain:
                            found.append(porcelain.split("\n", 1)[0].split()[0])
                        line_no += 1
                    elif line.startswith(" ") and line_no is not None:
                        line_no += 1
        return sorted(set(found))
    return predict


def build_predictors(scenarios: list[Scenario], git: GitProbe) -> list[tuple[str, str, str, Predictor]]:
    """(name, family, description, predictor), including one rule per author.

    The author rules are enumerated over the whole suite and only their best is
    reported: an attacker picks one rule and applies it everywhere, and
    choosing the matching author per scenario would need the oracle.
    """
    predictors: list[tuple[str, str, str, Predictor]] = []
    for author in sorted({c.author for s in scenarios for c in s.commits}):
        name = author.split("<")[0].strip() or author
        predictors.append((f"author:{name}", "metadata",
                           f"report every commit written by {name}", _by_author(author)))
    predictors.append(("message-admits-fault", "metadata",
                       "report the non-fixing commits whose subject admits a fault",
                       _message_admits_fault))
    for index, ordinal in ((0, "first"), (1, "second"), (2, "third")):
        predictors.append((f"position-{ordinal}", "position",
                           f"report the {ordinal} commit of the history", _at_index(index)))
    predictors.append(("position-before-fix", "position",
                       "report the commit immediately before the fix", _before_bfc))
    predictors.append(("position-all-non-fix", "position",
                       "report every commit that is not a fix", _all_non_bfc))
    predictors.append(("shape-last-toucher", "shape",
                       "report the newest commit before the fix that touched a file the fix touches",
                       _last_toucher(git)))
    predictors.append(("blame-deleted-lines", "blame",
                       "naive B-SZZ: blame every line the fix deletes", _blame_deleted_lines(git)))
    return predictors


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


#: Field and record separators for the one-shot `git log` read.
_FS, _RS = "\x1f", "\x1e"


def _read_history(repo_dir: Path, hash_to_id: dict[str, str], git: GitProbe) -> list[CommitInfo]:
    """The materialized history, parents before children.

    ``--topo-order --reverse`` is the documented order: it is deterministic,
    it puts a parent before its children, and it includes the commits that
    ``commit_generator`` expanded, which never appear in the scenario's YAML.
    """
    out = git(repo_dir, "log", "--all", "--topo-order", "--reverse",
              f"--format=%H{_FS}%an <%ae>{_FS}%s{_RS}")
    commits: list[CommitInfo] = []
    for record in out.split(_RS):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(_FS)
        if len(parts) < 3:
            continue
        commit_hash, author, subject = parts[0], parts[1], parts[2]
        commits.append(CommitInfo(hash=commit_hash, logical_id=hash_to_id.get(commit_hash),
                                  author=author, subject=subject))
    return commits


def _load_scenarios(generated_root: Path, scenarios_root: Path, advanced_scenarios_root: Path,
                    variant: str, git: GitProbe) -> tuple[list[Scenario], list[str]]:
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
        commits = _read_history(repo_dir, {h: cid for cid, h in hash_of.items()}, git)
        if not commits:
            errors.append(f"{scenario_id}: could not read the generated history.")
            continue
        scenarios.append(Scenario(
            scenario_id=scenario_id,
            suite=suite,
            category=(data.get("meta") or {}).get("category_code"),
            commits=commits,
            bfc_hashes={hash_of[b] for b in bfc_ids if b in hash_of},
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
    git = GitProbe()
    scenarios, errors = _load_scenarios(generated_root, scenarios_root, advanced_scenarios_root, variant, git)
    by_id = {s.scenario_id: s for s in scenarios}
    results: list[BaselineResult] = []
    for name, family, description, predictor in build_predictors(scenarios, git):
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
            {"scenario_id": sid, "category": by_id[sid].category, "commits": len(by_id[sid].commits)}
            for sid in unsolved
        ],
        "per_category": per_category,
        "errors": errors + git.failures,
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
