#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import enum
import json
import logging as log
import shutil
import sys
import time
import traceback
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from git import Repo


TOOL_SPECS = {
    "b-szz": {"szz_name": "b", "class": "BaseSZZ", "module": "szz.b_szz"},
    "ag-szz": {"szz_name": "ag", "class": "AGSZZ", "module": "szz.ag_szz", "max_change_size": 20},
    "ma-szz": {
        "szz_name": "ma",
        "class": "MASZZ",
        "module": "szz.ma_szz",
        "max_change_size": 20,
        "detect_move_from_other_files": 1,
    },
    "l-szz": {
        "szz_name": "l",
        "class": "LSZZ",
        "module": "szz.l_szz",
        "max_change_size": 20,
        "detect_move_from_other_files": 1,
    },
    "r-szz": {
        "szz_name": "r",
        "class": "RSZZ",
        "module": "szz.r_szz",
        "max_change_size": 20,
        "detect_move_from_other_files": 1,
    },
}


class ModificationType(enum.Enum):
    ADD = 1
    COPY = 2
    DELETE = 3
    MODIFY = 4
    RENAME = 5
    UNKNOWN = 6


@dataclass
class CompatModification:
    old_path: str | None
    new_path: str | None
    change_type: ModificationType
    diff_parsed: dict[str, list[tuple[int, str]]]

    @property
    def filename(self) -> str:
        path = self.new_path or self.old_path or ""
        return Path(path).name


class CompatCommit:
    def __init__(self, repo_path: str, commit_hash: str):
        self._repo_path = repo_path
        self._repo = Repo(repo_path)
        self._commit = self._repo.commit(commit_hash)
        self.hash = self._commit.hexsha
        self.msg = self._commit.message
        self.merge = len(self._commit.parents) > 1
        self.modifications = _commit_modifications(repo_path, self.hash)


class GitRepository:
    def __init__(self, path_to_repo: str):
        self.path_to_repo = path_to_repo

    def get_commit(self, commit_hash: str) -> CompatCommit:
        return CompatCommit(self.path_to_repo, commit_hash)


class RepositoryMining:
    def __init__(
        self,
        path_to_repo: str | None = None,
        single: str | None = None,
        to_commit: str | None = None,
        order: str | None = None,
        **_: Any,
    ):
        self.path_to_repo = path_to_repo
        self.single = single
        self.to_commit = to_commit
        self.order = order

    def traverse_commits(self):
        if self.path_to_repo is None:
            return iter(())
        if self.single:
            return iter([CompatCommit(self.path_to_repo, self.single)])
        if self.to_commit:
            return iter([CompatCommit(self.path_to_repo, self.to_commit)])
        return iter(())


class LinesCount:
    def __init__(self, path_to_repo: str, from_commit: str, to_commit: str):
        self.path_to_repo = path_to_repo
        self.from_commit = from_commit
        self.to_commit = to_commit

    def count(self) -> dict[str, int]:
        modifications = _commit_modifications(self.path_to_repo, self.to_commit)
        changed = 0
        for mod in modifications:
            changed += len(mod.diff_parsed.get("deleted", []))
            changed += len(mod.diff_parsed.get("added", []))
        return {"changed": changed}


def _install_compat_modules() -> None:
    pydriller = types.ModuleType("pydriller")
    pydriller.ModificationType = ModificationType
    pydriller.GitRepository = GitRepository
    pydriller.RepositoryMining = RepositoryMining
    sys.modules["pydriller"] = pydriller

    metrics = types.ModuleType("pydriller.metrics")
    process = types.ModuleType("pydriller.metrics.process")
    lines_count = types.ModuleType("pydriller.metrics.process.lines_count")
    lines_count.LinesCount = LinesCount
    sys.modules["pydriller.metrics"] = metrics
    sys.modules["pydriller.metrics.process"] = process
    sys.modules["pydriller.metrics.process.lines_count"] = lines_count

    dateparser = types.ModuleType("dateparser")
    dateparser.parse = _parse_date
    sys.modules["dateparser"] = dateparser


def _parse_date(value: str):
    normalized = value.strip().replace("Z", "+00:00")
    if normalized.endswith(" UTC"):
        normalized = normalized[:-4] + "+00:00"
    try:
        return dt.datetime.fromisoformat(normalized)
    except ValueError:
        return dt.datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")


def _commit_modifications(repo_path: str, commit_hash: str) -> list[CompatModification]:
    repo = Repo(repo_path)
    commit = repo.commit(commit_hash)
    if not commit.parents:
        return []
    parent = commit.parents[0].hexsha
    patch = repo.git.diff("--find-renames", "--find-copies", "--unified=0", parent, commit_hash)
    return _parse_git_diff(patch)


def _parse_git_diff(patch: str) -> list[CompatModification]:
    modifications: list[CompatModification] = []
    current: dict[str, Any] | None = None
    old_line: int | None = None
    new_line: int | None = None

    def finish() -> None:
        if current is None:
            return
        old_path = current.get("old_path")
        new_path = current.get("new_path")
        change_type = current.get("change_type") or ModificationType.MODIFY
        if current.get("new_file"):
            change_type = ModificationType.ADD
        elif current.get("deleted_file"):
            change_type = ModificationType.DELETE
        elif current.get("rename"):
            change_type = ModificationType.RENAME
        elif current.get("copy"):
            change_type = ModificationType.COPY
        modifications.append(
            CompatModification(
                old_path=old_path,
                new_path=new_path,
                change_type=change_type,
                diff_parsed={
                    "deleted": current["deleted"],
                    "added": current["added"],
                },
            )
        )

    for line in patch.splitlines():
        if line.startswith("diff --git "):
            finish()
            current = {"deleted": [], "added": []}
            old_line = None
            new_line = None
            parts = line.split()
            if len(parts) >= 4:
                current["old_path"] = _strip_diff_path(parts[2])
                current["new_path"] = _strip_diff_path(parts[3])
            continue
        if current is None:
            continue
        if line.startswith("new file mode"):
            current["new_file"] = True
        elif line.startswith("deleted file mode"):
            current["deleted_file"] = True
        elif line.startswith("rename from "):
            current["rename"] = True
            current["old_path"] = line.removeprefix("rename from ")
        elif line.startswith("rename to "):
            current["rename"] = True
            current["new_path"] = line.removeprefix("rename to ")
        elif line.startswith("copy from "):
            current["copy"] = True
            current["old_path"] = line.removeprefix("copy from ")
        elif line.startswith("copy to "):
            current["copy"] = True
            current["new_path"] = line.removeprefix("copy to ")
        elif line.startswith("--- "):
            path = line[4:]
            if path != "/dev/null":
                current["old_path"] = _strip_diff_path(path)
        elif line.startswith("+++ "):
            path = line[4:]
            if path != "/dev/null":
                current["new_path"] = _strip_diff_path(path)
        elif line.startswith("@@ "):
            old_line, new_line = _parse_hunk_header(line)
        elif line.startswith("-") and not line.startswith("---"):
            if old_line is not None:
                current["deleted"].append((old_line, line[1:]))
                old_line += 1
        elif line.startswith("+") and not line.startswith("+++"):
            if new_line is not None:
                current["added"].append((new_line, line[1:]))
                new_line += 1
        else:
            if old_line is not None and new_line is not None:
                old_line += 1
                new_line += 1
    finish()
    return modifications


def _strip_diff_path(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _parse_hunk_header(line: str) -> tuple[int, int]:
    pieces = line.split()
    old_start = int(pieces[1].split(",")[0][1:])
    new_start = int(pieces[2].split(",")[0][1:])
    return old_start, new_start


@dataclass
class ScenarioInput:
    scenario_id: str
    repo_name: str
    repo_path: Path
    fix_commits: list[dict[str, str | None]]
    commit_map: dict[str, Any]
    repository_id: str | None = None


def collect_scenarios(generated_root: Path, variant: str) -> list[ScenarioInput]:
    scenarios: list[ScenarioInput] = []
    for repo_path in sorted(generated_root.glob(f"*/{variant}/repo")):
        scenario_id = repo_path.parent.parent.name
        metadata_dir = repo_path.parent / "metadata"
        commit_map_path = metadata_dir / "commit-map.json"
        if not commit_map_path.exists():
            continue
        commit_map = json.loads(commit_map_path.read_text(encoding="utf-8"))
        fix_commits = _fix_commits_from_metadata(metadata_dir, commit_map)
        scenarios.append(
            ScenarioInput(
                scenario_id=scenario_id,
                repo_name=f"{scenario_id}/{variant}/repo",
                repo_path=repo_path,
                fix_commits=fix_commits,
                commit_map=commit_map,
                repository_id=_repository_id(metadata_dir),
            )
        )
    return scenarios


def _repository_id(metadata_dir: Path) -> str | None:
    """The repository id the generation recorded (issue #93), None for an output without a manifest."""
    try:
        value = json.loads((metadata_dir / "manifest.json").read_text(encoding="utf-8")).get("repository_id")
    except (OSError, ValueError, AttributeError):
        return None
    return value if isinstance(value, str) and value else None


def _fix_commits_from_metadata(metadata_dir: Path, commit_map: dict[str, Any]) -> list[dict[str, str | None]]:
    scenario_yml = metadata_dir / "scenario.yml"
    graph_yml = metadata_dir / "scenario.graph.yml"
    scenario = None
    if scenario_yml.exists():
        scenario = yaml.safe_load(scenario_yml.read_text(encoding="utf-8"))
    elif graph_yml.exists():
        scenario = yaml.safe_load(graph_yml.read_text(encoding="utf-8"))

    logical_ids: list[tuple[str, str | None]] = []
    if isinstance(scenario, dict):
        for bug in scenario.get("bugs", []) or []:
            if not isinstance(bug, dict):
                continue
            bug_id = bug.get("id") if isinstance(bug.get("id"), str) else None
            classic_fix = bug.get("bug_fixing_commit")
            if isinstance(classic_fix, str):
                logical_ids.append((classic_fix, bug_id))
            graph_fixes = bug.get("bug_fixing_commits")
            if isinstance(graph_fixes, list):
                for item in graph_fixes:
                    if isinstance(item, dict) and isinstance(item.get("commit"), str):
                        logical_ids.append((item["commit"], bug_id))
                    elif isinstance(item, str):
                        logical_ids.append((item, bug_id))

    if not logical_ids:
        for logical_id, entry in commit_map.items():
            if isinstance(entry, dict) and entry.get("role") == "bug_fixing":
                logical_ids.append((logical_id, None))

    seen = set()
    fixes: list[dict[str, str | None]] = []
    for logical_id, bug_id in logical_ids:
        if logical_id in seen:
            continue
        seen.add(logical_id)
        entry = commit_map.get(logical_id)
        if isinstance(entry, dict) and isinstance(entry.get("hash"), str):
            fixes.append({"logical_id": logical_id, "hash": entry["hash"], "bug_id": bug_id})
    return fixes


def hash_to_logical_id(commit_map: dict[str, Any]) -> dict[str, str]:
    return {
        entry["hash"]: logical_id
        for logical_id, entry in commit_map.items()
        if isinstance(entry, dict) and isinstance(entry.get("hash"), str)
    }


def run_tool(
    tool_name: str,
    scenarios: list[ScenarioInput],
    generated_root: Path,
    output_root: Path,
    tool_root: Path,
    limit: int | None = None,
) -> dict[str, Any]:
    spec = TOOL_SPECS[tool_name]
    module = __import__(spec["module"], fromlist=[spec["class"]])
    szz_class = getattr(module, spec["class"])
    detect_line_moved = None
    if tool_name in {"ma-szz", "l-szz", "r-szz"}:
        from szz.ma_szz import DetectLineMoved

        detect_line_moved = DetectLineMoved

    out_dir = output_root / tool_name
    raw_dir = out_dir / "raw"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    selected = scenarios[:limit] if limit is not None else scenarios
    records: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    started_at = dt.datetime.now(dt.UTC).isoformat()
    start_time = time.time()

    for index, scenario in enumerate(selected, start=1):
        scenario_predictions: list[dict[str, Any]] = []
        scenario_errors: list[str] = []
        raw_entries: list[dict[str, Any]] = []
        log.info("[%s] %d/%d %s", tool_name, index, len(selected), scenario.scenario_id)
        if not scenario.fix_commits:
            scenario_errors.append("No bug fixing commits found.")
        try:
            if scenario.fix_commits:
                szz = szz_class(repo_full_name=scenario.repo_name, repo_url="unused", repos_dir=str(generated_root))
                try:
                    logical_lookup = hash_to_logical_id(scenario.commit_map)
                    for fix in scenario.fix_commits:
                        kwargs = {
                            "issue_date_filter": False,
                            "max_change_size": spec.get("max_change_size"),
                            "filter_revert_commits": False,
                        }
                        if detect_line_moved is not None and spec.get("detect_move_from_other_files"):
                            kwargs["detect_move_from_other_files"] = detect_line_moved(spec["detect_move_from_other_files"])
                        kwargs = {key: value for key, value in kwargs.items() if value is not None}
                        impacted_files = szz.get_impacted_files(
                            fix_commit_hash=fix["hash"],
                            file_ext_to_parse=None,
                            only_deleted_lines=True,
                        )
                        bics = szz.find_bic(
                            fix_commit_hash=fix["hash"],
                            impacted_files=impacted_files,
                            **kwargs,
                        )
                        for bic in sorted((item for item in bics if item is not None), key=_bic_commit_hash):
                            bic_hash = _bic_commit_hash(bic)
                            prediction = {
                                "scenario_id": scenario.scenario_id,
                                "fix_commit": fix["hash"],
                                "fix_commit_id": fix["logical_id"],
                                "inducing_commit": bic_hash,
                                "inducing_commit_id": logical_lookup.get(bic_hash),
                                "tool": tool_name,
                                "raw_file": str(raw_dir / f"{scenario.scenario_id}.json"),
                            }
                            prediction.update(_bic_line_fields(bic))
                            if fix.get("bug_id"):
                                prediction["bug_id"] = fix["bug_id"]
                            scenario_predictions.append(prediction)
                            raw_entries.append(
                                {
                                    "fix_commit": fix,
                                    "inducing_commit": bic_hash,
                                    "inducing_commit_id": prediction["inducing_commit_id"],
                                    "line": _bic_line_fields(bic),
                                }
                            )
                finally:
                    del szz
        except Exception as exc:
            scenario_errors.append(f"{type(exc).__name__}: {exc}")
            (raw_dir / f"{scenario.scenario_id}.traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")

        unique_predictions = _dedupe_predictions(scenario_predictions)
        raw_payload = {
            "scenario_id": scenario.scenario_id,
            "repo_path": str(scenario.repo_path),
            "fix_commits": scenario.fix_commits,
            "predictions": unique_predictions,
            "raw_entries": raw_entries,
            "errors": scenario_errors,
        }
        (raw_dir / f"{scenario.scenario_id}.json").write_text(
            json.dumps(raw_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        record: dict[str, Any] = {"scenario_id": scenario.scenario_id, "predictions": unique_predictions}
        if scenario.repository_id:
            # the generation the predictions were made on, checked by szzbench evaluate (issue #93)
            record["repository_id"] = scenario.repository_id
        if scenario_errors:
            # scored as a tool error, not as the tool's answer (issue #95)
            record["status"] = "error"
            record["errors"] = list(scenario_errors)
        records.append(record)
        manifest.append(
            {
                "scenario_id": scenario.scenario_id,
                "status": "error" if scenario_errors else "ok",
                "prediction_count": len(unique_predictions),
                "fix_commit_count": len(scenario.fix_commits),
                "errors": scenario_errors,
            }
        )

    predictions_path = out_dir / f"{tool_name}-predictions.jsonl"
    with predictions_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    finished_at = dt.datetime.now(dt.UTC).isoformat()
    result = {
        "tool": tool_name,
        "tool_root": str(tool_root),
        "generated_root": str(generated_root),
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": time.time() - start_time,
        "scenario_count": len(selected),
        "ok_count": sum(1 for item in manifest if item["status"] == "ok"),
        "error_count": sum(1 for item in manifest if item["status"] == "error"),
        "prediction_count": sum(item["prediction_count"] for item in manifest),
        "predictions_path": str(predictions_path),
        "manifest": manifest,
    }
    (out_dir / f"{tool_name}-run-results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / f"{tool_name}-run-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def _dedupe_predictions(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for prediction in predictions:
        key = (
            prediction.get("scenario_id"),
            prediction.get("fix_commit"),
            prediction.get("inducing_commit"),
            prediction.get("bug_id"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(prediction)
    return unique


def _bic_commit_hash(bic: Any) -> str:
    commit = getattr(bic, "commit", bic)
    return commit.hexsha


def _bic_line_fields(bic: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if hasattr(bic, "file_path"):
        fields["file"] = bic.file_path
    if hasattr(bic, "line_num"):
        fields["line"] = bic.line_num
    if hasattr(bic, "line_str"):
        fields["line_content"] = bic.line_str
    if hasattr(bic, "input_file_path"):
        fields["input_file"] = bic.input_file_path
    if hasattr(bic, "input_line_num"):
        line_value = bic.input_line_num
        if isinstance(line_value, range):
            fields["input_line"] = list(line_value)
        else:
            fields["input_line"] = line_value
    return fields


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool-root", required=True, type=Path)
    parser.add_argument("--generated-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--variant", default="default")
    parser.add_argument("--tools", nargs="+", default=list(TOOL_SPECS))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--log-file", type=Path)
    args = parser.parse_args()

    handlers: list[log.Handler] = [log.StreamHandler()]
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(log.FileHandler(args.log_file, encoding="utf-8"))
    log.basicConfig(level=log.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)

    _install_compat_modules()
    sys.path.insert(0, str(args.tool_root))
    scenarios = collect_scenarios(args.generated_root, args.variant)
    args.output_root.mkdir(parents=True, exist_ok=True)
    summary = []
    for tool_name in args.tools:
        summary.append(
            run_tool(
                tool_name,
                scenarios,
                args.generated_root,
                args.output_root,
                args.tool_root,
                args.limit,
            )
        )
    (args.output_root / "pyszz-variants-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
