from __future__ import annotations

from pathlib import Path

class PathValidationError(ValueError):
    pass

def validate_repo_relative_path(relative: str) -> None:
    if not isinstance(relative, str) or not relative:
        raise PathValidationError("path must be a non-empty string")
    p = Path(relative)
    if p.is_absolute():
        raise PathValidationError("absolute paths are not allowed")
    if ".." in p.parts:
        raise PathValidationError("parent directory '..' is not allowed")
    if ".git" in p.parts:
        raise PathValidationError("paths under .git are not allowed")

def safe_join(root: Path, relative: str) -> Path:
    validate_repo_relative_path(relative)
    resolved_root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise PathValidationError("path escapes repository root") from exc
    return resolved
