from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from collections.abc import Sequence
from typing import Any
import json
import re

from .gitutils import GitError, git_parent, run_git
from .graph_scenario import DIRECT_BIC_ROLES, graph_bfc_entries, graph_bic_entries, load_graph_scenario
from .manifest import read_manifest, stale_message, staleness
from .scenario import load_yaml


@dataclass(frozen=True)
class Prediction:
    scenario_id: str
    inducing_commit: str
    fix_commit: str | None = None
    rank: int | None = None
    confidence: float | None = None
    tool: str | None = None
    raw_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "inducing_commit": self.inducing_commit,
        }
        if self.fix_commit is not None:
            data["fix_commit"] = self.fix_commit
        if self.rank is not None:
            data["rank"] = self.rank
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.tool is not None:
            data["tool"] = self.tool
        if self.raw_file is not None:
            data["raw_file"] = self.raw_file
        return data


@dataclass(frozen=True)
class AcceptableRelated:
    commit: str
    reason: str | None = None
    credit: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "commit": self.commit,
            "credit": self.credit,
        }
        if self.reason is not None:
            data["reason"] = self.reason
        return data


@dataclass(frozen=True)
class CommitLevelPolicy:
    evaluation_policy: str
    evaluation_variant: str | None
    required: list[str]
    acceptable_related: list[AcceptableRelated] = field(default_factory=list)
    related_origins: list[str] = field(default_factory=list)
    related_but_not_correct: list[str] = field(default_factory=list)
    relevant: list[str] = field(default_factory=list)
    minimum_required: int | None = None
    k_values: list[int] = field(default_factory=list)
    status_k: int | None = None
    expect_no_bic: bool = False
    known_distractors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    #: The oracle declares neither ``required`` nor ``expect_no_bic: true``, so
    #: ``required`` was taken from bugs[] (graph suite; validate-graph's GW130).
    required_inferred: bool = False


#: Outcome classes of a bug-fixing commit's first-parent diff (see docs/evaluation-policies.md).
FIX_SHAPES = ("empty_first_parent", "addition_only", "modifies")


@dataclass
class ScenarioEvaluation:
    scenario_id: str
    suite: str
    category: str | None
    status: str
    expected_bics: list[str]
    actual_bics: list[str]
    true_positives: list[str]
    false_positives: list[str]
    false_negatives: list[str]
    allowed_false_positives: list[str]
    prediction_count: int
    evaluation_policy: str | None = None
    evaluation_variant: str | None = None
    hard_false_positives: list[str] = field(default_factory=list)
    related_origin_hits: list[str] = field(default_factory=list)
    related_but_not_correct_hits: list[str] = field(default_factory=list)
    acceptable_related_hits: list[dict[str, Any]] = field(default_factory=list)
    weighted_credit: float | None = None
    possible_credit: float | None = None
    credit_ratio: float | None = None
    minimum_required: int | None = None
    minimum_required_met: bool | None = None
    top_k: dict[str, Any] | None = None
    unknown_predictions: list[str] = field(default_factory=list)
    precision: float | None = None
    recall: float | None = None
    scenario_path: str | None = None
    result_notes: list[str] = field(default_factory=list)
    known_distractor_hits: list[str] = field(default_factory=list)
    expect_no_bic: bool = False
    fix_shape: dict[str, str] | None = None
    branch_level: dict[str, Any] | None = None
    #: the per-fix result of a scenario with several bug-fixing commits (issue #92)
    attribution: dict[str, Any] | None = None
    #: what the tool's run on the scenario came to: ``ok`` (a record was given),
    #: ``error`` (the record says the tool failed), ``stale`` (made on another
    #: repository), ``invalid`` (a record could not be read) or ``missing`` (no record at all)
    run_status: str = "ok"
    run_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "suite": self.suite,
            "category": self.category,
            "status": self.status,
            "run_status": self.run_status,
            "run_errors": self.run_errors,
            "expected_bics": self.expected_bics,
            "actual_bics": self.actual_bics,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "allowed_false_positives": self.allowed_false_positives,
            "prediction_count": self.prediction_count,
            "evaluation_policy": self.evaluation_policy,
            "evaluation_variant": self.evaluation_variant,
            "hard_false_positives": self.hard_false_positives,
            "related_origin_hits": self.related_origin_hits,
            "related_but_not_correct_hits": self.related_but_not_correct_hits,
            "acceptable_related_hits": self.acceptable_related_hits,
            "weighted_credit": self.weighted_credit,
            "possible_credit": self.possible_credit,
            "credit_ratio": self.credit_ratio,
            "minimum_required": self.minimum_required,
            "minimum_required_met": self.minimum_required_met,
            "top_k": self.top_k,
            "unknown_predictions": self.unknown_predictions,
            "precision": self.precision,
            "recall": self.recall,
            "scenario_path": self.scenario_path,
            "result_notes": self.result_notes,
            "known_distractor_hits": self.known_distractor_hits,
            "expect_no_bic": self.expect_no_bic,
            "fix_shape": self.fix_shape,
            "branch_level": self.branch_level,
            "attribution": self.attribution,
        }


@dataclass
class EvaluationReport:
    scenarios: list[ScenarioEvaluation]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: Oracle notes that are information, not warnings (issue #126).
    info: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        total = len(self.scenarios)
        passed = sum(1 for item in self.scenarios if item.status == "PASS")
        failed = sum(1 for item in self.scenarios if item.status != "PASS")
        tool_errors = sum(1 for item in self.scenarios if item.run_status == "error")
        missing_records = sum(1 for item in self.scenarios if item.run_status == "missing")
        stale_predictions = sum(1 for item in self.scenarios if item.run_status == "stale")
        invalid_records = sum(1 for item in self.scenarios if item.run_status == "invalid")
        tp = sum(len(item.true_positives) for item in self.scenarios)
        fp = sum(len(item.false_positives) for item in self.scenarios)
        unknown = sum(len(item.unknown_predictions) for item in self.scenarios)
        fn = sum(len(item.false_negatives) for item in self.scenarios)
        allowed_fp = sum(len(item.allowed_false_positives) for item in self.scenarios)
        hard_fp = sum(len(item.hard_false_positives) for item in self.scenarios)
        related_origin_hits = sum(len(item.related_origin_hits) for item in self.scenarios)
        related_but_not_correct_hits = sum(len(item.related_but_not_correct_hits) for item in self.scenarios)
        known_distractor_hits = sum(len(item.known_distractor_hits) for item in self.scenarios)
        branch_level_scenarios = sum(1 for item in self.scenarios if item.branch_level is not None)
        attribution_scenarios = sum(1 for item in self.scenarios if item.attribution is not None)
        attribution_failures = sum(1 for item in self.scenarios
                                   if item.attribution is not None and item.attribution["status"] != "PASS")
        branch_level_failures = sum(1 for item in self.scenarios
                                    if item.branch_level is not None and item.branch_level["status"] != "PASS")
        fix_shape_counts = {shape: 0 for shape in FIX_SHAPES}
        for item in self.scenarios:
            for shape in (item.fix_shape or {}).values():
                fix_shape_counts[shape] = fix_shape_counts.get(shape, 0) + 1
        possible_credit = sum(item.possible_credit for item in self.scenarios if item.possible_credit is not None)
        weighted_credit = sum(item.weighted_credit for item in self.scenarios if item.weighted_credit is not None)
        # an unknown reference is a false positive of its own kind (issue #95)
        precision = _ratio(tp, tp + fp + unknown)
        recall = _ratio(tp, tp + fn)
        by_suite: dict[str, dict[str, int]] = {}
        for item in self.scenarios:
            bucket = by_suite.setdefault(item.suite, {"total": 0, "pass": 0, "fail": 0})
            bucket["total"] += 1
            if item.status == "PASS":
                bucket["pass"] += 1
            else:
                bucket["fail"] += 1
        return {
            "total_scenarios": total,
            "pass": passed,
            "fail": failed,
            "tool_errors": tool_errors,
            "missing_records": missing_records,
            "stale_predictions": stale_predictions,
            "invalid_records": invalid_records,
            "true_positives": tp,
            "false_positives": fp,
            "unknown_predictions": unknown,
            "false_negatives": fn,
            "allowed_false_positives": allowed_fp,
            "hard_false_positives": hard_fp,
            "related_origin_hits": related_origin_hits,
            "related_but_not_correct_hits": related_but_not_correct_hits,
            "known_distractor_hits": known_distractor_hits,
            "branch_level_scenarios": branch_level_scenarios,
            "branch_level_failures": branch_level_failures,
            "attribution_scenarios": attribution_scenarios,
            "attribution_failures": attribution_failures,
            "fix_shape_counts": fix_shape_counts,
            "weighted_credit": weighted_credit if possible_credit else None,
            "possible_credit": possible_credit if possible_credit else None,
            "credit_ratio": _float_ratio(weighted_credit, possible_credit),
            "precision": precision,
            "recall": recall,
            "by_suite": by_suite,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary(),
            "scenarios": [item.to_dict() for item in self.scenarios],
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }

    def to_markdown(self) -> str:
        summary = self.summary()
        lines = [
            "# SZZBench Evaluation Results",
            "",
            "## Summary",
            "",
            f"- Total scenarios: {summary['total_scenarios']}",
            f"- PASS: {summary['pass']}",
            f"- FAIL: {summary['fail']}",
            f"- Tool errors: {summary['tool_errors']}",
            f"- Missing prediction records: {summary['missing_records']}",
            f"- Predictions made on another repository: {summary['stale_predictions']}",
            f"- Invalid prediction records: {summary['invalid_records']}",
            f"- True positives: {summary['true_positives']}",
            f"- False positives: {summary['false_positives']}",
            f"- Unknown predictions (counted as false positives): {summary['unknown_predictions']}",
            f"- False negatives: {summary['false_negatives']}",
            f"- Allowed false positives: {summary['allowed_false_positives']}",
            f"- Hard false positives: {summary['hard_false_positives']}",
            f"- Related origin hits: {summary['related_origin_hits']}",
            f"- Related-but-not-correct hits: {summary['related_but_not_correct_hits']}",
            f"- Known distractor hits: {summary['known_distractor_hits']}",
            f"- Branch-level failures: {summary['branch_level_failures']} of {summary['branch_level_scenarios']} scenario(s) with a branch-level oracle",
            f"- Attribution failures: {summary['attribution_failures']} of {summary['attribution_scenarios']} scenario(s) with several bug-fixing commits",
            f"- Fix shapes (per BFC): {_format_fix_shape_counts(summary['fix_shape_counts'])}",
            f"- Weighted credit: {_format_credit(summary['weighted_credit'], summary['possible_credit'])}",
            f"- Precision: {_format_ratio(summary['precision'])}",
            f"- Recall: {_format_ratio(summary['recall'])}",
            "",
        ]
        if self.errors:
            lines.extend(["## Errors", ""])
            lines.extend(f"- {_md_line(error)}" for error in self.errors)
            lines.append("")
        if self.warnings:
            lines.extend(["## Warnings", ""])
            lines.extend(f"- {_md_line(warning)}" for warning in self.warnings)
            lines.append("")
        if self.info:
            lines.extend(["## Information", ""])
            lines.extend(f"- {_md_line(note)}" for note in self.info)
            lines.append("")
        lines.extend(
            [
                "## Results",
                "",
                "| Scenario | Status | Run | Suite | Policy | Variant | Category | Expected BICs | Actual BICs | TP | FP | Unknown | FN | Allowed FP | Predictions | Top-k | Distractor hits | Fix shape |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|",
            ]
        )
        for item in self.scenarios:
            lines.append(
                "| "
                + " | ".join(
                    _md_cell(cell) for cell in [
                        item.scenario_id,
                        item.status,
                        item.run_status,
                        item.suite,
                        item.evaluation_policy or "-",
                        item.evaluation_variant or "-",
                        item.category or "-",
                        "none (expect_no_bic)" if item.expect_no_bic else _join_ids(item.expected_bics),
                        _join_ids(item.actual_bics),
                        _join_ids(item.true_positives),
                        _join_ids(item.false_positives),
                        _join_ids(item.unknown_predictions),
                        _join_ids(item.false_negatives),
                        _join_ids(item.allowed_false_positives),
                        str(item.prediction_count),
                        _format_top_k(item.top_k),
                        _join_ids(item.known_distractor_hits),
                        _format_fix_shape(item.fix_shape),
                    ]
                )
                + " |"
            )
        lines.append("")
        noted = [item for item in self.scenarios if item.result_notes]
        if noted:
            # Per-scenario notes (inferred oracles, unread oracle sections,
            # ignored allowances, skipped fix-shape classification) must be
            # visible where people read the result, not only in the JSON.
            lines.extend(["## Scenario notes", ""])
            for item in noted:
                for note in item.result_notes:
                    lines.append(f"- {item.scenario_id}: {_md_line(note)}")
            lines.append("")
        return "\n".join(lines)


def evaluate_predictions(
    predictions_path: Path | None,
    *,
    generated_root: Path,
    scenarios_root: Path,
    advanced_scenarios_root: Path,
    variant: str = "default",
    include_generated: bool = False,
    evaluation_variant: str | None = None,
    reference_format: str = "auto",
) -> EvaluationReport:
    if predictions_path is None:
        predictions_by_scenario: dict[str, list[Prediction]] = {}
        explicit_scenarios: set[str] = set()
        run_errors: dict[str, list[str]] = {}
        invalid_records: dict[str, list[str]] = {}
        repository_ids: dict[str, str] = {}
        errors: list[str] = []
        warnings: list[str] = []
    else:
        (predictions_by_scenario, explicit_scenarios, run_errors, invalid_records, repository_ids,
         errors, warnings) = load_predictions(predictions_path)
        unmatched = sorted(explicit_scenarios - set(repository_ids))
        if unmatched:
            warnings.append(
                f"{len(unmatched)} scenario(s) have prediction records without repository_id, so SZZBench cannot "
                "tell whether they were made on these generated repositories; the adapters in tools/adapters "
                "write it (issue #93).")
    return evaluate_prediction_map(
        predictions_by_scenario,
        generated_root=generated_root,
        scenarios_root=scenarios_root,
        advanced_scenarios_root=advanced_scenarios_root,
        variant=variant,
        include_generated=include_generated,
        evaluation_variant=evaluation_variant,
        reference_format=reference_format,
        explicit_scenarios=explicit_scenarios,
        run_errors=run_errors,
        invalid_records=invalid_records,
        repository_ids=repository_ids,
        errors=errors,
        warnings=warnings,
    )


def evaluate_prediction_map(
    predictions_by_scenario: dict[str, list[Prediction]],
    *,
    generated_root: Path,
    scenarios_root: Path,
    advanced_scenarios_root: Path,
    variant: str = "default",
    include_generated: bool = False,
    evaluation_variant: str | None = None,
    reference_format: str = "auto",
    explicit_scenarios: set[str] | None = None,
    run_errors: dict[str, list[str]] | None = None,
    invalid_records: dict[str, list[str]] | None = None,
    repository_ids: dict[str, str] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> EvaluationReport:
    """Score predictions that are already in memory.

    :func:`evaluate_predictions` is the file-based entry point; the baseline
    predictors of ``szzbench baselines`` call this one so that they are scored
    by exactly the same policies as a real tool run.

    ``explicit_scenarios`` are the scenarios a record names, an empty one
    included; ``run_errors`` maps a scenario to what its record says went wrong.
    A scenario that only ``include_generated`` brings in has no record: it
    FAILs with ``run_status: missing`` instead of being read as an abstention,
    and a scenario with a run error FAILs with ``run_status: error`` (issue #95).

    A generated output that is stale -- no manifest, or one that no longer
    matches its scenario file or the generator's code -- is not scored; the
    report gets an error instead.  ``repository_ids`` maps a scenario to the
    repository id its prediction records name; one that differs from the
    generated repository's FAILs with ``run_status: stale`` (issue #93).

    ``invalid_records`` maps a scenario to the loading errors of its records
    that could not be read; it FAILs with ``run_status: invalid`` whatever its
    other records predict, and stays in the report even when none of its
    records could be read (issue #138).  Of the statuses that fail a scenario,
    ``error`` and ``stale`` come first: they say that the tool's run itself is
    no answer, which a file that could be read would not change.
    """
    errors = list(errors or [])
    warnings = list(warnings or [])
    run_errors = run_errors or {}
    invalid_records = invalid_records or {}
    repository_ids = repository_ids or {}
    requested = set(explicit_scenarios or predictions_by_scenario.keys()) | set(invalid_records)
    scenario_ids = set(requested)
    if include_generated:
        scenario_ids.update(_generated_scenario_ids(generated_root, variant))
    evaluations: list[ScenarioEvaluation] = []
    for scenario_id in sorted(scenario_ids):
        scenario_path, suite = _find_scenario_path(scenario_id, scenarios_root, advanced_scenarios_root)
        if scenario_path is None:
            if scenario_id in requested:
                # the predictions name it, so this is a claim about a scenario
                errors.append(f"Cannot find scenario for '{scenario_id}'.")
            else:
                # it only came from the generated output: a retired id's leftover
                warnings.append(orphan_output_warning(scenario_id, generated_root))
            continue
        scenario, scenario_errors = _load_scenario_for_evaluation(scenario_path, suite)
        errors.extend(scenario_errors)
        if scenario is None:
            continue
        output_dir = generated_root / scenario_id / variant
        stale_reason = staleness(output_dir, scenario_path)
        if stale_reason is not None:
            errors.append(stale_message(scenario_id, stale_reason))
            continue
        commit_map_path = output_dir / "metadata" / "commit-map.json"
        commit_map, commit_map_errors = _load_commit_map(commit_map_path)
        errors.extend(commit_map_errors)
        if commit_map is None:
            continue
        generated_id = (read_manifest(output_dir) or {}).get("repository_id")
        scenario_run_errors = run_errors.get(scenario_id, [])
        if scenario_id in run_errors:
            run_status = "error"
        elif scenario_id in repository_ids and repository_ids[scenario_id] != generated_id:
            run_status = "stale"
            scenario_run_errors = [f"the predictions were made on repository {repository_ids[scenario_id]}, "
                                   f"and the generated repository is {generated_id}; run the tool on it again"]
        elif scenario_id in invalid_records:
            run_status = "invalid"
            scenario_run_errors = invalid_records[scenario_id]
        elif scenario_id in requested:
            run_status = "ok"
        else:
            run_status = "missing"
        evaluations.append(
            evaluate_scenario(
                scenario_id,
                scenario,
                scenario_path,
                suite,
                commit_map,
                predictions_by_scenario.get(scenario_id, []),
                evaluation_variant=evaluation_variant,
                repo_dir=generated_root / scenario_id / variant / "repo",
                reference_format=reference_format,
                run_status=run_status,
                run_errors=scenario_run_errors,
            )
        )
    # Oracle-related notes (inferred required set, ignored allowances,
    # unsupported policies, unknown variants) are promoted to report warnings
    # so that the plain CLI output and the markdown "Warnings" section show them.
    # The note that an oracle section is not read is information instead: it
    # still goes with every result (PR #27 review), but nothing in the scenario
    # is wrong (issue #126).
    info: list[str] = []
    requested_variant = _requested_evaluation_variant(evaluation_variant)
    # A requested variant that a scenario does not define is a note on that
    # scenario's result, and one warning for the run: one per scenario buried
    # the warnings that matter among 143 of them (issue #140).
    undefined_prefix = (_UNDEFINED_VARIANT_NOTE.split("{used}")[0].format(name=requested_variant)
                        if requested_variant is not None else None)
    undefined: list[str] = []
    for item in evaluations:
        for note in item.result_notes:
            if note.startswith("fix_shape not computed"):
                continue
            if undefined_prefix is not None and note.startswith(undefined_prefix):
                undefined.append(item.scenario_id)
                continue
            (info if _is_information_note(note) else warnings).append(f"{item.scenario_id}: {note}")
    if undefined:
        graph_count = sum(1 for item in evaluations if item.suite == "advanced-scenarios")
        warnings.append(
            f"Evaluation variant '{requested_variant}' is not defined in {len(undefined)} of the {graph_count} graph "
            "scenario(s) evaluated; they were scored as without --evaluation-variant, against their default_variant "
            "or else commit_level, and each one's result notes say which.")
    classic_count = sum(1 for item in evaluations if item.suite == "scenarios")
    if requested_variant is not None and classic_count:
        # the classic suite has no variants (docs/evaluation-policies.md section 1.2); say so once, not per scenario
        info.append(f"--evaluation-variant applies to graph scenarios only; the {classic_count} classic scenario(s) "
                    "were scored against their own oracle.")
    return EvaluationReport(evaluations, errors=errors, warnings=warnings, info=info)


def _generated_scenario_ids(generated_root: Path, variant: str) -> set[str]:
    # every output directory, complete or not: one that has lost its repository
    # is reported as stale instead of dropping out of the report (issue #93)
    return {output_dir.parent.name for output_dir in generated_root.glob(f"*/{variant}") if output_dir.is_dir()}


def evaluate_scenario(
    scenario_id: str,
    scenario: dict[str, Any],
    scenario_path: Path,
    suite: str,
    commit_map: dict[str, Any],
    predictions: list[Prediction],
    *,
    evaluation_variant: str | None = None,
    repo_dir: Path | None = None,
    reference_format: str = "auto",
    run_status: str = "ok",
    run_errors: Sequence[str] = (),
) -> ScenarioEvaluation:
    """Score one scenario's predictions against its commit-level oracle.

    ``repo_dir`` is the generated repository (``.../<scenario>/<variant>/repo``).
    When it is given, each bug-fixing commit's first-parent diff is classified
    into a fix shape; when it is missing or Git fails, the classification is
    skipped with a result note.

    ``run_status`` is ``ok``, ``error`` (the record reports that the tool failed,
    ``run_errors`` says how), ``stale`` (the records were made on another
    repository, issue #93), ``invalid`` (a record could not be read,
    ``run_errors`` holds its loading errors, issue #138) or ``missing`` (there
    is no record); anything but ``ok`` fails the scenario whatever the
    predictions are (issue #95).
    """
    policy = _commit_level_policy(scenario, suite, evaluation_variant)
    notes = list(policy.notes)
    hash_to_id = _hash_to_logical_id(commit_map)
    ranking = _ranking(predictions, commit_map, hash_to_id, reference_format=reference_format)
    ranked_actual_ids = [reference for reference, known in ranking if known]
    unknown_predictions = [reference for reference, known in ranking if not known]

    scored = classify_prediction(policy, ranked_actual_ids, unknown_predictions=unknown_predictions,
                                 ranking=ranking)
    expected = set(policy.required)
    true_positives = scored.true_positives
    false_positives = scored.false_positives
    false_negatives = scored.false_negatives
    allowed_false_positives = scored.allowed_false_positives
    related_origin_hits = scored.related_origin_hits
    related_but_not_correct_hits = scored.related_but_not_correct_hits
    known_distractor_hits = scored.known_distractor_hits
    hard_false_positives = scored.hard_false_positives
    acceptable_related_hits = scored.acceptable_related_hits
    weighted_credit = scored.weighted_credit
    possible_credit = scored.possible_credit
    credit_ratio = scored.credit_ratio
    minimum_required_met = scored.minimum_required_met
    top_k = scored.top_k
    status = scored.status
    branch_level = _branch_level_result(scenario, suite, predictions, commit_map, hash_to_id, notes,
                                        reference_format=reference_format)
    if branch_level is not None and branch_level["status"] != "PASS" and status == "PASS":
        failed = [name for name, entry in branch_level["branches"].items() if entry["status"] != "PASS"]
        notes.append(f"branch_level: the commit-level oracle passes but branch(es) {', '.join(failed)} fail, so the scenario fails.")
        status = "FAIL"
    attribution = None
    if branch_level is None:        # a declared branch-level oracle already scores the fixes
        attribution = _attribution_result(scenario, suite, policy, predictions, commit_map, hash_to_id, notes,
                                          reference_format=reference_format)
    if attribution is not None and attribution["status"] != "PASS" and status == "PASS":
        failed = [bfc for bfc, entry in attribution["fixes"].items() if entry["status"] != "PASS"]
        notes.append(f"attribution: the commit-level oracle passes but fix(es) {', '.join(failed)} fail, so the scenario fails.")
        status = "FAIL"
    if run_status == "missing":
        notes.append("no prediction record: scored as a failure, not as an abstention "
                     "(a record with an empty prediction list is an abstention).")
        status = "FAIL"
    elif run_status == "error":
        notes.append(f"the tool reported an error ({'; '.join(run_errors)}), so the scenario fails "
                     "whatever it predicted.")
        status = "FAIL"
    elif run_status == "stale":
        notes.append(f"stale predictions: {'; '.join(run_errors)}; the scenario fails whatever they predict.")
        status = "FAIL"
    elif run_status == "invalid":
        unread = "; ".join(message.rstrip(".") for message in run_errors)
        notes.append(f"a prediction record could not be read ({unread}), so the scenario fails whatever "
                     "its other records predict.")
        status = "FAIL"
    # an unknown reference is a false positive of its own kind (issue #95)
    precision = _ratio(len(true_positives), len(true_positives) + len(false_positives) + len(unknown_predictions))
    recall = _ratio(len(true_positives), len(true_positives) + len(false_negatives))
    category = _scenario_category(scenario)
    fix_shape = _classify_fix_shapes(scenario, commit_map, repo_dir, notes) if repo_dir is not None else None
    return ScenarioEvaluation(
        scenario_id=scenario_id,
        suite=suite,
        category=category,
        status=status,
        expected_bics=sorted(expected),
        actual_bics=sorted(set(ranked_actual_ids)),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        allowed_false_positives=allowed_false_positives,
        prediction_count=len(predictions),
        evaluation_policy=policy.evaluation_policy,
        evaluation_variant=policy.evaluation_variant,
        hard_false_positives=hard_false_positives,
        related_origin_hits=related_origin_hits,
        related_but_not_correct_hits=related_but_not_correct_hits,
        acceptable_related_hits=acceptable_related_hits,
        weighted_credit=weighted_credit,
        possible_credit=possible_credit,
        credit_ratio=credit_ratio,
        minimum_required=policy.minimum_required,
        minimum_required_met=minimum_required_met,
        top_k=top_k,
        unknown_predictions=sorted(set(unknown_predictions)),
        precision=precision,
        recall=recall,
        scenario_path=str(scenario_path),
        result_notes=notes,
        known_distractor_hits=known_distractor_hits,
        expect_no_bic=policy.expect_no_bic,
        fix_shape=fix_shape,
        branch_level=branch_level,
        attribution=attribution,
        run_status=run_status,
        run_errors=list(run_errors),
    )


def _branch_level_result(
    scenario: dict[str, Any],
    suite: str,
    predictions: list[Prediction],
    commit_map: dict[str, Any],
    hash_to_id: dict[str, str],
    notes: list[str],
    *,
    reference_format: str = "auto",
) -> dict[str, Any] | None:
    """Score ``expected_szz.branch_level`` per declared bug-fixing commit.

    A graph scenario may declare ``branch_level: {<branch>: {bfc: <id>,
    required: [<ids>]}}`` when the same fault is fixed on several branches and
    the answer a tool must give depends on the fix it started from (issue #22).
    A prediction whose ``fix_commit`` resolves to a branch's ``bfc`` is scored
    against that branch's ``required`` set as an exact set; a prediction without
    ``fix_commit`` counts for every branch; one whose ``fix_commit`` resolves to
    no declared ``bfc`` counts for none and is noted.  Each branch is PASS or
    FAIL; the block is PASS when every branch is, and a FAIL fails the scenario
    even when the commit-level oracle passes.  An entry without a string
    ``bfc`` or a ``required`` list (GE127) fails, with a note, and no
    prediction is attributed to it.  Returns ``None`` when the scenario
    declares no branch-level oracle.
    """
    if suite != "advanced-scenarios":
        return None
    expected_szz = scenario.get("expected_szz") if isinstance(scenario.get("expected_szz"), dict) else {}
    declared = expected_szz.get("branch_level")
    if not isinstance(declared, dict) or not declared:
        return None
    resolved_fix: dict[int, str | None] = {}
    for index, prediction in enumerate(predictions):
        if prediction.fix_commit is not None:
            resolved_fix[index] = _normalize_commit_ref(prediction.fix_commit, commit_map, hash_to_id,
                                                        reference_format=reference_format)
    declared_bfcs: set[str] = set()
    branches: dict[str, dict[str, Any]] = {}
    for name, spec in declared.items():
        if not isinstance(spec, dict):
            notes.append(f"branch_level: entry '{name}' is not an object and was skipped.")
            continue
        bfc = spec.get("bfc")
        declared_required = spec.get("required")
        if isinstance(bfc, str):
            declared_bfcs.add(bfc)
        else:
            # without a bfc, the entry collected every prediction whose fix_commit
            # resolved to nothing, and passed on them (issue #147)
            notes.append(f"branch_level: entry '{name}' has no commit id under bfc (GE127); the branch fails.")
        if not isinstance(declared_required, list):
            notes.append(f"branch_level: entry '{name}' has no list under required (GE127); the branch fails.")
        if not isinstance(bfc, str) or not isinstance(declared_required, list):
            branches[str(name)] = {"bfc": bfc,
                                   "required": _string_list(declared_required) if isinstance(declared_required, list) else None,
                                   "predicted": [], "false_positives": [], "false_negatives": [],
                                   "unknown_predictions": [], "status": "FAIL"}
            continue
        required = _string_list(declared_required)
        attributed = [
            prediction for index, prediction in enumerate(predictions)
            # a fix_commit that resolves to nothing is attributed to no branch
            if prediction.fix_commit is None or (resolved_fix[index] is not None and resolved_fix[index] == bfc)
        ]
        ranked, unknown = _ranked_actual_ids(attributed, commit_map, hash_to_id, reference_format=reference_format)
        actual = set(ranked)
        false_positives = sorted(actual - set(required))
        false_negatives = sorted(set(required) - actual)
        status = "PASS" if not false_positives and not false_negatives and not unknown else "FAIL"
        branches[str(name)] = {
            "bfc": bfc,
            "required": list(required),
            "predicted": sorted(actual),
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "unknown_predictions": sorted(set(unknown)),
            "status": status,
        }
    stray = sorted({prediction.fix_commit for index, prediction in enumerate(predictions)
                    if prediction.fix_commit is not None and resolved_fix.get(index) not in declared_bfcs})
    if stray:
        notes.append(
            f"branch_level: {len(stray)} fix_commit value(s) resolve to no declared branch BFC ({', '.join(stray)}); "
            "those predictions count for no branch."
        )
    overall = "PASS" if branches and all(entry["status"] == "PASS" for entry in branches.values()) else "FAIL"
    return {"status": overall, "branches": branches}


#: Values of a record's optional ``status``: what the tool's run on the scenario
#: came to.  ``error`` makes the scenario FAIL with ``run_status: error`` whatever
#: the record predicts (issue #95); matching is case-insensitive.
RECORD_STATUSES = ("ok", "error")


#: Policies whose status is a comparison of sets, so a per-fix oracle is scored the same way.
SET_POLICIES = frozenset({"exact_set", "direct_only", "reintroduction_direct", "relaxed_with_related",
                          "relaxed_with_credit"})


def _fix_oracles(scenario: dict[str, Any], suite: str) -> dict[str, list[str]]:
    """Each declared bug-fixing commit and the direct BICs of the bugs it fixes."""
    oracles: dict[str, set[str]] = {}
    for bug in scenario.get("bugs", []) or []:
        if not isinstance(bug, dict):
            continue
        if suite == "advanced-scenarios":
            causes = {entry["commit"] for entry in graph_bic_entries(bug, roles=DIRECT_BIC_ROLES)
                      if isinstance(entry.get("commit"), str)}
        else:
            listed = ((bug.get("expected_szz") or {}).get("commit_level") or {}).get("true_positives")
            if not isinstance(listed, list):
                listed = bug.get("bug_introducing_commits") or []
            causes = {commit for commit in listed if isinstance(commit, str)}
        for entry in graph_bfc_entries(bug):
            commit = entry.get("commit")
            if isinstance(commit, str):
                oracles.setdefault(commit, set()).update(causes)
    return {bfc: sorted(causes) for bfc, causes in oracles.items()}


def _attribution_result(
    scenario: dict[str, Any],
    suite: str,
    policy: CommitLevelPolicy,
    predictions: list[Prediction],
    commit_map: dict[str, Any],
    hash_to_id: dict[str, str],
    notes: list[str],
    *,
    reference_format: str = "auto",
) -> dict[str, Any] | None:
    """Score a scenario's predictions per bug-fixing commit (issue #92).

    Commit-level scoring compares sets and cannot tell which fix a predicted
    BIC answers, so SZZG-0030's swapped answer (c2 -> c2, c3 -> c1) passed like
    the right one.  For a scenario with several declared bug-fixing commits and
    no ``branch_level`` block, each fix must lead to the direct BICs of the bugs
    it fixes, under the scenario's own policy.  Attribution follows
    ``branch_level``: a prediction counts for the fix its ``fix_commit``
    resolves to, one without ``fix_commit`` for every fix, and one whose
    ``fix_commit`` resolves to no declared fix for none (noted).  Returns None
    -- with a note when the reason is not obvious -- when there is nothing to
    attribute: one fix, a policy that is not a set comparison, or per-fix
    oracles whose union is not the commit-level oracle.  Stray fix references
    are noted in every scenario.
    """
    oracles = _fix_oracles(scenario, suite)
    resolved = {index: _normalize_commit_ref(prediction.fix_commit, commit_map, hash_to_id,
                                             reference_format=reference_format)
                for index, prediction in enumerate(predictions) if prediction.fix_commit is not None}
    stray = sorted({predictions[index].fix_commit for index, bfc in resolved.items() if bfc not in oracles})
    if stray:
        effect = "those predictions count for no fix" if len(oracles) > 1 else \
            "with one bug-fixing commit the reference is not scored"
        notes.append(f"attribution: {len(stray)} fix_commit value(s) resolve to no declared bug-fixing commit "
                     f"({', '.join(stray)}); {effect}.")
    if len(oracles) < 2:
        return None
    if policy.evaluation_policy not in SET_POLICIES or policy.expect_no_bic:
        notes.append(f"attribution: not scored under {policy.evaluation_policy}, which is not a comparison of sets.")
        return None
    union = sorted(set().union(*oracles.values()))
    if union != sorted(policy.required):
        notes.append(f"attribution: not scored, because the direct BICs of the bug-fixing commits ({', '.join(union)}) "
                     f"are not the commit-level oracle ({', '.join(sorted(policy.required))}).")
        return None
    fixes: dict[str, dict[str, Any]] = {}
    for bfc, required in oracles.items():
        attributed = [prediction for index, prediction in enumerate(predictions)
                      if prediction.fix_commit is None or resolved.get(index) == bfc]
        ranking = _ranking(attributed, commit_map, hash_to_id, reference_format=reference_format)
        known = [reference for reference, is_known in ranking if is_known]
        unknown = [reference for reference, is_known in ranking if not is_known]
        scored = classify_prediction(replace(policy, required=list(required), minimum_required=None), known,
                                     unknown_predictions=unknown, ranking=ranking)
        fixes[bfc] = {
            "required": list(required),
            "predicted": sorted(set(known)),
            "false_positives": scored.false_positives,
            "false_negatives": scored.false_negatives,
            "unknown_predictions": sorted(set(unknown)),
            "status": scored.status,
        }
    overall = "PASS" if all(entry["status"] == "PASS" for entry in fixes.values()) else "FAIL"
    return {"status": overall, "fixes": fixes}


def load_predictions(
    path: Path,
) -> tuple[dict[str, list[Prediction]], set[str], dict[str, list[str]], dict[str, list[str]], dict[str, str],
           list[str], list[str]]:
    """Read a predictions file: the predictions per scenario, the scenarios a
    record that could be read names, the run errors records report per
    scenario, the loading errors of the records that could not be read per
    scenario, the repository id the records of each scenario name, and the
    loading errors and warnings.

    A record with a loading error is not read at all -- none of its predictions
    count -- but when it names a scenario, the scenario is not dropped either:
    it FAILs with ``run_status: invalid``, whatever its other records predict
    (issue #138).  Before, a record whose predictions could not be read still
    answered its scenario, as an empty prediction that passed an empty oracle.
    """
    errors: list[str] = []
    warnings: list[str] = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return {}, set(), {}, {}, {}, [f"Cannot read predictions file: {exc}"], []
    try:
        # A file that is not UTF-8 raised UnicodeDecodeError (issue #137).  Decoding the
        # whole file, BOM included, keeps the reported byte and offset the file's own:
        # utf-8-sig drops the BOM first and counts from after it (PR #217 review).
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {}, set(), {}, {}, {}, [f"Cannot read predictions file: {path} is not UTF-8 "
                                       f"(byte 0x{raw[exc.start]:02x} at position {exc.start}); save it as UTF-8."], []
    # A BOM, as Windows editors and PowerShell write it, cost the first record (issue #137).
    text = text.removeprefix("\ufeff")
    records = _parse_prediction_records(text, str(path), errors)
    predictions: dict[str, list[Prediction]] = {}
    explicit_scenarios: set[str] = set()
    run_errors: dict[str, list[str]] = {}
    invalid_records: dict[str, list[str]] = {}
    repository_ids: dict[str, str] = {}
    for location, record in records:
        if not isinstance(record, dict):
            errors.append(f"{location}: prediction record must be a JSON object.")
            continue
        scenario_id = record.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            # nothing to attribute it to: a loading error only
            errors.append(f"{location}: prediction record lacks string scenario_id.")
            continue
        record_errors: list[str] = []
        status = record.get("status")
        unreadable_status = status is not None and (not isinstance(status, str)
                                                    or status.lower() not in RECORD_STATUSES)
        if unreadable_status:
            record_errors.append(f"{location}: status must be one of {', '.join(RECORD_STATUSES)} when present "
                                 f"(got {status!r}).")
        failed = not unreadable_status and status is not None and status.lower() == "error"
        named_repository = record.get("repository_id")
        if named_repository is not None:
            if not isinstance(named_repository, str) or not named_repository:
                record_errors.append(f"{location}: repository_id must be a non-empty string when present.")
            elif repository_ids.get(scenario_id, named_repository) != named_repository:
                record_errors.append(f"{location}: repository_id {named_repository} differs from the "
                                     f"{repository_ids[scenario_id]} an earlier record of {scenario_id} names.")
        top_level = [key for key in INDUCING_COMMIT_KEYS if record.get(key) is not None]
        read: list[Prediction] = []
        if "predictions" in record:
            nested = record["predictions"]
            if not isinstance(nested, list):
                # null included: it was read as "no list", and then as a record without inducing_commit
                record_errors.append(f"{location}: predictions must be a list when present (got {nested!r}).")
            else:
                if top_level:       # it used to be ignored without a word
                    record_errors.append(f"{location}: the record has both a predictions list and a top-level "
                                         f"{top_level[0]}; put every prediction in the list.")
                for index, item in enumerate(nested):
                    prediction = _prediction_from_record(scenario_id, item, f"{location}.predictions[{index}]",
                                                         record_errors)
                    if prediction is not None:
                        read.append(prediction)
        elif top_level or not (failed or unreadable_status):
            # one record per prediction; without an inducing commit, a failed record only reports
            # the failure, and one whose status cannot be read has its error already
            prediction = _prediction_from_record(scenario_id, record, location, record_errors)
            if prediction is not None:
                read.append(prediction)
        if record_errors:
            errors.extend(record_errors)
            invalid_records.setdefault(scenario_id, []).extend(record_errors)
            continue
        explicit_scenarios.add(scenario_id)
        if named_repository is not None:
            repository_ids.setdefault(scenario_id, named_repository)
        if failed:
            reported = run_errors.setdefault(scenario_id, [])
            reported.extend(message for message in _run_error_messages(record.get("errors")) if message not in reported)
        if read:
            predictions.setdefault(scenario_id, []).extend(read)
    return predictions, explicit_scenarios, run_errors, invalid_records, repository_ids, errors, warnings


def _run_error_messages(value: Any) -> list[str]:
    """The messages of a record's ``errors`` (a string or a list of them)."""
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        messages = [str(item) for item in value if item is not None and str(item)]
        if messages:
            return messages
    return ["the tool reported an error"]


def _parse_prediction_records(text: str, path_display: str, errors: list[str]) -> list[tuple[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        records = []
        for index, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append((f"{path_display}:{index}", json.loads(line)))
            except json.JSONDecodeError as exc:
                errors.append(f"{path_display}:{index}: invalid JSON record: {exc}")
        return records
    if isinstance(data, list):
        return [(f"{path_display}[{index}]", item) for index, item in enumerate(data)]
    if isinstance(data, dict) and isinstance(data.get("scenarios"), list):
        return [(f"{path_display}.scenarios[{index}]", item) for index, item in enumerate(data["scenarios"])]
    if isinstance(data, dict) and isinstance(data.get("predictions"), list) and not isinstance(data.get("scenario_id"), str):
        return [(f"{path_display}.predictions[{index}]", item) for index, item in enumerate(data["predictions"])]
    return [(path_display, data)]


def _prediction_from_record(
    scenario_id: str,
    record: Any,
    location: str,
    errors: list[str],
) -> Prediction | None:
    if not isinstance(record, dict):
        errors.append(f"{location}: prediction must be a JSON object.")
        return None
    inducing_commit = _first_string(record, INDUCING_COMMIT_KEYS)
    if inducing_commit is None:
        # a value of the wrong type is not a missing one (issue #138)
        supplied = [key for key in INDUCING_COMMIT_KEYS if record.get(key) is not None]
        if supplied:
            errors.append(f"{location}: {supplied[0]} must be a non-empty string (got {record[supplied[0]]!r}).")
        else:
            errors.append(f"{location}: prediction lacks inducing_commit.")
        return None
    rank = record.get("rank")
    if rank is not None and not _is_int(rank):           # `true` sorted as rank 1 (issue #146)
        errors.append(f"{location}: rank must be an integer when present.")
        return None
    confidence = record.get("confidence")
    if confidence is not None and _number_value(confidence) is None:
        errors.append(f"{location}: confidence must be a number when present.")
        return None
    fix_commit = _first_string(record, FIX_COMMIT_KEYS)
    if fix_commit is None:
        # An omitted or null fix reference means "unspecified" and, under a
        # branch-level oracle, the prediction counts for every branch.  A
        # supplied value that is not a non-empty string must not be read
        # that way (PR #71 review): it is an input error.
        supplied = [key for key in FIX_COMMIT_KEYS if record.get(key) is not None]
        if supplied:
            errors.append(
                f"{location}: {supplied[0]} must be a non-empty string when present (got {record[supplied[0]]!r})."
            )
            return None
    return Prediction(
        scenario_id=scenario_id,
        fix_commit=fix_commit,
        inducing_commit=inducing_commit,
        rank=rank,
        confidence=_number_value(confidence) if confidence is not None else None,
        tool=_first_string(record, ["tool"]),
        raw_file=_first_string(record, ["raw_file"]),
    )


#: Record keys that name the bug-fixing commit a prediction was made from.
FIX_COMMIT_KEYS = ["fix_commit", "bug_fixing_commit", "fix_commit_hash"]
#: Record keys that name the predicted bug-inducing commit.
INDUCING_COMMIT_KEYS = ["inducing_commit", "bug_introducing_commit", "bic", "inducing_commit_hash"]


def _first_string(record: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def orphan_output_warning(scenario_id: str, generated_root: Path) -> str:
    """The warning for a generated output whose scenario no longer exists.

    Retiring a scenario (docs/retired-ids.md) removes its source and index entry,
    but generated output is untracked and stays behind in existing checkouts; no
    command regenerates or removes it.  Consumers skip it rather than fail.
    """
    return (f"generated output '{scenario_id}' has no scenario; it was probably retired "
            f"(see docs/retired-ids.md) and is skipped. Remove {generated_root / scenario_id} to silence this.")


def _find_scenario_path(scenario_id: str, scenarios_root: Path, advanced_scenarios_root: Path) -> tuple[Path | None, str]:
    classic = scenarios_root / scenario_id / "scenario.yml"
    if classic.exists():
        return classic, "scenarios"
    graph = advanced_scenarios_root / scenario_id / "scenario.graph.yml"
    if graph.exists():
        return graph, "advanced-scenarios"
    return None, "unknown"


def _load_scenario_for_evaluation(path: Path, suite: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if suite == "advanced-scenarios":
        scenario, result = load_graph_scenario(path)
    else:
        scenario, result = load_yaml(path)
    errors.extend(f"{finding.location or path}: {finding.message}" for finding in result.findings if finding.severity == "ERROR")
    return scenario, errors


def _load_commit_map(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"Cannot read commit-map.json at {path}: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"Invalid commit-map.json at {path}: {exc}"]
    if not isinstance(data, dict):
        return None, [f"commit-map.json at {path} must contain a JSON object."]
    return data, []


def _commit_level_policy(
    scenario: dict[str, Any],
    suite: str,
    evaluation_variant: str | None,
) -> CommitLevelPolicy:
    if suite == "advanced-scenarios":
        return _graph_commit_level_policy(scenario, evaluation_variant)
    expected, allowed, distractors, notes = _expected_classic_commit_ids(scenario)
    return CommitLevelPolicy(
        evaluation_policy="exact_set",
        evaluation_variant=None,
        required=expected,
        acceptable_related=[AcceptableRelated(commit=commit) for commit in allowed],
        known_distractors=distractors,
        notes=notes,
    )


def _graph_commit_level_policy(
    scenario: dict[str, Any],
    evaluation_variant: str | None,
) -> CommitLevelPolicy:
    expected_szz = scenario.get("expected_szz") if isinstance(scenario.get("expected_szz"), dict) else {}
    base_commit_level = expected_szz.get("commit_level") if isinstance(expected_szz.get("commit_level"), dict) else {}
    notes: list[str] = []
    selected_variant = _selected_evaluation_variant(expected_szz, evaluation_variant, notes)
    selected_commit_level = base_commit_level
    if selected_variant is not None:
        variant_commit_level = selected_variant.get("commit_level")
        if isinstance(variant_commit_level, dict):
            selected_commit_level = dict(variant_commit_level)
            if "evaluation_policy" not in selected_commit_level and isinstance(base_commit_level.get("evaluation_policy"), str):
                selected_commit_level["evaluation_policy"] = base_commit_level["evaluation_policy"]
        else:
            selected_commit_level = {}
            notes.append(f"Evaluation variant '{selected_variant['name']}' has no commit_level; using inferred BICs.")

    policy_name = selected_commit_level.get("evaluation_policy")
    if not isinstance(policy_name, str) or not policy_name:
        policy_name = "exact_set"
    if policy_name not in _SUPPORTED_GRAPH_POLICIES:
        notes.append(f"Unsupported evaluation_policy '{policy_name}' treated as exact_set.")
        policy_name = "exact_set"

    required = _string_list(selected_commit_level.get("required"))
    expect_no_bic = selected_commit_level.get("expect_no_bic") is True
    if expect_no_bic and required:
        notes.append("expect_no_bic is true but required is non-empty; ignoring expect_no_bic.")
        expect_no_bic = False
    required_inferred = not required and not expect_no_bic
    if required_inferred:
        required = _graph_direct_bic_ids(scenario)
        if required:
            notes.append(
                "commit_level.required is missing or empty; required BICs inferred from "
                f"bugs[].bug_introducing_commits (roles {'/'.join(sorted(DIRECT_BIC_ROLES))}): {', '.join(required)}."
            )
        else:
            notes.append(
                "commit_level.required is missing or empty and no BICs could be inferred from bugs[]; "
                "the required set is empty (declare expect_no_bic: true for an intentionally empty oracle)."
            )
    unread_sections = sorted(key for key in expected_szz if key in _UNREAD_GRAPH_ORACLE_SECTIONS)
    if unread_sections:
        notes.append(_UNREAD_SECTIONS_NOTE.format(sections=", ".join(unread_sections)))

    acceptable_related = _acceptable_related_entries(selected_commit_level.get("acceptable_related"), notes)
    related_origins = _string_list(selected_commit_level.get("related_origins"))
    related_but_not_correct = _string_list(selected_commit_level.get("related_but_not_correct"))
    relevant = _string_list(selected_commit_level.get("relevant"))
    if expect_no_bic and (acceptable_related or related_origins or related_but_not_correct or relevant):
        # With an intentionally empty oracle every known prediction is a false
        # positive; keeping allowances would hide predictions from the FP counts
        # while the status still fails.
        ignored = [
            name
            for name, values in (
                ("acceptable_related", acceptable_related),
                ("related_origins", related_origins),
                ("related_but_not_correct", related_but_not_correct),
                ("relevant", relevant),
            )
            if values
        ]
        notes.append(
            f"expect_no_bic is true; {', '.join(ignored)} ignored because every known prediction counts as a false positive."
        )
        acceptable_related, related_origins, related_but_not_correct, relevant = [], [], [], []

    return CommitLevelPolicy(
        evaluation_policy=policy_name,
        evaluation_variant=selected_variant["name"] if selected_variant is not None else None,
        required=required,
        acceptable_related=acceptable_related,
        related_origins=related_origins,
        related_but_not_correct=related_but_not_correct,
        relevant=relevant,
        minimum_required=_minimum_required_value(selected_commit_level.get("minimum_required"), notes),
        k_values=_k_values(selected_commit_level.get("k_values"), notes),
        status_k=_status_k_value(selected_commit_level.get("status_k"), notes),
        expect_no_bic=expect_no_bic,
        known_distractors=_string_list(selected_commit_level.get("known_distractors")),
        notes=notes,
        required_inferred=required_inferred,
    )


#: The note that names them.  Nothing in the scenario is wrong, so it is
#: information rather than a warning (issue #126).
_UNREAD_SECTIONS_NOTE = "expected_szz also declares {sections}; these sections are not used by commit-level evaluation."


def _is_information_note(note: str) -> bool:
    """True for the oracle note reported as information: the sections the
    evaluator does not read.  Every other oracle note asks the author to change
    the scenario, and is promoted to a report warning."""
    return note.startswith(_UNREAD_SECTIONS_NOTE.split("{sections}")[0])


#: Oracle sections the commit-level evaluator does not read (reported as a note).
_UNREAD_GRAPH_ORACLE_SECTIONS = {
    "bug_level",
    "entity_level",
    "line_level",
    "bug_instances",
    "work_item_level",
}


_SUPPORTED_GRAPH_POLICIES = {
    "exact_set",
    "direct_only",
    "reintroduction_direct",
    "partial_credit",
    "top_k",
    "relaxed_with_related",
    "relaxed_with_credit",
}


#: The note on a scenario that does not define the requested variant.  A run
#: reports these once, as one warning, instead of once per scenario (issue #140).
_UNDEFINED_VARIANT_NOTE = "Requested evaluation variant '{name}' is not defined; using {used}."


def _requested_evaluation_variant(value: str | None) -> str | None:
    """``--evaluation-variant`` as the evaluator reads it: an empty or blank
    name, which is what an unset shell variable expands to, is no name, and
    selects what an omitted option selects (issue #140)."""
    return value if value is not None and value.strip() else None


def _selected_evaluation_variant(
    expected_szz: dict[str, Any],
    requested_variant: str | None,
    notes: list[str],
) -> dict[str, Any] | None:
    """The evaluation variant to score, or None for ``commit_level``.

    Without a requested name, the scenario's ``default_variant`` (None when it
    names no variant: GE129).  A requested name that the scenario does not
    define selects the same, with a note naming what was used.  It used to
    select ``commit_level``, so SZZG-0022, SZZG-0085 and SZZG-0146, which keep
    their whole oracle in variants, were scored against a required set
    inferred from bugs[] (issue #140).
    """
    requested_variant = _requested_evaluation_variant(requested_variant)
    variants = expected_szz.get("evaluation_variants")
    if requested_variant is not None:
        found = _evaluation_variant_named(variants, requested_variant)
        if found is not None:
            return found
        fallback_notes: list[str] = []
        fallback = _selected_evaluation_variant(expected_szz, None, fallback_notes)
        used = f"the default variant '{fallback['name']}'" if fallback is not None else "commit_level"
        notes.append(_UNDEFINED_VARIANT_NOTE.format(name=requested_variant, used=used))
        notes.extend(fallback_notes)
        return fallback
    if not isinstance(variants, list):
        return None
    default_variant = expected_szz.get("default_variant")
    if not isinstance(default_variant, str) or not default_variant:
        return None
    found = _evaluation_variant_named(variants, default_variant)
    if found is None:
        notes.append(f"default_variant '{default_variant}' is not defined; using commit_level.")
    return found


def _evaluation_variant_named(variants: Any, name: str) -> dict[str, Any] | None:
    """The variant called ``name``: spelt as written first, then after
    lower-casing and treating ``-`` and ``_`` alike."""
    if not isinstance(variants, list):
        return None
    for item in variants:
        if isinstance(item, dict) and item.get("name") == name:
            return item
    key = _evaluation_variant_key(name)
    for item in variants:
        if isinstance(item, dict) and _evaluation_variant_key(item.get("name")) == key:
            return item
    return None


def _evaluation_variant_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.lower().replace("_", "-")


def _graph_direct_bic_ids(scenario: dict[str, Any]) -> list[str]:
    """Infer the required BICs from bug metadata (roles normalized via normalize_bic_role).

    Malformed metadata is skipped rather than raised: validate-graph asks this
    of a scenario it has not accepted yet (GW130, PR #124 review).
    """
    expected: set[str] = set()
    bugs = scenario.get("bugs")
    for bug in bugs if isinstance(bugs, list) else []:
        if not isinstance(bug, dict) or not isinstance(bug.get("bug_introducing_commits") or [], list):
            continue
        for entry in graph_bic_entries(bug, roles=DIRECT_BIC_ROLES):
            commit = entry.get("commit")
            if isinstance(commit, str):
                expected.add(commit)
    return sorted(expected)


def _acceptable_related_entries(value: Any, notes: list[str]) -> list[AcceptableRelated]:
    entries: list[AcceptableRelated] = []
    if not isinstance(value, list):                     # GE124 reports it; see _string_list
        return entries
    for item in value:
        if isinstance(item, str):
            entries.append(AcceptableRelated(commit=item))
        elif isinstance(item, dict) and isinstance(item.get("commit"), str):
            credit = item.get("credit")
            number = 0.0 if credit is None else _number_value(credit)
            if number is None:
                # `credit: true` counted 1.0; a string counted 0 without a word (issue #146, GE131)
                notes.append(f"acceptable_related credit of '{item['commit']}' must be a number; ignoring it.")
                number = 0.0
            reason = item.get("reason")
            entries.append(
                AcceptableRelated(
                    commit=item["commit"],
                    reason=reason if isinstance(reason, str) else None,
                    credit=number,
                )
            )
    return entries


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _is_int(value: Any) -> bool:
    """An integer, and not a boolean.  ``bool`` is a subclass of ``int``, so
    ``true`` passed for 1 in ``rank``, ``k_values`` and ``minimum_required``
    (issue #146); validate-graph asks the same (GE131)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _number_value(value: Any) -> float | None:
    """``credit`` or ``confidence`` as a float, or None when it is not a number:
    a boolean (issue #146), a string, or an integer too large for a float,
    which raised OverflowError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value)
    except OverflowError:
        return None


def _minimum_required_value(value: Any, notes: list[str]) -> int | None:
    if value is None:
        return None
    if _is_int(value) and value >= 0:
        return value
    notes.append("minimum_required must be a non-negative integer; ignoring it.")
    return None


def _k_values(value: Any, notes: list[str]) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        notes.append("k_values must be a list of positive integers; ignoring it.")
        return []
    ignored = [item for item in value if not (_is_int(item) and item > 0)]
    if ignored:
        # `true` became the hit_at key "True" (issue #146)
        notes.append(f"k_values entries must be positive integers; ignoring {', '.join(map(repr, ignored))}.")
    return sorted({item for item in value if _is_int(item) and item > 0})


def _status_k_value(value: Any, notes: list[str]) -> int | None:
    if value is None:
        return None
    if _is_int(value) and value > 0:
        return value
    notes.append("status_k must be a positive integer; ignoring it.")
    return None


def _ranking(
    predictions: list[Prediction],
    commit_map: dict[str, Any],
    hash_to_id: dict[str, str],
    *,
    reference_format: str = "auto",
) -> list[tuple[str, bool]]:
    """The predicted commits in rank order, each once, as ``(reference, known)``.

    A known reference is normalized to its logical id; an unknown one is kept
    as written and holds its place, so under ``top_k`` it pushes a correct
    commit ranked after it down just as a wrong known commit does (issue #95).
    """
    indexed_predictions = list(enumerate(predictions))
    if any(prediction.rank is not None for prediction in predictions):
        indexed_predictions.sort(
            key=lambda item: (
                item[1].rank is None,
                item[1].rank if item[1].rank is not None else item[0],
                item[0],
            )
        )
    ranking: list[tuple[str, bool]] = []
    seen: set[tuple[str, bool]] = set()
    for _, prediction in indexed_predictions:
        normalized = _normalize_commit_ref(prediction.inducing_commit, commit_map, hash_to_id, reference_format=reference_format)
        entry = (prediction.inducing_commit, False) if normalized is None else (normalized, True)
        if entry not in seen:
            ranking.append(entry)
            seen.add(entry)
    return ranking


def _ranked_actual_ids(
    predictions: list[Prediction],
    commit_map: dict[str, Any],
    hash_to_id: dict[str, str],
    *,
    reference_format: str = "auto",
) -> tuple[list[str], list[str]]:
    """The known predicted commits in rank order, and the unknown references."""
    ranking = _ranking(predictions, commit_map, hash_to_id, reference_format=reference_format)
    return [ref for ref, known in ranking if known], [ref for ref, known in ranking if not known]


def _weighted_credit(
    true_positives: list[str],
    acceptable_related_hits: list[dict[str, Any]],
    expected_count: int,
) -> float | None:
    if expected_count == 0:
        return None
    credit = float(len(true_positives))
    for hit in acceptable_related_hits:
        value = hit.get("credit")
        if isinstance(value, (int, float)):
            credit += float(value)
    return min(float(expected_count), credit)


def _minimum_required_met(policy: CommitLevelPolicy, true_positive_count: int) -> bool | None:
    if policy.minimum_required is not None:
        return true_positive_count >= policy.minimum_required
    if policy.evaluation_policy == "partial_credit":
        return true_positive_count >= len(policy.required)
    return None


def _top_k_metrics(policy: CommitLevelPolicy, ranking: list[tuple[str, bool]]) -> dict[str, Any] | None:
    """hit@k and MRR over ``ranking``, the ``(reference, known)`` pairs in rank order.

    An unknown reference holds its rank but is never a hit, even when it is
    spelled like a relevant logical id: under ``--reference-format hash`` the
    id ``c1`` is an unknown reference, and reading it as ``c1`` put a hit at
    rank 1 that belonged to the hash at rank 2 (PR #99 review).
    """
    if policy.evaluation_policy != "top_k" and not policy.k_values:
        return None
    relevant = set(policy.relevant or policy.required)
    k_values = policy.k_values or [1, 3, 5]
    if policy.status_k is not None:
        status_k = policy.status_k
    else:
        status_k = max(policy.k_values) if policy.k_values else 1
    best_rank = None
    for index, (commit, known) in enumerate(ranking, start=1):
        if known and commit in relevant:
            best_rank = index
            break
    return {
        "k_values": k_values,
        "status_k": status_k,
        "relevant": sorted(relevant),
        "ranked_actual_bics": [commit for commit, known in ranking if known],
        "unknown_ranks": [index for index, (_, known) in enumerate(ranking, start=1) if not known],
        "best_rank": best_rank,
        "hit_at": {str(k): best_rank is not None and best_rank <= k for k in k_values},
        "mrr": (1.0 / best_rank) if best_rank is not None else 0.0,
    }


@dataclass
class ScoredPrediction:
    """What a policy makes of a predicted set of logical commit ids.

    Everything here is derived from the policy and the prediction alone - no
    repository, no commit map - so a check that wants to know "would this
    prediction pass?" can ask the evaluator instead of reimplementing it.  Both
    `evaluate_scenario` and the direct/origin lints of `graph_validator` go
    through this function; the lints used to re-derive parts of it and got two
    interactions wrong (PR #45 review).
    """

    status: str
    true_positives: list[str]
    false_positives: list[str]
    false_negatives: list[str]
    allowed_false_positives: list[str]
    related_origin_hits: list[str]
    related_but_not_correct_hits: list[str]
    known_distractor_hits: list[str]
    hard_false_positives: list[str]
    acceptable_related_hits: list[dict[str, Any]]
    weighted_credit: float
    possible_credit: float | None
    credit_ratio: float | None
    minimum_required_met: bool | None
    top_k: dict[str, Any] | None


def classify_prediction(
    policy: CommitLevelPolicy,
    ranked_actual_ids: Sequence[str],
    *,
    unknown_predictions: Sequence[str] = (),
    ranking: Sequence[tuple[str, bool]] | None = None,
) -> ScoredPrediction:
    """Score `ranked_actual_ids` against `policy`.

    ``ranking`` is the full rank order as ``(reference, known)`` pairs, unknown
    references included; ``top_k`` reads it when it is given and
    ``ranked_actual_ids`` otherwise.
    """
    expected = set(policy.required)
    allowed_map = {item.commit: item for item in policy.acceptable_related}
    allowed = set(allowed_map)
    actual = set(ranked_actual_ids)
    true_positives = sorted(actual & expected)
    allowed_false_positives = sorted(actual & allowed)
    related_origins = set(policy.related_origins)
    related_but_not_correct = set(policy.related_but_not_correct)
    acceptable_related_hits = [allowed_map[commit].to_dict() for commit in allowed_false_positives]
    weighted_credit = _weighted_credit(true_positives, acceptable_related_hits, len(expected))
    possible_credit = float(len(expected)) if expected else None
    minimum_required_met = _minimum_required_met(policy, len(true_positives))
    top_k = _top_k_metrics(policy, list(ranking) if ranking is not None
                           else [(commit, True) for commit in ranked_actual_ids])
    false_positives = sorted(actual - expected - allowed)
    false_negatives = sorted(expected - actual)
    hard_false_positives = sorted(actual - expected - allowed - related_origins - related_but_not_correct)
    related_but_not_correct_hits = sorted(actual & related_but_not_correct)
    return ScoredPrediction(
        status=_evaluation_status(
            policy,
            false_positives=false_positives,
            false_negatives=false_negatives,
            hard_false_positives=hard_false_positives,
            related_but_not_correct_hits=related_but_not_correct_hits,
            unknown_predictions=list(unknown_predictions),
            minimum_required_met=minimum_required_met,
            top_k=top_k,
            actual_count=len(actual),
        ),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        allowed_false_positives=allowed_false_positives,
        related_origin_hits=sorted(actual & related_origins),
        related_but_not_correct_hits=related_but_not_correct_hits,
        known_distractor_hits=sorted(actual & set(policy.known_distractors)),
        hard_false_positives=hard_false_positives,
        acceptable_related_hits=acceptable_related_hits,
        weighted_credit=weighted_credit,
        possible_credit=possible_credit,
        credit_ratio=_float_ratio(weighted_credit, possible_credit),
        minimum_required_met=minimum_required_met,
        top_k=top_k,
    )


def _evaluation_status(
    policy: CommitLevelPolicy,
    *,
    false_positives: list[str],
    false_negatives: list[str],
    hard_false_positives: list[str],
    related_but_not_correct_hits: list[str],
    unknown_predictions: list[str],
    minimum_required_met: bool | None,
    top_k: dict[str, Any] | None,
    actual_count: int,
) -> str:
    if unknown_predictions:
        return "FAIL"
    if policy.expect_no_bic:
        return "PASS" if actual_count == 0 else "FAIL"
    if policy.evaluation_policy == "top_k":
        if top_k is None or top_k["best_rank"] is None:
            return "FAIL"
        return "PASS" if top_k["best_rank"] <= top_k["status_k"] else "FAIL"
    if policy.evaluation_policy == "partial_credit":
        return "PASS" if minimum_required_met and not false_positives else "FAIL"
    if _allows_related_context(policy):
        relaxed_false_positives = hard_false_positives + related_but_not_correct_hits
        return "PASS" if not relaxed_false_positives and not false_negatives else "FAIL"
    return "PASS" if not false_positives and not false_negatives else "FAIL"


def _allows_related_context(policy: CommitLevelPolicy) -> bool:
    if policy.evaluation_policy in {"relaxed_with_related", "relaxed_with_credit"}:
        return True
    if policy.evaluation_variant is None:
        return False
    variant = policy.evaluation_variant.lower().replace("-", "_")
    return "origin" in variant or "related" in variant


def _expected_classic_commit_ids(scenario: dict[str, Any]) -> tuple[list[str], list[str], list[str], list[str]]:
    expected: set[str] = set()
    allowed: set[str] = set()
    distractors: set[str] = set()
    notes: list[str] = []
    for bug in scenario.get("bugs", []) or []:
        if not isinstance(bug, dict):
            continue
        commit_level = (bug.get("expected_szz") or {}).get("commit_level") or {}
        true_positives = commit_level.get("true_positives")
        if isinstance(true_positives, list):
            expected.update(item for item in true_positives if isinstance(item, str))
        else:
            bics = bug.get("bug_introducing_commits") or []
            expected.update(item for item in bics if isinstance(item, str))
        false_positives_allowed = commit_level.get("false_positives_allowed") or []
        allowed.update(item for item in false_positives_allowed if isinstance(item, str))
        distractors.update(_string_list(commit_level.get("known_distractors")))
    return sorted(expected), sorted(allowed), sorted(distractors), notes


def _scenario_bfc_ids(scenario: dict[str, Any]) -> list[str]:
    """Logical ids of every bug-fixing commit declared in bugs[] (classic or graph shape)."""
    ids: list[str] = []
    for bug in scenario.get("bugs", []) or []:
        if not isinstance(bug, dict):
            continue
        for entry in graph_bfc_entries(bug):
            commit = entry.get("commit")
            if isinstance(commit, str) and commit not in ids:
                ids.append(commit)
    return ids


def _classify_fix_shapes(
    scenario: dict[str, Any],
    commit_map: dict[str, Any],
    repo_dir: Path,
    notes: list[str],
) -> dict[str, str] | None:
    """Classify each BFC's first-parent diff; return None when nothing could be classified."""
    if not (repo_dir / ".git").exists():
        notes.append(f"fix_shape not computed: generated repository not found at {repo_dir}.")
        return None
    bfc_ids = _scenario_bfc_ids(scenario)
    if not bfc_ids:
        notes.append("fix_shape not computed: the scenario declares no bug-fixing commits.")
        return None
    shapes: dict[str, str] = {}
    for bfc_id in bfc_ids:
        entry = commit_map.get(bfc_id)
        bfc_hash = entry.get("hash") if isinstance(entry, dict) else None
        if not isinstance(bfc_hash, str) or not bfc_hash:
            notes.append(f"fix_shape not computed for '{bfc_id}': not present in commit-map.json.")
            continue
        try:
            shapes[bfc_id] = _classify_first_parent_diff(repo_dir, bfc_hash)
        except GitError as exc:
            notes.append(f"fix_shape not computed for '{bfc_id}': {exc}")
    return shapes or None


def _classify_first_parent_diff(repo_dir: Path, commit_hash: str) -> str:
    parent_hash = git_parent(repo_dir, commit_hash)
    if parent_hash:
        diff = run_git(repo_dir, ["diff", "--no-color", "--no-ext-diff", "--unified=0", "--no-renames", parent_hash, commit_hash]).stdout
    else:
        # Root commit: `git show` diffs against the empty tree (a root commit is never a merge).
        diff = run_git(repo_dir, ["show", "--format=", "--no-color", "--no-ext-diff", "--unified=0", "--no-renames", commit_hash]).stdout
    return classify_diff_text(diff)


def classify_diff_text(diff: str) -> str:
    """Return the fix shape of a unified diff: empty_first_parent, addition_only, or modifies."""
    if not diff.strip():
        return "empty_first_parent"
    in_hunk = False
    for line in diff.splitlines():
        if line.startswith("diff --git"):
            in_hunk = False
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("-"):
            return "modifies"
    return "addition_only"


def _hash_to_logical_id(commit_map: dict[str, Any]) -> dict[str, str]:
    lookup = {}
    for logical_id, entry in commit_map.items():
        if isinstance(logical_id, str) and isinstance(entry, dict) and isinstance(entry.get("hash"), str):
            # in lower case, as _normalize_commit_ref compares a hash (issue #142)
            lookup[entry["hash"].lower()] = logical_id
    return lookup


#: Prediction reference formats accepted by ``evaluate`` (issue #8).
#:
#: ``hash`` is the format a tool that reads the generated repository can
#: actually produce; ``logical`` is for adapters, fixtures and the tests, which
#: know the scenario; ``auto`` accepts both and stays the default so that
#: existing prediction files keep working.
REFERENCE_FORMATS = ("auto", "hash", "logical")


#: A full hash or an abbreviation of one, in any letter case (SHA-1: the generators use no other).
_HEX_REFERENCE = re.compile(r"[0-9a-fA-F]{7,40}")


def _normalize_commit_ref(
    ref: str,
    commit_map: dict[str, Any],
    hash_to_id: dict[str, str],
    *,
    reference_format: str = "auto",
) -> str | None:
    """The logical id that a predicted ``inducing_commit`` or ``fix_commit`` names, or None.

    Surrounding whitespace is not part of a reference, and a hash or a hash
    prefix is read in any letter case, as Git reads it: an upper-case hash,
    or one with the newline a shell pipeline leaves on it, was an unknown
    prediction (issue #142).  A logical id is matched as written.  The caller
    keeps an unknown reference as written.
    """
    if reference_format not in REFERENCE_FORMATS:
        raise ValueError(f"reference_format must be one of {REFERENCE_FORMATS}, got {reference_format!r}")
    ref = ref.strip()
    if not ref:
        return None
    if reference_format != "hash" and ref in commit_map:
        return ref
    if reference_format == "logical":
        return None
    if _HEX_REFERENCE.fullmatch(ref):
        ref = ref.lower()
    if ref in hash_to_id:
        return hash_to_id[ref]
    if len(ref) >= 7:
        matches = [logical_id for commit_hash, logical_id in hash_to_id.items() if commit_hash.startswith(ref)]
        if len(matches) == 1:
            return matches[0]
    return None


def _scenario_category(scenario: dict[str, Any]) -> str | None:
    meta = scenario.get("meta")
    if isinstance(meta, dict) and isinstance(meta.get("category"), str):
        return meta["category"]
    return None


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _float_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _format_credit(weighted_credit: float | None, possible_credit: float | None) -> str:
    if weighted_credit is None or possible_credit is None:
        return "-"
    return f"{weighted_credit:.3f}/{possible_credit:.3f}"


def _md_line(text: Any) -> str:
    """Text that stays on one Markdown line: line breaks and tabs become one space.

    Unknown references and run errors are the tool's own text, written as it
    came; a newline in one used to split a table row or a list item (issue #139).
    The JSON report keeps the text unchanged.
    """
    return re.sub(r"[ \t]*[\r\n\t]+[ \t]*", " ", str(text))


def _md_cell(text: Any) -> str:
    """A table cell: on one line, and with ``|`` escaped so that it cannot end the cell (issue #139)."""
    return _md_line(text).replace("|", "\\|")


def _join_ids(values: list[str]) -> str:
    if not values:
        return "-"
    return ", ".join(values)


def _format_top_k(top_k: dict[str, Any] | None) -> str:
    if top_k is None:
        return "-"
    best_rank = top_k.get("best_rank")
    hit = f"rank {best_rank}" if best_rank is not None else "miss"
    return f"{hit} (k={top_k.get('status_k')})"


def _format_fix_shape(fix_shape: dict[str, str] | None) -> str:
    if not fix_shape:
        return "-"
    return ", ".join(f"{commit}:{shape}" for commit, shape in fix_shape.items())


def _format_fix_shape_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{shape} {counts.get(shape, 0)}" for shape in FIX_SHAPES)
