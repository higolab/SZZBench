from __future__ import annotations

import base64
import os
import shutil
from pathlib import Path
from typing import Any

from .operations import OperationError, insert_after_once, normalize_newlines, replace_once
from .paths import safe_join

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


def apply_graph_operation_to_filesystem(repo_dir: Path, op: dict[str, Any]) -> None:
    """Apply one graph-scenario operation to a worktree.

    This is intentionally pragmatic. Entity operations are represented with a
    conservative file-level approximation until a parser-backed entity mover is
    implemented.
    """
    op_type = op.get("type")

    if op_type == "write_file":
        path = safe_join(repo_dir, op["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        encoding = op.get("encoding") or "utf-8"
        path.write_text(normalize_newlines(str(op["content"])), encoding=encoding, newline="\n")
        return

    if op_type == "replace":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"replace target does not exist: {op['path']}")
        encoding = op.get("encoding") or "utf-8"
        content = path.read_text(encoding=encoding)
        old = normalize_newlines(str(op["old"]))
        new = normalize_newlines(str(op["new"]))
        path.write_text(replace_once(content, old, new, op.get("occurrence")), encoding=encoding, newline="\n")
        return

    if op_type == "insert_after":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"insert_after target does not exist: {op['path']}")
        encoding = op.get("encoding") or "utf-8"
        content = path.read_text(encoding=encoding)
        anchor = normalize_newlines(str(op["anchor"]))
        inserted = normalize_newlines(str(op["content"]))
        path.write_text(insert_after_once(content, anchor, inserted, op.get("occurrence")), encoding=encoding, newline="\n")
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
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return

    if op_type in {"move_entity", "copy_entity"}:
        src = safe_join(repo_dir, op["from_file"])
        dst = safe_join(repo_dir, op["to_file"])
        if not src.exists():
            raise OperationError(f"{op_type} source file does not exist: {op['from_file']}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        content = src.read_text(encoding=op.get("encoding") or "utf-8")
        if dst.exists() and not op.get("overwrite", True):
            raise OperationError(f"{op_type} target file already exists: {op['to_file']}")
        header = _entity_operation_header(op_type, op)
        if dst.exists() and op.get("append", False):
            previous = dst.read_text(encoding=op.get("encoding") or "utf-8")
            dst.write_text(previous.rstrip() + "\n\n" + header + content, encoding=op.get("encoding") or "utf-8", newline="\n")
        else:
            dst.write_text(header + content, encoding=op.get("encoding") or "utf-8", newline="\n")
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
        path.write_bytes(base64.b64decode(str(op["content_base64"])))
        return

    if op_type == "write_generated_text_file":
        path = safe_join(repo_dir, op["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = int(op["lines"])
        template = str(op["template"])
        content = "\n".join(_render_template_line(template, line_no) for line_no in range(1, lines + 1)) + "\n"
        path.write_text(content, encoding=op.get("encoding") or "utf-8", newline="\n")
        return

    if op_type == "commit_generator":
        # Placeholder materialization for scalability scenarios. A future graph
        # generator may expand this into many real commits. For now it records
        # the intended generator in the repository so the logical commit is not empty.
        path = safe_join(repo_dir, op.get("path", "generated/unrelated-changes.txt"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"generator={op.get('generator')}\ncount={op.get('count')}\nfiles={op.get('files', '')}\n",
            encoding="utf-8",
            newline="\n",
        )
        return

    if op_type == "format_file":
        path = safe_join(repo_dir, op["path"])
        if not path.exists():
            raise OperationError(f"format target does not exist: {op['path']}")
        content = path.read_text(encoding=op.get("encoding") or "utf-8")
        formatted = "\n".join(line.rstrip() for line in content.splitlines()) + "\n"
        path.write_text(formatted, encoding=op.get("encoding") or "utf-8", newline="\n")
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
