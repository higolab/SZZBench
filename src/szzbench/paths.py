from __future__ import annotations

from pathlib import Path

class PathValidationError(ValueError):
    pass

# Code points HFS+ ignores when it compares names, so that ``.g<U+200C>it``
# opens ``.git`` on macOS.  The list is Git's own (``is_hfs_dotgit`` in
# ``utf8.c``), which refuses such tree entries for the same reason.
_HFS_IGNORED = frozenset(
    "\u200c\u200d\u200e\u200f"
    "\u202a\u202b\u202c\u202d\u202e"
    "\u206a\u206b\u206c\u206d\u206e\u206f"
    "\ufeff"
)


def _names_the_git_directory(component: str) -> bool:
    """Whether a file system may resolve ``component`` to the repository's own ``.git`` (issue #135).

    Comparing with ``.git`` as a string is not enough: macOS and Windows file
    systems are case-insensitive by default, so ``.GIT/config`` opens
    ``.git/config``.  On NTFS, ``.git`` and its 8.3 short name ``git~1`` also
    answer with trailing dots or spaces (``git~1.``), and with an alternate
    data stream (``.git::$INDEX_ALLOCATION``); a backslash separates
    directories there.  HFS+ ignores some invisible code points.  The rule
    is Git's own, which refuses these as tree entries (``is_ntfs_dotgit`` and
    ``is_hfs_dotgit`` in ``path.c``/``utf8.c``, applied by ``verify_path``),
    so the outcome does not depend on the platform.
    """
    name = "".join(ch for ch in component if ch not in _HFS_IGNORED).casefold()
    for prefix in (".git", "git~1"):
        if name.startswith(prefix):
            # is_ntfs_dotgit: only dots and spaces may follow, up to the end of the
            # name, a directory separator or the ":" of a stream
            for ch in name[len(prefix):]:
                if ch in "\\:":
                    return True
                if ch not in ". ":
                    return False
            return True
    return False


def validate_repo_relative_path(relative: str) -> None:
    if not isinstance(relative, str) or not relative:
        raise PathValidationError("path must be a non-empty string")
    p = Path(relative)
    if p.is_absolute():
        raise PathValidationError("absolute paths are not allowed")
    if ".." in p.parts:
        raise PathValidationError("parent directory '..' is not allowed")
    if any(_names_the_git_directory(part) for part in p.parts):
        raise PathValidationError("paths under .git are not allowed (in any letter case or file-system spelling)")

def safe_join(root: Path, relative: str) -> Path:
    validate_repo_relative_path(relative)
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PathValidationError("path escapes repository root") from exc
    return resolved
