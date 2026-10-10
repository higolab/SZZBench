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
    but the directories ``repo/`` and ``metadata/`` (an interrupted generation,
    or an empty directory), and nothing else.
    """
    out_dir = out_dir.resolve()
    if not out_dir.is_dir():
        return f"--out {out_dir} exists and is not a directory"
    if _holds_cwd(out_dir):
        return f"--out {out_dir} is the current directory or one of its parents"
    if out_dir in scenario_path.resolve().parents:
        return f"--out {out_dir} contains the scenario file being generated"
    if is_generated_output_dir(out_dir):
        return None
    # The reserved names count only as the directories a generation creates: a regular
    # file, or a link, named repo or metadata is somebody's data (PR #212 review).
    others = sorted(entry.name for entry in out_dir.iterdir()
                    if not (entry.name in OUTPUT_ENTRIES and entry.is_dir() and not entry.is_symlink()))
    if others:
        shown = ", ".join(others[:5]) + (", ..." if len(others) > 5 else "")
        return (f"--out {out_dir} is not a generated output (it holds {shown}); "
                "remove it yourself or choose another directory")
    return None


def _holds_cwd(path: Path) -> bool:
    """Whether the resolved ``path`` is the current directory or one of its parents."""
    try:
        cwd = Path.cwd().resolve()
    except OSError:
        return False
    return cwd == path or path in cwd.parents


def clean_root_problem(root: Path) -> str | None:
    """Why ``clean`` must not scan ``root``, or None when it may (issue #171).

    ``clean`` removes every generated output below its root, at any depth, so
    a mistyped ``--root`` (``/``, the home directory, the checkout itself)
    removed outputs anywhere below it, after a scan of the whole tree.
    """
    root = root.resolve()
    if root.parent == root:
        return f"--root {root} is the file-system root"
    try:
        home = Path.home().resolve()
    except (OSError, RuntimeError, KeyError):     # no home directory to compare with
        home = None
    if root == home:
        return f"--root {root} is the home directory"
    if _holds_cwd(root):
        return f"--root {root} is the current directory or one of its parents"
    return None


def is_default_clean_root(root: Path) -> bool:
    """Whether ``root`` is ``generated-input-repos`` of the current directory, which ``clean`` empties without asking."""
    return root.resolve() == DEFAULT_CLEAN_ROOT.resolve()


def find_generated_outputs(root: Path) -> list[Path]:
    problem = clean_root_problem(root)
    if problem is not None:
        raise CleanError(f"{problem}; clean removes every generated output below its root, at any depth. "
                         f"Pass the directory generate-all-repos writes into ({DEFAULT_CLEAN_ROOT} by default), "
                         "and check what it finds with --dry-run first.")
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


def remove_generated_outputs(outputs: list[Path]) -> None:
    for output in outputs:
        try:
            shutil.rmtree(output, onerror=_make_writable_and_retry)
        except OSError as exc:
            raise CleanError(f"Failed to remove generated output {output}: {exc}") from exc


def clean_generated_outputs(root: Path, *, dry_run: bool = False) -> list[Path]:
    outputs = find_generated_outputs(root)
    if not dry_run:
        remove_generated_outputs(outputs)
    return outputs


def _make_writable_and_retry(function, path: str, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)
