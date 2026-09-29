from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import atexit
import hashlib
import os
import re
import shutil
import subprocess
import tempfile


class GitError(RuntimeError):
    pass


#: Variables withheld from every Git subprocess (issue #96).  The first group is
#: what ``git rev-parse --local-env-vars`` lists: with ``GIT_DIR`` set, for
#: example, every commit of a generation went into the repository it named.
#: Then the configuration sources a caller can point elsewhere, the init
#: template and the attribute source, and the identity and dates the
#: generators always pass themselves.
ISOLATED_GIT_ENV = frozenset({
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
    "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE", "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE",
    "GIT_COMMON_DIR",
    "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_TEMPLATE_DIR", "GIT_ATTR_SOURCE",
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE",
})
#: ``GIT_CONFIG_KEY_<n>`` / ``GIT_CONFIG_VALUE_<n>``, the pairs ``GIT_CONFIG_COUNT`` counts.
ISOLATED_GIT_ENV_PREFIXES = ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")

_empty_home: Path | None = None


def _isolated_home() -> str:
    """An empty directory that stands in for ``HOME`` and ``XDG_CONFIG_HOME``.

    With it neither the global configuration (``~/.gitconfig``,
    ``$XDG_CONFIG_HOME/git/config``) nor the files Git reads without any
    configuration (``$XDG_CONFIG_HOME/git/ignore`` and ``.../attributes``)
    exist, on every Git version -- ``GIT_CONFIG_GLOBAL`` (Git 2.32) would
    cover only the configuration file.
    """
    global _empty_home
    if _empty_home is None or not _empty_home.is_dir():
        _empty_home = Path(tempfile.mkdtemp(prefix="szzbench-git-home-"))
        atexit.register(shutil.rmtree, _empty_home, True)
    return str(_empty_home)


def _git_env(extra_env: dict | None = None) -> dict:
    """Return an environment for Git subprocesses.

    Git runs isolated from the caller's Git setup (issue #96): the system and
    global configuration, configuration injected through the environment, the
    default ignore and attributes files, the init template, and the variables
    that point Git at another repository are all withheld, so what SZZBench
    generates and measures depends on the scenario and the Git version only --
    not on a developer's signing setup, hooks, global ignores or filters.
    ``extra_env`` holds only what a caller sets on purpose (commit identity and
    dates) and is applied last.

    On Windows, Python's default text encoding may be cp932. Git output can
    contain UTF-8 commit messages or paths, so run_git() decodes subprocess
    output explicitly as UTF-8. These environment values also encourage Git to
    produce UTF-8 output where supported.
    """
    git_env = {key: value for key, value in os.environ.items()
               if key not in ISOLATED_GIT_ENV and not key.startswith(ISOLATED_GIT_ENV_PREFIXES)}
    home = _isolated_home()
    git_env["HOME"] = home
    git_env["XDG_CONFIG_HOME"] = home
    git_env["GIT_CONFIG_NOSYSTEM"] = "1"
    git_env["GIT_ATTR_NOSYSTEM"] = "1"
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
    # an empty --template copies no hooks, whatever the installation ships
    run_git(repo_dir, ["init", "--template="])
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
def canonical_author(author: str | None) -> str:
    """The identity Git records for ``author``: ``name <email>`` as the generator writes it
    (``parse_author`` supplies the benchmark's default e-mail when none is given), so that two
    spellings of one identity (``A <a@x>``, ``A<a@x>``, `` A <a@x> ``) compare equal."""
    name, email = parse_author(author)
    return f"{name.strip()} <{email.strip()}>"     # git strips the ident's surrounding whitespace


#: Upper bound on the commits one ``commit_generator`` operation may expand into.
MAX_GENERATED_COMMITS = 2000


def planned_generated_commits(owner_id: str, commit_spec: dict[str, Any]) -> list[str]:
    """The ``<owner>.g<N>`` ids the generator will create for ``commit_spec``'s
    ``commit_generator`` operations, in order and with the count cap applied.
    A count the generator would reject is skipped here; it is reported there."""
    total = 0
    for op in commit_spec.get("operations") or []:
        if not isinstance(op, dict) or op.get("type") != "commit_generator":
            continue
        try:
            requested = int(op.get("count"))
        except (TypeError, ValueError):
            continue
        total += min(max(requested, 0), MAX_GENERATED_COMMITS)
    return [f"{owner_id}.g{n}" for n in range(1, total + 1)]


def history_graph(scenario: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """The scenario's commits and the parents of every commit the generated repository will
    contain, generated commits included.

    ``commit_generator`` commits are linear ancestors inserted between the owner's first parent
    and the owner: ``parent <- g1 <- ... <- gN <- owner``; the owner's other parents (a merge)
    are unchanged.  That is how ``_expand_commit_generators`` writes them.
    """
    commits = [c for c in (scenario.get("commits") or []) if isinstance(c, dict) and isinstance(c.get("id"), str)]
    parents_of: dict[str, list[str]] = {}
    for commit in commits:
        declared = [p for p in (commit.get("parents") or []) if isinstance(p, str)]
        generated = planned_generated_commits(commit["id"], commit)
        if not generated:
            parents_of[commit["id"]] = declared
            continue
        previous = declared[:1]
        for generated_id in generated:
            parents_of[generated_id] = previous
            previous = [generated_id]
        parents_of[commit["id"]] = previous + declared[1:]
    return commits, parents_of


def reachable_commit_ids(scenario: dict[str, Any]) -> set[str]:
    """The commits (generated ones included) still reachable from a ref once the generator has
    finished.

    Mirrors what ``git log --all`` sees in the generated repository: every branch points at the
    last commit declared on it, ``graph.ref_lifecycle.delete_branches`` removes those refs,
    ``graph.ref_lifecycle.tags`` adds refs at named commits — a generated ``<owner>.g<N>`` may be
    tagged, and then it and its ancestors stay visible while later generated commits and the
    owner may not — and HEAD stays on the last commit's branch or, when that branch is deleted,
    moves to the default branch if it survives and otherwise detaches at that commit.  Ancestry
    follows ``parents`` through the generated chains (``history_graph``).  A history without
    ``parents`` (the classic suite) is linear and entirely reachable.
    """
    commits, parents_of = history_graph(scenario)
    if not commits or not any("parents" in c for c in commits):
        return set(parents_of)
    repository = scenario.get("repository") if isinstance(scenario.get("repository"), dict) else {}
    default_branch = str(repository.get("default_branch") or "main")
    tips: dict[str, str] = {}
    for c in commits:
        tips[str(c.get("branch") or default_branch)] = c["id"]       # the latest commit on a branch is its tip
    graph = scenario.get("graph") if isinstance(scenario.get("graph"), dict) else {}
    lifecycle = graph.get("ref_lifecycle") if isinstance(graph.get("ref_lifecycle"), dict) else {}
    deleted = {n for n in (lifecycle.get("delete_branches") or []) if isinstance(n, str)}
    roots = {tip for branch, tip in tips.items() if branch not in deleted}
    for tag in lifecycle.get("tags") or []:
        if isinstance(tag, dict) and isinstance(tag.get("commit"), str):
            roots.add(tag["commit"])
    last = commits[-1]
    if str(last.get("branch") or default_branch) in deleted and (default_branch in deleted or default_branch not in tips):
        roots.add(last["id"])                                          # HEAD detaches at the commit it was on
    reachable: set[str] = set()
    stack = [r for r in roots if r in parents_of]
    while stack:
        cid = stack.pop()
        if cid in reachable:
            continue
        reachable.add(cid)
        stack.extend(p for p in parents_of.get(cid, []) if p in parents_of)
    return reachable


def resolved_commit_authors(scenario: dict[str, Any]) -> list[tuple[str, str]]:
    """``(commit id, canonical author)`` for every commit the generated repository will contain.

    This is the history model a metadata rule sees: the scenario's own commits with their explicit
    or deterministic default author (``resolve_commit_metadata``), each followed by the commits its
    ``commit_generator`` operations expand into, which the generator attributes with
    ``deterministic_author(scenario id, generated id)``; every commit — generated ones on their
    own account — only if a ref still reaches it once the ref lifecycle has run
    (``reachable_commit_ids``), as ``git log --all`` leaves the others out.  Any check that
    reasons about "the commits written by X" must use this list, not ``scenario['commits']`` alone.
    """
    meta = scenario.get("meta") if isinstance(scenario.get("meta"), dict) else {}
    repository = scenario.get("repository") if isinstance(scenario.get("repository"), dict) else {}
    scenario_id = str(meta.get("id") or repository.get("name") or "scenario")
    reachable = reachable_commit_ids(scenario)
    rows: list[tuple[str, str]] = []
    for index, commit in enumerate(scenario.get("commits") or []):
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        for generated_id in planned_generated_commits(commit["id"], commit):     # ancestors come first
            if generated_id in reachable:
                rows.append((generated_id, canonical_author(deterministic_author(scenario_id, generated_id))))
        if commit["id"] in reachable:
            rows.append((commit["id"], canonical_author(resolve_commit_metadata(scenario, commit, index).author)))
    return rows



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


def _stable_hash(*parts: Any) -> int:
    return int(hashlib.sha1(":".join(str(p) for p in parts).encode("utf-8")).hexdigest(), 16)


#: Window the per-scenario default base date is spread over (issue #9).  It
#: starts on a Monday so that the first commit of a scenario is a weekday.
DEFAULT_BASE_WINDOW_START = "2023-01-09T09:00:00Z"
DEFAULT_BASE_WINDOW_DAYS = 890


def default_base_date(scenario_id: str) -> str:
    """A per-scenario base date, so repositories do not all start on one day."""
    start = parse_timestamp(DEFAULT_BASE_WINDOW_START, field="base window")
    day = start + timedelta(days=_stable_hash(scenario_id, "base") % DEFAULT_BASE_WINDOW_DAYS)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return format_timestamp(day)


def deterministic_date(base_date: Any, commit_index: int, scenario_id: str | None = None) -> str:
    """Default date of commit ``commit_index`` (issue #9).

    Without a ``scenario_id`` the historical behaviour is kept:
    ``base_date + commit_index`` days.  With one, the commits of a scenario
    are spread over irregular gaps of one to nine weekdays at working-hour
    times, all derived from a stable hash of the scenario id, so that dates
    remain deterministic across regeneration while no longer being a ramp
    that every scenario shares.  Dates are strictly increasing in
    ``commit_index``, so a commit is always newer than its parents.
    """
    if base_date is None and scenario_id is not None:
        base_date = default_base_date(scenario_id)
    base = parse_timestamp(base_date if base_date is not None else DEFAULT_BASE_DATE, field="repository.base_date")
    if scenario_id is None:
        return format_timestamp(base + timedelta(days=commit_index))
    if commit_index == 0:
        # The first commit sits exactly on the base date, so an explicit
        # repository.base_date is reproduced verbatim.
        return format_timestamp(base)
    day = base
    for i in range(1, commit_index + 1):
        day += timedelta(days=1 + _stable_hash(scenario_id, "gap", i) % 9)
        while day.weekday() >= 5:
            day += timedelta(days=1)
    hour = 8 + _stable_hash(scenario_id, "hour", commit_index) % 11
    minute = _stable_hash(scenario_id, "minute", commit_index) % 60
    return format_timestamp(day.replace(hour=hour, minute=minute, second=0, microsecond=0))


def deterministic_author(scenario_id: str, key: Any) -> str:
    """Pick an author from the pool by a stable hash of (scenario id, key)."""
    return DEFAULT_AUTHOR_POOL[_stable_hash(scenario_id, key) % len(DEFAULT_AUTHOR_POOL)]


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
        """The identity and dates of this commit, as ``extra_env`` for :func:`run_git`."""
        name, email = parse_author(self.author)
        return {
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_AUTHOR_DATE": self.author_date,
            "GIT_COMMITTER_DATE": self.committer_date,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "author_date": self.author_date,
            "committer_date": self.committer_date,
        }


TIMESTAMP_KEYS = ("date", "author_date", "committer_date")


def _has_explicit_timestamp(scenario: dict[str, Any]) -> bool:
    """True when any commit of the scenario pins a timestamp."""
    commits = scenario.get("commits")
    if not isinstance(commits, list):
        return False
    return any(
        isinstance(commit, dict) and any(commit.get(key) is not None for key in TIMESTAMP_KEYS)
        for commit in commits
    )


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
    # A scenario that pins some of its timestamps was written against the plain
    # one-day-per-commit schedule; spreading the remaining commits over the new
    # irregular gaps would place them after the pinned ones and invert
    # parent/child dates.  Such scenarios keep the plain schedule, and only
    # scenarios whose timeline is entirely generated get the spread-out one.
    schedule_id: str | None = None if _has_explicit_timestamp(scenario) else scenario_id

    author = commit_spec.get("author")
    author_is_default = not (isinstance(author, str) and author.strip())
    if author_is_default:
        author = deterministic_author(scenario_id, commit_index)

    default_date: str | None = None

    def default() -> str:
        nonlocal default_date
        if default_date is None:
            default_date = deterministic_date(repository.get("base_date"), commit_index, schedule_id)
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
    env: dict[str, str] = {}
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
