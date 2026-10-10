from __future__ import annotations

import base64
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Iterator, NamedTuple

from .gitutils import MAX_GENERATED_COMMITS, commit_generator_count, commit_generator_files
from .operations import (
    OperationError,
    encode_line_endings,
    insert_after_once,
    normalize_newlines,
    read_text_raw,
    replace_once,
    resolve_line_ending,
    text_field,
    write_text_raw,
)
from .paths import PathValidationError, another_spelling_on_disk, safe_join, validate_repo_relative_path

SUPPORTED_GRAPH_OPERATIONS = {
    "write_file",
    "replace",
    "insert_after",
    "delete_file",
    "rename_file",
    "move_file",
    "copy_file",
    "move_entity",
    "copy_entity",
    "chmod",
    "write_binary_file",
    "write_generated_text_file",
    "commit_generator",
    "apply_squash",
    "apply_patch_from",
    "apply_patch",
    "format_file",
}

PATH_FIELDS_BY_OPERATION: dict[str, list[str]] = {
    "write_file": ["path"],
    "replace": ["path"],
    "insert_after": ["path"],
    "delete_file": ["path"],
    "rename_file": ["from", "to"],
    "move_file": ["from", "to"],
    "copy_file": ["from", "to"],
    "move_entity": ["from_file", "to_file"],
    "copy_entity": ["from_file", "to_file"],
    "chmod": ["path"],
    "write_binary_file": ["path"],
    "write_generated_text_file": ["path"],
    # reads and rewrites the file: its path is checked like the others (PR #234 review)
    "format_file": ["path"],
}

#: The fields that name the file an operation creates or rewrites, which ``git add -A``
#: then stages from the worktree: validation refuses one that is a file Git reads
#: (GE063), and the generator stops when Git does not stage one (issue #164).  The
#: files of ``commit_generator`` are named ``<generator>-NN.txt`` and written with
#: ``git fast-import``, past both.
WRITTEN_PATH_FIELDS_BY_OPERATION: dict[str, tuple[str, ...]] = {
    "write_file": ("path",),
    "replace": ("path",),
    "insert_after": ("path",),
    "write_binary_file": ("path",),
    "write_generated_text_file": ("path",),
    "format_file": ("path",),
    "rename_file": ("to",),
    "move_file": ("to",),
    "copy_file": ("to",),
    "move_entity": ("to_file",),
    "copy_entity": ("to_file",),
}

REQUIRED_FIELDS_BY_OPERATION: dict[str, list[str]] = {
    "write_file": ["path", "content"],
    "replace": ["path", "old", "new"],
    "insert_after": ["path", "anchor", "content"],
    "delete_file": ["path"],
    "rename_file": ["from", "to"],
    "move_file": ["from", "to"],
    "copy_file": ["from", "to"],
    "move_entity": ["entity", "from_file", "to_file"],
    "copy_entity": ["entity", "from_file", "to_file"],
    "chmod": ["path", "mode"],
    "write_binary_file": ["path", "content_base64"],
    "write_generated_text_file": ["path", "lines", "template"],
    "commit_generator": ["generator", "count"],
    "apply_squash": ["from_commits"],
    "apply_patch_from": ["commit"],
    "apply_patch": ["path", "patch"],
    "format_file": ["path"],
}


#: The whitespace a base64 value may carry (wrapped lines): ASCII only.
_BASE64_WHITESPACE = re.compile(r"[ \t\r\n\f\v]")


def decode_content_base64(value: Any) -> bytes:
    """The bytes of a ``write_binary_file`` ``content_base64``: one reading for validation,
    simulation and generation (issue #172, PR #214 review).

    ASCII whitespace is ignored, as wrapped lines need.  Any other character
    outside the base64 alphabet -- a non-ASCII one, or Unicode whitespace such as
    a no-break space, included -- is an error instead of being dropped, and so
    is wrong padding.  Raises ``ValueError`` (``binascii.Error`` is one).
    """
    if not isinstance(value, str):
        raise ValueError(f"content_base64 must be a string, not {type(value).__name__}")
    compact = _BASE64_WHITESPACE.sub("", value)
    if not compact.isascii():
        raise ValueError("content_base64 holds a character that is not ASCII")
    return base64.b64decode(compact, validate=True)


def apply_graph_operation_to_filesystem(repo_dir: Path, op: dict[str, Any]) -> None:
    """Apply one graph-scenario operation to a worktree.

    This is intentionally pragmatic. Entity operations are represented with a
    conservative file-level approximation until a parser-backed entity mover is
    implemented.

    A value the operation cannot use -- a ``mode`` that is not octal, a
    ``content_base64`` that does not decode, a file that is not text in the
    declared encoding, an unknown encoding -- used to escape as a ``ValueError``
    or ``LookupError``, and ``generate-graph`` printed a traceback and wrote no
    ``generation.log`` (issue #172).  It is now an ``OperationError`` that names
    the operation and its path, which the generator reports like its own errors.
    So is an ``OSError``: a write to a path that is a directory, or that lies
    below a file, reached the user as the bare OS message (issue #175).
    """
    try:
        _refuse_another_spelling(repo_dir, op)
        _apply_graph_operation(repo_dir, op)
    except PathValidationError:
        raise
    except (ValueError, LookupError) as exc:     # incl. UnicodeDecodeError, binascii.Error
        raise OperationError(f"{op.get('type')} {_operation_target(op)}: {_value_error_reason(op, exc)}") from exc
    except OSError as exc:                       # incl. IsADirectoryError, NotADirectoryError, shutil.SameFileError
        raise OperationError(f"{op.get('type')} {_operation_target(op)}: {_os_error_reason(repo_dir, exc)}") from exc


def _refuse_another_spelling(repo_dir: Path, op: dict[str, Any]) -> None:
    """Refuse a path of ``op`` that reaches an entry of the worktree spelt otherwise (issue #153).

    ``src/a.java`` written beside ``src/A.java`` overwrote it on macOS and was
    a second file on Linux, and a ``replace`` in ``src/a.java`` changed
    ``src/A.java`` on macOS and failed on Linux: the generated repository
    depended on the platform.  ``validate-graph --simulate`` refuses the same
    paths (``paths.file_path_conflict``), but ``generate-graph`` does not
    run it, and a scenario with commits Git computes is simulated by
    generating it.  A path that is not valid is left to ``safe_join``.
    """
    op_type = op.get("type")
    for key in PATH_FIELDS_BY_OPERATION.get(op_type, ()) if isinstance(op_type, str) else ():
        relative = op.get(key)
        try:
            validate_repo_relative_path(relative)
        except PathValidationError:
            continue
        found = another_spelling_on_disk(repo_dir, relative)
        if found is not None:
            mine, theirs = found
            raise OperationError(f"{op_type} {_operation_target(op)}: {mine!a} differs only in letter case or Unicode "
                                 f"normalization from {theirs!a}, which the worktree has: macOS (and Windows, for letter "
                                 "case) reads both as one name, so generation would depend on the platform")


def _operation_target(op: dict[str, Any]) -> str:
    keys = [key for key in ("path", "from", "to", "from_file", "to_file") if isinstance(op.get(key), str)]
    return " -> ".join(repr(op[key]) for key in keys) or "(no path)"


def _value_error_reason(op: dict[str, Any], exc: Exception) -> str:
    if isinstance(exc, UnicodeDecodeError):
        return (f"the file is not text in {op.get('encoding') or 'utf-8'} "
                f"(byte 0x{exc.object[exc.start]:02x} at position {exc.start})")
    if op.get("type") == "chmod":
        return (f"mode must be octal digits, got {op.get('mode')!r}; YAML reads an unquoted 0755 as the "
                f"integer 493, so quote it ('755')")
    if op.get("type") == "write_binary_file":
        return f"content_base64 does not decode ({exc})"
    return str(exc)


def _os_error_reason(repo_dir: Path, exc: OSError) -> str:
    """The OS's reason, with the file it names made relative to the repository."""
    if not exc.strerror:
        return str(exc)
    if not isinstance(exc.filename, str):
        return exc.strerror
    try:
        return f"{exc.strerror}: {Path(exc.filename).resolve().relative_to(repo_dir.resolve()).as_posix()}"
    except ValueError:
        return f"{exc.strerror}: {exc.filename}"


def _apply_graph_operation(repo_dir: Path, op: dict[str, Any]) -> None:
    op_type = op.get("type")

    if op_type == "write_file":
        path = safe_join(repo_dir, op["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        encoding = op.get("encoding") or "utf-8"
        # line_ending: lf (default) | crlf.  Text is normalized to LF first and
        # re-encoded, so YAML content may use either convention.
        write_text_raw(path, encode_line_endings(text_field(op, "content"), resolve_line_ending(op)), encoding)
        return

    if op_type == "replace":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"replace target does not exist: {op['path']}")
        encoding = op.get("encoding") or "utf-8"
        raw = read_text_raw(path, encoding)
        # Explicit line_ending wins; otherwise an existing CRLF file stays CRLF.
        line_ending = resolve_line_ending(op, raw)
        content = normalize_newlines(raw)
        old = normalize_newlines(text_field(op, "old"))
        new = normalize_newlines(text_field(op, "new"))
        write_text_raw(path, encode_line_endings(replace_once(content, old, new, op.get("occurrence")), line_ending), encoding)
        return

    if op_type == "insert_after":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"insert_after target does not exist: {op['path']}")
        encoding = op.get("encoding") or "utf-8"
        raw = read_text_raw(path, encoding)
        line_ending = resolve_line_ending(op, raw)
        content = normalize_newlines(raw)
        anchor = normalize_newlines(text_field(op, "anchor"))
        inserted = normalize_newlines(text_field(op, "content"))
        write_text_raw(path, encode_line_endings(insert_after_once(content, anchor, inserted, op.get("occurrence")), line_ending), encoding)
        return

    if op_type == "delete_file":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"delete target does not exist: {op['path']}")
        path.unlink()
        _remove_empty_parents(path.parent, repo_dir)
        return

    if op_type in {"rename_file", "move_file"}:
        src = safe_join(repo_dir, op["from"])
        dst = safe_join(repo_dir, op["to"])
        if not src.exists():
            raise OperationError(f"{op_type} source does not exist: {op['from']}")
        if dst.exists() and not op.get("overwrite", False):
            raise OperationError(f"{op_type} target already exists: {op['to']}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        _remove_empty_parents(src.parent, repo_dir)
        return

    if op_type == "copy_file":
        src = safe_join(repo_dir, op["from"])
        dst = safe_join(repo_dir, op["to"])
        if not src.exists():
            raise OperationError(f"copy source does not exist: {op['from']}")
        if dst.exists() and not op.get("overwrite", False):
            raise OperationError(f"copy target already exists: {op['to']}")
        if dst.is_dir():     # shutil.copy2 would copy into it (issue #175)
            raise OperationError(f"copy target is a directory: {op['to']}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return

    if op_type in {"move_entity", "copy_entity"}:
        src = safe_join(repo_dir, op["from_file"])
        dst = safe_join(repo_dir, op["to_file"])
        if not src.exists():
            raise OperationError(f"{op_type} source file does not exist: {op['from_file']}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        encoding = op.get("encoding") or "utf-8"
        content = read_text_raw(src, encoding)
        if dst.exists() and not op.get("overwrite", True):
            raise OperationError(f"{op_type} target file already exists: {op['to_file']}")
        header = _entity_operation_header(op_type, op)
        # An explicit line_ending wins, as on replace; otherwise the file written keeps the
        # line endings of the file it continues: an appended destination its own, any other
        # the source file's (issue #181).
        if dst.exists() and op.get("append", False):
            previous = read_text_raw(dst, encoding)
            text, continued = previous.rstrip() + "\n\n" + header + content, previous
        else:
            text, continued = header + content, content
        write_text_raw(dst, encode_line_endings(text, resolve_line_ending(op, continued)), encoding)
        if op_type == "move_entity" and op.get("remove_source_file", False):
            src.unlink()
            _remove_empty_parents(src.parent, repo_dir)
        return

    if op_type == "chmod":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"chmod target does not exist: {op['path']}")
        mode_raw = str(op["mode"])
        mode = int(mode_raw, 8)
        os.chmod(path, mode)
        return

    if op_type == "write_binary_file":
        path = safe_join(repo_dir, op["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(decode_content_base64(op["content_base64"]))
        return

    if op_type == "write_generated_text_file":
        path = safe_join(repo_dir, op["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = int(op["lines"])
        template = str(op["template"])
        body = "\n".join(_render_template_line(template, line_no) for line_no in range(1, lines + 1)) + "\n"
        # Optional header/footer wrap the generated lines (e.g. a Java class).
        content = _block_text(op.get("header")) + body + _block_text(op.get("footer"))
        path.write_text(content, encoding=op.get("encoding") or "utf-8", newline="\n")
        return

    if op_type == "commit_generator":
        raise OperationError("commit_generator must be handled by the graph generator, not the generic operation layer")

    if op_type == "format_file":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"format target does not exist: {op['path']}")
        encoding = op.get("encoding") or "utf-8"
        raw = read_text_raw(path, encoding)
        # Without line_ending only trailing whitespace changes: a CRLF file stays CRLF.
        # read_text used to turn every \r\n into \n, so the commit also rewrote each line
        # ending (issue #181).  An explicit line_ending converts the file, as on replace.
        formatted = "\n".join(line.rstrip() for line in normalize_newlines(raw).splitlines()) + "\n"
        write_text_raw(path, encode_line_endings(formatted, resolve_line_ending(op, raw)), encoding)
        return

    if op_type == "apply_patch":
        raise OperationError("apply_patch is recognized by the graph schema but is not implemented in this MVP")

    if op_type == "apply_squash":
        raise OperationError("apply_squash must be handled by the graph generator, not the generic operation layer")

    if op_type == "apply_patch_from":
        raise OperationError("apply_patch_from must be handled by the graph generator, not the generic operation layer")

    raise OperationError(f"unsupported graph operation: {op_type}")


def _render_template_line(template: str, line_no: int) -> str:
    return template.replace("${line}", str(line_no)).replace("{line}", str(line_no))


def _block_text(value: Any) -> str:
    """Normalize an optional header/footer block and make it end with a newline."""
    if value is None:
        return ""
    text = normalize_newlines(str(value))
    if text and not text.endswith("\n"):
        text += "\n"
    return text


DEFAULT_COMMIT_GENERATOR_DIRECTORY = "generated"
#: A file written by ``commit_generator`` keeps at most this many change lines, so
#: that blobs stay small even for thousands of generated commits (issue #18).
GENERATED_FILE_MAX_LINES = 50


def commit_generator_path(path: Any) -> str:
    """A ``commit_generator``'s ``path`` in the spelling generation reads it.

    Backslashes become ``/``; a trailing ``/`` and ``.`` or empty components
    are dropped; a missing or blank value is the default directory, and ``""``
    (``/`` written alone) the repository root.  The simulator of
    ``validate-graph --simulate`` reads the field here too, so that it does not
    refuse a spelling generation accepts (PR #219 review).
    """
    if path is None or str(path).strip() == "":
        return DEFAULT_COMMIT_GENERATOR_DIRECTORY
    text = str(path).strip().replace("\\", "/").rstrip("/")
    return PurePosixPath(text).as_posix() if text else ""


def commit_generator_directory(path: Any) -> str:
    """Return the directory generated files live in for a ``commit_generator``.

    ``path`` is a directory.  For backward compatibility a file-like value such
    as ``generated/unrelated-batch-1.txt`` (the old placeholder file) means its
    parent directory.  An empty string denotes the repository root.
    """
    text = commit_generator_path(path)
    candidate = PurePosixPath(text)
    if text and candidate.suffix:
        parent = candidate.parent.as_posix()
        return "" if parent == "." else parent
    return text


class CommitGeneratorPlan(NamedTuple):
    """One ``commit_generator`` operation as generation reads it."""
    generator: str
    directory: str      # "" is the repository root
    count: int          # ``requested`` capped at MAX_GENERATED_COMMITS
    files: int
    requested: int


def commit_generator_plan(op: dict[str, Any], owner_id: str) -> CommitGeneratorPlan:
    """Read a ``commit_generator`` operation of commit ``owner_id``.

    A ``count`` or ``files`` that generation cannot use is a ``ValueError`` that
    names the field and the commit.  The generator and the simulator of
    ``validate-graph --simulate`` both read the operation here (issue #175),
    and ``count`` and ``files`` are read as ``gitutils.planned_generated_commits``
    reads them for ``verify-graph`` (issue #230).
    """
    generator = str(op.get("generator") or "unrelated_changes")
    requested = commit_generator_count(op, owner_id)
    files = commit_generator_files(op, owner_id)
    return CommitGeneratorPlan(generator, commit_generator_directory(op.get("path")),
                               min(requested, MAX_GENERATED_COMMITS), files, requested)


def commit_generator_changes(plans: Iterable[CommitGeneratorPlan],
                             read_file: Callable[[str], str]) -> Iterator[tuple[str, str, str]]:
    """``(generator, path, content)`` for every commit the plans of one owner expand into, in order.

    Generated commit *k* of a plan appends ``<generator> change <sequence>`` to
    ``<directory>/<generator>-<NN>.txt``, ``NN = (k-1) mod files + 1``, where
    ``sequence`` counts the owner's generated commits over all its plans;
    ``content`` is the whole file after the commit, at most
    ``GENERATED_FILE_MAX_LINES`` lines.  ``read_file(path)`` gives a file's
    content before the first of them ("" when there is none): the generator
    reads the worktree, the simulator its snapshot, so that the two write the
    same files (issue #175).
    """
    contents: dict[str, str] = {}
    sequence = 0
    for plan in plans:
        for k in range(1, plan.count + 1):
            sequence += 1
            file_name = f"{plan.generator}-{(k - 1) % plan.files + 1:02d}.txt"
            path = f"{plan.directory}/{file_name}" if plan.directory else file_name
            if path not in contents:
                contents[path] = read_file(path)
            # The written line must not carry the generated commit id: a logical-id
            # prefix inside the repository is an answer cue (issue #8).
            contents[path] = _append_generated_line(contents[path], f"{plan.generator} change {sequence}")
            yield plan.generator, path, contents[path]


def _append_generated_line(content: str, line: str) -> str:
    lines = content.splitlines()
    lines.append(line)
    if len(lines) > GENERATED_FILE_MAX_LINES:
        lines = lines[-GENERATED_FILE_MAX_LINES:]
    return "\n".join(lines) + "\n"


def _entity_operation_header(op_type: str, op: dict[str, Any]) -> str:
    entity = op.get("entity", {})
    name = entity.get("name") or entity.get("signature") or "unknown"
    return f"// SZZBench {op_type}: {name}\n"


def _remove_empty_parents(path: Path, stop: Path) -> None:
    stop = stop.resolve()
    current = path.resolve()
    while current != stop:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
