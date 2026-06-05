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
                "| Scenario | Status | Suite | Category | Expected BICs | Actual BICs | TP | FP | FN | Allowed FP | Predictions |",
                "|---|---:|---|---|---|---|---|---|---|---|---:|",
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
    predictions_path: Path,
    *,
    generated_root: Path,
    scenarios_root: Path,
    advanced_scenarios_root: Path,
    variant: str = "default",
) -> EvaluationReport:
    predictions_by_scenario, explicit_scenarios, errors, warnings = load_predictions(predictions_path)
    scenario_ids = sorted(explicit_scenarios or predictions_by_scenario.keys())
    evaluations: list[ScenarioEvaluation] = []
    for scenario_id in scenario_ids:
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
            )
        )
    return EvaluationReport(evaluations, errors=errors, warnings=warnings)


def evaluate_scenario(
    scenario_id: str,
    scenario: dict[str, Any],
    scenario_path: Path,
    suite: str,
    commit_map: dict[str, Any],
    predictions: list[Prediction],
) -> ScenarioEvaluation:
    expected_ids, allowed_ids, notes = _expected_commit_ids(scenario, suite)
    hash_to_id = _hash_to_logical_id(commit_map)
    actual_ids: set[str] = set()
    unknown_predictions: list[str] = []
    for prediction in predictions:
        normalized = _normalize_commit_ref(prediction.inducing_commit, commit_map, hash_to_id)
        if normalized is None:
            unknown_predictions.append(prediction.inducing_commit)
            continue
        actual_ids.add(normalized)

    expected = set(expected_ids)
    allowed = set(allowed_ids)
    actual = set(actual_ids)
    true_positives = sorted(actual & expected)
    false_positives = sorted(actual - expected - allowed)
    false_negatives = sorted(expected - actual)
    allowed_false_positives = sorted(actual & allowed)
    status = "PASS" if not false_positives and not false_negatives and not unknown_predictions else "FAIL"
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
        unknown_predictions=sorted(set(unknown_predictions)),
        precision=precision,
        recall=recall,
        scenario_path=str(scenario_path),
        result_notes=notes,
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


def _expected_commit_ids(scenario: dict[str, Any], suite: str) -> tuple[list[str], list[str], list[str]]:
    if suite == "advanced-scenarios":
        return _expected_graph_commit_ids(scenario)
    return _expected_classic_commit_ids(scenario)


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


def _expected_graph_commit_ids(scenario: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    expected: set[str] = set()
    allowed: set[str] = set()
    notes: list[str] = []
    commit_level = (scenario.get("expected_szz") or {}).get("commit_level") or {}
    required = commit_level.get("required")
    if isinstance(required, list):
        expected.update(item for item in required if isinstance(item, str))
    else:
        for bug in scenario.get("bugs", []) or []:
            if not isinstance(bug, dict):
                continue
            for entry in graph_bic_entries(bug):
                commit = entry.get("commit")
                role = entry.get("role")
                if isinstance(commit, str) and role in {None, "direct", "reintroducing", "contributing"}:
                    expected.add(commit)
    for item in commit_level.get("acceptable_related") or []:
        if isinstance(item, str):
            allowed.add(item)
        elif isinstance(item, dict) and isinstance(item.get("commit"), str):
            allowed.add(item["commit"])
    policy = commit_level.get("evaluation_policy")
    if isinstance(policy, str) and policy not in {"exact_set", "direct_only"}:
        notes.append(f"Unsupported evaluation_policy '{policy}' treated as exact_set.")
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


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _join_ids(values: list[str]) -> str:
    if not values:
        return "-"
    return ", ".join(values)
