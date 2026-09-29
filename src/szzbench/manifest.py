"""What a generated output was made from, and whether it still matches (issue #93).

A generation writes ``metadata/manifest.json`` last, once the repository is
complete -- and verified, when verification was asked for.  It records the
SHA-256 of the scenario file, a fingerprint of the generator's code, and the
repository id: a digest of the commit hashes, which prediction records carry so
that a run can be matched to the repository it was made on.

An output is **stale** when it has no manifest (an interrupted generation, or
one made before the manifest existed), when its scenario file or the generator's
code has changed since, when it is unverified and verification is asked for, or
when what the manifest describes is no longer all there: ``repo/.git`` with
every commit of the commit map, the commit map the repository id was taken
from, and the scenario copy (and, for a graph scenario, the graph map) in
``metadata/``.  ``generate-all-repos`` regenerates a stale output instead of
skipping it; ``evaluate``, ``baselines`` and ``coverage`` refuse to score it.
Until 2026-09-29 an output counted as done as soon as ``repo/.git`` existed, so
an edited scenario was scored against a repository generated from its old
version.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MANIFEST_NAME = "manifest.json"
MANIFEST_FORMAT = 1

#: The modules whose code decides what a generated repository contains; a change
#: to any of them makes every existing output stale.  The generators also import
#: validation, verification and reporting code, which does not write a commit
#: (EXCLUDED_FROM_FINGERPRINT); tests/test_generation_manifest.py checks that
#: every module the generators import is in exactly one of the two lists.
GENERATION_MODULES = ("generator", "graph_generator", "gitutils", "operations", "graph_operations",
                      "scenario", "graph_scenario", "paths")
EXCLUDED_FROM_FINGERPRINT = ("validator", "graph_validator", "graph_simulator", "verifier", "graph_verifier",
                             "evaluator", "findings", "policies", "readme")

_fingerprint: str | None = None


def _normalized_bytes(path: Path) -> bytes:
    """File content with CRLF read as LF, so a checkout's line endings change nothing."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(_normalized_bytes(path)).hexdigest()


def generator_fingerprint() -> str:
    """SHA-256 over the source of :data:`GENERATION_MODULES`."""
    global _fingerprint
    if _fingerprint is None:
        digest = hashlib.sha256()
        package = Path(__file__).resolve().parent
        for module in sorted(GENERATION_MODULES):
            digest.update(module.encode("utf-8") + b"\0")
            digest.update(_normalized_bytes(package / f"{module}.py") + b"\0")
        _fingerprint = digest.hexdigest()
    return _fingerprint


def repository_id(commit_map: dict[str, Any]) -> str:
    """A digest of every logical commit and its hash: equal exactly when the histories are."""
    pairs = sorted((str(cid), str(entry.get("hash"))) for cid, entry in commit_map.items() if isinstance(entry, dict))
    return hashlib.sha256(json.dumps(pairs).encode("utf-8")).hexdigest()[:16]


def write_manifest(metadata_dir: Path, *, scenario_id: str, scenario_path: Path, commit_map: dict[str, Any],
                   verified: bool) -> dict[str, Any]:
    from .gitutils import git_version

    manifest = {
        "format": MANIFEST_FORMAT,
        "scenario_id": scenario_id,
        "scenario_sha256": file_sha256(scenario_path),
        "generator": generator_fingerprint(),
        "repository_id": repository_id(commit_map),
        "verified": bool(verified),
        "git_version": ".".join(str(part) for part in git_version()),
    }
    (metadata_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def read_manifest(output_dir: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((output_dir / "metadata" / MANIFEST_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def staleness(output_dir: Path, scenario_path: Path, *, require_verified: bool = False) -> str | None:
    """Why ``output_dir`` is not a complete output of ``scenario_path``; None when it is."""
    if not output_dir.is_dir():
        return f"nothing has been generated at {output_dir}"
    manifest = read_manifest(output_dir)
    if manifest is None:
        return "it has no generation manifest (an interrupted generation, or one made before 2026-09-29)"
    if manifest.get("format") != MANIFEST_FORMAT:
        return f"its manifest has format {manifest.get('format')!r}, not {MANIFEST_FORMAT}"
    if manifest.get("scenario_sha256") != file_sha256(scenario_path):
        return "its scenario file has changed since it was generated"
    if manifest.get("generator") != generator_fingerprint():
        return "SZZBench's generator code has changed since it was generated"
    if require_verified and not manifest.get("verified"):
        return "it was generated without verification"
    return _incompleteness(output_dir, scenario_path, manifest)


def _incompleteness(output_dir: Path, scenario_path: Path, manifest: dict[str, Any]) -> str | None:
    """What the manifest describes and the output no longer has.

    A manifest outlives its output when ``repo/`` or a metadata file is moved,
    deleted or replaced after the generation; such an output is as stale as an
    unfinished one.  Extra objects and refs do not count -- an SZZ tool may
    check out, commit or branch in the repository it analyses -- but every
    commit the output was generated with must still be there.
    """
    git_dir = output_dir / "repo" / ".git"
    metadata = output_dir / "metadata"
    if not git_dir.exists():
        return "its repository is missing (no repo/.git)"
    try:
        commit_map = json.loads((metadata / "commit-map.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        commit_map = None
    if not isinstance(commit_map, dict):
        return "its commit map (metadata/commit-map.json) is missing or unreadable"
    if repository_id(commit_map) != manifest.get("repository_id"):
        return "its commit map (metadata/commit-map.json) has changed since it was generated"
    graph = scenario_path.name.endswith(".graph.yml")
    copy = metadata / ("scenario.graph.yml" if graph else "scenario.yml")
    if not copy.is_file() or file_sha256(copy) != manifest.get("scenario_sha256"):
        return f"its copy of the scenario (metadata/{copy.name}) is missing or differs from the scenario file"
    if graph and not (metadata / "graph-map.json").is_file():
        return "its graph map (metadata/graph-map.json) is missing"
    return _missing_commits(git_dir, commit_map)


def _missing_commits(git_dir: Path, commit_map: dict[str, Any]) -> str | None:
    from .gitutils import GitError, run_git_with_input

    hashes = {str(cid): str(entry.get("hash")) for cid, entry in commit_map.items() if isinstance(entry, dict)}
    # --git-dir, because Git would otherwise look for a repository in the
    # directories above one whose .git is not a repository; absolute, because
    # Git runs inside the repository and would resolve a relative one from
    # there (the CLI's roots are relative by default)
    try:
        listed = run_git_with_input(git_dir.parent, [f"--git-dir={git_dir.resolve()}", "cat-file",
                                                     "--batch-check=%(objecttype)"],
                                    "".join(f"{value}\n" for value in hashes.values()).encode("utf-8"))
    except GitError as exc:
        return f"its repository cannot be read ({str(exc).splitlines()[0]})"
    answers = dict(zip(hashes, listed.stdout.decode("utf-8", errors="replace").splitlines()))
    missing = sorted(cid for cid in hashes if answers.get(cid) != "commit")
    if missing:
        shown = ", ".join(missing[:5]) + (", ..." if len(missing) > 5 else "")
        return f"its repository lacks {len(missing)} of the {len(hashes)} commits it was generated with ({shown})"
    return None


def stale_message(scenario_id: str, reason: str) -> str:
    return (f"{scenario_id}: the generated repository is stale: {reason}. It is not scored; "
            "`szzbench generate-all-repos` regenerates stale outputs.")
