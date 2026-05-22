from __future__ import annotations

from pathlib import Path

from .paths import safe_join

SUPPORTED_OPERATIONS = {"write_file", "replace"}
FUTURE_OPERATIONS = {"delete_file", "rename_file", "copy_file", "apply_patch", "format_file"}

class OperationError(RuntimeError):
    pass

def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")

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

def apply_operation_to_memory(files: dict[str, str], op: dict) -> None:
    op_type = op.get("type")
    if op_type == "write_file":
        files[op["path"]] = normalize_newlines(op["content"])
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
        path.write_text(normalize_newlines(op["content"]), encoding="utf-8", newline="\n")
        return
    if op_type == "replace":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"replace target does not exist: {op['path']}")
        content = path.read_text(encoding="utf-8")
        old = normalize_newlines(op["old"])
        new = normalize_newlines(op["new"])
        new_content = replace_once(content, old, new, op.get("occurrence"))
        path.write_text(new_content, encoding="utf-8", newline="\n")
        return
    raise OperationError(f"unsupported operation: {op_type}")
