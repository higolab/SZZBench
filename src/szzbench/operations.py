from __future__ import annotations

import codecs
from pathlib import Path

from .paths import safe_join

SUPPORTED_OPERATIONS = {"write_file", "replace"}
FUTURE_OPERATIONS = {"delete_file", "rename_file", "copy_file", "apply_patch", "format_file"}

LINE_ENDINGS = {"lf": "\n", "crlf": "\r\n"}

class OperationError(RuntimeError):
    pass

def type_label(value: object) -> str:
    """The type of a YAML value as a message names it (``int``, ``null (a blank value)``)."""
    return "null (a blank value)" if value is None else type(value).__name__

def normalize_newlines(text: str) -> str:
    # A number or a YAML null used to escape from here as an AttributeError
    # traceback (issue #151).  The validators reject one first (E041 / GE053).
    if not isinstance(text, str):
        raise OperationError(f"expected text, not {type_label(text)}")
    return text.replace("\r\n", "\n").replace("\r", "\n")

def text_field(op: dict, key: str) -> str:
    """The text an operation writes or matches (``content``, ``old``, ``new``, ``anchor``).

    Anything but a string is an OperationError: the graph suite read the value
    through ``str()``, so a blank ``content:`` wrote the text ``None`` into the
    file (issue #151).
    """
    value = op.get(key)
    if not isinstance(value, str):
        what = "is missing" if key not in op else f"must be a string, not {type_label(value)}"
        raise OperationError(f"{op.get('type')}.{key} {what}")
    return value

def detect_crlf(content: str) -> bool:
    """Return True when every newline of ``content`` is CRLF (and there is one)."""
    crlf = content.count("\r\n")
    return crlf > 0 and crlf == content.count("\n")

def resolve_line_ending(op: dict, existing_content: str | None = None) -> str:
    """Return the newline sequence an operation must write.

    ``line_ending: lf|crlf`` wins.  Without the key, an existing CRLF file keeps
    CRLF (detected from its content); everything else is written with LF.
    """
    value = op.get("line_ending")
    if value is None:
        if existing_content is not None and detect_crlf(existing_content):
            return "\r\n"
        return "\n"
    if not isinstance(value, str) or value.lower() not in LINE_ENDINGS:
        raise OperationError(f"line_ending must be 'lf' or 'crlf', got {value!r}")
    return LINE_ENDINGS[value.lower()]

def encode_line_endings(text: str, line_ending: str) -> str:
    """Normalize ``text`` to LF and re-encode it with ``line_ending``."""
    normalized = normalize_newlines(text)
    if line_ending == "\n":
        return normalized
    return normalized.replace("\n", line_ending)

def read_text_raw(path: Path, encoding: str = "utf-8") -> str:
    """Read a text file without newline translation (CRLF stays CRLF)."""
    with path.open("r", encoding=encoding, newline="") as fh:
        return fh.read()

def write_text_raw(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write ``text`` exactly as given (no newline translation)."""
    with path.open("w", encoding=encoding, newline="") as fh:
        fh.write(text)

def find_all_occurrences(text: str, needle: str) -> list[int]:
    if needle == "":
        return []
    positions = []
    start = 0
    while True:
        pos = text.find(needle, start)
        if pos == -1:
            return positions
        positions.append(pos)
        start = pos + len(needle)

def replace_once(content: str, old: str, new: str, occurrence: int | None = None) -> str:
    positions = find_all_occurrences(content, old)
    if not positions:
        raise OperationError("replace.old not found")
    if len(positions) > 1 and occurrence is None:
        raise OperationError("replace.old is not unique; specify occurrence")
    if occurrence is None:
        occurrence = 1
    if not isinstance(occurrence, int) or occurrence < 1 or occurrence > len(positions):
        raise OperationError("replace.occurrence out of range")
    start = positions[occurrence - 1]
    end = start + len(old)
    return content[:start] + new + content[end:]

def insert_after_once(content: str, anchor: str, inserted: str, occurrence: int | None = None) -> str:
    positions = find_all_occurrences(content, anchor)
    if not positions:
        raise OperationError("insert_after.anchor not found")
    if len(positions) > 1 and occurrence is None:
        raise OperationError("insert_after.anchor is not unique; specify occurrence")
    if occurrence is None:
        occurrence = 1
    if not isinstance(occurrence, int) or occurrence < 1 or occurrence > len(positions):
        raise OperationError("insert_after.occurrence out of range")
    start = positions[occurrence - 1]
    end = start + len(anchor)
    return content[:end] + inserted + content[end:]

#: The codecs a classic operation may name.  They differ only in the BOM, and
#: the BOM is the one byte-level detail the in-memory simulator models.
ENCODINGS = {"utf-8", "utf-8-sig"}

def resolve_encoding(op: dict) -> str:
    """Return the codec an operation reads and writes with (``utf-8`` by default).

    Like ``line_ending`` the key is closed: ``utf-8`` or ``utf-8-sig`` in any
    spelling Python accepts, anything else an OperationError — so a scenario
    cannot depend on bytes the simulator does not model.
    """
    value = op.get("encoding")
    if value is None:
        return "utf-8"
    try:
        name = codecs.lookup(value).name if isinstance(value, str) else None
    except LookupError:
        name = None
    if name not in ENCODINGS:
        raise OperationError(f"encoding must be 'utf-8' or 'utf-8-sig', got {value!r}")
    return name

def decode_stored(stored: str, encoding: str) -> str:
    """What ``read_text_raw(path, encoding)`` returns for a simulated file.

    The simulator stores a file as its bytes decoded with UTF-8, so a BOM is a
    leading U+FEFF; ``utf-8-sig`` strips one on read and ``utf-8`` keeps it as
    text, exactly as the codecs behave on disk.
    """
    return stored.encode("utf-8").decode(encoding)

def encode_stored(text: str, encoding: str) -> str:
    """What ``write_text_raw(path, text, encoding)`` leaves on disk, as stored text."""
    return text.encode(encoding).decode("utf-8")

def apply_operation_to_memory(files: dict[str, str], op: dict) -> None:
    # The in-memory simulator works on LF-normalized text: line_ending only
    # affects the bytes written to the generated repository.  The encoding is
    # applied, because it changes the bytes without changing the text (the
    # BOM) and a scenario may be built on exactly that (SZZ-0206); otherwise a
    # BOM-only commit would be E250 "produces no changes" here and real in Git.
    op_type = op.get("type")
    if op_type == "write_file":
        files[op["path"]] = encode_stored(normalize_newlines(text_field(op, "content")), resolve_encoding(op))
        return
    if op_type == "replace":
        path = op["path"]
        if path not in files:
            raise OperationError(f"replace target does not exist: {path}")
        encoding = resolve_encoding(op)
        content = decode_stored(files[path], encoding)
        old = normalize_newlines(text_field(op, "old"))
        new = normalize_newlines(text_field(op, "new"))
        files[path] = encode_stored(replace_once(content, old, new, op.get("occurrence")), encoding)
        return
    raise OperationError(f"unsupported operation: {op_type}")

def apply_operation_to_filesystem(repo_dir: Path, op: dict) -> None:
    op_type = op.get("type")
    if op_type == "write_file":
        path = safe_join(repo_dir, op["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_raw(path, encode_line_endings(text_field(op, "content"), resolve_line_ending(op)), resolve_encoding(op))
        return
    if op_type == "replace":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"replace target does not exist: {op['path']}")
        encoding = resolve_encoding(op)
        raw = read_text_raw(path, encoding)
        line_ending = resolve_line_ending(op, raw)
        content = normalize_newlines(raw)
        old = normalize_newlines(text_field(op, "old"))
        new = normalize_newlines(text_field(op, "new"))
        new_content = replace_once(content, old, new, op.get("occurrence"))
        write_text_raw(path, encode_line_endings(new_content, line_ending), encoding)
        return
    raise OperationError(f"unsupported operation: {op_type}")
