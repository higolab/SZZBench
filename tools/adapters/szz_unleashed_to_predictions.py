#!/usr/bin/env python3
"""Run SZZ Unleashed over SZZBench's generated repositories, and convert its results to predictions.

With --jar, the script runs SZZ Unleashed's bug-introducer finder on every
generated repository first (examples/szz-unleashed-run/README.md says how to
build the jar), then converts what it wrote.  Without --jar it only converts
`fix_and_introducers_pairs.json` files that a run left under --generated-root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import argparse
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

import yaml


#: SZZ Unleashed's `-d`, the depth of its line mapping graph, when --depth is not given: its own
#: default.  Depth 1 answers much as blaming the deleted lines does; examples/szz-unleashed-run/
#: records both.
DEFAULT_DEPTH = 3
RESULT_FILE = "results/fix_and_introducers_pairs.json"
DEFAULT_RESULT_GLOB = f"*/default/szz-unleashed/run-depth{DEFAULT_DEPTH}/{RESULT_FILE}"

#: A Java stack trace in SZZ Unleashed's output: it prints an exception and carries on, so the
#: run exits 0 with an answer that the exception may have cut short.
STACK_TRACE = re.compile(r"^(Exception in thread \S+ )?(?P<exception>[\w$.]+(Exception|Error))(: .*)?$", re.M)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run SZZ Unleashed on generated SZZBench repositories (with --jar), and convert "
                    "fix_and_introducers_pairs.json files to SZZBench predictions JSONL."
    )
    parser.add_argument(
        "--generated-root",
        default="generated-input-repos",
        help="Root containing generated SZZBench repositories.",
    )
    parser.add_argument("--variant", default="default", help="Generated repository variant name under each scenario.")
    parser.add_argument(
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"SZZ Unleashed's -d, the depth of its line mapping graph (default {DEFAULT_DEPTH}); it names the "
             "run directory, szz-unleashed/run-depth<depth>.",
    )
    parser.add_argument("--jar", help="SZZ Unleashed's szz_find_bug_introducers jar: run it on every generated "
                                      "repository first.")
    parser.add_argument("--java", default="java", help="The java executable that runs --jar.")
    parser.add_argument(
        "--glob",
        help="Glob under --generated-root for SZZ Unleashed result files to convert "
             f"(default: */<variant>/szz-unleashed/run-depth<depth>/{RESULT_FILE}). Not used with --jar.",
    )
    parser.add_argument("--out", help="Output JSONL path. Defaults to stdout.")
    parser.add_argument("--tool", default="szz-unleashed", help="Tool label to include in each prediction.")
    args = parser.parse_args(argv)

    generated_root = Path(args.generated_root)
    run_dir_name = f"szz-unleashed/run-depth{args.depth}"
    errors: list[str] = []
    records: list[dict[str, Any]] = []

    if args.jar:
        summary = run_szz_unleashed(generated_root, args.variant, args.depth, Path(args.jar), args.java)
        for scenario_id, run_errors in summary["runs"].items():
            output_dir = generated_root / scenario_id / args.variant
            if run_errors:
                errors.extend(f"{scenario_id}: {error}" for error in run_errors)
                record = _failed_record(scenario_id, run_errors[0])
                record["errors"] = list(run_errors)
                records.append(_add_repository_id(record, output_dir / "metadata"))
                continue
            record, record_errors = _convert_result(output_dir / run_dir_name / RESULT_FILE, scenario_id,
                                                    generated_root, output_dir, args.tool)
            errors.extend(record_errors)
            records.append(record)
        if args.out:
            summary_path = Path(args.out).with_name("szz-unleashed-run.json")
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        pattern = args.glob or f"*/{args.variant}/{run_dir_name}/{RESULT_FILE}"
        for result_path in sorted(generated_root.glob(pattern)):
            scenario_id = _scenario_id_from_path(generated_root, result_path)
            if scenario_id is None:
                errors.append(f"Cannot infer scenario id from {result_path}")
                continue
            record, record_errors = _convert_result(result_path, scenario_id, generated_root,
                                                    generated_root / scenario_id / args.variant, args.tool)
            errors.extend(record_errors)
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


def _convert_result(result_path: Path, scenario_id: str, generated_root: Path, output_dir: Path,
                    tool: str) -> tuple[dict[str, Any], list[str]]:
    """One scenario's record from its result file."""
    # A result that cannot be used is written as a failed record, so that
    # SZZBench scores a tool error rather than a missing or empty answer (#95).
    try:
        pairs = json.loads(result_path.read_text(encoding="utf-8"))
    except OSError as exc:
        error = f"Cannot read {result_path}: {exc}"
        return _add_repository_id(_failed_record(scenario_id, error), output_dir / "metadata"), [error]
    except json.JSONDecodeError as exc:
        error = f"Invalid JSON in {result_path}: {exc}"
        return _add_repository_id(_failed_record(scenario_id, error), output_dir / "metadata"), [error]
    predictions, conversion_errors = _convert_pairs(pairs, scenario_id, result_path, generated_root, tool)
    _add_logical_ids(predictions, output_dir / "metadata" / "commit-map.json")
    record: dict[str, Any] = {"scenario_id": scenario_id, "predictions": predictions}
    _add_repository_id(record, output_dir / "metadata")
    if conversion_errors:
        record["status"] = "error"
        record["errors"] = conversion_errors
    return record, conversion_errors


def _add_repository_id(record: dict[str, Any], metadata_dir: Path) -> dict[str, Any]:
    repository = _repository_id(metadata_dir)
    if repository:
        # the generation the predictions were made on, checked by szzbench evaluate (issue #93)
        record["repository_id"] = repository
    return record


def _add_logical_ids(predictions: list[dict[str, Any]], commit_map_path: Path) -> None:
    """Name each commit's logical id next to its hash, as the other adapters do."""
    try:
        commit_map = read_commit_map(commit_map_path)
    except IncompleteOutput:
        return
    logical = {entry["hash"]: logical_id for logical_id, entry in commit_map.items()
               if isinstance(entry, dict) and isinstance(entry.get("hash"), str)}
    for prediction in predictions:
        for key in ("fix_commit", "inducing_commit"):
            if prediction.get(key) in logical:
                prediction[f"{key}_id"] = logical[prediction[key]]


# --- running SZZ Unleashed ---------------------------------------------------------------------

def run_szz_unleashed(generated_root: Path, variant: str, depth: int, jar: Path, java: str) -> dict[str, Any]:
    """Run the jar on every generated repository; return the run summary with per-scenario errors.

    Each run gets an issue list with one entry per bug-fixing commit.  SZZ
    Unleashed keeps a candidate as bug-introducing when it was committed
    before the issue was reported, and the scenarios record no report date,
    so each entry's dates are its fix's committer date: every candidate,
    being older than the fix, passes.
    """
    home = tempfile.mkdtemp(prefix="szz-unleashed-home-")
    atexit.register(shutil.rmtree, home, True)
    environment = isolated_environment(dict(os.environ), home)
    started = time.time()
    runs: dict[str, list[str]] = {}
    for repo in sorted(generated_root.glob(f"*/{variant}/repo")):
        scenario_id = repo.parent.parent.name
        metadata = repo.parent / "metadata"
        try:
            runs[scenario_id] = _run_one(repo, metadata, repo.parent / f"szz-unleashed/run-depth{depth}",
                                         scenario_id, depth, jar, java, home, environment)
        except IncompleteOutput as exc:
            # an incomplete generated output is a tool error, not a scenario to leave out, nor one that
            # stops the run (issue #95)
            runs[scenario_id] = [str(exc)]
        except (OSError, ValueError, subprocess.CalledProcessError) as exc:
            # a scenario the run could not be set up for is a tool error, not an answer (issue #95)
            runs[scenario_id] = [f"{type(exc).__name__}: {exc}"]
    return {
        "tool": "szz-unleashed",
        "jar": str(jar),
        "jar_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(),
        "java": _java_version(java, environment),
        "depth": depth,
        "variant": variant,
        "elapsed_seconds": round(time.time() - started, 1),
        "scenario_count": len(runs),
        "error_count": sum(1 for errors in runs.values() if errors),
        "runs": runs,
    }


def _run_one(repo: Path, metadata: Path, run_dir: Path, scenario_id: str, depth: int, jar: Path, java: str,
             home: str, environment: dict[str, str]) -> list[str]:
    commit_map = read_commit_map(metadata / "commit-map.json")
    fixes = fix_commits(metadata, commit_map)
    if not fixes:
        return ["No bug fixing commits found."]
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    issues = {}
    for logical_id, fix_hash in fixes:
        date = subprocess.run(["git", "log", "-1", "--format=%ci", fix_hash], cwd=repo, env=environment,
                              capture_output=True, text=True, check=True).stdout.strip()
        issues[f"{scenario_id} {logical_id}"] = {"hash": fix_hash, "creationdate": date, "resolutiondate": date,
                                                 "commitdate": date}
    (run_dir / "issue_list.json").write_text(json.dumps(issues, indent=2) + "\n", encoding="utf-8")
    command = [java, f"-Duser.home={home}", "-jar", str(jar.resolve()), "-i", "issue_list.json",
               "-r", str(repo.resolve()), "-d", str(depth)]
    completed = subprocess.run(command, cwd=run_dir, env=environment, capture_output=True, text=True)
    output = completed.stdout + completed.stderr
    (run_dir / "run.log").write_text(output, encoding="utf-8")
    errors = []
    if completed.returncode != 0:
        errors.append(f"SZZ Unleashed exited with status {completed.returncode}")
    trace = STACK_TRACE.search(output)
    if trace and "\tat " in output:
        errors.append(f"SZZ Unleashed printed a stack trace and carried on: {trace.group('exception')}")
    if not (run_dir / RESULT_FILE).exists():
        errors.append(f"SZZ Unleashed wrote no {RESULT_FILE}")
    return errors


class IncompleteOutput(ValueError):
    """A generated output's metadata file that is missing, unreadable, or not what it should hold."""


def read_commit_map(path: Path) -> dict[str, Any]:
    """A generated output's commit map. IncompleteOutput says what is wrong with one that cannot be used."""
    try:
        commit_map = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        problem = "is missing" if not path.exists() else f"cannot be read ({type(exc).__name__}: {exc})"
        raise IncompleteOutput(f"{path} {problem}: the generated output is incomplete") from exc
    if not isinstance(commit_map, dict):
        kind = {list: "an array", str: "a string", bool: "a boolean", int: "a number", float: "a number"}.get(
            type(commit_map), "null")
        raise IncompleteOutput(f"{path} holds {kind}, not a JSON object: the generated output is incomplete")
    return commit_map


def fix_commits(metadata: Path, commit_map: dict[str, Any]) -> list[tuple[str, str]]:
    """The (logical id, hash) of every bug-fixing commit the scenario declares, in declaration order."""
    scenario = None
    for name in ("scenario.yml", "scenario.graph.yml"):
        if (metadata / name).exists():
            try:
                scenario = yaml.safe_load((metadata / name).read_text(encoding="utf-8"))
            except (OSError, ValueError, yaml.YAMLError) as exc:
                problem = " ".join(str(exc).split())
                raise IncompleteOutput(f"{metadata / name} cannot be read ({type(exc).__name__}: {problem}): "
                                       "the generated output is incomplete") from exc
            break
    logical_ids: list[str] = []
    if isinstance(scenario, dict):
        for bug in scenario.get("bugs", []) or []:
            if not isinstance(bug, dict):
                continue
            if isinstance(bug.get("bug_fixing_commit"), str):
                logical_ids.append(bug["bug_fixing_commit"])
            for item in bug.get("bug_fixing_commits") or []:
                if isinstance(item, dict) and isinstance(item.get("commit"), str):
                    logical_ids.append(item["commit"])
                elif isinstance(item, str):
                    logical_ids.append(item)
    if not logical_ids:
        logical_ids = [logical_id for logical_id, entry in commit_map.items()
                       if isinstance(entry, dict) and entry.get("role") == "bug_fixing"]
    fixes = []
    for logical_id in dict.fromkeys(logical_ids):
        entry = commit_map.get(logical_id)
        if isinstance(entry, dict) and isinstance(entry.get("hash"), str):
            fixes.append((logical_id, entry["hash"]))
    return fixes


def isolated_environment(environ: dict[str, str], home: str) -> dict[str, str]:
    """SZZBench's Git isolation (issue #96) for SZZ Unleashed's JGit and for git.

    JGit reads the configuration under Java's user.home, which the command sets
    to the same empty directory; git reads HOME and XDG_CONFIG_HOME.  Every
    `GIT_*` variable but `GIT_EXEC_PATH` is withheld.
    """
    isolated = {key: value for key, value in environ.items()
                if not key.startswith("GIT_") or key == "GIT_EXEC_PATH"}
    isolated.update({"HOME": home, "XDG_CONFIG_HOME": home,
                     "GIT_CONFIG_NOSYSTEM": "1", "GIT_ATTR_NOSYSTEM": "1"})
    return isolated


def _java_version(java: str, environment: dict[str, str]) -> str | None:
    try:
        completed = subprocess.run([java, "-version"], env=environment, capture_output=True, text=True)
    except OSError:
        return None
    lines = (completed.stderr or completed.stdout).strip().splitlines()
    return lines[0] if lines else None


# --- converting results ------------------------------------------------------------------------

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
    seen = set()
    raw_file = _display_path(result_path, generated_root)
    for index, item in enumerate(pairs):
        if isinstance(item, list) and len(item) >= 2 and isinstance(item[0], str) and isinstance(item[1], str):
            fix_commit, inducing_commit = item[0], item[1]
        elif isinstance(item, dict) and _first_string(
                item, ["inducing_commit", "inducing_commit_hash", "bug_introducing_commit", "bic"]) is not None:
            fix_commit = _first_string(item, ["fix_commit", "fix_commit_hash", "bug_fixing_commit"])
            inducing_commit = _first_string(
                item,
                ["inducing_commit", "inducing_commit_hash", "bug_introducing_commit", "bic"],
            )
        else:
            errors.append(f"{result_path}: cannot convert pair at index {index} for {scenario_id}.")
            continue
        # SZZ Unleashed repeats a pair once per line that leads to it; one prediction is its answer
        if (fix_commit, inducing_commit) in seen:
            continue
        seen.add((fix_commit, inducing_commit))
        prediction = {"inducing_commit": inducing_commit, "tool": tool, "raw_file": raw_file}
        if fix_commit is not None:
            prediction = {"fix_commit": fix_commit, **prediction}
        predictions.append(prediction)
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
