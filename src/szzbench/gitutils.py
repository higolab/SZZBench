from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import hashlib
import os
import re
import subprocess


class GitError(RuntimeError):
    pass


def _git_env(extra_env: dict | None = None) -> dict:
    """Return an environment for Git subprocesses.

    On Windows, Python's default text encoding may be cp932. Git output can
    contain UTF-8 commit messages or paths, so run_git() decodes subprocess
    output explicitly as UTF-8. These environment values also encourage Git to
    produce UTF-8 output where supported.
    """
    git_env = os.environ.copy()
    git_env.setdefault("LANG", "C.UTF-8")
    git_env.setdefault("LC_ALL", "C.UTF-8")
    if extra_env:
        git_env.update(extra_env)
    return git_env


def run_git(repo_dir: Path, args: list[str], *, env: dict | None = None, capture: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            env=_git_env(env),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        detail = stderr or stdout
        raise GitError(f"git {' '.join(args)} failed: {detail}") from exc


def run_git_with_input(repo_dir: Path, args: list[str], data: bytes, *, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run Git with ``data`` on standard input, in binary mode.

    Binary mode matters for ``git fast-import`` streams: text mode would
    translate newlines on Windows and corrupt the byte counts of the stream.
    """
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_dir,
            env=_git_env(env),
            input=data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip() if exc.stderr else ""
        stdout = exc.stdout.decode("utf-8", errors="replace").strip() if exc.stdout else ""
        detail = stderr or stdout
        raise GitError(f"git {' '.join(args)} failed: {detail}") from exc


def init_repo(repo_dir: Path, branch: str) -> None:
    repo_dir.mkdir(parents=True, exist_ok=True)
    run_git(repo_dir, ["init"])
    run_git(repo_dir, ["branch", "-M", branch])
    run_git(repo_dir, ["config", "user.name", "SZZ Benchmark"])
    run_git(repo_dir, ["config", "user.email", "szz-benchmark@example.com"])
    run_git(repo_dir, ["config", "core.autocrlf", "false"])
    run_git(repo_dir, ["config", "core.filemode", "false"])
    run_git(repo_dir, ["config", "i18n.commitEncoding", "utf-8"])
    run_git(repo_dir, ["config", "i18n.logOutputEncoding", "utf-8"])


_AUTHOR_RE = re.compile(r"^\s*(?P<name>.*?)\s*<(?P<email>[^<>]+)>\s*$")


def parse_author(author: str | None) -> tuple[str, str]:
    if not author:
        return "SZZ Benchmark", "szz-benchmark@example.com"
    match = _AUTHOR_RE.match(author)
    if not match:
        return author, "szz-benchmark@example.com"
    return match.group("name"), match.group("email")


# ---------------------------------------------------------------------------
# Deterministic commit metadata (issue #9)
# ---------------------------------------------------------------------------

DEFAULT_BASE_DATE = "2024-01-01T10:00:00Z"

# Six plausible authors, rotated by a stable hash so that the author of a
# commit does not depend on its role.  The e-mail addresses intentionally do
# not collide with the explicit authors used by existing scenarios
# (alice@example.com, bob@example.com, ...).
DEFAULT_AUTHOR_POOL: tuple[str, ...] = (
    "Aiko Tanaka <aiko.tanaka@example.com>",
    "Bruno Fischer <bruno.fischer@example.com>",
    "Chen Wei <chen.wei@example.com>",
    "Dana Okafor <dana.okafor@example.com>",
    "Elena Rossi <elena.rossi@example.com>",
    "Farid Haddad <farid.haddad@example.com>",
)


def parse_timestamp(value: Any, *, field: str = "date") -> datetime:
    """Parse an ISO 8601 timestamp (``2024-01-01T10:00:00Z`` or with offset).

    YAML may already have turned an unquoted timestamp into a ``datetime``;
    such values are accepted as-is (naive values are treated as UTC).
    """
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise GitError(f"{field} must be an ISO 8601 timestamp string, got {value!r}")
    text = value.strip()
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise GitError(f"{field} is not a valid ISO 8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_timestamp(value: datetime) -> str:
    """Format a timestamp as ISO 8601 with ``Z`` for UTC (Git accepts this)."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    text = value.isoformat()
    if text.endswith("+00:00"):
        text = text[:-6] + "Z"
    return text


def timestamp_to_git_raw(value: str) -> str:
    """Convert an ISO 8601 timestamp to Git's raw ``<epoch> <+hhmm>`` form."""
    parsed = parse_timestamp(value)
    return f"{int(parsed.timestamp())} {parsed.strftime('%z')}"


def deterministic_date(base_date: Any, commit_index: int) -> str:
    """Return ``base_date + commit_index days`` (issue #9 default dates)."""
    base = parse_timestamp(base_date if base_date is not None else DEFAULT_BASE_DATE, field="repository.base_date")
    return format_timestamp(base + timedelta(days=commit_index))


def deterministic_author(scenario_id: str, key: Any) -> str:
    """Pick an author from the pool by a stable hash of (scenario id, key)."""
    digest = hashlib.sha1(f"{scenario_id}:{key}".encode("utf-8")).hexdigest()
    return DEFAULT_AUTHOR_POOL[int(digest, 16) % len(DEFAULT_AUTHOR_POOL)]


def json_safe_timestamp(value: Any) -> Any:
    """Return a JSON-serialisable form of a scenario timestamp value."""
    if isinstance(value, datetime):
        return format_timestamp(parse_timestamp(value))
    return value


def _as_timestamp_string(value: Any, *, field: str) -> str:
    if isinstance(value, datetime):
        return format_timestamp(parse_timestamp(value))
    if isinstance(value, str) and value.strip():
        return value
    raise GitError(f"{field} must be a non-empty ISO 8601 timestamp string, got {value!r}")


@dataclass
class CommitMetadata:
    """Effective author and dates for one generated commit."""

    author: str
    author_date: str
    committer_date: str
    author_is_default: bool = False
    author_date_is_default: bool = False
    committer_date_is_default: bool = False

    @property
    def author_name(self) -> str:
        return parse_author(self.author)[0]

    @property
    def author_email(self) -> str:
        return parse_author(self.author)[1]

    def git_env(self) -> dict[str, str]:
        name, email = parse_author(self.author)
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = name
        env["GIT_AUTHOR_EMAIL"] = email
        env["GIT_COMMITTER_NAME"] = name
        env["GIT_COMMITTER_EMAIL"] = email
        env["GIT_AUTHOR_DATE"] = self.author_date
        env["GIT_COMMITTER_DATE"] = self.committer_date
        return env

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "author_date": self.author_date,
            "committer_date": self.committer_date,
        }


def resolve_commit_metadata(scenario: dict[str, Any], commit_spec: dict[str, Any], commit_index: int) -> CommitMetadata:
    """Resolve the effective author/author_date/committer_date of a commit.

    Explicit values are preserved exactly.  ``author_date`` and
    ``committer_date`` fall back to ``date``; ``date`` falls back to a
    deterministic default (``repository.base_date`` or
    ``2024-01-01T10:00:00Z`` plus the commit index in days).  A missing
    ``author`` is taken from a fixed pool rotated by a stable hash of
    (scenario id, commit index), independent of the commit role.
    """
    repository = scenario.get("repository") if isinstance(scenario.get("repository"), dict) else {}
    meta = scenario.get("meta") if isinstance(scenario.get("meta"), dict) else {}
    scenario_id = str(meta.get("id") or repository.get("name") or "scenario")

    author = commit_spec.get("author")
    author_is_default = not (isinstance(author, str) and author.strip())
    if author_is_default:
        author = deterministic_author(scenario_id, commit_index)

    default_date: str | None = None

    def default() -> str:
        nonlocal default_date
        if default_date is None:
            default_date = deterministic_date(repository.get("base_date"), commit_index)
        return default_date

    date = commit_spec.get("date")
    date_value = _as_timestamp_string(date, field="date") if date is not None else None

    author_date = commit_spec.get("author_date")
    committer_date = commit_spec.get("committer_date")
    if author_date is not None:
        author_date_value = _as_timestamp_string(author_date, field="author_date")
        author_date_is_default = False
    elif date_value is not None:
        author_date_value = date_value
        author_date_is_default = False
    else:
        author_date_value = default()
        author_date_is_default = True
    if committer_date is not None:
        committer_date_value = _as_timestamp_string(committer_date, field="committer_date")
        committer_date_is_default = False
    elif date_value is not None:
        committer_date_value = date_value
        committer_date_is_default = False
    else:
        committer_date_value = default()
        committer_date_is_default = True

    return CommitMetadata(
        author=str(author),
        author_date=author_date_value,
        committer_date=committer_date_value,
        author_is_default=author_is_default,
        author_date_is_default=author_date_is_default,
        committer_date_is_default=committer_date_is_default,
    )


def commit_all(
    repo_dir: Path,
    *,
    message: str,
    author: str | None,
    date: str | None = None,
    author_date: str | None = None,
    committer_date: str | None = None,
    body: str | None = None,
) -> str:
    """Stage everything and commit.

    ``author_date``/``committer_date`` take precedence over ``date``; when none
    is given the commit gets the generation time (callers that want
    deterministic metadata pass values from :func:`resolve_commit_metadata`).
    """
    run_git(repo_dir, ["add", "-A"])
    status = run_git(repo_dir, ["status", "--porcelain"]).stdout.strip()
    if not status:
        raise GitError("commit would be empty")
    name, email = parse_author(author)
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = name
    env["GIT_AUTHOR_EMAIL"] = email
    env["GIT_COMMITTER_NAME"] = name
    env["GIT_COMMITTER_EMAIL"] = email
    effective_author_date = author_date or date
    effective_committer_date = committer_date or date
    if effective_author_date:
        env["GIT_AUTHOR_DATE"] = effective_author_date
    if effective_committer_date:
        env["GIT_COMMITTER_DATE"] = effective_committer_date
    args = ["commit", "-m", message]
    if body:
        args.extend(["-m", body])
    run_git(repo_dir, args, env=env)
    return run_git(repo_dir, ["rev-parse", "HEAD"]).stdout.strip()


def git_show(repo_dir: Path, revision: str, path: str) -> str:
    return run_git(repo_dir, ["show", f"{revision}:{path}"]).stdout


def git_message(repo_dir: Path, revision: str) -> str:
    return run_git(repo_dir, ["log", "-1", "--pretty=%s", revision]).stdout.strip()


def git_body(repo_dir: Path, revision: str) -> str:
    return run_git(repo_dir, ["log", "-1", "--pretty=%b", revision]).stdout


def git_author_date(repo_dir: Path, revision: str) -> str:
    return run_git(repo_dir, ["log", "-1", "--pretty=%aI", revision]).stdout.strip()


def git_unmerged_paths(repo_dir: Path) -> list[str]:
    """Return the paths with unmerged index entries (conflicts), sorted.

    ``-z`` makes Git emit the paths verbatim, NUL-separated, instead of the
    quoted/escaped display form it uses for non-ASCII or special characters,
    so the result can be compared with the keys of a ``resolution`` mapping.
    """
    out = run_git(repo_dir, ["diff", "--name-only", "--diff-filter=U", "-z"]).stdout
    return sorted({path for path in out.split("\0") if path})


def git_refs(repo_dir: Path) -> dict[str, dict[str, str]]:
    """Return ``{"branches": {name: hash}, "tags": {name: hash}}``."""
    out = run_git(repo_dir, ["for-each-ref", "--format=%(refname) %(objectname)"]).stdout
    refs: dict[str, dict[str, str]] = {"branches": {}, "tags": {}}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        refname, object_name = parts
        if refname.startswith("refs/heads/"):
            refs["branches"][refname[len("refs/heads/"):]] = object_name
        elif refname.startswith("refs/tags/"):
            refs["tags"][refname[len("refs/tags/"):]] = object_name
    return refs


def git_parent(repo_dir: Path, revision: str) -> str | None:
    try:
        return run_git(repo_dir, ["rev-parse", f"{revision}^"]).stdout.strip()
    except GitError:
        return None


def git_hash_exists(repo_dir: Path, revision: str) -> bool:
    try:
        run_git(repo_dir, ["cat-file", "-e", f"{revision}^{{commit}}"])
        return True
    except GitError:
        return False


def git_blame_line(repo_dir: Path, revision: str, path: str, line_number: int) -> str:
    out = run_git(repo_dir, ["blame", "--porcelain", "-L", f"{line_number},{line_number}", revision, "--", path]).stdout.strip()
    if not out:
        return ""
    return out.splitlines()[0].split()[0].lstrip("^")
