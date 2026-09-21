from __future__ import annotations

from pathlib import Path

from .paths import safe_join

SUPPORTED_OPERATIONS = {"write_file", "replace"}
FUTURE_OPERATIONS = {"delete_file", "rename_file", "copy_file", "apply_patch", "format_file"}

LINE_ENDINGS = {"lf": "\n", "crlf": "\r\n"}

class OperationError(RuntimeError):
    pass

def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")

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

def writes_bom(op: dict) -> bool:
    """True when the operation's ``encoding`` makes Python emit a UTF-8 BOM."""
    encoding = op.get("encoding")
    return isinstance(encoding, str) and encoding.lower().replace("_", "-") == "utf-8-sig"

def apply_operation_to_memory(files: dict[str, str], op: dict) -> None:
    # The in-memory simulator always works on LF-normalized text; line_ending
    # only affects the bytes written to the generated repository.
    op_type = op.get("type")
    if op_type == "write_file":
        text = normalize_newlines(op["content"])
        # The BOM is the one encoding detail the simulator models: a utf-8-sig
        # write starts the text with U+FEFF, so a BOM-only re-save of a file is
        # a change here as it is in Git (otherwise it would be E250 "no changes").
        if writes_bom(op) and not text.startswith("\ufeff"):
            text = "\ufeff" + text
        files[op["path"]] = text
        return
    if op_type == "replace":
        path = op["path"]
        if path not in files:
            raise OperationError(f"replace target does not exist: {path}")
        old = normalize_newlines(op["old"])
        new = normalize_newlines(op["new"])
        files[path] = replace_once(files[path], old, new, op.get("occurrence"))
        return
    raise OperationError(f"unsupported operation: {op_type}")

def apply_operation_to_filesystem(repo_dir: Path, op: dict) -> None:
    op_type = op.get("type")
    if op_type == "write_file":
        path = safe_join(repo_dir, op["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        # encoding: utf-8 (default) | utf-8-sig (BOM) | any codec Python knows;
        # the in-memory simulator never sees it, only the bytes on disk do.
        encoding = op.get("encoding") or "utf-8"
        write_text_raw(path, encode_line_endings(op["content"], resolve_line_ending(op)), encoding)
        return
    if op_type == "replace":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"replace target does not exist: {op['path']}")
        encoding = op.get("encoding") or "utf-8"
        raw = read_text_raw(path, encoding)
        line_ending = resolve_line_ending(op, raw)
        content = normalize_newlines(raw)
        old = normalize_newlines(op["old"])
        new = normalize_newlines(op["new"])
        new_content = replace_once(content, old, new, op.get("occurrence"))
        write_text_raw(path, encode_line_endings(new_content, line_ending), encoding)
        return
    raise OperationError(f"unsupported operation: {op_type}")
