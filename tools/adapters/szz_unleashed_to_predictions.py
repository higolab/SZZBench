#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import json
import sys


DEFAULT_RESULT_GLOB = "*/default/szz-unleashed/run-depth1/results/fix_and_introducers_pairs.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert SZZ Unleashed fix_and_introducers_pairs.json files to SZZBench predictions JSONL."
    )
    parser.add_argument(
        "--generated-root",
        default="generated-input-repos",
        help="Root containing generated SZZBench repositories.",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_RESULT_GLOB,
        help="Glob under --generated-root for SZZ Unleashed result files.",
    )
    parser.add_argument("--out", help="Output JSONL path. Defaults to stdout.")
    parser.add_argument("--tool", default="szz-unleashed", help="Tool label to include in each prediction.")
    args = parser.parse_args(argv)

    generated_root = Path(args.generated_root)
    records = []
    errors = []
    for result_path in sorted(generated_root.glob(args.glob)):
        scenario_id = _scenario_id_from_path(generated_root, result_path)
        if scenario_id is None:
            errors.append(f"Cannot infer scenario id from {result_path}")
            continue
        # A result that cannot be used is written as a failed record, so that
        # SZZBench scores a tool error rather than a missing or empty answer (#95).
        try:
            pairs = json.loads(result_path.read_text(encoding="utf-8"))
        except OSError as exc:
            errors.append(f"Cannot read {result_path}: {exc}")
            records.append(_failed_record(scenario_id, errors[-1]))
            continue
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in {result_path}: {exc}")
            records.append(_failed_record(scenario_id, errors[-1]))
            continue
        predictions, conversion_errors = _convert_pairs(pairs, scenario_id, result_path, generated_root, args.tool)
        errors.extend(conversion_errors)
        record: dict[str, Any] = {"scenario_id": scenario_id, "predictions": predictions}
        repository = _repository_id(generated_root / scenario_id / "default" / "metadata")
        if repository:
            # the generation the predictions were made on, checked by szzbench evaluate (issue #93)
            record["repository_id"] = repository
        if conversion_errors:
            record["status"] = "error"
            record["errors"] = conversion_errors
        records.append(record)

    output = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    for error in errors:
        print(f"[ERROR] {error}", file=sys.stderr)
    return 1 if errors else 0


def _repository_id(metadata_dir: Path) -> str | None:
    """The repository id the generation recorded (issue #93), None for an output without a manifest."""
    try:
        value = json.loads((metadata_dir / "manifest.json").read_text(encoding="utf-8")).get("repository_id")
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) and value else None


def _failed_record(scenario_id: str, error: str) -> dict[str, Any]:
    return {"scenario_id": scenario_id, "status": "error", "errors": [error], "predictions": []}


def _scenario_id_from_path(generated_root: Path, result_path: Path) -> str | None:
    try:
        return result_path.relative_to(generated_root).parts[0]
    except (ValueError, IndexError):
        return None


def _convert_pairs(
    pairs: Any,
    scenario_id: str,
    result_path: Path,
    generated_root: Path,
    tool: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(pairs, list):
        return [], [f"{result_path}: expected a JSON array."]
    predictions = []
    errors = []
    raw_file = _display_path(result_path, generated_root)
    for index, item in enumerate(pairs):
        if isinstance(item, list) and len(item) >= 2 and isinstance(item[0], str) and isinstance(item[1], str):
            predictions.append(
                {
                    "fix_commit": item[0],
                    "inducing_commit": item[1],
                    "tool": tool,
                    "raw_file": raw_file,
                }
            )
            continue
        if isinstance(item, dict):
            fix_commit = _first_string(item, ["fix_commit", "fix_commit_hash", "bug_fixing_commit"])
            inducing_commit = _first_string(
                item,
                ["inducing_commit", "inducing_commit_hash", "bug_introducing_commit", "bic"],
            )
            if inducing_commit is not None:
                prediction = {
                    "inducing_commit": inducing_commit,
                    "tool": tool,
                    "raw_file": raw_file,
                }
                if fix_commit is not None:
                    prediction["fix_commit"] = fix_commit
                predictions.append(prediction)
                continue
        errors.append(f"{result_path}: cannot convert pair at index {index} for {scenario_id}.")
    return predictions, errors


def _first_string(record: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
