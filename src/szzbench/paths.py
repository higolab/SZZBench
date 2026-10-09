from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

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


# ``C:`` at the start of a path makes it absolute or drive-relative on Windows.
_DRIVE_PREFIX = re.compile(r"[A-Za-z]:")


def validate_repo_relative_path(relative: str) -> None:
    """Refuse a path that is not a repository-relative POSIX path (issues #135, #136).

    A scenario path has the form the manifest, ``commit-map.json`` and the
    generated READMEs use: names separated by ``/``, none of them empty (as
    in ``a//b`` or after a trailing ``/``), ``.``, ``..``, only whitespace or
    a spelling of ``.git``; no backslash, no drive prefix such as ``C:``, no
    control character.  The grammar is read from the string, not with
    ``pathlib.Path``, whose reading depends on the host: Windows splits a
    name at a backslash and takes ``C:`` for a drive, macOS and Linux keep
    both in one file name.  Such a path used to be accepted on one platform
    and refused on another, a NUL byte was accepted and ended generation in
    a traceback, and ``src/Dir/`` was written as the file ``src/Dir``.
    """
    if not isinstance(relative, str) or not relative:
        raise PathValidationError("path must be a non-empty string")
    for ch in relative:
        if ord(ch) < 0x20 or ord(ch) == 0x7F:
            raise PathValidationError(f"control character U+{ord(ch):04X} is not allowed")
    if PurePosixPath(relative).is_absolute():
        raise PathValidationError("absolute paths are not allowed")
    if _DRIVE_PREFIX.match(relative):
        raise PathValidationError(f"drive prefix '{relative[:2]}' is not allowed")
    parts = relative.split("/")
    if parts[-1] == "":
        raise PathValidationError("a trailing '/' is not allowed")
    if "" in parts:
        raise PathValidationError("an empty component ('//') is not allowed")
    if "." in parts:
        raise PathValidationError("current directory '.' is not allowed")
    if ".." in parts:
        raise PathValidationError("parent directory '..' is not allowed")
    if any(part.isspace() for part in parts):
        raise PathValidationError("a component of only whitespace is not allowed")
    if any(_names_the_git_directory(part) for part in parts):
        raise PathValidationError("paths under .git are not allowed (in any letter case or file-system spelling)")
    # last, so that a backslash after .git is reported as the .git path it is on Windows
    if "\\" in relative:
        raise PathValidationError("a backslash is not allowed; separate directories with '/'")

def safe_join(root: Path, relative: str) -> Path:
    validate_repo_relative_path(relative)
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PathValidationError("path escapes repository root") from exc
    return resolved
