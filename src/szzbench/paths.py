from __future__ import annotations

import os
import re
import unicodedata
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


def file_system_key(name: str) -> str:
    """``name`` as the file systems of macOS compare names: two names with one key are one file there.

    APFS and HFS+ ignore letter case and Unicode normalization (``café`` with a
    precomposed ``é`` and ``café`` with ``e`` and a combining accent are one
    file), and HFS+ ignores some invisible code points as well (#135).  The key
    is Unicode's canonical caseless match, NFD(casefold(NFD(name))), of the name
    without those code points; Windows, which ignores letter case only, is
    covered by it too (PR #231 review).  It is taken name by name, so the key of
    a path is the keys of its names joined by ``/``.  Ref names (issue #229) and
    file paths (issue #153) are compared by it.
    """
    visible = "".join(ch for ch in name if ch not in _HFS_IGNORED)
    return unicodedata.normalize("NFD", unicodedata.normalize("NFD", visible).casefold())


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


def another_spelling_on_disk(root: Path, relative: str) -> tuple[str, str] | None:
    """``(prefix of relative, entry of root)`` when ``relative`` reaches an entry spelt otherwise (issue #153).

    ``relative`` is walked name by name.  A name its directory does not hold as
    written, but holds in a spelling with the same :func:`file_system_key`
    (``a.java`` beside ``A.java``), is that entry on macOS (and on Windows, for
    letter case) and a new one on Linux, so what a write makes of it depends on
    the platform.  The two paths are given up to that name; None when every
    name is there as written, or is not there at all.
    """
    names = relative.split("/")
    directory = root
    for depth, name in enumerate(names):
        try:
            entries = os.listdir(directory)
        except OSError:                  # not there (yet), or a file: the write itself says so
            return None
        if name not in entries:
            key = file_system_key(name)
            other = next((entry for entry in sorted(entries) if file_system_key(entry) == key), None)
            if other is None:
                return None
            return "/".join(names[:depth + 1]), "/".join([*names[:depth], other])
        directory = directory / name
    return None
