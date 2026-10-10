from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import difflib
import math
import re

from .findings import ValidationResult
from .operations import (SUPPORTED_OPERATIONS, FUTURE_OPERATIONS, OperationError, apply_operation_to_memory,
                         find_all_occurrences, resolve_encoding, resolve_line_ending, type_label)
from .paths import PathValidationError, file_path_conflict, file_system_key, ref_name_problem, validate_repo_relative_path
from .retired_ids import read_retired_ids
from .scenario import load_yaml
from .gitutils import (_AUTHOR_RE, TIMESTAMP_KEYS, GitError, parse_timestamp, resolve_commit_metadata,
                       resolved_commit_authors)

#: The commit roles (``commits[].role``) of both suites, decisions/vocabulary.md
#: section 2.2: the classic suite's eleven, and five more the graph suite uses --
#: generic noise, the commit an origin BIC copies or a rewrite replays, a
#: reintroduction, the commit a release branch starts from, and a commit
#: ``commit_generator`` expands (issue #18).  ``validate`` reports any other role
#: (E030) and ``validate-graph --lint`` too (GE405, issue #195).  The role
#: describes the commit for a reader: it is copied into commit-map.json and read
#: by no scorer.
ALLOWED_ROLES = {
    "initial", "bug_introducing", "bug_fixing", "distractor", "refactoring",
    "formatting", "test_change", "merge", "revert", "cleanup", "feature_addition",
    "intermediate", "origin_bug_introducing", "bug_reintroducing", "release_branch_point", "generated",
}

#: The status of a scenario (decisions/vocabulary.md section 4): ``draft`` may fail
#: the lints, ``active`` passes ``--strict --lint`` and generates, ``retired`` is
#: listed in docs/retired-ids.md.  W002 / GW018 report any other (issue #157).
SCENARIO_STATUSES = ("draft", "active", "retired")

#: The operation fields whose value is text the generator writes or matches.  A
#: number or a blank value (YAML null) in one ended `validate --simulate` and
#: `generate` in an AttributeError traceback (issue #151).
TEXT_FIELDS_BY_OPERATION = {"write_file": ("content",), "replace": ("old", "new")}
#: The field that names the file an operation creates or rewrites (E051, issue #164).
WRITTEN_PATH_FIELDS = {"write_file": ("path",), "replace": ("path",)}
#: What a lint may meet in a scenario it has to resolve as the evaluator or the generator
#: would.  The static checks report such input first; a lint that meets it anyway says so
#: instead of passing in silence, and anything else is a bug that should be seen (issue #161).
LINT_INPUT_ERRORS = (GitError, ValueError, TypeError, OverflowError)

# --- the commit message rule (E012 / GE070, issue #163) ----------------------

#: What both validators tell the author after the problem itself.
COMMIT_MESSAGE_RULE = "Write it on one line, without leading or trailing whitespace; a message body is not supported."

#: A message that starts so is a sign-off, which Git does not count as a message.
SIGN_OFF_PREFIX = "Signed-off-by: "

#: The characters Git drops at the end of a line: its own isspace(), not Python's.
_GIT_LINE_END_WHITESPACE = " \t\r"


def subject_read_back(message: str) -> str:
    """The subject the verifiers read back after ``git commit -m <message>``.

    Without an editor ``git commit`` cleans the message up with
    ``--cleanup=whitespace``: every line loses its trailing spaces, tabs and
    carriage returns, and the blank lines before and after the text go.  The
    subject (``git log --format=%s``) is the first paragraph, its lines joined
    by a space.  ``gitutils.git_message``, which both verifiers compare with
    ``message``, decodes a carriage return as a line break and strips the
    subject of the whitespace Python knows, which is more than Git's.
    """
    lines = [line.rstrip(_GIT_LINE_END_WHITESPACE) for line in message.split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    paragraph: list[str] = []
    for line in lines:
        if not line:
            break
        paragraph.append(line)
    return " ".join(paragraph).replace("\r", "\n").strip()


def commit_message_problem(message: str) -> str | None:
    """Why ``git commit -m <message>`` would not store ``message`` as the subject verification reads back, or None.

    The rule both suites apply (issue #163): a ``message`` is the commit's
    subject, a single line without leading or trailing whitespace.  The
    verifiers compare it with the subject Git gives back (E602, GE623), so a
    message with a trailing newline (``message: |``) or with a body after a
    blank line passed validation and failed generation, with no word on why.
    A tab, a no-break space or any other character inside the line is stored
    and read back as written.  Measured with Git 2.39 and 2.50, which agree.
    """
    if "\0" in message:
        return "contains a NUL character, which cannot be passed to git commit"
    try:
        message.encode("utf-8")
    except UnicodeEncodeError as exc:
        return (f"contains a lone surrogate (U+{ord(message[exc.start]):04X}), which is not UTF-8 text, "
                "so Git cannot store it as written")
    if not message:
        return "is empty, and Git refuses a commit with an empty message"
    if not message.strip():
        return "is only whitespace, which Git removes, and Git refuses a commit with an empty message"
    if message.startswith(SIGN_OFF_PREFIX) and "\n" not in message:
        return (f"starts with '{SIGN_OFF_PREFIX.strip()}': Git does not count a sign-off line as a message, "
                "and refuses the commit as having an empty message")
    subject = subject_read_back(message)
    if subject == message:
        return None
    text = message.strip()
    if "\n" in text:
        paragraphs = [part for part in re.split(r"\n[ \t\r]*\n", text) if part.strip()]
        line_count = text.count("\n") + 1
        what = ("has a body after a blank line, which Git stores apart from the subject" if len(paragraphs) > 1
                else f"spans {line_count} lines, which Git joins into one subject")
    elif message.lstrip(" \t\r").startswith("\n"):
        what = "starts with a line break, which Git drops"
    elif message.rstrip(" \t\r").endswith("\n"):
        what = "ends with a line break (a `message: |` block scalar keeps one), which Git drops"
    elif "\r" in text:
        what = "contains a carriage return, which verification reads back as a line break"
    elif message != message.lstrip():
        what = f"starts with whitespace ({message[0]!r}), which verification strips from the subject"
    elif message[-1] in _GIT_LINE_END_WHITESPACE:
        what = f"ends with whitespace ({message[-1]!r}), which Git drops"
    else:
        what = f"ends with whitespace ({message[-1]!r}), which verification strips from the subject"
    return f"{what}: the subject read back would be {subject!r}, so verification would fail"

# --- the commit metadata the generators read (E013 / E014, GE071 / GE072, issue #152) ---

#: The schema_version of a classic scenario: every shipped one declares it.
CLASSIC_SCHEMA_VERSION = "1.0"

#: What Git drops from either end of an author's name (``verifier._IDENT_END_CRUD``,
#: which this module cannot import): Git 2.39 refuses a name made only of them.
_IDENT_CRUD = "".join(chr(code) for code in range(33)) + ".,:;<>\"\\'"


#: The instants Git records as written, with Git 2.39 and 2.50 alike: from the
#: epoch up to, not including, 2100, in a year from 1970 to 2099 where the value is
#: written.  Outside them Git refuses the value ("invalid date format") or records
#: another date: both read 0001-01-01 as 2001-01-01, and 2.39 records an instant
#: before the epoch as an unsigned timestamp near 2**64.
GIT_FIRST_INSTANT = datetime(1970, 1, 1, tzinfo=timezone.utc)
GIT_END_INSTANT = datetime(2100, 1, 1, tzinfo=timezone.utc)


def timestamp_problem(value: Any) -> str | None:
    """Why the generators cannot give ``value`` to Git as a pinned timestamp, or None.

    A commit's ``date``, ``author_date`` and ``committer_date`` and
    ``repository.base_date`` are read by ``gitutils.parse_timestamp``: an ISO
    8601 string, or the ``datetime`` PyYAML makes of an unquoted one, and the
    instant has to be one Git records (``GIT_FIRST_INSTANT`` to
    ``GIT_END_INSTANT``).  Nothing else looked at them, so ``date: yesterday``
    passed validation and failed generation.  A blank value (YAML null) is
    refused too: without the key the generator picks a date, and with a blank
    one it did the same without a word.
    """
    if isinstance(value, date) and not isinstance(value, datetime):
        return (f"is the date {value.isoformat()} without a time (YAML reads an unquoted date as one); "
                f"write a timestamp such as '{value.isoformat()}T10:00:00Z'")
    if not isinstance(value, (str, datetime)):
        return (f"must be an ISO 8601 timestamp such as '2024-01-01T10:00:00Z', not {type_label(value)}; "
                "without the key the generator picks a date")
    shown = repr(value) if isinstance(value, str) else f"'{value.isoformat()}'"
    try:
        parsed = parse_timestamp(value)
    except GitError:
        return f"{shown} is not an ISO 8601 timestamp such as '2024-01-01T10:00:00Z'"
    if not (1970 <= parsed.year <= 2099 and GIT_FIRST_INSTANT <= parsed < GIT_END_INSTANT):
        return (f"{shown} is not a date Git records: write an instant from 1970-01-01T00:00:00Z up to "
                "2099-12-31T23:59:59Z, in a year from 1970 to 2099 where it is written")
    offset = parsed.utcoffset()
    if offset is not None and offset.total_seconds() % 60:
        # Git keeps an offset as +hhmm: +00:00:30 became +0000, and the instant moved by 30 seconds
        # (E605 in the classic suite, nothing at all in the graph suite; PR #236 review)
        return (f"{shown} has the offset {offset} with seconds, and Git records an offset in whole minutes (+hhmm), "
                "so it would record another instant; write the offset in hours and minutes")
    return None


def author_problem(value: Any) -> str | None:
    """Why the generators would not record ``value`` as the commit's author, or None.

    ``gitutils.resolve_commit_metadata`` replaced an ``author`` that is not a
    non-empty string by a default author, and ``parse_author`` read a string
    without ``<email>`` as a name with the benchmark's own address; both
    passed validation without a word.  An author is ``Name <email>`` as
    ``parse_author`` reads it, with a name Git keeps and an address.
    """
    if not isinstance(value, str):
        return f"must be a string 'Name <email>', not {type_label(value)}; without the key the generator picks an author"
    # the generators pass it to Git in its environment, which takes neither (PR #236 review)
    if "\0" in value:
        return f"{value!r} contains a NUL character, which cannot be passed to Git"
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        return f"{value!r} contains a lone surrogate (U+{ord(value[exc.start]):04X}), which is not UTF-8 text"
    match = _AUTHOR_RE.match(value)
    if match is None:
        return f"{value!r} is not 'Name <email>'"
    if not match.group("name").strip(_IDENT_CRUD):
        return f"{value!r} has no name, and Git refuses a commit without one"
    if not match.group("email").strip():
        return f"{value!r} has an empty e-mail address"
    return None


def default_branch_problem(repository: Any) -> str | None:
    """E015's message for a ``repository.default_branch`` generation cannot create, or None (issue #239).

    The rule of the graph suite's branch names (GE023, ``paths.ref_name_problem``).
    ``validate`` asks it, and ``generate`` before ``git init``: the field was
    checked for its type only, and a name Git refuses failed ``git branch -M``
    with Git's message (``unknown switch`` for ``-x``).  A value that is not a
    string is E010's.
    """
    name = repository.get("default_branch") if isinstance(repository, dict) else None
    if not isinstance(name, str):
        return None
    problem = ref_name_problem(name, "branch")
    return None if problem is None else f"repository.default_branch {name!r} is not a valid branch name: {problem}."


def check_scheduled_dates(data: dict[str, Any], result: ValidationResult, *, code: str, graph: bool = False) -> None:
    """``code`` for a date the generators would give a commit that names none, outside what Git records.

    A commit without ``date`` / ``author_date`` / ``committer_date`` gets one
    from a schedule that starts at ``repository.base_date``
    (``gitutils.resolve_commit_metadata``, which both generators call).  The
    base date alone was checked, so a base date near the end of the range Git
    records passed, and generation failed at a later commit with Git's
    ``invalid date format`` (PR #236 review).  The first such commit is named;
    the dates are increasing, so the ones after it fail too.  Run after the
    explicit values have been checked, so that each problem is reported once.
    In the graph suite a commit with ``inherit_author_date`` takes its author
    date from its rewrite source (``graph_generator._apply_inherit_options``),
    whose own date is checked where it is declared: only its committer date
    comes from the schedule (PR #236 review).
    """
    if any(f.code == code for f in result.findings):
        return                           # a written date is wrong already
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else {}
    found: list[tuple[int, str, str, str]] = []          # (index, commit id, key, value)
    for index, commit in enumerate(commits):
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        try:
            metadata = resolve_commit_metadata(data, commit, index)
        except (GitError, ValueError, TypeError, OverflowError):
            # a value other checks report, or a schedule past the dates Python can represent
            found.append((index, commit["id"], "date", "a date past the year 9999"))
            break
        inherits_author_date = graph and bool(commit.get("inherit_author_date"))
        for key, value, is_default in (("author_date", metadata.author_date, metadata.author_date_is_default),
                                       ("committer_date", metadata.committer_date, metadata.committer_date_is_default)):
            if key == "author_date" and inherits_author_date:
                continue                 # replaced by the rewrite source's author date
            if is_default and timestamp_problem(value) is not None:
                found.append((index, commit["id"], key, value))
                break
    if not found:
        return
    index, cid, key, value = found[0]
    base = repository.get("base_date")
    where = "repository.base_date" if base is not None else f"commits[{index}]"
    since = f"repository.base_date {base!r}" if base is not None else "the default base date"
    later = "; the commits after it get later dates" if index < len(commits) - 1 else ""
    result.error(code, f"Commit '{cid}' names no date, and the schedule from {since} gives it the {key} {value}, "
                 f"which Git does not record (it records an instant from 1970-01-01T00:00:00Z up to "
                 f"2099-12-31T23:59:59Z){later}: choose an earlier base date, or write the commit's date.", where)


def _committer_date_source(commit: dict[str, Any], repository: dict[str, Any]) -> tuple[str | None, str]:
    """The key that writes ``commit``'s committer date, or None when it is scheduled, and how to name it."""
    for key in ("committer_date", "date"):          # resolve_commit_metadata's order
        if commit.get(key) is not None:
            return key, f"its {key}"
    base = "repository.base_date" if repository.get("base_date") is not None else "the default base date"
    return None, f"scheduled from {base}, as '{commit['id']}' writes no date or committer_date"


def check_commit_date_order(data: dict[str, Any], result: ValidationResult, *, code: str, timestamp_code: str,
                            graph: bool = False) -> None:
    """``code`` for a commit the generators would commit before one of its parents (issue #241).

    Each commit gets the dates it writes, or one from the schedule
    (``gitutils.resolve_commit_metadata``, which both generators call).  As
    soon as any commit writes a date, the others get the plain schedule,
    ``repository.base_date`` (or ``2024-01-01T10:00:00Z``) plus the commit's
    index in days, and a written date that did not fit it put a child before
    its parent, as did two written dates in the wrong order.  The graph
    verifier found it after generation (GE630, by hash), and the classic
    suite generated and verified such a history.  The committer date, the
    one GE630 compares (``inherit_author_date`` changes the author date
    only), is compared with each parent's: the previous commit in the
    classic suite, every entry of ``parents`` in the graph suite.  Two
    scheduled dates are in order (the schedule grows with the index, and
    parents come first), so the finding is at the child's written date, or
    else at the parent's.  Instants are compared in whole seconds, as Git
    records them.  Run after ``check_scheduled_dates``: no date is compared
    once one is reported (``timestamp_code``).
    """
    if any(f.code == timestamp_code for f in result.findings):
        return
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else {}
    # (index, commit, committer date, its second) of each commit whose date resolves
    seen: dict[str, tuple[int, dict[str, Any], str, int]] = {}
    previous: str | None = None          # the classic parent
    for index, commit in enumerate(commits):
        cid = commit.get("id") if isinstance(commit, dict) else None
        if not isinstance(cid, str):
            previous = None
            continue
        if graph:
            declared = commit.get("parents") if isinstance(commit.get("parents"), list) else []
            # an unknown or later parent is GE038 / GE039, a repeated one GE049
            parents = [p for p in dict.fromkeys(p for p in declared if isinstance(p, str)) if p in seen]
        else:
            parents = [previous] if previous in seen else []
        previous = None
        try:
            committed = resolve_commit_metadata(data, commit, index).committer_date
            second = math.floor(parse_timestamp(committed).timestamp())
        except (GitError, ValueError, TypeError, OverflowError):
            continue                     # a value other checks report
        for pid in parents:
            parent_index, parent, parent_committed, parent_second = seen[pid]
            if parent_second <= second:
                continue
            child_key, child_source = _committer_date_source(commit, repository)
            parent_key, parent_source = _committer_date_source(parent, repository)
            if child_key is None:
                advice = f"write an earlier date for '{pid}', or a date for '{cid}' too"
            elif parent_key is None:
                advice = f"write a date for '{pid}' too, or a later one for '{cid}'"
            else:
                advice = f"write an earlier date for '{pid}' or a later one for '{cid}'"
            # at the date the scenario writes: the child's, or else the parent's
            where = (f"commits[{index}].{child_key}" if child_key is not None
                     else f"commits[{parent_index}].{parent_key}" if parent_key is not None else f"commits[{index}]")
            result.error(code, f"Commit '{cid}' would be committed at {committed} ({child_source}), before its parent "
                         f"'{pid}' at {parent_committed} ({parent_source}): {advice}.", where)
        seen.setdefault(cid, (index, commit, committed, second))
        previous = cid


#: The keys of a classic ``fix`` that hold the text validation looks up (E311).
FIX_STATEMENT_KEYS = ("statement", "added_statement", "removed_statement")


def _is_blank(value: Any) -> bool:
    """A statement that is a string and has nothing but whitespace: it is found in any text."""
    return isinstance(value, str) and not value.strip()


def check_commit_metadata(commit: dict[str, Any], cid: Any, loc: str, result: ValidationResult, *,
                          timestamp_code: str, author_code: str) -> None:
    """``timestamp_code`` for a date the generators cannot read, ``author_code`` for an author they would not record."""
    for key in TIMESTAMP_KEYS:
        if key in commit:
            problem = timestamp_problem(commit[key])
            if problem is not None:
                result.error(timestamp_code, f"Commit '{cid}' {key} {problem}.", f"{loc}.{key}")
    if "author" in commit:
        problem = author_problem(commit["author"])
        if problem is not None:
            result.error(author_code, f"Commit '{cid}' author {problem}.", f"{loc}.author")


def check_status(meta: dict[str, Any], result: ValidationResult, *, code: str) -> None:
    """W002 / GW018: ``meta.status``, when present, is one of ``SCENARIO_STATUSES`` (issue #157).

    No check read the field: a status outside the vocabulary reached the index
    and the README header, which show it as if it were one, and
    ``validate-index`` was satisfied because both copies agreed.  A warning, so
    ``--strict`` fails on it.  Without the key there is nothing to check.
    """
    if "status" not in meta:
        return
    status = meta["status"]
    if not isinstance(status, str):
        result.warning(code, f"meta.status must be one of {SCENARIO_STATUSES}, not {type_label(status)}.", "meta.status")
    elif status not in SCENARIO_STATUSES:
        result.warning(code, f"meta.status '{status}' is not one of {SCENARIO_STATUSES} "
                       "(decisions/vocabulary.md section 4).", "meta.status")


# --- Git's own files in the worktree (E051 / GE063, issue #164) --------------

#: The files of the worktree that Git reads, in any directory, and what reading one does
#: to a generated repository.  Both simulators take a written file to be committed as
#: written; the generators commit with ``git add -A``, which reads the scenario's own
#: ``.gitignore`` and ``.gitattributes``.  A file a ``.gitignore`` matched was left out of
#: every tree (a commit that wrote nothing else failed with "commit would be empty"), and
#: ``* text=auto`` stored a ``line_ending: crlf`` file as LF, with no finding anywhere.
GIT_CONTROL_FILES = {
    ".gitignore": "its rules decide which files `git add -A` stages, so a file they match would be left out of "
                  "the commit the scenario describes",
    ".gitattributes": "its attributes (text, eol, ident, working-tree-encoding, ...) decide the bytes Git stores, "
                      "so a blob would differ from what the scenario writes",
    ".gitmodules": "it declares submodules, which `git submodule` and `git clone --recurse-submodules` act on and "
                   "neither the generators nor the simulators model",
}
#: The factor by which a scenario declares that its subject is a ``.gitattributes`` rule (SZZG-0134).
GITATTRIBUTES_FACTOR = "gitattributes-bic"
_GIT_CONTROL_FILE_KEYS = {file_system_key(name): name for name in GIT_CONTROL_FILES}


def git_control_file(path: str) -> str | None:
    """The file of :data:`GIT_CONTROL_FILES` the last name of ``path`` is, or None.

    Names are compared by ``paths.file_system_key``: Git on macOS reads
    ``.GITIGNORE`` as ``.gitignore`` (and Git on Windows, for letter case),
    Git on Linux does not.
    """
    return _GIT_CONTROL_FILE_KEYS.get(file_system_key(path.rsplit("/", 1)[-1]))


def check_git_control_files(data: dict[str, Any], result: ValidationResult, *, code: str,
                            written_fields: dict[str, tuple[str, ...]]) -> None:
    """``code`` for an operation that writes a file Git reads (issue #164).

    ``written_fields`` names, for each operation, the fields that hold the
    file it creates or rewrites.  ``.gitignore`` and ``.gitmodules`` are
    refused everywhere; ``.gitattributes`` unless ``meta.factors`` declares
    :data:`GITATTRIBUTES_FACTOR`, the scenario's subject being what the rule
    does to the blobs.
    """
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    factors = meta.get("factors")
    attributes_declared = isinstance(factors, list) and GITATTRIBUTES_FACTOR in factors
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    for i, commit in enumerate(commits):
        operations = commit.get("operations") if isinstance(commit, dict) else None
        for j, op in enumerate(operations if isinstance(operations, list) else []):
            if not isinstance(op, dict) or not isinstance(op.get("type"), str):
                continue
            for key in written_fields.get(op["type"], ()):
                path = op.get(key)
                name = git_control_file(path) if isinstance(path, str) else None
                if name is None or (name == ".gitattributes" and attributes_declared):
                    continue
                shown = f"'{path}'" if path.isascii() else ascii(path)      # invisible code points spelt out
                what = "a file Git reads" if path.rsplit("/", 1)[-1] == name else f"which Git on macOS can read as {name}"
                remedy = (f"Declare the factor '{GITATTRIBUTES_FACTOR}' in meta.factors to write one on purpose."
                          if name == ".gitattributes" else f"A scenario cannot write {name}.")
                result.error(code, f"Operation '{op['type']}' writes {shown}, {what}: {GIT_CONTROL_FILES[name]}. "
                             f"{remedy}", f"commits[{i}].operations[{j}].{key}")

# --- opt-in lint vocabulary (shared with graph_validator) -------------------

# Schema keys and operation names that must not be used as scenario factors.
RESERVED_FACTOR_WORDS = frozenset({
    "expected_szz", "faults", "fixes", "fault", "fix", "bug_fixing_commits",
    "bug_introducing_commits", "issues", "work_items", "clone_relationships",
    "bug_instances", "evaluation_variants", "developer_hints", "allow_empty",
    "commit_generators", "commit_generator", "write_file", "replace", "rename_file",
    "move_file", "copy_file", "delete_file", "move_entity", "copy_entity",
    "write_binary_file", "write_generated_text_file", "chmod", "insert_after",
    "cherry_pick_of", "backport_of", "rebase_of", "edit", "drop",
})

# Explicit answer cues that disclose a commit's oracle role (issue #8).
#
# The words between "introduce" and "bug" may be hyphenated
# ("introduce context-sensitive bug"), and a commit can admit its role without
# the word "bug" at all ("introduce ambiguous faulty statement"), so the gap
# accepts hyphens and the vocabulary includes fault words on their own.
LEAK_ROLE_RE = re.compile(
    r"introduc\w*\s+([\w-]+\s+){0,3}bugs?\b|bug[- ]introduc|\bBIC\b|\bBFC\b|distractor|"
    r"intermediate change|initial state|\bnoise\b|\bunrelated\b|\breplay|reintroduc|"
    r"\bbuggy\b|\bfaulty\b|\bfault(?:y|s)?\b\s+(?:statement|line|code|commit)|"
    r"(?:with|containing|introduces?)\s+(?:a\s+|the\s+)?(?:[\w-]+\s+){0,2}bugs?\b",
    re.IGNORECASE,
)
#: A message that starts with a scenario logical id (``c1: ...``).  Kept for the
#: W411 message; :func:`logical_id_reference` is the general check.
LOGICAL_ID_PREFIX_RE = re.compile(r"^[a-z]{1,2}\d+:", re.IGNORECASE)
#: An id-shaped token used as a prefix anywhere in the message.  Issue and
#: work-item identifiers are written ``ISSUE-482`` / ``WI-001`` and keep their
#: hyphen, so they do not match; ``c2:``, ``Rel1:`` and ``WI-001 c2:`` do.
LOGICAL_ID_TOKEN_RE = re.compile(r"(?<![\w-])[A-Za-z]{1,4}\d+:")


def logical_id_reference(message: str, commit_ids: Iterable[str] = ()) -> str | None:
    """Return the logical-id prefix a message exposes, or ``None``.

    A commit id of the same scenario counts wherever it appears, because
    ``WI-001 c2: ...`` discloses exactly as much as ``c2: ...`` and
    ``suspected c0`` names a commit in the benchmark's own vocabulary.
    """
    for commit_id in commit_ids:
        if not isinstance(commit_id, str) or not commit_id:
            continue
        match = re.search(rf"(?<![\w-]){re.escape(commit_id)}(?![\w-])", message, re.IGNORECASE)
        if match:
            return match.group(0)
    match = LOGICAL_ID_TOKEN_RE.search(message)
    return match.group(0) if match else None
# operation type -> field whose text is written into the repository
LEAK_CONTENT_FIELDS = {"write_file": "content", "replace": "new", "insert_after": "content"}

# Declared ghost classes (issue #7): checked only when a scenario opts in.
ADD_ONLY_FIX_FACTORS = frozenset({"addition-only-fix", "ghost-fix", "add_only_fix"})
DELETE_ONLY_BIC_FACTORS = frozenset({"deletion-only-bic", "line-deletion-bic"})
ADD_ONLY_FIX_TYPES = frozenset({"line_addition", "file_creation"})

# Factors that declare a legitimate rewrite of the fault line / a tangled BFC.
FAULT_REWRITE_FACTOR_RE = re.compile(r"after-bic|rewrite|refactor|format|whitespace|rename|move|inline|extract")
TANGLED_BFC_FACTOR_RE = re.compile(r"tangled|distractor|candidate")
#: A scenario may pair an addition-only fix with deleted lines *on purpose* —
#: a distractor's comment, an adjacent unrelated edit.  When it declares that,
#: W420 is not a finding but the scenario's subject (issues #6, #7).
DECLARED_BFC_NOISE_RE = re.compile(r"tangled|noise|distractor|adjacent-edit")

# Factors declaring that a statement legitimately occurs more than once: the
# fault text is duplicated on purpose (W301), or the fix text already exists
# elsewhere in the file, typically in another overload (W330).
DUPLICATE_STATEMENT_FACTOR_RE = re.compile(r"duplicate|ambiguous|overload|repetitive")

# Factors declaring that the BFC edits lines the BIC did not write because the
# repair does not live where the fault was introduced: the root cause is in
# another file, the BIC is a configuration or dependency change, the fix has to
# update call sites, or the faulty expression spans lines from several commits.
# This is NOT tangling -- `tangled-bfc` means the commit mixes the fix with
# *unrelated* changes (see decisions/vocabulary.md §2), and a single-line pure
# repair whose blame reaches a non-BIC is not mixing anything.
NON_LOCAL_FIX_FACTOR_RE = re.compile(r"root-cause|config|caller-update|multi-line-statement|cross-file")


#: The graph command that does what each classic command does (issue #119).
GRAPH_COMMANDS = {"validate": "validate-graph", "generate": "generate-graph", "verify": "verify-graph"}


def graph_scenario_guard(data: dict[str, Any], path: Path, command: str) -> ValidationResult:
    """E003: a graph scenario handed to a classic command (issue #119).

    The classic checks cannot read one: ``validate`` and ``generate`` crashed
    on its BIC mappings, and ``verify`` skipped the blame check and reported
    a clean summary.  A file is a graph scenario by the rule behind GE001 (a
    string ``schema_version`` containing ``graph``, ``load_graph_scenario``)
    or, when it has no ``schema_version``, by its name (GW014).
    """
    result = ValidationResult()
    schema_version = data.get("schema_version")
    if isinstance(schema_version, str) and "graph" in schema_version:
        reason = f"its schema_version is '{schema_version}'"
    elif schema_version is None and path.name == "scenario.graph.yml":
        reason = "it is named scenario.graph.yml and has no schema_version"
    else:
        return result
    result.error("E003", f"{path.as_posix()} is a graph scenario ({reason}), and `szzbench {command}` reads only classic "
                 f"scenarios. Run `szzbench {GRAPH_COMMANDS[command]}` instead.", "schema_version")
    return result


#: The classic command that does what each graph command does (issue #155).
CLASSIC_COMMANDS = {graph: classic for classic, graph in GRAPH_COMMANDS.items()}


def classic_scenario_guard(data: dict[str, Any], path: Path, command: str) -> ValidationResult:
    """GE003: a classic scenario handed to a graph command (issue #155), the mirror of E003.

    ``validate-graph`` reported GE001 and went on to check the file against
    the graph schema (GE013, GW014, GE048, GW120), ``generate-graph`` said
    "Run 'szzbench validate-graph'", and ``verify-graph`` compared the
    repository with a graph the scenario does not have; none named the
    classic command.  A file is a classic scenario when its
    ``schema_version`` is a string without ``graph`` (GE001's rule; every
    shipped one declares ``"1.0"``) and it is not named
    ``scenario.graph.yml``, or when it has no ``schema_version`` and is named
    ``scenario.yml``.  A graph scenario that declares a wrong version in its
    own ``scenario.graph.yml``, a non-string ``schema_version``, and none in
    a file of another name keep GE001 and the graph checks.  No file is both
    a graph scenario to E003 and a classic one here.
    """
    result = ValidationResult()
    schema_version = data.get("schema_version")
    if isinstance(schema_version, str) and "graph" not in schema_version and path.name != "scenario.graph.yml":
        reason = f"its schema_version is '{schema_version}'"
    elif schema_version is None and path.name == "scenario.yml":
        reason = "it is named scenario.yml and has no schema_version"
    else:
        return result
    result.error("GE003", f"{path.as_posix()} is a classic scenario ({reason}), and `szzbench {command}` reads only graph "
                 f"scenarios. Run `szzbench {CLASSIC_COMMANDS[command]}` instead.", "schema_version")
    return result


def validate_scenario_file(
    path: Path,
    *,
    simulate: bool = False,
    lint: bool = False,
) -> tuple[dict[str, Any] | None, ValidationResult, dict[str, dict[str, str]] | None]:
    """Validate a classic scenario.yml.

    ``lint`` enables the opt-in W4xx lints; the snapshot-based lints need the
    in-memory simulation, so ``lint`` implies ``simulate``.  A graph scenario
    stops at E003, before any other check.
    """
    data, result = load_yaml(path)
    if data is None:
        return None, result, None
    guard = graph_scenario_guard(data, path, "validate")
    if guard.has_errors():
        result.extend(guard)
        return data, result, None
    result.extend(validate_static(data, scenario_path=path))
    snapshots = None
    if (simulate or lint) and not result.has_errors():
        snapshots, sim_result = simulate_commits(data)
        result.extend(sim_result)
        if snapshots is not None and not sim_result.has_errors():
            result.extend(validate_oracle_against_snapshots(data, snapshots))
    if lint and not result.has_errors():
        result.extend(lint_scenario(data, snapshots, scenario_path=path))
    return data, result, snapshots

def validate_static(data: dict[str, Any], *, scenario_path: Path | None = None) -> ValidationResult:
    result = ValidationResult()
    for key in ["schema_version", "meta", "repository", "commits", "bugs"]:
        if key not in data:
            result.error("E010", f"Missing required top-level field '{key}'.", key)
    if "schema_version" in data:
        # 1.0 unquoted is a number, and the value was compared with nothing (issue #152)
        schema_version = data["schema_version"]
        if not isinstance(schema_version, str):
            result.error("E010", f"schema_version must be a string, not {type_label(schema_version)}; quote it: "
                         f'schema_version: "{CLASSIC_SCHEMA_VERSION}".', "schema_version")
        elif schema_version != CLASSIC_SCHEMA_VERSION:
            result.error("E004", f"schema_version is '{schema_version}'; a classic scenario declares "
                         f'schema_version: "{CLASSIC_SCHEMA_VERSION}".', "schema_version")
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else None
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else None
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    bugs = data.get("bugs") if isinstance(data.get("bugs"), list) else []
    if meta is None:
        result.error("E010", "'meta' must be an object.", "meta")
    else:
        for key in ["id", "title", "category", "factors"]:
            if key not in meta:
                result.error("E010", f"meta is missing required field '{key}'.", f"meta.{key}")
            elif key != "factors" and not isinstance(meta[key], str):
                # checked for presence only, as the docs claimed otherwise (issue #152)
                result.error("E010", f"meta.{key} must be a string, not {type_label(meta[key])}.", f"meta.{key}")
        if not isinstance(meta.get("factors", []), list):
            result.error("E010", "meta.factors must be a list.", "meta.factors")
        if scenario_path is not None and isinstance(meta.get("id"), str):
            parent = scenario_path.parent.name
            if parent != meta["id"]:
                result.warning("W001", f"meta.id is '{meta['id']}', but scenario directory is '{parent}'.", "meta.id")
        check_status(meta, result, code="W002")                                                           # issue #157
    if repository is None:
        result.error("E010", "'repository' must be an object.", "repository")
    else:
        for key in ["name", "default_branch", "language"]:
            if key not in repository:
                result.error("E010", f"repository is missing required field '{key}'.", f"repository.{key}")
            elif not isinstance(repository[key], str):
                # default_branch: 1 ended generate in a TypeError traceback from git (issue #152)
                result.error("E010", f"repository.{key} must be a string, not {type_label(repository[key])}.",
                             f"repository.{key}")
        problem = default_branch_problem(repository)
        if problem is not None:
            result.error("E015", problem, "repository.default_branch")
        if "base_date" in repository:
            problem = timestamp_problem(repository["base_date"])
            if problem is not None:
                result.error("E013", f"repository.base_date {problem}.", "repository.base_date")
    if not isinstance(data.get("commits"), list):
        result.error("E010", "'commits' must be a list.", "commits")
    if not isinstance(data.get("bugs"), list):
        result.error("E010", "'bugs' must be a list.", "bugs")
    if len(commits) == 0:
        result.error("E011", "At least one commit is required.", "commits")

    commit_ids: list[str] = []
    commit_by_id: dict[str, dict] = {}
    for i, commit in enumerate(commits):
        loc = f"commits[{i}]"
        if not isinstance(commit, dict):
            result.error("E010", "Each commit must be an object.", loc)
            continue
        for key in ["id", "message", "operations"]:
            if key not in commit:
                result.error("E010", f"commit is missing required field '{key}'.", f"{loc}.{key}")
        if "message" in commit and not isinstance(commit["message"], str):
            # git commit -m got the value and raised TypeError in generate (issue #151)
            result.error("E010", f"commit.message must be a string, not {type_label(commit['message'])}.", f"{loc}.message")
        elif isinstance(commit.get("message"), str):
            # a trailing newline or a body passed, and generation failed at verification (issue #163)
            problem = commit_message_problem(commit["message"])
            if problem is not None:
                result.error("E012", f"Commit '{commit.get('id')}' message {problem}. {COMMIT_MESSAGE_RULE}",
                             f"{loc}.message")
        cid = commit.get("id")
        if isinstance(cid, str):
            if cid in commit_by_id:
                result.error("E020", f"Duplicate commit id '{cid}'.", f"{loc}.id")
            commit_by_id[cid] = commit
            commit_ids.append(cid)
        elif "id" in commit:
            # id: 0 was skipped here, and commit-map.json keys it '0' (issue #152)
            result.error("E010", f"commit.id must be a string, not {type_label(cid)}.", f"{loc}.id")
        check_commit_metadata(commit, cid, loc, result, timestamp_code="E013", author_code="E014")
        role = commit.get("role")
        if role is not None and not isinstance(role, str):
            # a list or a mapping raised TypeError on the set lookup below, out of
            # validate --json (issue #150)
            result.error("E030", f"Commit role must be a string, one of ALLOWED_ROLES, not {type_label(role)}.",
                         f"{loc}.role")
        elif role is not None and role not in ALLOWED_ROLES:
            result.error("E030", f"Unknown commit role '{role}'.", f"{loc}.role")
        operations = commit.get("operations")
        if not isinstance(operations, list):
            result.error("E010", "commit.operations must be a list.", f"{loc}.operations")
            continue
        for j, op in enumerate(operations):
            op_loc = f"{loc}.operations[{j}]"
            if not isinstance(op, dict):
                result.error("E010", "Each operation must be an object.", op_loc)
                continue
            op_type = op.get("type")
            if not isinstance(op_type, str):
                result.error("E041", "operation.type is required and must be a string.", f"{op_loc}.type")
                continue
            if op_type not in SUPPORTED_OPERATIONS:
                if op_type in FUTURE_OPERATIONS:
                    result.error("E900", f"Operation '{op_type}' is recognized but not supported by the initial generator.", f"{op_loc}.type")
                else:
                    result.error("E040", f"Unknown operation type '{op_type}'.", f"{op_loc}.type")
                continue
            required = {"write_file": ["path", "content"], "replace": ["path", "old", "new"]}[op_type]
            for key in required:
                if key not in op:
                    result.error("E041", f"Operation '{op_type}' is missing required field '{key}'.", f"{op_loc}.{key}")
            for key in TEXT_FIELDS_BY_OPERATION[op_type]:
                if key in op and not isinstance(op[key], str):
                    result.error("E041", f"Operation '{op_type}' field '{key}' must be a string, not {type_label(op[key])}.",
                                 f"{op_loc}.{key}")
            path = op.get("path")
            if isinstance(path, str):
                try:
                    validate_repo_relative_path(path)
                except PathValidationError as exc:
                    result.error("E050", f"Invalid path '{path}': {exc}", f"{op_loc}.path")
            elif "path" in op:
                # path: 123 skipped the check above, and generation refused it (issue #152)
                result.error("E041", f"Operation '{op_type}' field 'path' must be a string path, not {type_label(path)}.",
                             f"{op_loc}.path")
            for key, resolve in (("line_ending", resolve_line_ending), ("encoding", resolve_encoding)):
                # read by the operation itself, which --simulate does not do for line_ending (issue #152)
                try:
                    resolve(op)
                except OperationError as exc:
                    result.error("E042", f"Operation '{op_type}' {exc}.", f"{op_loc}.{key}")
    check_scheduled_dates(data, result, code="E013")     # PR #236 review
    check_commit_date_order(data, result, code="E016", timestamp_code="E013")    # issue #241
    check_git_control_files(data, result, code="E051", written_fields=WRITTEN_PATH_FIELDS)    # issue #164
    bug_ids: set[str] = set()
    index_by_commit = {cid: i for i, cid in enumerate(commit_ids)}
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        if not isinstance(bug, dict):
            result.error("E010", "Each bug must be an object.", loc)
            continue
        bid = bug.get("id")
        if not isinstance(bid, str):
            result.error("E010", "bug.id is required and must be a string.", f"{loc}.id")
            bid = f"<bug[{i}]>"
        elif bid in bug_ids:
            result.error("E021", f"Duplicate bug id '{bid}'.", f"{loc}.id")
        else:
            bug_ids.add(bid)
        bfc = bug.get("bug_fixing_commit")
        bics = bug.get("bug_introducing_commits")
        if not isinstance(bfc, str):
            result.error("E010", "bug_fixing_commit is required and must be a string.", f"{loc}.bug_fixing_commit")
        elif bfc not in commit_by_id:
            result.error("E060", f"bug {bid} refers to unknown bug_fixing_commit '{bfc}'.", f"{loc}.bug_fixing_commit")
        if not isinstance(bics, list):
            result.error("E010", "bug_introducing_commits is required and must be a list.", f"{loc}.bug_introducing_commits")
            bics = []
        elif len(bics) == 0:
            result.error("E082", f"bug {bid} has an empty bug_introducing_commits list.", f"{loc}.bug_introducing_commits")
        elif len(named := [bic for bic in bics if isinstance(bic, str)]) != len(set(named)):
            # Only strings can be compared here; the loop below reports any other
            # entry as E010 (a graph scenario's mappings crashed set(), issue #119).
            result.error("E083", f"bug {bid} has duplicate BIC entries.", f"{loc}.bug_introducing_commits")
        for bic in bics:
            if not isinstance(bic, str):
                result.error("E010", "Each bug_introducing_commits entry must be a string.", f"{loc}.bug_introducing_commits")
                continue
            if bic not in commit_by_id:
                result.error("E061", f"bug {bid} refers to unknown bug-introducing commit '{bic}'.", f"{loc}.bug_introducing_commits")
            elif isinstance(bfc, str) and bfc in commit_by_id and index_by_commit[bic] >= index_by_commit[bfc]:
                result.error("E070", f"BIC '{bic}' must precede BFC '{bfc}' in the initial linear-history model.", loc)
        for key in ("fault", "fix"):
            if key in bug and not isinstance(bug[key], dict):
                # every check reads them as mappings: a list skipped them all (issue #152)
                result.error("E010", f"bug {bid} {key} must be an object, not {type_label(bug[key])}.", f"{loc}.{key}")
        fault = bug.get("fault")
        if isinstance(fault, dict):
            fcommit = fault.get("commit")
            if isinstance(fcommit, str):
                if fcommit not in commit_by_id:
                    result.error("E062", f"bug {bid} fault.commit refers to unknown commit '{fcommit}'.", f"{loc}.fault.commit")
                elif fcommit not in bics:
                    result.error("E080", f"bug {bid} fault.commit '{fcommit}' is not listed in bug_introducing_commits.", f"{loc}.fault.commit")
        fix = bug.get("fix")
        if isinstance(fix, dict):
            fix_commit = fix.get("commit")
            if isinstance(fix_commit, str):
                if fix_commit not in commit_by_id:
                    result.error("E063", f"bug {bid} fix.commit refers to unknown commit '{fix_commit}'.", f"{loc}.fix.commit")
                elif fix_commit != bfc:
                    result.error("E081", f"bug {bid} fix.commit '{fix_commit}' does not match bug_fixing_commit '{bfc}'.", f"{loc}.fix.commit")
        if isinstance(bfc, str) and bfc in commit_by_id:
            role = commit_by_id[bfc].get("role")
            if role is not None and role != "bug_fixing":
                result.warning("W090", f"bug {bid} BFC '{bfc}' has role '{role}', not 'bug_fixing'.", loc)
        for bic in bics:
            if isinstance(bic, str) and bic in commit_by_id:
                role = commit_by_id[bic].get("role")
                if role is not None and role != "bug_introducing":
                    result.warning("W091", f"bug {bid} BIC '{bic}' has role '{role}', not 'bug_introducing'.", loc)
    return result


def simulate_commits(data: dict[str, Any]) -> tuple[dict[str, dict[str, str]] | None, ValidationResult]:
    result = ValidationResult()
    files: dict[str, str] = {}
    snapshots: dict[str, dict[str, str]] = {}
    for i, commit in enumerate(data.get("commits", [])):
        cid = commit.get("id", f"<commit[{i}]>")
        before = deepcopy(files)
        for j, op in enumerate(commit.get("operations", [])):
            try:
                path = op.get("path")
                if op.get("type") == "write_file" and isinstance(path, str):
                    conflict = file_path_conflict(path, files)      # issue #153
                    if conflict is not None:
                        raise OperationError(f"write_file {conflict}")
                apply_operation_to_memory(files, op)
            except OperationError as exc:
                # one code for every cause, as GE201; the message names the cause (issue #154)
                result.error("E201", f"Operation failed in commit '{cid}': {exc}", f"commits[{i}].operations[{j}]")
                return None, result
        if files == before:
            result.error("E250", f"Commit '{cid}' produces no changes.", f"commits[{i}]")
            return None, result
        snapshots[cid] = deepcopy(files)
    return snapshots, result

def validate_oracle_against_snapshots(data: dict[str, Any], snapshots: dict[str, dict[str, str]]) -> ValidationResult:
    result = ValidationResult()
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    factors = meta.get("factors")
    # W301/W320/W330 report facts that some scenarios exist to exhibit.  A
    # scenario says so in meta.factors, the same way W430/W431 are declared.
    duplicate_declared = factor_matches(factors, DUPLICATE_STATEMENT_FACTOR_RE)
    rewrite_declared = factor_matches(factors, FAULT_REWRITE_FACTOR_RE)
    commits = data.get("commits", [])
    index_by_commit = {c.get("id"): i for i, c in enumerate(commits) if isinstance(c, dict)}
    for i, bug in enumerate(data.get("bugs", [])):
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        fault = bug.get("fault", {})
        fix = bug.get("fix", {})
        bfc = bug.get("bug_fixing_commit")
        # An empty statement is in every text: an empty fix.statement passed E311 and
        # was "already present" (W330), an empty fault.statement was "absent" (issue #152)
        blank_fix = [key for key in FIX_STATEMENT_KEYS if isinstance(fix, dict) and _is_blank(fix.get(key))]
        for key in blank_fix:
            result.error("E311", f"bug {bid} fix.{key} is empty; write the text the fix leaves in (or removes from) "
                         "the file.", f"{loc}.fix.{key}")
        if isinstance(fault, dict):
            fcommit = fault.get("commit")
            ffile = fault.get("file")
            change_type = fault.get("change_type")
            blank_fault = change_type != "omission" and _is_blank(fault.get("statement"))
            if blank_fault:
                result.error("E301", f"bug {bid} fault.statement is empty; write the faulty text as fault.commit "
                             "leaves it.", f"{loc}.fault.statement")
            if fcommit in snapshots and isinstance(ffile, str):
                snap = snapshots[fcommit]
                if ffile not in snap:
                    result.error("E300", f"bug {bid} fault.file '{ffile}' does not exist at fault.commit '{fcommit}'.", f"{loc}.fault.file")
                elif change_type != "omission" and not blank_fault:
                    stmt = fault.get("statement")
                    if not isinstance(stmt, str):
                        result.error("E301", f"bug {bid} fault.statement is required for non-omission bugs.", f"{loc}.fault.statement")
                    else:
                        count = len(find_all_occurrences(snap[ffile], stmt))
                        if count == 0:
                            result.error("E301", f"bug {bid} fault.statement does not exist at fault.commit '{fcommit}'.", f"{loc}.fault.statement")
                        elif count > 1 and not duplicate_declared:
                            result.warning("W301", f"bug {bid} fault.statement appears {count} times at fault.commit '{fcommit}'; declare the duplication with a factor if intended.", f"{loc}.fault.statement")
        if isinstance(fix, dict):
            fix_commit = fix.get("commit")
            fix_file = fix.get("file")
            if fix_commit in snapshots and isinstance(fix_file, str):
                snap = snapshots[fix_commit]
                if fix_file not in snap:
                    result.error("E310", f"bug {bid} fix.file '{fix_file}' does not exist at fix.commit '{fix_commit}'.", f"{loc}.fix.file")
                elif not blank_fix:
                    fix_text = fix.get("added_statement") or fix.get("statement")
                    removed_text = fix.get("removed_statement")
                    if isinstance(fix_text, str):
                        if fix_text not in snap[fix_file]:
                            result.error("E311", f"bug {bid} fix statement does not exist at fix.commit '{fix_commit}'.", f"{loc}.fix")
                    elif not isinstance(removed_text, str):
                        result.error("E311", f"bug {bid} fix.statement, fix.added_statement or fix.removed_statement is required.", f"{loc}.fix")
                    # A fix that only deletes is declared by what it removed, so that
                    # text must be there before the fix and gone after it.  Checking
                    # only the second half accepts a statement that never existed.
                    if isinstance(removed_text, str):
                        if removed_text in snap[fix_file]:
                            result.error("E312", f"bug {bid} fix.removed_statement is still present at fix.commit '{fix_commit}'.", f"{loc}.fix.removed_statement")
                        fix_index = index_by_commit.get(fix_commit)
                        before_id = commits[fix_index - 1].get("id") if fix_index else None
                        before_files = snapshots.get(before_id) or {}
                        if before_id is not None and removed_text not in before_files.get(fix_file, ""):
                            result.error("E313", f"bug {bid} fix.removed_statement is not present in '{fix_file}' immediately before fix.commit '{fix_commit}'; the fix removed nothing.", f"{loc}.fix.removed_statement")
        if isinstance(bfc, str) and bfc in index_by_commit and index_by_commit[bfc] > 0:
            parent_id = commits[index_by_commit[bfc] - 1].get("id")
            parent_snapshot = snapshots.get(parent_id, {})
            if isinstance(fault, dict) and fault.get("change_type") != "omission":
                ffile = fault.get("file")
                stmt = fault.get("statement")
                if isinstance(ffile, str) and isinstance(stmt, str):
                    if ffile not in parent_snapshot:
                        result.warning("W320", f"bug {bid} fault.file is absent in the BFC parent '{parent_id}'.", loc)
                    elif stmt not in parent_snapshot[ffile] and not rewrite_declared:
                        result.warning("W320", f"bug {bid} fault.statement is not present immediately before BFC '{bfc}'; declare the rewrite with a factor if intended.", loc)
            if isinstance(fix, dict) and not blank_fix:
                fix_file = fix.get("file")
                fix_text = fix.get("added_statement") or fix.get("statement")
                if isinstance(fix_file, str) and isinstance(fix_text, str) and fix_file in parent_snapshot:
                    if fix_text in parent_snapshot[fix_file] and not duplicate_declared and "removed_statement" not in fix:
                        result.warning("W330", f"bug {bid} fix statement is already present before BFC '{bfc}'.", loc)
        if isinstance(fault, dict) and fault.get("change_type") == "omission":
            if "statement" in fault:
                result.warning("W350", f"bug {bid} is omission, but fault.statement is present.", f"{loc}.fault.statement")
            missing = fault.get("missing_statement")
            if "missing_statement" not in fault:
                result.error("E351", f"bug {bid} is omission, but fault.missing_statement is missing.", f"{loc}.fault.missing_statement")
            elif not isinstance(missing, str):
                # E351 tested the key only: null and a number passed (issue #237)
                result.error("E351", f"bug {bid} fault.missing_statement must be a string, not {type_label(missing)}.",
                             f"{loc}.fault.missing_statement")
            elif _is_blank(missing):
                result.error("E351", f"bug {bid} fault.missing_statement is empty; write the statement the fault "
                             "omits.", f"{loc}.fault.missing_statement")
    return result


# --- opt-in lints (shared helpers) ------------------------------------------

def error_prefix(prefix: str) -> str:
    """The error-code prefix of a lint family: ``W`` -> ``E``, ``GW`` -> ``GE``."""
    return prefix[:-1] + "E"


def lint_factors(factors: Any, result: ValidationResult, *, prefix: str, location: str = "meta.factors") -> None:
    """Vocabulary lint for meta.factors.

    Emits ``E400`` / ``GE400`` (factor is a schema key / operation name),
    ``E401`` / ``GE401`` (empty factor list) and ``E402`` / ``GE402`` (hyphen
    and underscore styles mixed within one scenario).  These were warnings
    while the suites were being migrated to the vocabulary of
    ``decisions/vocabulary.md``; since the migration is complete they are
    errors (section 6, step 4 of that decision).
    """
    if not isinstance(factors, list):
        return
    code = error_prefix(prefix)
    if not factors:
        result.error(f"{code}401", "meta.factors is empty; declare at least one semantic factor.", location)
        return
    names = [f for f in factors if isinstance(f, str)]
    for i, name in enumerate(names):
        if name in RESERVED_FACTOR_WORDS:
            result.error(f"{code}400", f"Factor '{name}' is a schema key or operation name, not a semantic factor.", f"{location}[{i}]")
    if any("-" in n for n in names) and any("_" in n for n in names):
        result.error(f"{code}402", "Factors mix hyphen and underscore styles; use one convention per scenario.", location)


def lint_readme_header(data: dict[str, Any], suite: str, scenario_path: Path, result: ValidationResult, *,
                       prefix: str) -> None:
    """W455 / GW455: the sibling README disagrees with the scenario.

    A README opens with a header rendered from the scenario file (``szzbench
    readme``, ``docs/scenario-readme.md``).  The lint reports a README without
    that header, one whose header no longer matches the YAML, and one that
    still carries a hand-written ``## Factors`` or ``## Source`` copy of what
    the header states -- the copies that drifted in issue #19.  A missing
    README is not a lint finding.
    """
    from .readme import check_readme, render_header

    readme = scenario_path.with_name("README.md")
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return
    header = render_header(data, suite)
    for problem in check_readme(text, header):
        result.warning(f"{prefix}455", f"README {problem}; run `szzbench readme --write`.", readme.name)


#: What a scenario is for (issue #14).  ``control`` verifies that a method
#: handles a specific input condition and may well be solvable by a cheap rule;
#: ``discriminating`` is designed so the declared baselines do not solve it.
#: ``szzbench baselines`` checks the declaration against the measurement.
SCENARIO_TIERS = ("control", "discriminating")


#: The graded difficulties (``decisions/vocabulary.md`` section 4).  ``advanced``
#: was the graph suite's placeholder until 2026-09-22, when the suite was graded
#: from the measured blame class.
SCENARIO_DIFFICULTIES = ("easy", "medium", "hard")


def lint_difficulty(meta: Any, result: ValidationResult, *, prefix: str) -> None:
    """``<prefix>461``: every scenario declares a graded difficulty."""
    difficulty = meta.get("difficulty") if isinstance(meta, dict) else None
    if difficulty is None:
        result.warning(f"{prefix}461", "meta.difficulty is missing; declare 'easy', 'medium' or 'hard'.", "meta.difficulty")
    elif difficulty not in SCENARIO_DIFFICULTIES:
        result.warning(f"{prefix}461", f"meta.difficulty '{difficulty}' is not one of {SCENARIO_DIFFICULTIES}; "
                       "'szzbench coverage' reports the floor the blame class sets.", "meta.difficulty")


#: The cheap-rule families a scenario may declare it defeats (issue #35).  A
#: family is defeated when none of its declared baselines solves the scenario;
#: ``szzbench baselines`` checks the declaration against the measurement.
DEFEATABLE_FAMILIES = ("blame", "shape", "position")


def lint_defeats(meta: Any, result: ValidationResult, *, prefix: str) -> None:
    """``<prefix>462``: ``meta.defeats`` names the cheap-rule families the scenario is built to make fail.

    Optional for a ``control``.  When present it must be a list of distinct
    family names, and a ``discriminating`` scenario must declare it and list
    every family, because that is what the tier means.
    """
    if not isinstance(meta, dict):
        return
    if "defeats" not in meta:
        if meta.get("tier") == "discriminating":
            # 18 discriminating scenarios declared nothing, so neither this lint nor
            # `szzbench baselines` (declared_defeated_but_solved) checked them (issue #207)
            result.warning(f"{prefix}462", "meta.defeats is missing; a discriminating scenario defeats every family: "
                           f"declare defeats: [{', '.join(DEFEATABLE_FAMILIES)}] or change the tier.", "meta.defeats")
        return
    defeats = meta.get("defeats")
    if not isinstance(defeats, list) or not all(isinstance(item, str) for item in defeats):
        result.warning(f"{prefix}462", f"meta.defeats must be a list of family names from {DEFEATABLE_FAMILIES}.", "meta.defeats")
        return
    unknown = [item for item in defeats if item not in DEFEATABLE_FAMILIES]
    if unknown:
        result.warning(f"{prefix}462", f"meta.defeats names unknown families {unknown}; use {DEFEATABLE_FAMILIES}.", "meta.defeats")
    if len(set(defeats)) != len(defeats):
        result.warning(f"{prefix}462", "meta.defeats lists a family twice.", "meta.defeats")
    if meta.get("tier") == "discriminating" and set(defeats) != set(DEFEATABLE_FAMILIES):
        result.warning(f"{prefix}462", "a discriminating scenario defeats every family; list all of "
                       f"{DEFEATABLE_FAMILIES} or change the tier.", "meta.defeats")


def lint_tier(meta: Any, result: ValidationResult, *, prefix: str) -> None:
    """``<prefix>460``: every scenario declares a tier from the vocabulary."""
    tier = meta.get("tier") if isinstance(meta, dict) else None
    if tier is None:
        result.warning(f"{prefix}460", "meta.tier is missing; declare 'control' or 'discriminating'.", "meta.tier")
    elif tier not in SCENARIO_TIERS:
        result.warning(f"{prefix}460", f"meta.tier '{tier}' is not one of {SCENARIO_TIERS}.", "meta.tier")


def lint_author_coincidence(data: dict[str, Any], suite: str, result: ValidationResult, *, prefix: str) -> None:
    """Issue #43: does some author's set of commits equal the resolved default oracle?

    That is exactly the condition under which the cheap baseline "report every
    commit written by X" returns the oracle, so the scenario is solved by the
    author rotation rather than by any signal.  The oracle is resolved the way
    the evaluator resolves it (default variant, inferred BICs); the history is
    the one the generated repository will have (``resolved_commit_authors``):
    every commit with its explicit or deterministic default author, compared as
    Git records it (``name <email>``), plus the commits ``commit_generator``
    expands, which the author baseline sees through ``git log --all``.  A
    multi-commit coincidence is a warning
    (``<prefix>413``); a one-commit oracle is solved by many cheap rules anyway,
    so its coincidence is reported as information (``<info prefix>413``).
    """
    from .evaluator import _commit_level_policy   # evaluator imports nothing from here

    try:
        required = set(_commit_level_policy(data, suite, None).required)
        history = resolved_commit_authors(data)   # scenario commits and the commits commit_generator expands
    except LINT_INPUT_ERRORS as exc:
        # a malformed date or base_date is E013 / GE071 since issue #152, and the lints run only
        # without errors; if one gets here anyway, the lint says it did not run (issue #161)
        result.warning(f"{prefix}413", f"the author lint could not resolve the history ({exc}), so the "
                       "author coincidence was not checked.", "commits")
        return
    if not required or len(history) < 2:
        return
    owned: dict[str, set[str]] = {}
    for cid, author in history:
        owned.setdefault(author, set()).add(cid)
    explicit_by_id = {c.get("id"): bool(c.get("author")) for c in (data.get("commits") or []) if isinstance(c, dict)}
    info_prefix = prefix[:-1] + "I"
    for author, ids in sorted(owned.items()):
        if ids != required:
            continue
        explicit = "explicit" if all(explicit_by_id.get(cid) for cid in ids) else "generator-assigned"
        message = (f"author {author!r} wrote exactly the required commit(s) {sorted(required)} and nothing else "
                   f"({explicit}), so the baseline 'report every commit by this author' returns the oracle by coincidence "
                   f"(issue #43); give the required commits distinct explicit authors")
        if len(required) >= 2:
            result.warning(f"{prefix}413", message, "commits")
        else:
            result.info(f"{info_prefix}413", message + " - or leave it: a one-commit oracle is solved by many cheap rules anyway", "commits")


def lint_leakage(commits: Iterable[Any], bfc_ids: set[str], result: ValidationResult, *, prefix: str) -> None:
    """Answer-cue lint for commit messages and written file contents (issue #8).

    Emits ``<prefix>410`` (role wording in a non-BFC message), ``<prefix>411``
    (logical-id prefix in any message) and ``<prefix>412`` (role wording in
    text written by write_file / replace.new / insert_after.content).
    """
    commits = list(commits)
    commit_ids = [c.get("id") for c in commits if isinstance(c, dict) and isinstance(c.get("id"), str)]
    for i, commit in enumerate(commits):
        if not isinstance(commit, dict):
            continue
        cid = commit.get("id", f"<commit[{i}]>")
        loc = f"commits[{i}]"
        message = commit.get("message")
        if isinstance(message, str):
            exposed = logical_id_reference(message, commit_ids)
            if exposed:
                result.warning(f"{prefix}411", f"Commit '{cid}' message exposes the logical-id prefix '{exposed}'.", f"{loc}.message")
            if cid not in bfc_ids:
                leak = LEAK_ROLE_RE.search(message)
                if leak:
                    result.warning(f"{prefix}410", f"Commit '{cid}' is not a bug-fixing commit, but its message discloses a role: '{leak.group(0)}'.", f"{loc}.message")
        operations = commit.get("operations")
        if not isinstance(operations, list):
            continue
        for j, op in enumerate(operations):
            if not isinstance(op, dict):
                continue
            field = LEAK_CONTENT_FIELDS.get(op.get("type"))
            if field is None or not isinstance(op.get(field), str):
                continue
            leak = LEAK_ROLE_RE.search(op[field])
            if leak:
                path = op.get("path", "?")
                result.warning(f"{prefix}412", f"Commit '{cid}' writes role wording '{leak.group(0)}' into '{path}' ({op.get('type')}.{field}).", f"{loc}.operations[{j}].{field}")


def factor_matches(factors: Any, pattern: re.Pattern[str]) -> bool:
    return isinstance(factors, list) and any(isinstance(f, str) and pattern.search(f) for f in factors)


# --- opt-in lints (classic suite) -------------------------------------------

def lint_scenario(data: dict[str, Any], snapshots: dict[str, dict[str, str]] | None, *,
                  scenario_path: Path | None = None) -> ValidationResult:
    """Run the W4xx lints on a statically valid classic scenario.

    ``snapshots`` (from :func:`simulate_commits`) enables the ghost-invariant
    and fault-line-integrity lints; without it only the vocabulary and
    leakage lints run.  ``scenario_path`` enables the lint that compares the
    scenario with its sibling README (W455).
    """
    result = ValidationResult()
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    factors = meta.get("factors")
    commits = [c for c in (data.get("commits") or []) if isinstance(c, dict)]
    bugs = [b for b in (data.get("bugs") or []) if isinstance(b, dict)]
    bfc_ids = {b.get("bug_fixing_commit") for b in bugs if isinstance(b.get("bug_fixing_commit"), str)}

    lint_factors(factors, result, prefix="W")
    lint_tier(data.get("meta"), result, prefix="W")
    lint_difficulty(data.get("meta"), result, prefix="W")
    lint_defeats(data.get("meta"), result, prefix="W")
    lint_leakage(commits, bfc_ids, result, prefix="W")
    lint_author_coincidence(data, "scenarios", result, prefix="W")
    if scenario_path is not None:
        lint_readme_header(data, "scenarios", scenario_path, result, prefix="W")
    if snapshots is not None:
        result.extend(_lint_ghost_invariants(commits, bugs, factors, snapshots))
        result.extend(_lint_fault_line_integrity(commits, bugs, factors, snapshots))
    return result


def _parent_snapshot(commits: list[dict[str, Any]], index: int, snapshots: dict[str, dict[str, str]]) -> dict[str, str]:
    if index <= 0:
        return {}
    return snapshots.get(commits[index - 1].get("id"), {})


def _removed_lines(before: dict[str, str], after: dict[str, str]) -> dict[str, list[tuple[int, str]]]:
    """Lines of ``before`` that are deleted or modified in ``after``, per path.

    Each entry is ``(line_index_in_before, text)``.
    """
    removed: dict[str, list[tuple[int, str]]] = {}
    for path, old in before.items():
        new = after.get(path)
        if new == old:
            continue
        old_lines = old.splitlines()
        if new is None:
            removed[path] = list(enumerate(old_lines))
            continue
        matcher = difflib.SequenceMatcher(None, old_lines, new.splitlines(), autojunk=False)
        hits = [(k, old_lines[k]) for tag, i1, i2, _, _ in matcher.get_opcodes() if tag in {"delete", "replace"} for k in range(i1, i2)]
        if hits:
            removed[path] = hits
    return removed


def _added_lines(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    """Lines of ``after`` that do not come from ``before``, per path."""
    added: dict[str, list[str]] = {}
    for path, new in after.items():
        old = before.get(path)
        if new == old:
            continue
        new_lines = new.splitlines()
        if old is None:
            if new_lines:
                added[path] = new_lines
            continue
        matcher = difflib.SequenceMatcher(None, old.splitlines(), new_lines, autojunk=False)
        hits = [new_lines[k] for tag, _, _, j1, j2 in matcher.get_opcodes() if tag in {"insert", "replace"} for k in range(j1, j2)]
        if hits:
            added[path] = hits
    return added


def _lint_ghost_invariants(
    commits: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    factors: Any,
    snapshots: dict[str, dict[str, str]],
) -> ValidationResult:
    """W420/W421: declared add-only BFCs and delete-only BICs must be exactly that."""
    result = ValidationResult()
    factor_set = {f for f in factors if isinstance(f, str)} if isinstance(factors, list) else set()
    add_only_declared = bool(factor_set & ADD_ONLY_FIX_FACTORS)
    delete_only_declared = bool(factor_set & DELETE_ONLY_BIC_FACTORS)
    index_by_commit = {c.get("id"): i for i, c in enumerate(commits)}
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        fault = bug.get("fault") if isinstance(bug.get("fault"), dict) else {}
        fix = bug.get("fix") if isinstance(bug.get("fix"), dict) else {}
        bfc = bug.get("bug_fixing_commit")
        bics = [b for b in (bug.get("bug_introducing_commits") or []) if isinstance(b, str)]
        omission_add_only = fault.get("change_type") == "omission" and fix.get("fix_type") in ADD_ONLY_FIX_TYPES
        declared_noise = any(DECLARED_BFC_NOISE_RE.search(f) for f in factor_set)
        if (add_only_declared or omission_add_only) and not declared_noise and bfc in index_by_commit and bfc in snapshots:
            reason = "declared as an addition-only fix" if add_only_declared else "an omission bug with an addition-only fix_type"
            before = _parent_snapshot(commits, index_by_commit[bfc], snapshots)
            for path, hits in sorted(_removed_lines(before, snapshots[bfc]).items()):
                first = hits[0][1].strip()
                result.warning("W420", f"bug {bid} is {reason}, but BFC '{bfc}' deletes or modifies {len(hits)} existing line(s) in '{path}' (first: '{first}').", loc)
        if delete_only_declared:
            for bic in bics:
                if bic not in index_by_commit or bic not in snapshots:
                    continue
                before = _parent_snapshot(commits, index_by_commit[bic], snapshots)
                for path, lines in sorted(_added_lines(before, snapshots[bic]).items()):
                    result.warning("W421", f"bug {bid} is declared as a deletion-only BIC, but BIC '{bic}' adds {len(lines)} line(s) in '{path}' (first: '{lines[0].strip()}').", loc)
    return result


def _track_line_authors(commits: list[dict[str, Any]], snapshots: dict[str, dict[str, str]]) -> dict[str, dict[str, list[str]]]:
    """Per commit, the commit id that last changed each line of each file.

    A simple difflib-based blame over the linear history: equal blocks keep
    their author, inserted or replaced lines are attributed to the commit.
    """
    authors: dict[str, list[str]] = {}
    previous: dict[str, str] = {}
    by_commit: dict[str, dict[str, list[str]]] = {}
    for commit in commits:
        cid = commit.get("id")
        current = snapshots.get(cid)
        if current is None:
            continue
        next_authors: dict[str, list[str]] = {}
        for path, content in current.items():
            new_lines = content.splitlines()
            old_content = previous.get(path)
            if old_content is None or path not in authors:
                next_authors[path] = [cid] * len(new_lines)
                continue
            old_authors = authors[path]
            merged: list[str] = []
            matcher = difflib.SequenceMatcher(None, old_content.splitlines(), new_lines, autojunk=False)
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    merged.extend(old_authors[i1:i2])
                elif tag in {"insert", "replace"}:
                    merged.extend([cid] * (j2 - j1))
            next_authors[path] = merged
        authors = next_authors
        previous = current
        by_commit[cid] = {p: list(a) for p, a in authors.items()}
    return by_commit


def _lint_fault_line_integrity(
    commits: list[dict[str, Any]],
    bugs: list[dict[str, Any]],
    factors: Any,
    snapshots: dict[str, dict[str, str]],
) -> ValidationResult:
    """W430/W431: the fault line survives to the BFC and the BFC only removes BIC lines."""
    result = ValidationResult()
    index_by_commit = {c.get("id"): i for i, c in enumerate(commits)}
    rewrite_declared = factor_matches(factors, FAULT_REWRITE_FACTOR_RE)
    # Either the BFC carries unrelated or cosmetic edits, or the repair legitimately
    # sits away from the BIC; both explain a BFC that touches non-BIC lines.
    tangled_declared = (factor_matches(factors, TANGLED_BFC_FACTOR_RE)
                        or factor_matches(factors, DECLARED_BFC_NOISE_RE)
                        or factor_matches(factors, NON_LOCAL_FIX_FACTOR_RE))
    authors_by_commit = _track_line_authors(commits, snapshots) if not tangled_declared else {}
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        bid = bug.get("id", f"<bug[{i}]>")
        fault = bug.get("fault") if isinstance(bug.get("fault"), dict) else {}
        bfc = bug.get("bug_fixing_commit")
        bics = {b for b in (bug.get("bug_introducing_commits") or []) if isinstance(b, str)}
        if bfc not in index_by_commit:
            continue
        bfc_index = index_by_commit[bfc]
        stmt = fault.get("statement")
        ffile = fault.get("file")
        fcommit = fault.get("commit")
        if (
            not rewrite_declared
            and fault.get("change_type") != "omission"
            and isinstance(stmt, str) and isinstance(ffile, str)
            and fcommit in index_by_commit
        ):
            for k in range(index_by_commit[fcommit] + 1, bfc_index):
                cid = commits[k].get("id")
                if cid in bics or cid not in snapshots:
                    continue
                before = _parent_snapshot(commits, k, snapshots)
                after = snapshots[cid]
                if ffile in before and stmt in before[ffile] and stmt not in after.get(ffile, ""):
                    result.warning("W430", f"bug {bid}: intermediate non-BIC commit '{cid}' removes the fault statement from '{ffile}' before BFC '{bfc}'; declare the rewrite with a factor if intended.", f"commits[{k}]")
        if not tangled_declared and bfc_index > 0 and bfc in snapshots:
            parent_id = commits[bfc_index - 1].get("id")
            before = snapshots.get(parent_id, {})
            parent_authors = authors_by_commit.get(parent_id, {})
            for path, hits in sorted(_removed_lines(before, snapshots[bfc]).items()):
                line_authors = parent_authors.get(path, [])
                foreign = sorted({line_authors[k] for k, _ in hits if k < len(line_authors) and line_authors[k] not in bics})
                if foreign:
                    first = next(text for k, text in hits if k < len(line_authors) and line_authors[k] in foreign).strip()
                    result.warning("W431", f"bug {bid} BFC '{bfc}' deletes or modifies line(s) in '{path}' last changed by non-BIC commit(s) {foreign} (first: '{first}'); declare a tangled BFC with a factor if intended.", loc)
    return result


# --- index consistency ------------------------------------------------------

#: The one shape of both index files (issue #200): ``scenarios`` at the top level, and
#: entries with these keys, in this order.  All but ``path`` and ``readme`` are copied
#: from the scenario's ``meta``.  The graph index had a ``schema_version`` that called it a
#: draft, a ``description``, a ``scenario_count`` and ``notes``, and entries without
#: ``slug`` and ``difficulty``; the classic entries had no ``readme``.
INDEX_TOP_LEVEL_KEYS = ("scenarios",)
INDEX_ENTRY_KEYS = ("id", "title", "slug", "category_code", "category", "factors", "difficulty", "status", "path",
                    "readme")


def load_index(index_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """``index_path`` as loaded, or None and why it cannot be read, in words that name the index (issue #158).

    ``load_yaml`` words its messages for a scenario file, and ``validate-index``
    (IE001) and the builders passed them on: an empty ``index.yml`` read "The
    root of scenario.yml must be a mapping/object", and a missing one "Cannot
    read scenario file: [Errno 2] ...".
    """
    name = index_path.name
    try:
        raw = index_path.read_bytes()
    except FileNotFoundError:
        return None, f"{name} does not exist."
    except OSError as exc:
        return None, f"Cannot read {name}: {exc.strerror or exc}."
    if not raw.strip():
        return None, f"{name} is empty."
    data, result = load_yaml(index_path)
    if data is not None:
        return data, None
    finding = result.findings[0]
    if finding.code == "E002":
        return None, f"The root of {name} must be a mapping/object."
    return None, finding.message        # E000 (not UTF-8) and E001 (YAML) name no scenario file


def _index_readme_problem(readme: Any, repository_root: Path) -> str | None:
    """Why an index entry's ``readme`` names no README ``validate-index`` can see, or None (issue #158).

    ``Path.is_file`` raises ``PermissionError`` and the other ``OSError``s on
    Python 3.10-3.13 (3.14 returns False), and ``ValueError`` for a NUL byte, so
    an entry pointing into a directory without search permission ended
    ``validate-index`` in a traceback (PR #261 review).
    """
    if not isinstance(readme, str) or not readme:
        return "names no file"
    try:
        if (repository_root / readme).is_file():
            return None
    except (OSError, ValueError) as exc:
        return f"cannot be checked ({getattr(exc, 'strerror', None) or exc})"
    return "names no file"


def validate_index_file(index_path: Path, root: Path, scenario_filename: str) -> ValidationResult:
    """Check one index.yml against the scenario directories under ``root``.

    IE codes are errors, IW codes warnings; locations are prefixed with the
    index path so that results for several indexes can be merged.
    """
    result = ValidationResult()
    prefix = index_path.as_posix()
    data, problem = load_index(index_path)
    if data is None:
        result.error("IE001", f"Cannot load index: {problem}", prefix)
        return result
    for key in data:
        if key not in INDEX_TOP_LEVEL_KEYS:
            # the graph index's schema_version, description, scenario_count and notes, which
            # nothing read but IE010 / IE011, now retired (issue #200)
            result.warning("IW004", f"The index has a top-level key {key!r}, which nothing reads; an index has "
                           "'scenarios' only.", f"{prefix}:{key}")
    entries = data.get("scenarios")
    if not isinstance(entries, list):
        result.error("IE002", "'scenarios' must be a list.", f"{prefix}:scenarios")
        return result
    if not root.is_dir():
        result.error("IE003", f"Scenario root '{root.as_posix()}' is not a directory.", prefix)
        return result

    expected_rel = lambda sid: f"{root.name}/{sid}/{scenario_filename}"  # noqa: E731
    # the entries' paths are relative to the directory that holds the root (IW023)
    repository_root = root.absolute().parent
    seen: set[str] = set()
    previous_id: str | None = None
    retired = read_retired_ids(root)
    for i, entry in enumerate(entries):
        loc = f"{prefix}:scenarios[{i}]"
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            result.error("IE020", "Index entry must be an object with a string id.", loc)
            continue
        sid = entry["id"]
        if sid in seen:
            result.error("IE021", f"Duplicate index entry '{sid}'.", f"{loc}.id")
            continue
        seen.add(sid)
        if previous_id is not None and sid < previous_id:
            # the builders append a new entry at the end, and the Scenario Editor
            # inserts one, in id order (issue #111); nothing kept the order (issue #158)
            result.warning("IW048", f"Index entry '{sid}' comes after '{previous_id}'; the index lists its entries "
                           "in id order.", f"{loc}.id")
        previous_id = sid
        if sid in retired:
            # A withdrawn scenario leaves a gap that stays one (issue #112).
            result.error("IE047", f"Index entry '{sid}' uses a retired id (docs/retired-ids.md); ids are never reused.", f"{loc}.id")
        # Both indexes have entries of one shape (issue #200).  The comparisons below
        # skip a key the entry does not have, so the graph index's missing slug and
        # difficulty were never compared.
        for key in entry:
            if key not in INDEX_ENTRY_KEYS:
                result.warning("IW004", f"Index entry '{sid}' has a key {key!r}, which nothing reads; an entry has "
                               f"{', '.join(INDEX_ENTRY_KEYS)}.", f"{loc}.{key}")
        for key in INDEX_ENTRY_KEYS[1:]:
            if key not in entry:
                result.error("IE046", f"Index entry '{sid}' has no {key}; an entry has {', '.join(INDEX_ENTRY_KEYS)}.",
                             f"{loc}.{key}")
        scenario_file = root / sid / scenario_filename
        if not scenario_file.is_file():
            result.error("IE022", f"Index entry '{sid}' has no scenario file at '{expected_rel(sid)}'.", loc)
            continue
        path_value = entry.get("path")
        if isinstance(path_value, str) and Path(path_value).as_posix() != expected_rel(sid):
            result.warning("IW023", f"Index entry '{sid}' path is '{path_value}', expected '{expected_rel(sid)}'.", f"{loc}.path")
        if "readme" in entry:
            # nothing looked at the graph index's readme (issue #158); both indexes have one since issue #200
            readme = entry["readme"]
            problem = _index_readme_problem(readme, repository_root)
            if problem is not None:
                result.error("IE024", f"Index entry '{sid}' readme {readme!r} {problem} (expected "
                             f"'{root.name}/{sid}/README.md').", f"{loc}.readme")
        scenario_data, scenario_load = load_yaml(scenario_file)
        if scenario_data is None:
            detail = "; ".join(f.message for f in scenario_load.findings)
            result.error("IE042", f"Scenario file for '{sid}' cannot be loaded: {detail}", loc)
            continue
        meta = scenario_data.get("meta") if isinstance(scenario_data.get("meta"), dict) else {}
        if meta.get("id") != sid:
            result.error("IE040", f"Index entry id '{sid}' does not match meta.id '{meta.get('id')}' in {expected_rel(sid)}.", f"{loc}.id")
        if "title" in entry and entry.get("title") != meta.get("title"):
            result.error("IE041", f"Index entry '{sid}' title '{entry.get('title')}' does not match meta.title '{meta.get('title')}'.", f"{loc}.title")
        if "status" in entry and entry.get("status") != meta.get("status"):
            # The third mirrored field to drift in three PRs (issue #19).
            result.error("IE045", f"Index entry '{sid}' status '{entry.get('status')}' does not match meta.status '{meta.get('status')}'.", f"{loc}.status")
        # title, status and factors each drifted before they were checked.  The
        # index copies four more scalars from meta; nothing checked those either.
        for key in ("slug", "category", "category_code", "difficulty"):
            if key in entry and entry.get(key) != meta.get(key):
                result.error("IE046", f"Index entry '{sid}' {key} '{entry.get(key)}' does not match meta.{key} '{meta.get(key)}'.", f"{loc}.{key}")
        if "factors" in entry:
            # The index repeats a field that changes with the scenario, which is
            # how it drifted before (issue #19); the copy has to be checked.  Both
            # sides are unvalidated input here - validate_index_file does not run
            # scenario validation first - so a non-list is reported rather than
            # coerced: list() on an int raises, and list() on a mapping silently
            # compares its keys (PR #46 review).
            index_factors, meta_factors = entry.get("factors"), meta.get("factors")
            bad = [(name, value) for name, value in (("index entry", index_factors), ("meta.factors", meta_factors))
                   if value is not None and not isinstance(value, list)]
            if bad:
                for name, value in bad:
                    result.error("IE044", f"Index entry '{sid}': {name} factors must be a list, got {type(value).__name__}.", f"{loc}.factors")
            elif list(index_factors or []) != list(meta_factors or []):
                result.error("IE043", f"Index entry '{sid}' factors {list(index_factors or [])} do not match meta.factors {list(meta_factors or [])}.", f"{loc}.factors")

    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / scenario_filename).is_file() and child.name not in seen:
            result.error("IE030", f"Scenario directory '{root.name}/{child.name}' has no index entry.", f"{prefix}:scenarios")
        if child.is_dir() and child.name in retired and child.name not in seen:
            result.error("IE047", f"Scenario directory '{root.name}/{child.name}' uses a retired id (docs/retired-ids.md); ids are never reused.", f"{prefix}:scenarios")
    return result


def validate_scenario_indexes(scenarios_root: Path, advanced_scenarios_root: Path) -> ValidationResult:
    """Validate scenarios/index.yml and advanced-scenarios/index.yml."""
    result = ValidationResult()
    result.extend(validate_index_file(scenarios_root / "index.yml", scenarios_root, "scenario.yml"))
    result.extend(validate_index_file(advanced_scenarios_root / "index.yml", advanced_scenarios_root, "scenario.graph.yml"))
    return result
