#!/usr/bin/env python3
"""Run PySZZ's B-, AG-, MA-, L- and R-SZZ over SZZBench's generated repositories.

PySZZ is not part of SZZBench: pass an unpacked copy with --tool-root.  Run
this script with a Python that has the libraries PySZZ's requirements.txt pins
for these variants (GitPython 3.1.7, PyDriller 1.15.2, dateparser 0.7.6), and
with srcML on PATH for AG-, MA-, L- and R-SZZ.  examples/pyszz-run/README.md
says where to get each and records a run over the shipped suite.
"""
from __future__ import annotations

import argparse
import atexit
import datetime as dt
import enum
import json
import logging as log
import os
import platform
import shutil
import subprocess
import sys
import tempfile
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

#: AG-SZZ and the variants built on it skip comment lines, and PySZZ finds the
#: comments of Java, C, C++ and C# files with srcML.  Without srcML every such
#: file logs an error and keeps its comments: the variant runs, but it is no
#: longer the variant.
TOOLS_NEEDING_SRCML = ("ag-szz", "ma-szz", "l-szz", "r-szz")

#: MA-SZZ, L-SZZ and R-SZZ exclude meta-changes with `git blame
#: --ignore-revs-file`, which GitPython releases after the 3.1.7 that PySZZ's
#: requirements.txt pins refuse as an unsafe option.
TOOLS_NEEDING_IGNORE_REVS_FILE = ("ma-szz", "l-szz", "r-szz")

#: The ERROR records PySZZ logs as part of its normal behaviour: a file that
#: its comment parsers do not handle keeps its comment lines, as it does in
#: PySZZ's own environment.  Every other ERROR record is an exception PySZZ
#: caught and carried on from, and fails the scenario as a tool error.
BENIGN_PYSZZ_ERRORS = ("file not supported by srcML: ", "unable to parse comments for: ")


class _ErrorCapture(log.Handler):
    """Collects the ERROR records PySZZ logs while one scenario runs."""

    def __init__(self) -> None:
        super().__init__(level=log.ERROR)
        self.messages: list[str] = []

    def emit(self, record: log.LogRecord) -> None:
        self.messages.append(record.getMessage())


def split_pyszz_errors(messages: list[str]) -> tuple[list[str], list[str]]:
    """Split what PySZZ logged at ERROR into failures and benign notes.

    PySZZ catches its own exceptions and logs the traceback, so a blame that
    raised looks like a blame that found nothing.  A failure is reported by
    the traceback's last line, which names the exception.
    """
    failures: list[str] = []
    benign: list[str] = []
    for message in messages:
        if message.startswith(BENIGN_PYSZZ_ERRORS):
            benign.append(message)
            continue
        lines = [line for line in message.strip().splitlines() if line.strip()]
        summary = lines[-1].strip() if message.startswith("Traceback") and lines else message.strip()
        failures.append(f"PySZZ logged an error and carried on: {summary}")
    return failures, benign


def isolated_git_environment(environ: dict[str, str], home: str) -> dict[str, str]:
    """The environment PySZZ's Git runs in: SZZBench's own isolation (issue #96).

    PySZZ runs `git blame` through GitPython, so a setting in the caller's
    ~/.gitconfig (`blame.ignoreRevsFile`, for example) or an inherited
    `GIT_*` variable would change its answers.  The system and global
    configuration, the default ignore and attributes files and every `GIT_*`
    variable but `GIT_EXEC_PATH` are withheld.
    """
    isolated = {key: value for key, value in environ.items()
                if not key.startswith("GIT_") or key == "GIT_EXEC_PATH"}
    isolated.update({"HOME": home, "XDG_CONFIG_HOME": home,
                     "GIT_CONFIG_NOSYSTEM": "1", "GIT_ATTR_NOSYSTEM": "1"})
    return isolated


def pydriller_1x_available() -> bool:
    """True when the PyDriller 1.x that PySZZ imports is installed.

    PySZZ is written against PyDriller 1.x (`GitRepository`,
    `RepositoryMining`); PyDriller 2 renamed both.
    """
    try:
        import pydriller
    except ImportError:
        return False
    return all(hasattr(pydriller, name) for name in ("GitRepository", "RepositoryMining", "ModificationType"))


def fixed_hash_seed_command(environ: dict[str, str], argv: list[str], executable: str
                            ) -> tuple[list[str], dict[str, str]] | None:
    """The command that runs this script again with a fixed hash seed, or None when a seed is set.

    L-SZZ keeps the first of equally large candidates in the iteration order
    of a set of GitPython commits, and that order follows Python's
    per-process hash seed: 15 scenarios of the shipped suite give L-SZZ two
    equally large candidates, which one it answers changes from run to run,
    and in three of them that decides the verdict.  A fixed seed makes a run
    repeatable; PYTHONHASHSEED=random asks for the old behaviour.
    """
    if "PYTHONHASHSEED" in environ:
        return None
    return [executable, *argv], {**environ, "PYTHONHASHSEED": "0"}


def _first_output_line(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError:
        return None
    lines = (completed.stdout or completed.stderr).strip().splitlines()
    return lines[0] if lines else None


def run_environment(uses_compat: dict[str, bool]) -> dict[str, Any]:
    """What a run depended on, recorded next to its results."""
    import git

    def version_of(module: str, distribution: str) -> str:
        if uses_compat.get(module):
            return "adapter compatibility layer"
        try:
            from importlib.metadata import version
            return version(distribution)
        except Exception:
            return "unknown"

    return {
        "python": platform.python_version(),
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "random"),
        "platform": platform.platform(),
        "git": _first_output_line(["git", "--version"]),
        "srcml": _first_output_line(["srcml", "--version"]),
        "GitPython": getattr(git, "__version__", "unknown"),
        "PyDriller": version_of("pydriller", "PyDriller"),
        "dateparser": version_of("dateparser", "dateparser"),
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
    """Stand in for the PyDriller 1.x and dateparser that PySZZ imports (`--compat-layer` only).

    The stand-in is an approximation, not PyDriller.  Measured over the
    shipped suite against PyDriller 1.15.2 with the same hash seed, its line
    counts give a root commit no lines, which changes L-SZZ's choice of the
    largest candidate in the 29 scenarios where PyDriller finds the root
    commit largest, and it diffs a merge fix against its first parent, where
    PyDriller 1.15.2 reports no modified files (SZZG-0046, every variant).
    """
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


def _dateparser_available() -> bool:
    try:
        import dateparser  # noqa: F401
    except ImportError:
        return False
    return True


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
    #: why PySZZ cannot run on this output; the scenario is then recorded as a tool error
    setup_error: str | None = None


def collect_scenarios(generated_root: Path, variant: str) -> list[ScenarioInput]:
    """Every generated repository under the root, including one PySZZ cannot run on.

    An output whose commit map is missing or unreadable is incomplete. It is
    kept, with a setup error, so that it gets a tool-error record instead of
    vanishing from the run (issue #95).
    """
    scenarios: list[ScenarioInput] = []
    for repo_path in sorted(generated_root.glob(f"*/{variant}/repo")):
        scenario_id = repo_path.parent.parent.name
        metadata_dir = repo_path.parent / "metadata"
        commit_map_path = metadata_dir / "commit-map.json"
        try:
            commit_map = json.loads(commit_map_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problem = ("is missing" if not commit_map_path.exists()
                       else f"cannot be read ({type(exc).__name__}: {exc})")
            scenarios.append(
                ScenarioInput(
                    scenario_id=scenario_id,
                    repo_name=f"{scenario_id}/{variant}/repo",
                    repo_path=repo_path,
                    fix_commits=[],
                    commit_map={},
                    repository_id=_repository_id(metadata_dir),
                    setup_error=f"{commit_map_path} {problem}: the generated output is incomplete",
                )
            )
            continue
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
    environment: dict[str, Any] | None = None,
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
    started_at = dt.datetime.now(dt.timezone.utc).isoformat()
    start_time = time.time()

    for index, scenario in enumerate(selected, start=1):
        scenario_predictions: list[dict[str, Any]] = []
        scenario_errors: list[str] = []
        raw_entries: list[dict[str, Any]] = []
        log.info("[%s] %d/%d %s", tool_name, index, len(selected), scenario.scenario_id)
        if scenario.setup_error:
            scenario_errors.append(scenario.setup_error)
        elif not scenario.fix_commits:
            scenario_errors.append("No bug fixing commits found.")
        capture = _ErrorCapture()
        log.getLogger().addHandler(capture)
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
        finally:
            log.getLogger().removeHandler(capture)
        pyszz_failures, pyszz_notes = split_pyszz_errors(capture.messages)
        if pyszz_failures:
            # an exception PySZZ caught is a tool error, not an empty answer (issue #95)
            scenario_errors.extend(pyszz_failures)
            (raw_dir / f"{scenario.scenario_id}.pyszz-errors.txt").write_text(
                "\n\n".join(message for message in capture.messages if not message.startswith(BENIGN_PYSZZ_ERRORS)),
                encoding="utf-8",
            )

        unique_predictions = _dedupe_predictions(scenario_predictions)
        raw_payload = {
            "scenario_id": scenario.scenario_id,
            "repo_path": str(scenario.repo_path),
            "fix_commits": scenario.fix_commits,
            "predictions": unique_predictions,
            "raw_entries": raw_entries,
            "errors": scenario_errors,
            "pyszz_logged": pyszz_notes,
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

    finished_at = dt.datetime.now(dt.timezone.utc).isoformat()
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
        "environment": environment,
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tool-root", required=True, type=Path)
    parser.add_argument("--generated-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--variant", default="default")
    parser.add_argument("--tools", nargs="+", default=list(TOOL_SPECS), choices=list(TOOL_SPECS))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--compat-layer", action="store_true",
                        help="Replace PyDriller 1.x and dateparser with the adapter's approximation. "
                             "For smoke tests only: its results differ from PySZZ's (see _install_compat_modules).")
    args = parser.parse_args(argv)

    needs_srcml = [tool for tool in args.tools if tool in TOOLS_NEEDING_SRCML]
    if needs_srcml and shutil.which("srcml") is None:
        print(f"[ERROR] {', '.join(needs_srcml)} skip comment lines, and PySZZ finds the comments of Java, C, C++ "
              "and C# files with srcML, which is not on PATH. Install srcML (PySZZ's Docker image uses 1.0.0), "
              "or run only b-szz.", file=sys.stderr)
        return 2
    missing = [name for name, present in (("PyDriller 1.x", pydriller_1x_available()),
                                          ("dateparser", _dateparser_available())) if not present]
    if missing and not args.compat_layer:
        print(f"[ERROR] PySZZ imports {' and '.join(missing)}, which {'is' if len(missing) == 1 else 'are'} not "
              "installed. Install the versions PySZZ's requirements.txt pins: "
              "pip install GitPython==3.1.7 PyDriller==1.15.2 dateparser==0.7.6", file=sys.stderr)
        return 2

    handlers: list[log.Handler] = [log.StreamHandler()]
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(log.FileHandler(args.log_file, encoding="utf-8"))
    log.basicConfig(level=log.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)

    import git

    needs_ignore_revs_file = [tool for tool in args.tools if tool in TOOLS_NEEDING_IGNORE_REVS_FILE]
    if needs_ignore_revs_file and "--ignore-revs-file" in getattr(Repo, "unsafe_git_blame_options", ()):
        log.warning("GitPython %s refuses `git blame --ignore-revs-file`, which %s use to exclude meta-changes: "
                    "a scenario where they need it fails as a tool error. PySZZ's requirements.txt pins "
                    "GitPython 3.1.7.", git.__version__, ", ".join(needs_ignore_revs_file))

    home = tempfile.mkdtemp(prefix="pyszz-git-home-")
    atexit.register(shutil.rmtree, home, True)
    isolated = isolated_git_environment(dict(os.environ), home)
    os.environ.clear()
    os.environ.update(isolated)

    uses_compat = {"pydriller": args.compat_layer, "dateparser": args.compat_layer}
    if args.compat_layer:
        log.warning("--compat-layer: PyDriller 1.x and dateparser are replaced by the adapter's approximation, "
                    "so these results are not PySZZ's")
        _install_compat_modules()
    environment = run_environment(uses_compat)
    log.info("environment: %s", json.dumps(environment))
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
                environment,
            )
        )
    (args.output_root / "pyszz-variants-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for result in summary:
        for item in result["manifest"]:
            for error in item["errors"]:
                print(f"[ERROR] {result['tool']} {item['scenario_id']}: {error}", file=sys.stderr)
    return exit_status(summary)


def exit_status(summary: list[dict[str, Any]]) -> int:
    """1 when any variant recorded a tool error, as the other adapters exit: a run with errors
    must not look like a clean one, although every record is still written."""
    return 1 if any(result["error_count"] for result in summary) else 0


if __name__ == "__main__":
    rerun = fixed_hash_seed_command(dict(os.environ), sys.argv, sys.executable)
    if rerun is not None:
        command, environment = rerun
        os.execve(command[0], command, environment)
    raise SystemExit(main())
