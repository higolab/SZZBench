from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
import atexit
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata


class GitError(RuntimeError):
    pass


#: The one ``GIT_*`` variable a Git subprocess still receives: it locates Git's
#: own programs.  Every other ``GIT_*`` variable of the caller is withheld
#: (issue #96).  Naming the dangerous ones one by one missed some -- with
#: ``GIT_DEFAULT_HASH=sha256`` a generation verified with 64-character hashes,
#: with ``GIT_DEFAULT_REF_FORMAT=reftable`` it wrote a reftable repository, and
#: with ``GIT_DIR`` set every commit went into the repository it named -- while
#: SZZBench needs none of them: the identity and dates of a commit are passed
#: as ``extra_env``.
KEPT_GIT_ENV = frozenset({"GIT_EXEC_PATH"})


def _withheld(key: str) -> bool:
    return key.startswith("GIT_") and key not in KEPT_GIT_ENV


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
    global configuration, the default ignore and attributes files, the init
    template, and every ``GIT_*`` variable but ``GIT_EXEC_PATH`` (configuration
    injected through the environment, the repository it points at, the object
    and ref format of a new repository, diff and pathspec behaviour) are
    withheld, so what SZZBench generates and measures depends on the scenario
    and the Git version only -- not on a developer's signing setup, hooks,
    global ignores or filters.  ``extra_env`` holds only what a caller sets on
    purpose (commit identity and dates) and is applied last.

    On Windows, Python's default text encoding may be cp932. Git output can
    contain UTF-8 commit messages or paths, so run_git() decodes subprocess
    output explicitly as UTF-8. These environment values also encourage Git to
    produce UTF-8 output where supported.
    """
    git_env = {key: value for key, value in os.environ.items() if not _withheld(key)}
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
    except OSError as exc:
        raise _could_not_run(repo_dir, args, exc) from exc


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
    except OSError as exc:
        raise _could_not_run(repo_dir, args, exc) from exc


def _could_not_run(repo_dir: Path, args: list[str], exc: OSError) -> GitError:
    """Git could not be started at all: a missing working directory, no ``git`` on PATH,
    no permission.  A GitError like any other, so every caller that handles one handles
    this too, instead of a FileNotFoundError traceback (issue #166)."""
    if not Path(repo_dir).is_dir():
        reason = f"the directory {repo_dir} does not exist"
    else:
        reason = exc.strerror or str(exc)
    return GitError(f"git {args[0] if args else ''} could not run: {reason}")


_git_version: tuple[int, ...] | None = None


def git_version() -> tuple[int, ...]:
    """The installed Git's version as numbers, ``()`` when it cannot be read."""
    global _git_version
    if _git_version is None:
        try:
            out = subprocess.run(["git", "--version"], capture_output=True, text=True, env=_git_env()).stdout
        except OSError:
            out = ""
        match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", out)
        _git_version = tuple(int(part) for part in match.groups() if part is not None) if match else ()
    return _git_version


def init_args() -> list[str]:
    """``git init`` arguments that fix what a new repository looks like.

    An empty ``--template`` copies no hooks, whatever the installation ships.
    The object and ref formats are pinned to SHA-1 and files, the formats of
    every published hash and of what SZZ tools read, where Git knows the options
    (2.29 and 2.45): the caller's environment no longer reaches Git, but a Git
    whose built-in default changes would otherwise change every hash.
    """
    args = ["init", "--template="]
    version = git_version()
    if version >= (2, 29):
        args.append("--object-format=sha1")
    if version >= (2, 45):
        args.append("--ref-format=files")
    return args


def init_repo(repo_dir: Path, branch: str) -> None:
    repo_dir.mkdir(parents=True, exist_ok=True)
    run_git(repo_dir, init_args())
    run_git(repo_dir, ["branch", "-M", branch])
    run_git(repo_dir, ["config", "user.name", "SZZ Benchmark"])
    run_git(repo_dir, ["config", "user.email", "szz-benchmark@example.com"])
    run_git(repo_dir, ["config", "core.autocrlf", "false"])
    run_git(repo_dir, ["config", "core.filemode", "false"])
    run_git(repo_dir, ["config", "i18n.commitEncoding", "utf-8"])
    run_git(repo_dir, ["config", "i18n.logOutputEncoding", "utf-8"])


#: The default branch of a scenario without ``repository.default_branch`` (the
#: graph suite warns, GW021; the classic suite requires the key, E010).
DEFAULT_BRANCH = "main"


def scenario_default_branch(scenario: dict[str, Any]) -> Any:
    """``repository.default_branch`` as the generators, the validators and the verifiers read it (issue #239).

    ``main`` when the key is absent or null, and otherwise the value as
    written, which validation requires to be a valid branch name (E010 and
    E015, GE022 and GE023).  The readings used to differ: the generators
    handed an empty name to Git, which refused it, while the validators and
    the verifiers read it as ``main``.
    """
    repository = scenario.get("repository") if isinstance(scenario.get("repository"), dict) else {}
    value = repository.get("default_branch")
    return DEFAULT_BRANCH if value is None else value


def commit_branch(commit: dict[str, Any], default_branch: Any) -> Any:
    """The branch of a graph commit as the generator, the validator and the verifier read it (issue #239).

    The default branch when ``branch`` is absent or null, and otherwise the
    value as written, which validation requires to be a valid branch name
    (GE035, GE023).  ``branch: ""`` used to be the default branch to all of
    them, without a word, while ``default_branch: ""`` reached Git.
    """
    value = commit.get("branch")
    return default_branch if value is None else value


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


def commit_generator_count(op: dict[str, Any], owner_id: str) -> int:
    """The ``count`` of a ``commit_generator`` operation of commit ``owner_id``, before the cap.

    A value ``int()`` cannot read -- ``many``, a missing count, ``.nan``, or
    ``.inf`` and ``-.inf`` (``OverflowError``) -- or a negative one is a
    ``ValueError`` that names the field and the commit, as
    ``graph_operations.commit_generator_plan`` (generation and ``--simulate``)
    refuses it.  ``planned_generated_commits`` reads the count here, so that it
    skips exactly the counts generation refuses: it caught ``TypeError`` and
    ``ValueError`` only, and an infinite count ended ``verify-graph`` in a
    traceback (issue #230).
    """
    try:
        requested = int(op.get("count"))
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"commit_generator.count of commit '{owner_id}' must be an integer.") from None
    if requested < 0:
        raise ValueError(f"commit_generator.count of commit '{owner_id}' must not be negative.")
    return requested


def planned_generated_commits(owner_id: str, commit_spec: dict[str, Any]) -> list[str]:
    """The ``<owner>.g<N>`` ids the generator will create for ``commit_spec``'s
    ``commit_generator`` operations, in order and with the count cap applied.
    A count the generator would reject (``commit_generator_count``) is skipped
    here; ``validate-graph`` reports it (GE062), and so do ``--simulate`` and
    generation."""
    total = 0
    for op in commit_spec.get("operations") or []:
        if not isinstance(op, dict) or op.get("type") != "commit_generator":
            continue
        try:
            requested = commit_generator_count(op, owner_id)
        except ValueError:
            continue
        total += min(requested, MAX_GENERATED_COMMITS)
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
    default_branch = str(scenario_default_branch(scenario))
    tips: dict[str, str] = {}
    for c in commits:
        tips[str(commit_branch(c, default_branch))] = c["id"]        # the latest commit on a branch is its tip
    graph = scenario.get("graph") if isinstance(scenario.get("graph"), dict) else {}
    lifecycle = graph.get("ref_lifecycle") if isinstance(graph.get("ref_lifecycle"), dict) else {}
    deleted = {n for n in (lifecycle.get("delete_branches") or []) if isinstance(n, str)}
    roots = {tip for branch, tip in tips.items() if branch not in deleted}
    for tag in lifecycle.get("tags") or []:
        if isinstance(tag, dict) and isinstance(tag.get("commit"), str):
            roots.add(tag["commit"])
    last = commits[-1]
    if str(commit_branch(last, default_branch)) in deleted and (default_branch in deleted or default_branch not in tips):
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


#: A trailing ISO 8601 offset in its basic form (``+0900``), which ``datetime.fromisoformat``
#: reads only from Python 3.11 on.
_BASIC_OFFSET = re.compile(r"([+-]\d{2})(\d{2})$")


def parse_timestamp(value: Any, *, field: str = "date") -> datetime:
    """Parse an ISO 8601 timestamp (``2024-01-01T10:00:00Z`` or with offset).

    YAML may already have turned an unquoted timestamp into a ``datetime``;
    such values are accepted as-is.  A value without a zone, quoted or not, is
    UTC (issue #133).
    """
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        raise GitError(f"{field} must be an ISO 8601 timestamp string, got {value!r}")
    text = value.strip()
    if text.endswith("Z") or text.endswith("z"):
        text = text[:-1] + "+00:00"
    elif "T" in text or " " in text:
        text = _BASIC_OFFSET.sub(r"\1:\2", text)
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
    """A pinned timestamp in the form Git is given and ``commit-map.json`` records (issue #133).

    The value is parsed and written back with its zone, so Git never reads a
    zone-less value in the machine's local time: ``"2024-01-01T10:00:00"``
    (quoted) and ``2024-01-01T10:00:00`` (a YAML timestamp) are both UTC, as
    :func:`parse_timestamp` and the validators already read them.  A value
    with ``Z`` or an offset is written back unchanged, so no shipped hash
    moves.  A value that is not ISO 8601 is an error naming the field, not a
    date Git happens to accept.
    """
    if isinstance(value, datetime) or (isinstance(value, str) and value.strip()):
        return format_timestamp(parse_timestamp(value, field=field))
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

    Explicit values keep their instant and their offset; a value without a
    zone is UTC (issue #133).  ``author_date`` and
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


def ignored_written_paths(repo_dir: Path, written: Iterable[str]) -> list[tuple[str, str]]:
    """``(path, rule)`` for each path of ``written`` that ``git add -A`` left out of the index (issue #164).

    Both simulators take a file an operation writes to be in the next commit.
    ``git add -A`` stages it only when no ignore rule of the repository matches
    it: a ``.gitignore`` the scenario wrote, or ``.git/info/exclude`` (the
    global ones are withheld, #96).  An ignored file stayed in the worktree
    only, and a commit that wrote nothing else failed with "commit would be
    empty".  ``rule`` is what ``git check-ignore -v`` names: the pattern, its
    file and its line.  Paths are compared in NFC, the form Git lists them in
    on macOS (``core.precomposeUnicode``).
    """
    wanted = {unicodedata.normalize("NFC", path) for path in written if isinstance(path, str)}
    if not wanted:
        return []
    listed = run_git(repo_dir, ["ls-files", "-z", "--others", "--ignored", "--exclude-standard"]).stdout
    ignored = sorted({path for path in listed.split("\0") if path and unicodedata.normalize("NFC", path) in wanted})
    if not ignored:
        return []
    rules: dict[str, str] = {}
    try:
        # "./" keeps a path that starts with ":" from being read as pathspec magic
        out = run_git_with_input(repo_dir, ["check-ignore", "--stdin", "-z", "-v"],
                                 b"".join(f"./{path}".encode("utf-8") + b"\0" for path in ignored)).stdout
        fields = out.decode("utf-8", errors="replace").split("\0")
        for start in range(0, len(fields) - 3, 4):
            source, line, pattern, path = fields[start:start + 4]
            rules[path[2:] if path.startswith("./") else path] = f"'{pattern}' in {source}, line {line}"
    except GitError:
        pass                      # the paths are still named, without their rule
    return [(path, rules.get(path, "an ignore rule")) for path in ignored]


def refuse_ignored_written_paths(repo_dir: Path, written: Iterable[str], commit_id: str | None = None) -> None:
    """Stop when ``git add -A`` left out a file the commit writes (issue #164); call it after staging.

    The generated commit would not hold what the scenario, the simulators and
    the oracle describe, and nothing said so.  Validation refuses a scenario
    that writes ``.gitignore`` (E051 / GE063), so this guards generation when
    that check is passed by.
    """
    found = ignored_written_paths(repo_dir, written)
    if not found:
        return
    listing = ", ".join(f"{path} ({rule})" for path, rule in found)
    who = f"Commit '{commit_id}'" if commit_id is not None else "The commit"
    what, them = ("a file", "it") if len(found) == 1 else ("files", "them")
    raise GitError(f"{who} writes {what} Git ignores: {listing}. `git add -A` leaves {them} out of the commit, so the "
                   "generated tree would differ from the scenario's; validation refuses a scenario that writes "
                   ".gitignore (E051 / GE063).")


def commit_all(
    repo_dir: Path,
    *,
    message: str,
    author: str | None,
    date: str | None = None,
    author_date: str | None = None,
    committer_date: str | None = None,
    body: str | None = None,
    written: Iterable[str] = (),
    commit_id: str | None = None,
) -> str:
    """Stage everything and commit.

    ``author_date``/``committer_date`` take precedence over ``date``; when none
    is given the commit gets the generation time (callers that want
    deterministic metadata pass values from :func:`resolve_commit_metadata`).
    ``written`` holds the paths the commit's operations wrote: one that Git
    does not stage stops the commit, before it could be reported as empty
    (issue #164).  ``commit_id`` names the commit in that message.
    """
    run_git(repo_dir, ["add", "-A"])
    refuse_ignored_written_paths(repo_dir, written, commit_id)
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
