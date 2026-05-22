from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat

DEFAULT_CLEAN_ROOT = Path("generated-input-repos")


class CleanError(RuntimeError):
    pass


def is_generated_output_dir(path: Path) -> bool:
    metadata_dir = path / "metadata"
    return (
        (path / "repo" / ".git").is_dir()
        and metadata_dir.is_dir()
        and (
            (metadata_dir / "commit-map.json").is_file()
            or (metadata_dir / "generation.log").is_file()
            or (metadata_dir / "generation-error.json").is_file()
        )
    )


def find_generated_outputs(root: Path) -> list[Path]:
    root = root.resolve()
    if not root.exists():
        return []
    if not root.is_dir():
        raise CleanError(f"Clean root is not a directory: {root}")
    if is_generated_output_dir(root):
        return [root]

    outputs: set[Path] = set()
    for metadata_dir in root.rglob("metadata"):
        candidate = metadata_dir.parent
        if is_generated_output_dir(candidate):
            outputs.add(candidate)
    return sorted(outputs)


def clean_generated_outputs(root: Path, *, dry_run: bool = False) -> list[Path]:
    outputs = find_generated_outputs(root)
    if dry_run:
        return outputs
    for output in outputs:
        try:
            shutil.rmtree(output, onerror=_make_writable_and_retry)
        except OSError as exc:
            raise CleanError(f"Failed to remove generated output {output}: {exc}") from exc
    return outputs


def _make_writable_and_retry(function, path: str, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)
