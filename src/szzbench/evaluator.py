from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from .graph_scenario import graph_bic_entries, load_graph_scenario
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
    notes: list[str] = field(default_factory=list)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "suite": self.suite,
            "category": self.category,
            "status": self.status,
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
        }


@dataclass
class EvaluationReport:
    scenarios: list[ScenarioEvaluation]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        total = len(self.scenarios)
        passed = sum(1 for item in self.scenarios if item.status == "PASS")
        failed = sum(1 for item in self.scenarios if item.status != "PASS")
        tp = sum(len(item.true_positives) for item in self.scenarios)
        fp = sum(len(item.false_positives) for item in self.scenarios)
        fn = sum(len(item.false_negatives) for item in self.scenarios)
        allowed_fp = sum(len(item.allowed_false_positives) for item in self.scenarios)
        hard_fp = sum(len(item.hard_false_positives) for item in self.scenarios)
        related_origin_hits = sum(len(item.related_origin_hits) for item in self.scenarios)
        related_but_not_correct_hits = sum(len(item.related_but_not_correct_hits) for item in self.scenarios)
        possible_credit = sum(item.possible_credit for item in self.scenarios if item.possible_credit is not None)
        weighted_credit = sum(item.weighted_credit for item in self.scenarios if item.weighted_credit is not None)
        precision = _ratio(tp, tp + fp)
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
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "allowed_false_positives": allowed_fp,
            "hard_false_positives": hard_fp,
            "related_origin_hits": related_origin_hits,
            "related_but_not_correct_hits": related_but_not_correct_hits,
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
            f"- True positives: {summary['true_positives']}",
            f"- False positives: {summary['false_positives']}",
            f"- False negatives: {summary['false_negatives']}",
            f"- Allowed false positives: {summary['allowed_false_positives']}",
            f"- Hard false positives: {summary['hard_false_positives']}",
            f"- Related origin hits: {summary['related_origin_hits']}",
            f"- Related-but-not-correct hits: {summary['related_but_not_correct_hits']}",
            f"- Weighted credit: {_format_credit(summary['weighted_credit'], summary['possible_credit'])}",
            f"- Precision: {_format_ratio(summary['precision'])}",
            f"- Recall: {_format_ratio(summary['recall'])}",
            "",
        ]
        if self.errors:
            lines.extend(["## Errors", ""])
            lines.extend(f"- {error}" for error in self.errors)
            lines.append("")
        if self.warnings:
            lines.extend(["## Warnings", ""])
            lines.extend(f"- {warning}" for warning in self.warnings)
            lines.append("")
        lines.extend(
            [
                "## Results",
                "",
                "| Scenario | Status | Suite | Policy | Variant | Category | Expected BICs | Actual BICs | TP | FP | FN | Allowed FP | Predictions |",
                "|---|---:|---|---|---|---|---|---|---|---|---|---|---:|",
            ]
        )
        for item in self.scenarios:
            lines.append(
                "| "
                + " | ".join(
                    [
                        item.scenario_id,
                        item.status,
                        item.suite,
                        item.evaluation_policy or "-",
                        item.evaluation_variant or "-",
                        item.category or "-",
                        _join_ids(item.expected_bics),
                        _join_ids(item.actual_bics),
                        _join_ids(item.true_positives),
                        _join_ids(item.false_positives),
                        _join_ids(item.false_negatives),
                        _join_ids(item.allowed_false_positives),
                        str(item.prediction_count),
                    ]
                )
                + " |"
            )
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
) -> EvaluationReport:
    if predictions_path is None:
        predictions_by_scenario: dict[str, list[Prediction]] = {}
        explicit_scenarios: set[str] = set()
        errors: list[str] = []
        warnings: list[str] = []
    else:
        predictions_by_scenario, explicit_scenarios, errors, warnings = load_predictions(predictions_path)
    scenario_ids = set(explicit_scenarios or predictions_by_scenario.keys())
    if include_generated:
        scenario_ids.update(_generated_scenario_ids(generated_root, variant))
    evaluations: list[ScenarioEvaluation] = []
    for scenario_id in sorted(scenario_ids):
        scenario_path, suite = _find_scenario_path(scenario_id, scenarios_root, advanced_scenarios_root)
        if scenario_path is None:
            errors.append(f"Cannot find scenario for '{scenario_id}'.")
            continue
        scenario, scenario_errors = _load_scenario_for_evaluation(scenario_path, suite)
        errors.extend(scenario_errors)
        if scenario is None:
            continue
        commit_map_path = generated_root / scenario_id / variant / "metadata" / "commit-map.json"
        commit_map, commit_map_errors = _load_commit_map(commit_map_path)
        errors.extend(commit_map_errors)
        if commit_map is None:
            continue
        evaluations.append(
            evaluate_scenario(
                scenario_id,
                scenario,
                scenario_path,
                suite,
                commit_map,
                predictions_by_scenario.get(scenario_id, []),
                evaluation_variant=evaluation_variant,
            )
        )
    return EvaluationReport(evaluations, errors=errors, warnings=warnings)


def _generated_scenario_ids(generated_root: Path, variant: str) -> set[str]:
    scenario_ids = set()
    for repo_dir in generated_root.glob(f"*/{variant}/repo"):
        if repo_dir.is_dir() and (repo_dir / ".git").exists():
            scenario_ids.add(repo_dir.parent.parent.name)
    return scenario_ids


def evaluate_scenario(
    scenario_id: str,
    scenario: dict[str, Any],
    scenario_path: Path,
    suite: str,
    commit_map: dict[str, Any],
    predictions: list[Prediction],
    *,
    evaluation_variant: str | None = None,
) -> ScenarioEvaluation:
    policy = _commit_level_policy(scenario, suite, evaluation_variant)
    hash_to_id = _hash_to_logical_id(commit_map)
    ranked_actual_ids, unknown_predictions = _ranked_actual_ids(predictions, commit_map, hash_to_id)

    expected = set(policy.required)
    allowed_map = {item.commit: item for item in policy.acceptable_related}
    allowed = set(allowed_map)
    actual = set(ranked_actual_ids)
    true_positives = sorted(actual & expected)
    false_positives = sorted(actual - expected - allowed)
    false_negatives = sorted(expected - actual)
    allowed_false_positives = sorted(actual & allowed)
    related_origins = set(policy.related_origins)
    related_but_not_correct = set(policy.related_but_not_correct)
    related_origin_hits = sorted(actual & related_origins)
    related_but_not_correct_hits = sorted(actual & related_but_not_correct)
    hard_false_positives = sorted(actual - expected - allowed - related_origins - related_but_not_correct)
    acceptable_related_hits = [
        allowed_map[commit].to_dict()
        for commit in allowed_false_positives
        if commit in allowed_map
    ]
    weighted_credit = _weighted_credit(true_positives, acceptable_related_hits, len(expected))
    possible_credit = float(len(expected)) if expected else None
    credit_ratio = _float_ratio(weighted_credit, possible_credit)
    minimum_required_met = _minimum_required_met(policy, len(true_positives))
    top_k = _top_k_metrics(policy, ranked_actual_ids)
    status = _evaluation_status(
        policy,
        false_positives=false_positives,
        false_negatives=false_negatives,
        hard_false_positives=hard_false_positives,
        related_but_not_correct_hits=related_but_not_correct_hits,
        unknown_predictions=unknown_predictions,
        minimum_required_met=minimum_required_met,
        top_k=top_k,
    )
    precision = _ratio(len(true_positives), len(true_positives) + len(false_positives))
    recall = _ratio(len(true_positives), len(true_positives) + len(false_negatives))
    category = _scenario_category(scenario)
    return ScenarioEvaluation(
        scenario_id=scenario_id,
        suite=suite,
        category=category,
        status=status,
        expected_bics=sorted(expected),
        actual_bics=sorted(actual),
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
        result_notes=policy.notes,
    )


def load_predictions(path: Path) -> tuple[dict[str, list[Prediction]], set[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, set(), [f"Cannot read predictions file: {exc}"], []
    records = _parse_prediction_records(text, str(path), errors)
    predictions: dict[str, list[Prediction]] = {}
    explicit_scenarios: set[str] = set()
    for location, record in records:
        if not isinstance(record, dict):
            errors.append(f"{location}: prediction record must be a JSON object.")
            continue
        scenario_id = record.get("scenario_id")
        if not isinstance(scenario_id, str) or not scenario_id:
            errors.append(f"{location}: prediction record lacks string scenario_id.")
            continue
        explicit_scenarios.add(scenario_id)
        nested = record.get("predictions")
        if nested is not None:
            if not isinstance(nested, list):
                errors.append(f"{location}: predictions must be a list when present.")
                continue
            for index, item in enumerate(nested):
                prediction = _prediction_from_record(scenario_id, item, f"{location}.predictions[{index}]", errors)
                if prediction is not None:
                    predictions.setdefault(scenario_id, []).append(prediction)
            continue
        prediction = _prediction_from_record(scenario_id, record, location, errors)
        if prediction is not None:
            predictions.setdefault(scenario_id, []).append(prediction)
    return predictions, explicit_scenarios, errors, warnings


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
    inducing_commit = _first_string(record, ["inducing_commit", "bug_introducing_commit", "bic", "inducing_commit_hash"])
    if inducing_commit is None:
        errors.append(f"{location}: prediction lacks inducing_commit.")
        return None
    rank = record.get("rank")
    if rank is not None and not isinstance(rank, int):
        errors.append(f"{location}: rank must be an integer when present.")
        return None
    confidence = record.get("confidence")
    if confidence is not None and not isinstance(confidence, (int, float)):
        errors.append(f"{location}: confidence must be a number when present.")
        return None
    return Prediction(
        scenario_id=scenario_id,
        fix_commit=_first_string(record, ["fix_commit", "bug_fixing_commit", "fix_commit_hash"]),
        inducing_commit=inducing_commit,
        rank=rank,
        confidence=float(confidence) if confidence is not None else None,
        tool=_first_string(record, ["tool"]),
        raw_file=_first_string(record, ["raw_file"]),
    )


def _first_string(record: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


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
    expected, allowed, notes = _expected_classic_commit_ids(scenario)
    return CommitLevelPolicy(
        evaluation_policy="exact_set",
        evaluation_variant=None,
        required=expected,
        acceptable_related=[AcceptableRelated(commit=commit) for commit in allowed],
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
    if not required:
        required = _graph_direct_bic_ids(scenario)

    return CommitLevelPolicy(
        evaluation_policy=policy_name,
        evaluation_variant=selected_variant["name"] if selected_variant is not None else None,
        required=required,
        acceptable_related=_acceptable_related_entries(selected_commit_level.get("acceptable_related")),
        related_origins=_string_list(selected_commit_level.get("related_origins")),
        related_but_not_correct=_string_list(selected_commit_level.get("related_but_not_correct")),
        relevant=_string_list(selected_commit_level.get("relevant")),
        minimum_required=_minimum_required_value(selected_commit_level.get("minimum_required"), notes),
        k_values=_k_values(selected_commit_level.get("k_values")),
        notes=notes,
    )


_SUPPORTED_GRAPH_POLICIES = {
    "exact_set",
    "direct_only",
    "reintroduction_direct",
    "partial_credit",
    "top_k",
    "relaxed_with_related",
    "relaxed_with_credit",
}


def _selected_evaluation_variant(
    expected_szz: dict[str, Any],
    requested_variant: str | None,
    notes: list[str],
) -> dict[str, Any] | None:
    variants = expected_szz.get("evaluation_variants")
    if not isinstance(variants, list):
        if requested_variant:
            notes.append(f"Requested evaluation variant '{requested_variant}' is not defined; using commit_level.")
        return None
    default_variant = expected_szz.get("default_variant")
    selected_name = requested_variant if requested_variant is not None else default_variant
    if not isinstance(selected_name, str) or not selected_name:
        return None
    for item in variants:
        if isinstance(item, dict) and item.get("name") == selected_name:
            return item
    selected_key = _evaluation_variant_key(selected_name)
    for item in variants:
        if isinstance(item, dict) and _evaluation_variant_key(item.get("name")) == selected_key:
            return item
    notes.append(f"Requested evaluation variant '{selected_name}' is not defined; using commit_level.")
    return None


def _evaluation_variant_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.lower().replace("_", "-")


def _graph_direct_bic_ids(scenario: dict[str, Any]) -> list[str]:
    expected: set[str] = set()
    for bug in scenario.get("bugs", []) or []:
        if not isinstance(bug, dict):
            continue
        for entry in graph_bic_entries(bug):
            commit = entry.get("commit")
            role = entry.get("role")
            if isinstance(commit, str) and role in {None, "direct", "reintroducing", "contributing"}:
                expected.add(commit)
    return sorted(expected)


def _acceptable_related_entries(value: Any) -> list[AcceptableRelated]:
    entries: list[AcceptableRelated] = []
    for item in value or []:
        if isinstance(item, str):
            entries.append(AcceptableRelated(commit=item))
        elif isinstance(item, dict) and isinstance(item.get("commit"), str):
            credit = item.get("credit", 0.0)
            reason = item.get("reason")
            entries.append(
                AcceptableRelated(
                    commit=item["commit"],
                    reason=reason if isinstance(reason, str) else None,
                    credit=float(credit) if isinstance(credit, (int, float)) else 0.0,
                )
            )
    return entries


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _minimum_required_value(value: Any, notes: list[str]) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and value >= 0:
        return value
    notes.append("minimum_required must be a non-negative integer; ignoring it.")
    return None


def _k_values(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return sorted({item for item in value if isinstance(item, int) and item > 0})


def _ranked_actual_ids(
    predictions: list[Prediction],
    commit_map: dict[str, Any],
    hash_to_id: dict[str, str],
) -> tuple[list[str], list[str]]:
    indexed_predictions = list(enumerate(predictions))
    if any(prediction.rank is not None for prediction in predictions):
        indexed_predictions.sort(
            key=lambda item: (
                item[1].rank is None,
                item[1].rank if item[1].rank is not None else item[0],
                item[0],
            )
        )
    ranked_actual_ids: list[str] = []
    seen: set[str] = set()
    unknown_predictions: list[str] = []
    for _, prediction in indexed_predictions:
        normalized = _normalize_commit_ref(prediction.inducing_commit, commit_map, hash_to_id)
        if normalized is None:
            unknown_predictions.append(prediction.inducing_commit)
            continue
        if normalized not in seen:
            ranked_actual_ids.append(normalized)
            seen.add(normalized)
    return ranked_actual_ids, unknown_predictions


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


def _top_k_metrics(policy: CommitLevelPolicy, ranked_actual_ids: list[str]) -> dict[str, Any] | None:
    if policy.evaluation_policy != "top_k" and not policy.k_values:
        return None
    relevant = set(policy.relevant or policy.required)
    k_values = policy.k_values or [1, 3, 5]
    best_rank = None
    for index, commit in enumerate(ranked_actual_ids, start=1):
        if commit in relevant:
            best_rank = index
            break
    return {
        "k_values": k_values,
        "relevant": sorted(relevant),
        "ranked_actual_bics": ranked_actual_ids,
        "best_rank": best_rank,
        "hit_at": {str(k): best_rank is not None and best_rank <= k for k in k_values},
        "mrr": (1.0 / best_rank) if best_rank is not None else 0.0,
    }


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
) -> str:
    if unknown_predictions:
        return "FAIL"
    if policy.evaluation_policy == "top_k":
        return "PASS" if top_k is not None and top_k["best_rank"] is not None else "FAIL"
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


def _expected_classic_commit_ids(scenario: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    expected: set[str] = set()
    allowed: set[str] = set()
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
    return sorted(expected), sorted(allowed), notes


def _hash_to_logical_id(commit_map: dict[str, Any]) -> dict[str, str]:
    lookup = {}
    for logical_id, entry in commit_map.items():
        if isinstance(logical_id, str) and isinstance(entry, dict) and isinstance(entry.get("hash"), str):
            lookup[entry["hash"]] = logical_id
    return lookup


def _normalize_commit_ref(ref: str, commit_map: dict[str, Any], hash_to_id: dict[str, str]) -> str | None:
    if ref in commit_map:
        return ref
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


def _join_ids(values: list[str]) -> str:
    if not values:
        return "-"
    return ", ".join(values)
