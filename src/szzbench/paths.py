from __future__ import annotations

import os
from collections.abc import Collection
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


#: The characters Git refuses anywhere in a ref name, besides the control
#: characters (refs.c ``refname_disposition``; ``*`` only outside refspec patterns).
_REF_NAME_FORBIDDEN = {" ": "a space", "~": "'~'", "^": "'^'", ":": "':'", "?": "'?'", "*": "'*'", "[": "'['",
                       "\\": "a backslash", "\x7f": "the control character DEL"}

#: The refs the generators create by name: branches (``git branch -M``, ``git checkout -B``,
#: ``git checkout``) and the tags of ``graph.ref_lifecycle`` (``git tag``).
REF_KINDS = ("branch", "tag")

#: The longest file name the file systems take: 255 bytes of UTF-8 (Linux), 255 UTF-16 code units of the
#: name as written (APFS) or of its decomposed form (HFS+).  Git stores a ref as a file, each component of
#: its name a file name, and writes the ref through a lock file named as the last component and ``.lock``.
FILE_NAME_MAX = 255
_LOCK_SUFFIX = ".lock"
_FILE_NAME_UNITS = "bytes in UTF-8 on Linux, UTF-16 code units on macOS, of the decomposed form on HFS+"


def _file_name_length(component: str) -> tuple[int, str]:
    """The length of ``component`` as the strictest file system counts it, and the unit (PR #243 review).

    Linux counts the bytes of UTF-8; APFS counts the UTF-16 code units of the
    name as written, never more than those bytes; HFS+ counts the UTF-16 code
    units of the decomposed form (NFD), more than the bytes for a character
    such as U+01D5 (two bytes, three code points once decomposed).
    """
    utf8 = len(component.encode("utf-8"))
    hfs = len(unicodedata.normalize("NFD", component).encode("utf-16-le")) // 2
    if hfs > utf8:
        return hfs, "UTF-16 code units in its decomposed form, as HFS+ counts them"
    return utf8, "bytes in UTF-8"


def ref_name_problem(name: str, kind: str) -> str | None:
    """Why the generators cannot create the ``kind`` ref ``name`` as written, or None (issues #229, #239).

    ``kind`` is ``"branch"`` (``refs/heads/<name>``) or ``"tag"``
    (``refs/tags/<name>``).  The rules are those of ``git check-ref-format``
    (refs.c ``check_refname_format``), and what Git's commands and the file
    systems of macOS add to them:

    - a name that starts with ``-``, which ``git branch`` and ``git tag`` read
      as an option (``git check-ref-format --branch`` refuses it too);
    - ``HEAD``, which Git refuses as a branch, and Git 2.50 as a tag (Git 2.39
      accepts that one);
    - ``HEAD`` in another letter case (``head``), which Git accepts: macOS
      (and Windows) stores it in the file of ``refs/heads/HEAD`` or
      ``refs/tags/HEAD``, and Git then finds the name ``HEAD`` ambiguous, so
      ``git checkout -b`` fails (``fatal: ambiguous object name: 'HEAD'``);
    - a component that ends with ``.lock`` in another spelling (``v1.LOCK``),
      which is the lock file of another ref there (PR #231 review);
    - a name not in Unicode normalization form C: Git on macOS converts the
      names it is given to NFC (``core.precomposeUnicode``, which ``git init``
      sets there), so ``cafe`` with a combining accent became ``café`` with a
      precomposed ``é`` there and stayed as written elsewhere;
    - for a branch, ``@``: Git 2.50 reads ``git checkout @`` as ``HEAD`` and
      stays on the current branch, which the generator then reset to the
      branch's commit (Git 2.39 switches to the branch);
    - a whitespace character other than the ASCII space Git refuses
      (U+00A0 and the other spaces of Unicode): Git creates the ref, and
      SZZBench reads the refs and ``HEAD`` back from Git's output split and
      stripped at whitespace, so verification failed (PR #243 review);
    - a component longer than a file name may be (:data:`FILE_NAME_MAX`,
      counted by :func:`_file_name_length`), the last one less the
      ``.lock`` of its lock file: Git failed with ``cannot lock ref`` after
      ``git init`` (PR #243 review).

    A test compares the rule with ``git check-ref-format`` on about a hundred
    names, under Git 2.39 and 2.50.
    """
    if kind not in REF_KINDS:
        raise ValueError(f"unknown ref kind {kind!r}")
    if name == "":
        return "it is empty"
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return "it is not valid UTF-8"
    if name.startswith("-"):
        return f"it starts with '-', which git {kind} reads as an option"
    if name == "HEAD":
        return "it is HEAD, which Git refuses as a branch name" if kind == "branch" else \
            "it is HEAD, which recent versions of git tag refuse"
    for char in name:
        if char in _REF_NAME_FORBIDDEN:
            return f"it contains {_REF_NAME_FORBIDDEN[char]}"
        if ord(char) < 0x20:
            return f"it contains the control character {char!r}"
        if char.isspace():
            # Git accepts U+00A0, U+2028 and the like; git_refs splits Git's list of refs at whitespace and
            # HEAD is read stripped, so my\u00a0topic was generated and failed verification (PR #243 review)
            return (f"it contains the whitespace character U+{ord(char):04X} {unicodedata.name(char, '')}".rstrip()
                    + ", which Git accepts and SZZBench cannot read back from Git's list of refs "
                      "(Git refuses the ASCII space)")
    if ".." in name:
        return "it contains '..'"
    if "@{" in name:
        return "it contains '@{'"
    components = name.split("/")
    if "" in components:
        return "it has an empty component (a '/' at its start or end, or '//')"
    for component in components:
        if component.startswith("."):
            return f"its component '{component}' starts with '.'"
        if component.endswith(".lock"):
            return f"its component '{component}' ends with '.lock'"
        if file_system_key(component).endswith(".lock"):
            # Git accepts v1.LOCK, but on macOS and Windows its file is v1's lock file, so a
            # later tag v1 fails with Git's "File exists" after the first one was created (PR #231 review)
            return (f"its component '{component}' ends with '.lock' in another spelling, which a file system that "
                    "ignores letter case or Unicode normalization (macOS; Windows ignores case) reads as Git's lock file")
    for index, component in enumerate(components):
        # Git accepts a component of any length: "a" * 251 failed with "cannot lock ref" (File name too long)
        # after git init, since the lock file a.....a.lock is longer than a file name may be (PR #243 review)
        length, unit = _file_name_length(component)
        which = "it is" if len(components) == 1 else (
            "its last component is" if index == len(components) - 1 else f"its component {index + 1} is")
        if index == len(components) - 1 and length > FILE_NAME_MAX - len(_LOCK_SUFFIX):
            return (f"{which} too long for a file name: {length} {unit}, and Git writes the {kind} through a lock "
                    f"file named as it and '{_LOCK_SUFFIX}'. A file name takes at most {FILE_NAME_MAX} "
                    f"({_FILE_NAME_UNITS}), so the last component takes at most {FILE_NAME_MAX - len(_LOCK_SUFFIX)}")
        if length > FILE_NAME_MAX:
            return (f"{which} too long for a file name: {length} {unit}, and Git stores it as a directory, whose "
                    f"name takes at most {FILE_NAME_MAX} ({_FILE_NAME_UNITS})")
    if name.endswith("."):
        return "it ends with '.'"
    precomposed = unicodedata.normalize("NFC", name)
    if precomposed != name:
        # Git on macOS (core.precomposeUnicode, which git init sets there) converts the name
        # in its arguments to NFC: cafe + U+0301 became the branch caf\u00e9 (issue #239)
        return (f"it is not in Unicode normalization form C (NFC): Git on macOS creates the {kind} {precomposed!a} "
                "instead, and Git elsewhere the name as written")
    if file_system_key(name) == file_system_key("HEAD"):
        return (f"it is HEAD in another letter case, which a file system that ignores letter case (macOS, Windows) "
                f"stores as the {kind} HEAD: Git then finds the name HEAD ambiguous, and git checkout -b fails")
    if kind == "branch" and name == "@":
        return "it is '@', which recent versions of git checkout read as HEAD instead of the branch"
    return None


def ref_names_clash(name: str, other: str) -> str | None:
    """How two refs of one kind, named ``name`` and ``other``, clash in the files Git stores them in, or None (issues #229, #239).

    ``"spelling"``: the names differ only in what the file systems of macOS
    ignore (:func:`file_system_key`: letter case, Unicode normalization), so
    macOS (and Windows, for letter case) stores both as one file.
    ``"directory"``: one name is a leading path of the other, compared the same
    way (``feature`` and ``feature/x``): Git stores a ref as a file, and the
    one would be a directory of the other.  Equal names are one ref: None.
    """
    if name == other:
        return None
    key, other_key = file_system_key(name), file_system_key(other)
    if key == other_key:
        return "spelling"
    if key.startswith(other_key + "/") or other_key.startswith(key + "/"):
        return "directory"
    return None


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


def file_path_conflict(path: str, files: Collection[str]) -> str | None:
    """Why a worktree with the files ``files`` cannot take a file at ``path``, or None (issues #153, #175; the generator asks it too, PR #234 review).

    Both simulators keep a snapshot as a flat dict of paths, which has no
    directories and compares names as strings.  Generation writes to a file
    system.  There ``path`` cannot lie below a file or be a directory:
    generation stopped with ``File exists`` or ``Is a directory`` where the
    classic simulator saw one more file (the graph simulator has refused both
    since issue #175).  And macOS (Windows, for letter case) reads two names
    with one ``file_system_key`` as one: ``src/a.java`` overwrote
    ``src/A.java`` there and was a second file on Linux, where both simulators
    saw a second file.  Names are compared one by one, so ``src/foo/B.java``
    beside ``src/Foo/A.java`` is refused as well.  Writing a file of ``files``
    again, spelt as it is there, is no conflict.  The message starts with
    ``target``; the caller names the operation before it.
    """
    if path in files:
        return None
    names = path.split("/")
    keys = [file_system_key(name) for name in names]
    for other in files:
        other_names = other.split("/")
        depth = 0
        while depth < min(len(names), len(other_names)) and file_system_key(other_names[depth]) == keys[depth]:
            if other_names[depth] != names[depth]:
                mine, theirs = "/".join(names[:depth + 1]), "/".join(other_names[:depth + 1])
                kind = "file" if depth + 1 == len(other_names) else "directory"
                # two normalizations of a name look alike: spell them out
                spelt = "" if (mine + theirs).isascii() else f" (spelt {mine!a} and {theirs!a})"
                target = path if mine == path else f"{path}: its directory {mine}"
                return (f"target {target} differs only in letter case or Unicode normalization from the {kind} "
                        f"{theirs}{spelt}: macOS (and Windows, for letter case) reads both as one name, so "
                        "generation would depend on the platform")
            depth += 1
        if depth == len(other_names):
            return f"target lies below the file {other}: {path}"
        if depth == len(names):
            return f"target is a directory: {path}"
    return None
