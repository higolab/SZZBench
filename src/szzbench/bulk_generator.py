from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .generator import GenerationError, generate_repository
from .graph_generator import GraphGenerationError, generate_graph_repository
from .manifest import staleness

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
    #: why an existing output was regenerated without --overwrite (issue #93)
    stale_reason: str | None = None


@dataclass(frozen=True)
class GenerateAllRepositoriesResult:
    items: list[GeneratedRepositoryItem]
    #: Output directories under the root whose scenario no longer exists -- left
    #: behind when a scenario is retired (docs/retired-ids.md).  Generation only
    #: visits scenario files, so it can neither refresh nor remove them, and the
    #: consumers that walk the output root would otherwise trip over them.
    orphans: list[Path] = field(default_factory=list)

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

    @property
    def regenerated_count(self) -> int:
        return sum(1 for item in self.items if item.status == "generated" and item.stale_reason is not None)


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
        output_exists = output_dir.exists()

        # An existing output is kept only when its manifest says it is complete and
        # was made from this scenario by this generator; anything else -- an
        # interrupted generation, an edited scenario, changed generator code, an
        # output from before the manifest -- is regenerated (issue #93).
        stale_reason = None
        if output_exists and not overwrite:
            stale_reason = staleness(output_dir, scenario_path, require_verified=verify)
            if stale_reason is None:
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

        try:
            if kind == "classic":
                commit_map, _ = generate_repository(scenario_path, output_dir, force=output_exists, verify=verify)
            else:
                commit_map, _ = generate_graph_repository(scenario_path, output_dir, force=output_exists, verify=verify)
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
                    stale_reason=stale_reason,
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
                stale_reason=stale_reason,
            )
        )

    known = {path.parent.name for path, _ in scenario_specs}
    orphans = sorted(
        child for child in output_root.iterdir()
        if child.is_dir() and child.name not in known and (child / "default").is_dir()
    )
    return GenerateAllRepositoriesResult(items=items, orphans=orphans)


def _find_scenario_files(root: Path, filename: str) -> list[Path]:
    root = root.resolve()
    if not root.exists():
        raise GenerateAllRepositoriesError(f"Scenario root does not exist: {root}")
    if not root.is_dir():
        raise GenerateAllRepositoriesError(f"Scenario root is not a directory: {root}")
    return sorted(path for path in root.rglob(filename) if path.is_file())
