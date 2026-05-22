from __future__ import annotations

from pathlib import Path
import json
import shutil
from datetime import datetime, timezone

from .findings import ValidationResult
from .gitutils import GitError, commit_all, init_repo
from .operations import OperationError, apply_operation_to_filesystem
from .scenario import load_yaml
from .validator import validate_scenario_file
from .verifier import verify_generated_repo

class GenerationError(RuntimeError):
    pass

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
        if not force:
            raise GenerationError(f"Output directory already exists: {out_dir}. Use --force to overwrite.")
        shutil.rmtree(out_dir)
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
        for commit_spec in scenario.get("commits", []):
            cid = commit_spec["id"]
            log(f"Applying commit {cid}: {commit_spec.get('message', '')}")
            for op in commit_spec.get("operations", []):
                apply_operation_to_filesystem(repo_dir, op)
            actual_hash = commit_all(repo_dir, message=commit_spec["message"], author=commit_spec.get("author"), date=commit_spec.get("date"))
            commit_map[cid] = {
                "hash": actual_hash,
                "message": commit_spec.get("message"),
                "author": commit_spec.get("author"),
                "date": commit_spec.get("date"),
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
                raise GenerationError("Generated repository failed verification.")
        log("Generation completed successfully.")
        (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
        return commit_map, verify_result
    except (OperationError, GitError, OSError) as exc:
        log(f"ERROR: {exc}")
        error_info = {"error": str(exc), "timestamp": datetime.now(timezone.utc).isoformat()}
        (metadata_dir / "generation-error.json").write_text(json.dumps(error_info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (metadata_dir / "generation.log").write_text("\n".join(generation_log) + "\n", encoding="utf-8")
        raise GenerationError(str(exc)) from exc
