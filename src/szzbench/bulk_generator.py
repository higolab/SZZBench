from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .generator import GenerationError, generate_repository
from .graph_generator import GraphGenerationError, generate_graph_repository

DEFAULT_GENERATED_INPUT_REPOS_ROOT = Path("generated-input-repos")
DEFAULT_SCENARIOS_ROOT = Path("scenarios")
DEFAULT_ADVANCED_SCENARIOS_ROOT = Path("advanced-scenarios")

ScenarioKind = Literal["classic", "graph"]
GenerationStatus = Literal["generated", "skipped", "failed"]


class GenerateAllRepositoriesError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedRepositoryItem:
    kind: ScenarioKind
    scenario_id: str
    scenario_path: Path
    output_dir: Path
    status: GenerationStatus
    commit_count: int = 0
    overwritten: bool = False
    error: str | None = None


@dataclass(frozen=True)
class GenerateAllRepositoriesResult:
    items: list[GeneratedRepositoryItem]

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def generated_count(self) -> int:
        return sum(1 for item in self.items if item.status == "generated")

    @property
    def skipped_count(self) -> int:
        return sum(1 for item in self.items if item.status == "skipped")

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == "failed")

    @property
    def overwritten_count(self) -> int:
        return sum(1 for item in self.items if item.status == "generated" and item.overwritten)


def generate_all_repositories(
    *,
    scenarios_root: Path = DEFAULT_SCENARIOS_ROOT,
    advanced_scenarios_root: Path = DEFAULT_ADVANCED_SCENARIOS_ROOT,
    output_root: Path = DEFAULT_GENERATED_INPUT_REPOS_ROOT,
    overwrite: bool = False,
    verify: bool = True,
) -> GenerateAllRepositoriesResult:
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    items: list[GeneratedRepositoryItem] = []
    scenario_specs = [
        *[(path, "classic") for path in _find_scenario_files(scenarios_root, "scenario.yml")],
        *[(path, "graph") for path in _find_scenario_files(advanced_scenarios_root, "scenario.graph.yml")],
    ]

    for scenario_path, kind in scenario_specs:
        scenario_id = scenario_path.parent.name
        output_dir = output_root / scenario_id / "default"
        repo_exists = (output_dir / "repo" / ".git").is_dir()
        output_exists = output_dir.exists()

        if repo_exists and not overwrite:
            items.append(
                GeneratedRepositoryItem(
                    kind=kind,
                    scenario_id=scenario_id,
                    scenario_path=scenario_path,
                    output_dir=output_dir,
                    status="skipped",
                )
            )
            continue

        if output_exists and not overwrite:
            items.append(
                GeneratedRepositoryItem(
                    kind=kind,
                    scenario_id=scenario_id,
                    scenario_path=scenario_path,
                    output_dir=output_dir,
                    status="failed",
                    error="Output directory already exists but repo/.git is missing. Use --overwrite to replace it.",
                )
            )
            continue

        try:
            if kind == "classic":
                commit_map, _ = generate_repository(scenario_path, output_dir, force=overwrite, verify=verify)
            else:
                commit_map, _ = generate_graph_repository(scenario_path, output_dir, force=overwrite, verify=verify)
        except (GenerationError, GraphGenerationError) as exc:
            items.append(
                GeneratedRepositoryItem(
                    kind=kind,
                    scenario_id=scenario_id,
                    scenario_path=scenario_path,
                    output_dir=output_dir,
                    status="failed",
                    overwritten=overwrite and output_exists,
                    error=str(exc),
                )
            )
            continue

        items.append(
            GeneratedRepositoryItem(
                kind=kind,
                scenario_id=scenario_id,
                scenario_path=scenario_path,
                output_dir=output_dir,
                status="generated",
                commit_count=len(commit_map),
                overwritten=overwrite and output_exists,
            )
        )

    return GenerateAllRepositoriesResult(items=items)


def _find_scenario_files(root: Path, filename: str) -> list[Path]:
    root = root.resolve()
    if not root.exists():
        raise GenerateAllRepositoriesError(f"Scenario root does not exist: {root}")
    if not root.is_dir():
        raise GenerateAllRepositoriesError(f"Scenario root is not a directory: {root}")
    return sorted(path for path in root.rglob(filename) if path.is_file())
