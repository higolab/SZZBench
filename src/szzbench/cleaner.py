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


#: What a generated output holds at its top level.  An output whose generation was
#: interrupted may lack the files is_generated_output_dir looks for, but nothing else.
OUTPUT_ENTRIES = frozenset({"repo", "metadata"})


def replaceable_output_problem(out_dir: Path, scenario_path: Path) -> str | None:
    """Why ``generate --force`` must not remove the existing ``out_dir``, or None when it may (issue #165).

    ``--force`` used to delete whatever ``--out`` named: unrelated files, the
    directory holding the scenario being generated, the current directory.
    It may now replace a generated output, or a directory that holds nothing
    but ``repo/`` and ``metadata/`` (an interrupted generation, or an empty
    directory), and nothing else.
    """
    out_dir = out_dir.resolve()
    if not out_dir.is_dir():
        return f"--out {out_dir} exists and is not a directory"
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        cwd = None
    if cwd is not None and (cwd == out_dir or out_dir in cwd.parents):
        return f"--out {out_dir} is the current directory or one of its parents"
    if out_dir in scenario_path.resolve().parents:
        return f"--out {out_dir} contains the scenario file being generated"
    if is_generated_output_dir(out_dir):
        return None
    others = sorted(entry.name for entry in out_dir.iterdir() if entry.name not in OUTPUT_ENTRIES)
    if others:
        shown = ", ".join(others[:5]) + (", ..." if len(others) > 5 else "")
        return (f"--out {out_dir} is not a generated output (it holds {shown}); "
                "remove it yourself or choose another directory")
    return None


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
