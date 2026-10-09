from __future__ import annotations

from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

from .cleaner import replaceable_output_problem
from .findings import ValidationResult
from .gitutils import GitError, commit_all, init_repo, json_safe_timestamp, resolve_commit_metadata
from .manifest import write_manifest
from .operations import OperationError, apply_operation_to_filesystem
from .scenario import load_yaml
from .validator import validate_scenario_file
from .verifier import verify_generated_repo

class GenerationError(RuntimeError):
    def __init__(self, message: str, *, verify_result: ValidationResult | None = None) -> None:
        super().__init__(message)
        #: The findings, when it was the verification that failed: the CLI prints them (issue #163).
        self.verify_result = verify_result

def generate_repository(scenario_path: Path, out_dir: Path, *, force: bool = False, verify: bool = True) -> tuple[dict, ValidationResult | None]:
    scenario_path = scenario_path.resolve()
    out_dir = out_dir.resolve()
    repo_dir = out_dir / "repo"
    metadata_dir = out_dir / "metadata"
    _, validation_result, _ = validate_scenario_file(scenario_path, simulate=True)
    if validation_result.has_errors():
        raise GenerationError("Scenario validation failed. Run 'szzbench validate --simulate' for details.")
    scenario, load_result = load_yaml(scenario_path)
    if scenario is None or load_result.has_errors():
        raise GenerationError("Failed to load scenario.")
    if out_dir.exists():
        if not force and out_dir.is_dir():
            raise GenerationError(f"Output directory already exists: {out_dir}. Use --force to overwrite.")
        problem = replaceable_output_problem(out_dir, scenario_path)
        if problem is not None:
            raise GenerationError(f"{problem}.")
        try:
            shutil.rmtree(out_dir)
        except OSError as exc:
            raise GenerationError(f"Cannot remove the previous output {out_dir}: {exc}") from exc
    repo_dir.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    generation_log: list[str] = []
    commit_map: dict[str, dict] = {}
    def log(msg: str) -> None:
        generation_log.append(msg)
    try:
        branch = scenario.get("repository", {}).get("default_branch", "main")
        init_repo(repo_dir, branch)
        log(f"Initialized Git repository at {repo_dir}")
        for index, commit_spec in enumerate(scenario.get("commits", [])):
            cid = commit_spec["id"]
            log(f"Applying commit {cid}: {commit_spec.get('message', '')}")
            for op in commit_spec.get("operations", []):
                apply_operation_to_filesystem(repo_dir, op)
            # Missing author/date values are filled deterministically (issue #9)
            # so that generated metadata never depends on the generation time
            # or on the commit role.  Explicit values are used verbatim.
            metadata = resolve_commit_metadata(scenario, commit_spec, index)
            actual_hash = commit_all(
                repo_dir,
                message=commit_spec["message"],
                author=metadata.author,
                author_date=metadata.author_date,
                committer_date=metadata.committer_date,
            )
            commit_map[cid] = {
                "hash": actual_hash,
                "message": commit_spec.get("message"),
                "author": metadata.author,
                "date": json_safe_timestamp(commit_spec.get("date")),
                "author_date": metadata.author_date,
                "committer_date": metadata.committer_date,
                "role": commit_spec.get("role"),
            }
            log(f"Created commit {cid}: {actual_hash}")
        shutil.copy2(scenario_path, metadata_dir / "scenario.yml")
        (metadata_dir / "commit-map.json").write_text(json.dumps(commit_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (metadata_dir / "validation-result.json").write_text(json.dumps(validation_result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        verify_result = None
        if verify:
            verify_result = verify_generated_repo(repo_dir, scenario_path, metadata_dir / "commit-map.json")
            (metadata_dir / "verify-result.json").write_text(json.dumps(verify_result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            if verify_result.has_errors():
                # Recorded here like every other failure (issue #163): the except clause
                # below does not catch GenerationError, so the output used to be left
                # without generation.log and generation-error.json.
                error = "Generated repository failed verification."
                for finding in verify_result.error_findings():
                    log(f"Verification: {finding.format()}")
                log(f"ERROR: {error}")
                _record_failure(metadata_dir, generation_log, error)
                raise GenerationError(error, verify_result=verify_result)
        log("Generation completed successfully.")
        (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
        # written last: an output without it is incomplete (issue #93)
        write_manifest(metadata_dir, scenario_id=str(scenario.get("meta", {}).get("id") or out_dir.parent.name),
                       scenario_path=scenario_path, commit_map=commit_map, verified=verify)
        return commit_map, verify_result
    # ValueError: safe_join's PathValidationError, and a path the file system
    # refuses (a NUL byte), used to end generation in a traceback (issue #136)
    except (OperationError, GitError, OSError, ValueError) as exc:
        log(f"ERROR: {exc}")
        error_info = {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
        (metadata_dir / "generation-error.json").write_text(json.dumps(error_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
        raise GenerationError(str(exc)) from exc

def _record_failure(metadata_dir: Path, generation_log: list[str], error: str) -> None:
    """What the except clause of generate_repository writes for its own errors."""
    error_info = {"error": error, "timestamp": datetime.now(timezone.utc).isoformat()}
    (metadata_dir / "generation-error.json").write_text(json.dumps(error_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
