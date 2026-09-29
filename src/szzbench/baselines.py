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
from .manifest import stale_message, staleness

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
    tier: str | None
    commits: list[CommitInfo]
    bfc_hashes: set[str]
    repo_dir: Path
    #: the cheap-rule families the scenario declares it defeats (``meta.defeats``); None when undeclared
    defeats: list[str] | None = None

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


@dataclass
class Baseline:
    """One cheap rule.

    ``scores_on_abstention`` decides what happens on a scenario the rule makes
    no prediction for. Every rule but :data:`ABSTAIN` is credited **only where
    it predicts**: letting a rule pass a scenario whose answer is "no commit"
    merely by staying silent would give every rule the same free pass, and it
    is what made the ``position-k`` enumeration wrong three times. The one
    honest version of that strategy is a rule of its own.
    """

    name: str
    family: str
    description: str
    predict: Predictor
    scores_on_abstention: bool = False


#: The rule that never names a commit. It is the only one credited for silence,
#: which is a correct answer when a scenario's oracle is empty.
ABSTAIN = "abstain"


def _abstain(scenario: Scenario) -> list[str]:
    return []

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


def position_indices(scenarios: list[Scenario], answer_hashes: dict[str, set[str]]) -> list[int]:
    """Every index ``position-k`` is enumerated for.

    The family is "report the commit at index k" for **every** k: a rule that
    works at one depth is no weaker an attacker than one that works at another,
    and stopping at k = 2 would let a scenario look discriminating merely
    because its answer sits deeper.

    Enumerating a thousand rules that provably score nothing is wasteful, so
    the enumeration is restricted. ``position-k`` names exactly one commit and
    is credited only where it names one (see :class:`Baseline`), so it can
    score only at an index holding a commit the scorer knows about; those
    indices are enumerated, plus 0, 1 and 2 so the report always shows the
    shallow rules.

    "Knows about" is deliberately every set the commit-level policy mentions,
    not just ``required``: under ``top_k`` a prediction passes when it hits
    ``relevant``, which need not overlap ``required`` at all, and an earlier
    version of this restriction dropped the only passing rule of such a
    scenario (PR #40 review). ``test_the_restriction_keeps_every_passing_rule``
    compares the restricted enumeration against a full sweep through the real
    evaluator, across policies, rather than re-asserting this reasoning.

    An index past the end of a history is not a rule this drops: predicting
    nothing is :data:`ABSTAIN`, enumerated once under its own name instead of
    once per out-of-range k.

    ``answer_hashes`` is used only to decide which rules to *enumerate*; no
    predictor ever sees it.
    """
    indices = {0, 1, 2}
    for scenario in scenarios:
        answers = answer_hashes.get(scenario.scenario_id, set())
        for index, commit in enumerate(scenario.commits):
            if commit.hash in answers:
                indices.add(index)
    return sorted(i for i in indices if any(len(s.commits) > i for s in scenarios))


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

    #: Git's empty tree, used as the parent of a root commit.
    EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

    def parent_of(self, repo: Path, commit: str) -> str:
        """The first parent, or the empty tree for a root commit.

        A root commit has no ``<commit>^``; asking for it is an ordinary Git
        failure that would otherwise be recorded as one.
        """
        parents = self(repo, "rev-list", "--parents", "-n", "1", commit).split()
        return parents[1] if len(parents) > 1 else self.EMPTY_TREE

    def paths_touched(self, repo: Path, commit: str) -> list[str]:
        """Paths a commit changes, read NUL-delimited so no quoting is involved."""
        out = self(repo, "diff", "--name-only", "--no-renames", "-z",
                   self.parent_of(repo, commit), commit)
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


def blame_deleted_lines(git: GitProbe, scenario: Scenario) -> list[str]:
    """The commits naive B-SZZ names: blame every line the fix deletes, against
    its first parent, over every bug-fixing commit of the scenario.

    The diff is taken one file at a time, with the path coming from the
    NUL-delimited file list rather than from a ``--- a/`` header: Git
    terminates that header with a tab when the path contains a space and
    quotes paths with special characters.  Shared by the ``blame-deleted-lines``
    baseline and by ``szzbench coverage``'s ``blame_class``.
    """
    found: list[str] = []
    for bfc_hash in _bfc_hashes(scenario):
        parent = git.parent_of(scenario.repo_dir, bfc_hash)      # the empty tree for a root fix
        for path in git.paths_touched(scenario.repo_dir, bfc_hash):
            diff = git(scenario.repo_dir, "diff", "-U0", "--no-renames", parent, bfc_hash, "--", path)
            line_no: int | None = None
            for line in diff.splitlines():
                if line.startswith("@@"):
                    match = _HUNK_RE.match(line)
                    line_no = int(match.group(1)) if match else None
                elif line.startswith("-") and not line.startswith("---") and line_no is not None:
                    porcelain = git(scenario.repo_dir, "blame", "--line-porcelain",
                                    "-L", f"{line_no},{line_no}", parent, "--", path)
                    if porcelain:
                        found.append(porcelain.split("\n", 1)[0].split()[0])
                    line_no += 1
                elif line.startswith(" ") and line_no is not None:
                    line_no += 1
    return sorted(set(found))


def _blame_deleted_lines(git: GitProbe) -> Predictor:
    """Naive B-SZZ as a baseline predictor (see :func:`blame_deleted_lines`)."""
    def predict(scenario: Scenario) -> list[str]:
        return blame_deleted_lines(git, scenario)
    return predict


def build_predictors(scenarios: list[Scenario], git: GitProbe,
                     answer_hashes: dict[str, set[str]] | None = None) -> list[Baseline]:
    """The declared family, including one rule per author.

    The author rules are enumerated over the whole suite and only their best is
    reported: an attacker picks one rule and applies it everywhere, and
    choosing the matching author per scenario would need the oracle.
    """
    predictors: list[Baseline] = []
    for author in sorted({c.author for s in scenarios for c in s.commits}):
        name = author.split("<")[0].strip() or author
        predictors.append(Baseline(f"author:{name}", "metadata",
                                   f"report every commit written by {name}", _by_author(author)))
    predictors.append(Baseline("message-admits-fault", "metadata",
                               "report the non-fixing commits whose subject admits a fault",
                               _message_admits_fault))
    for index in position_indices(scenarios, answer_hashes or {}):
        predictors.append(Baseline(f"position-{index}", "position",
                                   f"report the commit at index {index} of the history", _at_index(index)))
    predictors.append(Baseline("position-before-fix", "position",
                               "report the commit immediately before the fix", _before_bfc))
    predictors.append(Baseline("position-all-non-fix", "position",
                               "report every commit that is not a fix", _all_non_bfc))
    predictors.append(Baseline(ABSTAIN, "position", "report no commit at all",
                               _abstain, scores_on_abstention=True))
    predictors.append(Baseline("shape-last-toucher", "shape",
                               "report the newest commit before the fix that touched a file the fix touches",
                               _last_toucher(git)))
    predictors.append(Baseline("blame-deleted-lines", "blame",
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
                    variant: str, git: GitProbe, *, warnings: list[str] | None = None) -> tuple[list[Scenario], list[str]]:
    from .evaluator import _find_scenario_path, _load_commit_map, _load_scenario_for_evaluation, orphan_output_warning

    scenarios: list[Scenario] = []
    errors: list[str] = []
    for repo_dir in sorted(generated_root.glob(f"*/{variant}/repo")):
        if not (repo_dir / ".git").exists():
            continue
        scenario_id = repo_dir.parent.parent.name
        path, suite = _find_scenario_path(scenario_id, scenarios_root, advanced_scenarios_root)
        if path is None:
            # A generated output with no scenario is what a retired id leaves
            # behind in an existing checkout (docs/retired-ids.md).  It is not a
            # scenario to score, and it must not fail the run.
            if warnings is not None:
                warnings.append(orphan_output_warning(scenario_id, generated_root))
            continue
        data, load_errors = _load_scenario_for_evaluation(path, suite)
        errors.extend(load_errors)
        if data is None:
            continue
        stale_reason = staleness(repo_dir.parent, path)
        if stale_reason is not None:        # not scored: its oracle may not be this repository's (#93)
            errors.append(stale_message(scenario_id, stale_reason))
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
            tier=(data.get("meta") or {}).get("tier"),
            commits=commits,
            bfc_hashes={hash_of[b] for b in bfc_ids if b in hash_of},
            repo_dir=repo_dir,
            defeats=_declared_defeats((data.get("meta") or {}).get("defeats")),
        ))
    return scenarios, errors


def _declared_defeats(value: Any) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    return None


def _answer_hashes(scenarios: list[Scenario], scenarios_root: Path,
                   advanced_scenarios_root: Path) -> dict[str, set[str]]:
    """Per scenario, the hashes of every commit its commit-level policy names.

    Not only ``required``: a ``top_k`` scenario passes on a hit in
    ``relevant``, and the allowance lists can carry credit under the relaxed
    policies, so a single prediction naming any of them may be scored. Only
    :func:`position_indices` reads this, to decide which ``position-k`` rules
    are worth running; the predictors are never given it.
    """
    from .evaluator import _commit_level_policy, _find_scenario_path, _load_scenario_for_evaluation

    answers: dict[str, set[str]] = {}
    for scenario in scenarios:
        path, suite = _find_scenario_path(scenario.scenario_id, scenarios_root, advanced_scenarios_root)
        if path is None:
            continue
        data, _ = _load_scenario_for_evaluation(path, suite)
        if data is None:
            continue
        policy = _commit_level_policy(data, suite, None)
        named = set(policy.required) | set(policy.relevant) | set(policy.related_origins)
        named |= set(policy.related_but_not_correct) | set(policy.known_distractors)
        named |= {entry.commit for entry in policy.acceptable_related}
        hash_of_id = {c.logical_id: c.hash for c in scenario.commits if c.logical_id}
        answers[scenario.scenario_id] = {hash_of_id[r] for r in named if r in hash_of_id}
    return answers


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
    warnings: list[str] = []
    scenarios, errors = _load_scenarios(generated_root, scenarios_root, advanced_scenarios_root, variant, git,
                                        warnings=warnings)
    by_id = {s.scenario_id: s for s in scenarios}
    results: list[BaselineResult] = []
    answer_hashes = _answer_hashes(scenarios, scenarios_root, advanced_scenarios_root)
    for baseline in build_predictors(scenarios, git, answer_hashes):
        if baseline.family not in selected:
            continue
        predictions: dict[str, list[Prediction]] = {}
        for scenario in scenarios:
            guessed = list(baseline.predict(scenario))
            if guessed:
                predictions[scenario.scenario_id] = [
                    Prediction(scenario_id=scenario.scenario_id, inducing_commit=c,
                               tool=f"baseline:{baseline.name}")
                    for c in guessed
                ]
        # Scenarios the rule says nothing about are scored only for the rule
        # that exists to say nothing; for every other rule they are simply not
        # solved by it.  The abstaining rule names every scenario explicitly:
        # a scenario without a record is a failure, not an abstention (#95).
        report = evaluate_prediction_map(
            predictions,
            generated_root=generated_root,
            scenarios_root=scenarios_root,
            advanced_scenarios_root=advanced_scenarios_root,
            variant=variant,
            explicit_scenarios=set(by_id) if baseline.scores_on_abstention else None,
        )
        result = BaselineResult(name=baseline.name, family=baseline.family,
                                description=baseline.description)
        result.passed = [item.scenario_id for item in report.scenarios if item.status == "PASS"]
        solved = set(result.passed)
        result.failed = [s.scenario_id for s in scenarios if s.scenario_id not in solved]
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

    # A declared tier is a claim about the scenario; the measurement checks it.
    #
    # The two directions need different evidence.  Finding *a* solver refutes a
    # `discriminating` declaration whichever families ran.  Claiming that none
    # exists - which is what a promotion candidate asserts - needs every
    # declared family, so a filtered run does not assess it at all.
    complete = set(selected) == set(FAMILIES)
    declared = Counter(s.tier or "undeclared" for s in scenarios)
    wrongly_discriminating = sorted(s.scenario_id for s in scenarios
                                    if s.tier == "discriminating" and s.scenario_id in solved_any)
    unsolved_controls = sorted(s.scenario_id for s in scenarios
                               if s.tier == "control" and s.scenario_id not in solved_any) if complete else None

    # `meta.defeats` (issue #35): the families a scenario is built to make fail.
    # A declared family that does solve the scenario is a contradiction, and it
    # can be refuted by any run that includes that family.  The abstain rule is
    # scored on its silence and is not a way of "solving" a scenario a tool
    # could copy, so it does not count against a declaration.
    solved_by_rule: dict[str, list[str]] = defaultdict(list)
    for result in results:
        if result.name == ABSTAIN:
            continue
        for sid in result.passed:
            solved_by_rule[sid].append(f"{result.family}:{result.name}")
    defeated_but_solved = []
    declaring = 0
    for scenario in scenarios:
        if scenario.defeats is None:
            continue
        declaring += 1
        for family in scenario.defeats:
            if family not in selected:
                continue
            rules = sorted(name for tag in solved_by_rule.get(scenario.scenario_id, []) for fam, name in [tag.split(":", 1)] if fam == family)
            if rules:
                defeated_but_solved.append({"scenario_id": scenario.scenario_id, "family": family, "solved_by": rules})

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
        "families_run": list(selected),
        "complete": complete,
        "tiers": dict(sorted(declared.items())),
        "declared_discriminating_but_solved": wrongly_discriminating,
        "declared_control_but_unsolved": unsolved_controls,
        "scenarios_declaring_defeats": declaring,
        "declared_defeated_but_solved": defeated_but_solved,
        "errors": errors + git.failures,
        "warnings": warnings,
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
    scope = "baseline" if report.get("complete", True) else "selected baseline"
    lines.append(f"  solved by at least one {scope}: {solved}/{total} = {100 * solved / total:.1f}%" if total else "")
    lines.append(f"  solved by no {scope}: {len(report['unsolved'])}")
    for item in report["unsolved_detail"]:
        lines.append(f"      {item['scenario_id']} [{item['category']}] {item['commits']} commits")
    lines.append("")
    lines.append(f"  declared tiers: " + ", ".join(f"{k} {v}" for k, v in report["tiers"].items()))
    wrong = report["declared_discriminating_but_solved"]
    if wrong:
        lines.append(f"  [WARNING] declared discriminating but solved by a cheap rule: {', '.join(wrong)}")
    promote = report["declared_control_but_unsolved"]
    if promote is None:
        lines.append(f"  promotion candidates: not assessed - only the "
                     f"{', '.join(report['families_run'])} famil"
                     f"{'y' if len(report['families_run']) == 1 else 'ies'} ran; "
                     f"a control can only be promoted when no declared family solves it")
    elif promote:
        lines.append(f"  declared control but solved by no cheap rule (promotion candidates): {', '.join(promote)}")
    declaring = report.get("scenarios_declaring_defeats", 0)
    if declaring:
        contradictions = report.get("declared_defeated_but_solved", [])
        lines.append(f"  declared defeats (meta.defeats): {declaring} scenario(s) declare the families they defeat; "
                     f"{len(contradictions)} contradiction(s)")
        for item in contradictions:
            lines.append(f"  [WARNING] {item['scenario_id']} declares it defeats {item['family']} but "
                         f"{', '.join(item['solved_by'])} solves it")
    lines.append("")
    lines.append("  per category (solved by any baseline / total)")
    for category in sorted(report["per_category"]):
        bucket = report["per_category"][category]
        rate = 100 * bucket["solved"] / bucket["total"] if bucket["total"] else 0.0
        lines.append(f"      {category:4s} {bucket['solved']:3d}/{bucket['total']:<3d} {rate:5.1f}%")
    for warning in report.get("warnings", []):
        lines.append(f"  [WARNING] {warning}")
    for error in report["errors"]:
        lines.append(f"  [ERROR] {error}")
    return "\n".join(lines)
