from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import json
import shutil
import traceback

from .cleaner import replaceable_output_problem
from .findings import Finding, ValidationResult
from .generator import GenerationError, generate_repository
from .graph_generator import GraphGenerationError, generate_graph_repository
from .manifest import staleness

DEFAULT_GENERATED_INPUT_REPOS_ROOT = Path("generated-input-repos")
DEFAULT_SCENARIOS_ROOT = Path("scenarios")
DEFAULT_ADVANCED_SCENARIOS_ROOT = Path("advanced-scenarios")
#: What generate-all-repos appends to an output directory's name for the directory it
#: generates into: ``<id>/default.tmp``.  The complete output replaces ``<id>/default``
#: only afterwards, and a failed generation leaves its files there (issue #168).
ATTEMPT_SUFFIX = ".tmp"

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
    #: the traceback of an exception other than a generation error (issue #162)
    traceback: str | None = None
    #: the errors of a verification that failed the generation (issue #163)
    verification_errors: tuple[Finding, ...] = ()
    #: every finding of the verification, warnings included (issue #169): of this run's
    #: generation, or, for a skipped output, the one its generation recorded in
    #: metadata/verify-result.json.  None for a run without verification (--no-verify).
    verification: ValidationResult | None = None

    @property
    def warned(self) -> bool:
        return self.verification is not None and self.verification.warning_count() > 0

    def to_dict(self) -> dict:
        """One item of ``generate-all-repos --json``; ``generate --json`` prints the same keys for its one output."""
        return {
            "kind": self.kind,
            "scenario_id": self.scenario_id,
            "scenario": str(self.scenario_path),
            "output_dir": str(self.output_dir),
            "status": self.status,
            "commit_count": self.commit_count,
            "overwritten": self.overwritten,
            "stale_reason": self.stale_reason,
            "error": self.error,
            "traceback": self.traceback,
            "verification": self.verification.to_dict() if self.verification is not None else None,
        }


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

    @property
    def warned_count(self) -> int:
        """Outputs whose verification has a warning, the skipped ones included; ``--strict`` fails on them (issue #169)."""
        return sum(1 for item in self.items if item.warned)

    def to_dict(self) -> dict:
        """What ``generate-all-repos --json`` prints (issue #169)."""
        return {
            "items": [item.to_dict() for item in self.items],
            "orphans": [str(orphan) for orphan in self.orphans],
            "summary": {
                "total": self.total_count,
                "generated": self.generated_count,
                "skipped": self.skipped_count,
                "overwritten": self.overwritten_count,
                "regenerated": self.regenerated_count,
                "failed": self.failed_count,
                "warned": self.warned_count,
                "orphaned": len(self.orphans),
            },
        }


def generate_all_repositories(
    *,
    scenarios_root: Path = DEFAULT_SCENARIOS_ROOT,
    advanced_scenarios_root: Path = DEFAULT_ADVANCED_SCENARIOS_ROOT,
    output_root: Path = DEFAULT_GENERATED_INPUT_REPOS_ROOT,
    overwrite: bool = False,
    verify: bool = True,
) -> GenerateAllRepositoriesResult:
    output_root = output_root.resolve()
    scenario_specs = [
        *[(path, "classic") for path in _find_scenario_files(scenarios_root, "scenario.yml")],
        *[(path, "graph") for path in _find_scenario_files(advanced_scenarios_root, "scenario.graph.yml")],
    ]
    # checked before anything is written: the second scenario overwrote the first one's
    # output, and was reported as a routine regeneration (issue #168)
    clash = _shared_output_problem(scenario_specs, output_root)
    if clash is not None:
        raise GenerateAllRepositoriesError(clash)
    output_root.mkdir(parents=True, exist_ok=True)

    items: list[GeneratedRepositoryItem] = []
    for scenario_path, kind in scenario_specs:
        scenario_id = scenario_path.parent.name
        output_dir = output_root / scenario_id / "default"
        output_exists = False
        stale_reason = None
        attempt = None          # where this run's generation writes, once it has begun
        # Everything done for one scenario -- the staleness check included, which reads
        # the scenario file -- is inside one boundary, so that whatever it raises is that
        # scenario's failure and the run goes on (issue #162, PR #213 review).
        try:
            output_exists = output_dir.exists()

            # An existing output is kept only when its manifest says it is complete and
            # was made from this scenario by this generator; anything else -- an
            # interrupted generation, an edited scenario, changed generator code, an
            # output from before the manifest -- is regenerated (issue #93).
            if output_exists and not overwrite:
                stale_reason = staleness(output_dir, scenario_path, require_verified=verify)
                saved = _saved_verification(output_dir) if verify and stale_reason is None else None
                if verify and stale_reason is None and saved is None:
                    # a verified output reports, and --strict judges, the verification it
                    # recorded; without it, the output is verified again (issue #169)
                    stale_reason = "its verification result (metadata/verify-result.json) is missing or unreadable"
                if stale_reason is None:
                    items.append(
                        GeneratedRepositoryItem(
                            kind=kind,
                            scenario_id=scenario_id,
                            scenario_path=scenario_path,
                            output_dir=output_dir,
                            status="skipped",
                            verification=saved,
                        )
                    )
                    continue

            # Generated beside the output and put in its place only once complete (and
            # verified): the old output was removed first, so a regeneration that failed
            # left a partial output where a complete one had been (issue #168).  The
            # generators resolve their --out, and the graph generator names the manifest's
            # scenario after its parent directory, so the attempt is a sibling of the
            # resolved output.
            target = output_dir.resolve()
            staging = target.with_name(target.name + ATTEMPT_SUFFIX)
            _prepare_attempt(target, staging, scenario_path, replace=output_exists)
            attempt = staging
            generate = generate_repository if kind == "classic" else generate_graph_repository
            commit_map, verify_result = generate(scenario_path, staging, verify=verify)
            attempt = None
            _put_in_place(staging, target, replace=output_exists)
        except (GenerationError, GraphGenerationError) as exc:
            items.append(
                GeneratedRepositoryItem(
                    kind=kind,
                    scenario_id=scenario_id,
                    scenario_path=scenario_path,
                    output_dir=output_dir,
                    status="failed",
                    overwritten=overwrite and output_exists,
                    error=_with_attempt(str(exc), attempt, kept=output_exists),
                    stale_reason=stale_reason,
                    verification_errors=(tuple(exc.verify_result.error_findings()) if exc.verify_result is not None else ()),
                    verification=exc.verify_result,
                )
            )
            continue
        except Exception as exc:
            # Any other exception is this scenario's failure too, not the run's: the
            # run used to stop here with a traceback, leaving the later scenarios
            # unvisited and no summary (issue #162).  KeyboardInterrupt still stops it.
            error = f"{type(exc).__name__}: {exc}"
            if attempt is not None:
                _record_unexpected_failure(attempt, error)
            items.append(
                GeneratedRepositoryItem(
                    kind=kind,
                    scenario_id=scenario_id,
                    scenario_path=scenario_path,
                    output_dir=output_dir,
                    status="failed",
                    overwritten=overwrite and output_exists,
                    error=_with_attempt(error, attempt, kept=output_exists),
                    stale_reason=stale_reason,
                    traceback=traceback.format_exc(),
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
                verification=verify_result,
            )
        )

    known = {path.parent.name for path, _ in scenario_specs}
    orphans = sorted(child for child in output_root.iterdir() if _is_orphan(child, known))
    return GenerateAllRepositoriesResult(items=items, orphans=orphans)


def _is_orphan(child: Path, known: set[str]) -> bool:
    """An output directory whose scenario no longer exists.  A directory that cannot be
    inspected is not reported: before Python 3.14 the probe raises PermissionError,
    which would end the run after every scenario was handled, before its summary."""
    try:
        return child.is_dir() and child.name not in known and (child / "default").is_dir()
    except OSError:
        return False


def _saved_verification(output_dir: Path) -> ValidationResult | None:
    """The findings the generation of ``output_dir`` wrote to ``metadata/verify-result.json``; None when unreadable."""
    try:
        data = json.loads((output_dir / "metadata" / "verify-result.json").read_text(encoding="utf-8"))
        return ValidationResult(Finding(entry["severity"], entry["code"], entry["message"], entry.get("location"))
                                for entry in data["findings"])
    except (OSError, ValueError, LookupError, TypeError, AttributeError):
        return None


def _shared_output_problem(scenario_specs: list[tuple[Path, ScenarioKind]], output_root: Path) -> str | None:
    """Why two scenarios would be generated into one output directory, or None (issue #168).

    The output of ``<root>/<id>/`` is ``<out-root>/<id>/default`` for both suites.
    Letter case does not tell two ids apart, since a case-insensitive file system
    (macOS, Windows) stores both outputs in one directory.
    """
    by_key: dict[str, list[Path]] = {}
    for path, _ in scenario_specs:
        by_key.setdefault(path.parent.name.casefold(), []).append(path)
    clashes = [paths for paths in by_key.values() if len(paths) > 1]
    if not clashes:
        return None
    described = "; ".join(" and ".join(str(path) for path in paths) for paths in clashes)
    return (f"Two scenarios share an id, and one would overwrite the other's output in "
            f"{output_root / '<id>' / 'default'}: {described}. Rename one of the directories "
            "(letter case does not tell two ids apart)")


def _prepare_attempt(target: Path, staging: Path, scenario_path: Path, *, replace: bool) -> None:
    """Check, before generating, that the old output may be replaced, and remove an earlier failed attempt.

    The generators refused to replace an output directory holding anything but a
    generated output (issue #165); generate-all-repos replaces it itself now, so
    it asks the same question first.  ``staging`` is left by a failed generation
    of an earlier run, and is replaced under the same rule.
    """
    if replace:
        problem = replaceable_output_problem(target, scenario_path)
        if problem is not None:
            raise GenerationError(f"{problem}.")
    if staging.exists() or staging.is_symlink():
        problem = replaceable_output_problem(staging, scenario_path)
        if problem is not None:
            raise GenerationError(f"{problem}.")
        try:
            shutil.rmtree(staging)
        except OSError as exc:
            raise GenerationError(f"Cannot remove the failed attempt of an earlier run, {staging}: {exc}") from exc


def _put_in_place(staging: Path, target: Path, *, replace: bool) -> None:
    """Replace ``target`` with the complete output generated into ``staging``.

    Nothing is written into the output: its manifest stays the last file written
    (issue #93), and ``generation.log`` names the repository where it was
    initialized, in ``staging``.
    """
    try:
        if replace:
            shutil.rmtree(target)
        staging.rename(target)
    except OSError as exc:
        raise GenerationError(f"Cannot put the new output {staging} in place of {target}: {exc}") from exc


def _with_attempt(error: str, attempt: Path | None, *, kept: bool) -> str:
    """``error``, and where the failed generation left its files, once it had begun (issue #168)."""
    try:
        begun = attempt is not None and attempt.exists()
    except OSError:
        begun = False
    if not begun:
        return error
    previous = "the previous output was left in place, and " if kept else ""
    return f"{error.rstrip('.')}; {previous}the files of this attempt are in {attempt}"


def _record_unexpected_failure(output_dir: Path, error: str) -> None:
    """Write ``metadata/generation-error.json`` into the attempt the generator had begun.

    The generators write it for their own errors.  ``output_dir`` is the
    directory generate-all-repos generates into (issue #168), so a complete
    output is never marked; an attempt with a manifest is left alone all the
    same.

    It is best effort, and nothing in it may raise: it runs inside the handler
    that keeps the run going.  The probes are inside the boundary too, since
    before Python 3.14 ``Path.exists`` and ``Path.is_dir`` raise
    ``PermissionError`` for a directory that cannot be searched, where 3.14
    returns False (PR #213 review).
    """
    metadata_dir = output_dir / "metadata"
    try:
        if not metadata_dir.is_dir() or (metadata_dir / "manifest.json").exists():
            return
        info = {"error": error, "timestamp": datetime.now(timezone.utc).isoformat()}
        (metadata_dir / "generation-error.json").write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n",
                                                             encoding="utf-8")
    except OSError:
        pass


def _find_scenario_files(root: Path, filename: str) -> list[Path]:
    """``<root>/*/<filename>``: the scenario of each directory directly below ``root``.

    The search was recursive, so with the outputs below a scenario root it also
    found the copy of the scenario each output keeps in ``metadata/`` (issue
    #93), and generated a scenario named ``metadata`` from it (issue #168).
    """
    root = root.resolve()
    if not root.exists():
        raise GenerateAllRepositoriesError(f"Scenario root does not exist: {root}")
    if not root.is_dir():
        raise GenerateAllRepositoriesError(f"Scenario root is not a directory: {root}")
    try:
        candidates = [child / filename for child in root.iterdir()]
    except OSError as exc:
        raise GenerateAllRepositoriesError(f"Cannot read the scenario root {root}: {exc}") from exc
    return sorted(path for path in candidates if _is_file(path))


def _is_file(path: Path) -> bool:
    """Whether ``path`` is a file; False for one that cannot be inspected, which the recursive search skipped
    too (before Python 3.14, ``Path.is_file`` raises PermissionError for it)."""
    try:
        return path.is_file()
    except OSError:
        return False
