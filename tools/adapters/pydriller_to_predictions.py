#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import json
import sys
import time
import traceback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run PyDriller SZZ on generated SZZBench repositories and emit SZZBench predictions JSONL."
    )
    parser.add_argument("--pydriller-path", help="Path to a PyDriller source checkout. If omitted, imports installed PyDriller.")
    parser.add_argument("--generated-root", default="generated-input-repos", help="Root containing generated SZZBench repositories.")
    parser.add_argument("--scenarios-root", default="scenarios", help="Root directory for classic scenarios.")
    parser.add_argument("--advanced-scenarios-root", default="advanced-scenarios", help="Root directory for graph scenarios.")
    parser.add_argument("--variant", default="default", help="Generated repository variant name under each scenario.")
    parser.add_argument("--out", help="Output predictions JSONL path. Defaults to stdout.")
    parser.add_argument("--raw-dir", help="Directory for per-scenario raw PyDriller results.")
    parser.add_argument("--results-json", help="Path for combined raw run results JSON.")
    parser.add_argument("--manifest-json", help="Path for run manifest JSON.")
    parser.add_argument("--tool", default="pydriller", help="Tool label to include in each prediction.")
    parser.add_argument(
        "--include-empty-records",
        action="store_true",
        help="Kept for compatibility: every scenario the adapter ran on now gets a record, an empty one when "
             "PyDriller found nothing, because SZZBench fails a scenario without a record (issue #95).",
    )
    args = parser.parse_args(argv)

    if args.pydriller_path:
        sys.path.insert(0, str(Path(args.pydriller_path).expanduser().resolve()))

    try:
        from pydriller import Git  # type: ignore
    except Exception as exc:
        print(f"[ERROR] Cannot import PyDriller: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("[ERROR] Install PyDriller dependencies or pass --pydriller-path to a source checkout.", file=sys.stderr)
        return 1

    generated_root = Path(args.generated_root)
    scenarios_root = Path(args.scenarios_root)
    advanced_scenarios_root = Path(args.advanced_scenarios_root)
    output_paths = _resolve_output_paths(args)
    if output_paths.raw_dir is not None:
        output_paths.raw_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for scenario_id in _generated_scenario_ids(generated_root, args.variant):
        suite, scenario_path = _find_scenario_path(scenario_id, scenarios_root, advanced_scenarios_root)
        result = _run_scenario(
            Git,
            scenario_id,
            suite,
            scenario_path,
            generated_root,
            args.variant,
            output_paths.raw_dir,
            args.tool,
        )
        results.append(result)

    # One record per scenario the adapter ran on: an empty one is PyDriller's answer
    # "nothing", and a failure is written into the record so that SZZBench scores
    # it as a tool error instead of an abstention (issue #95).
    records = []
    for result in results:
        record: dict[str, Any] = {"scenario_id": result["scenario_id"], "predictions": result.get("predictions") or []}
        if result.get("errors"):
            record["status"] = "error"
            record["errors"] = list(result["errors"])
        records.append(record)

    output = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    if output_paths.predictions is None:
        sys.stdout.write(output)
    else:
        output_paths.predictions.parent.mkdir(parents=True, exist_ok=True)
        output_paths.predictions.write_text(output, encoding="utf-8")

    summary = {
        "tool": args.tool,
        "pydriller_path": str(Path(args.pydriller_path).expanduser().resolve()) if args.pydriller_path else None,
        "target": "generated repositories",
        "variant": args.variant,
        "scenario_count": len(results),
        "ok_count": sum(1 for item in results if item["status"] == "OK"),
        "error_count": sum(1 for item in results if item["status"] != "OK"),
        "prediction_count": sum(len(item.get("predictions") or []) for item in results),
        "prediction_record_count": len(records),
        "predictions_jsonl": str(output_paths.predictions) if output_paths.predictions is not None else None,
        "raw_dir": str(output_paths.raw_dir) if output_paths.raw_dir is not None else None,
        "results_json": str(output_paths.results_json) if output_paths.results_json is not None else None,
        "manifest_json": str(output_paths.manifest_json) if output_paths.manifest_json is not None else None,
    }
    if output_paths.results_json is not None:
        output_paths.results_json.parent.mkdir(parents=True, exist_ok=True)
        output_paths.results_json.write_text(
            json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if output_paths.manifest_json is not None:
        output_paths.manifest_json.parent.mkdir(parents=True, exist_ok=True)
        output_paths.manifest_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for result in results:
        if result["status"] != "OK":
            for error in result["errors"]:
                print(f"[ERROR] {result['scenario_id']}: {error}", file=sys.stderr)
    print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)
    return 1 if summary["error_count"] else 0


class OutputPaths:
    def __init__(
        self,
        *,
        predictions: Path | None,
        raw_dir: Path | None,
        results_json: Path | None,
        manifest_json: Path | None,
    ) -> None:
        self.predictions = predictions
        self.raw_dir = raw_dir
        self.results_json = results_json
        self.manifest_json = manifest_json


def _resolve_output_paths(args: argparse.Namespace) -> OutputPaths:
    predictions = Path(args.out) if args.out else None
    base_dir = predictions.parent if predictions is not None else None
    raw_dir = Path(args.raw_dir) if args.raw_dir else (base_dir / "raw" if base_dir is not None else None)
    results_json = Path(args.results_json) if args.results_json else (
        base_dir / "pydriller-run-results.json" if base_dir is not None else None
    )
    manifest_json = Path(args.manifest_json) if args.manifest_json else (
        base_dir / "pydriller-run-manifest.json" if base_dir is not None else None
    )
    return OutputPaths(predictions=predictions, raw_dir=raw_dir, results_json=results_json, manifest_json=manifest_json)


def _generated_scenario_ids(generated_root: Path, variant: str) -> list[str]:
    scenario_ids = []
    for repo_dir in generated_root.glob(f"*/{variant}/repo"):
        if repo_dir.is_dir() and (repo_dir / ".git").exists():
            scenario_ids.append(repo_dir.parent.parent.name)
    return sorted(set(scenario_ids))


def _find_scenario_path(scenario_id: str, scenarios_root: Path, advanced_scenarios_root: Path) -> tuple[str | None, Path | None]:
    classic = scenarios_root / scenario_id / "scenario.yml"
    if classic.exists():
        return "scenarios", classic
    graph = advanced_scenarios_root / scenario_id / "scenario.graph.yml"
    if graph.exists():
        return "advanced-scenarios", graph
    return None, None


def _run_scenario(
    git_class: Any,
    scenario_id: str,
    suite: str | None,
    scenario_path: Path | None,
    generated_root: Path,
    variant: str,
    raw_dir: Path | None,
    tool: str,
) -> dict[str, Any]:
    started = time.time()
    generated_dir = generated_root / scenario_id / variant
    repo_dir = generated_dir / "repo"
    commit_map_path = generated_dir / "metadata" / "commit-map.json"
    raw_path = raw_dir / f"{scenario_id}.json" if raw_dir is not None else None
    result: dict[str, Any] = {
        "scenario_id": scenario_id,
        "suite": suite,
        "scenario_path": str(scenario_path) if scenario_path is not None else None,
        "repo_path": str(repo_dir),
        "raw_result_path": str(raw_path) if raw_path is not None else None,
        "status": "UNKNOWN",
        "fix_commits": [],
        "predictions": [],
        "errors": [],
        "elapsed_seconds": None,
    }
    try:
        if scenario_path is None or suite is None:
            raise AdapterError(f"Cannot find scenario file for {scenario_id}.")
        scenario = _load_yaml(scenario_path)
        commit_map = _load_json(commit_map_path)
        fix_commits = _bug_fixing_commits(scenario, suite)
        result["fix_commits"] = fix_commits
        git = git_class(str(repo_dir))
        for fix_id in fix_commits:
            entry = commit_map.get(fix_id)
            if not isinstance(entry, dict) or not isinstance(entry.get("hash"), str):
                result["errors"].append(f"Unknown fix logical commit: {fix_id}")
                continue
            fix_hash = entry["hash"]
            try:
                commit = git.get_commit(fix_hash)
                blamed = git.get_commits_last_modified_lines(commit)
            except Exception as exc:
                result["errors"].append(f"{fix_id}/{fix_hash}: {type(exc).__name__}: {exc}")
                continue
            for file_path, inducing_hashes in sorted(blamed.items()):
                for inducing_hash in sorted(inducing_hashes):
                    prediction = {
                        "scenario_id": scenario_id,
                        "fix_commit": fix_hash,
                        "fix_commit_id": fix_id,
                        "inducing_commit": inducing_hash,
                        "file": file_path,
                        "tool": tool,
                    }
                    if raw_path is not None:
                        prediction["raw_file"] = str(raw_path)
                    result["predictions"].append(prediction)
        result["status"] = "ERROR" if result["errors"] else "OK"
    except Exception as exc:
        result["status"] = "ERROR"
        result["errors"].append(f"{type(exc).__name__}: {exc}")
        result["traceback"] = traceback.format_exc()
    finally:
        result["elapsed_seconds"] = round(time.time() - started, 6)
        if raw_path is not None:
            raw_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


class AdapterError(Exception):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except Exception as exc:
        raise AdapterError(f"Cannot import PyYAML: {type(exc).__name__}: {exc}") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AdapterError(f"{path} must contain a YAML object.")
    return data


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AdapterError(f"{path} must contain a JSON object.")
    return data


def _bug_fixing_commits(scenario: dict[str, Any], suite: str) -> list[str]:
    commits = []
    for bug in scenario.get("bugs") or []:
        if not isinstance(bug, dict):
            continue
        if suite == "advanced-scenarios":
            for entry in bug.get("bug_fixing_commits") or []:
                if isinstance(entry, str):
                    commits.append(entry)
                elif isinstance(entry, dict) and isinstance(entry.get("commit"), str):
                    commits.append(entry["commit"])
        if isinstance(bug.get("bug_fixing_commit"), str):
            commits.append(bug["bug_fixing_commit"])
    return _unique(commits)


def _unique(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


if __name__ == "__main__":
    raise SystemExit(main())
