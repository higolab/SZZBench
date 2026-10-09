from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any
import difflib

from .operations import type_label
from .paths import file_system_key
from .scenario import load_yaml
from .findings import ValidationResult


def load_graph_scenario(path: Path) -> tuple[dict[str, Any] | None, ValidationResult]:
    data, result = load_yaml(path)
    if data is None:
        return None, result
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str) or "graph" not in schema_version:
        result.error("GE001", "scenario.graph.yml must use the graph schema_version 'graph-1.0'.", "schema_version")
    return data, result


def commit_id_of(entry: Any) -> str | None:
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict) and isinstance(entry.get("commit"), str):
        return entry["commit"]
    return None


#: Normalized BIC roles whose commits form the inferred `required` set when a
#: graph scenario declares no explicit commit-level oracle.
DIRECT_BIC_ROLES: frozenset[str] = frozenset({"direct", "reintroducing", "contributing"})


def normalize_bic_role(role: Any) -> str:
    """Map a bug-entry role spelling to one of the canonical role classes.

    Scenarios use many free-form spellings (``direct_squash_bic``,
    ``merge_introducing``, ``old_origin_bic``, ...). The evaluator and the
    verifier only need to know which class a role belongs to:

    - ``direct``: the commit itself introduced the fault (also the default
      when the role is missing);
    - ``origin``: the commit is where a copied/replayed fault first appeared;
    - ``reintroducing``: the commit brought a previously fixed fault back;
    - ``contributing``: the commit is one of several that jointly caused it;
    - ``other``: anything not covered above.
    """
    if role is None:
        return "direct"
    if not isinstance(role, str):
        return "other"
    value = role.strip().lower()
    if not value:
        return "direct"
    if "origin" in value:
        return "origin"
    if "reintroduc" in value:
        return "reintroducing"
    if "contribut" in value:
        return "contributing"
    if value.startswith("direct") or "introduc" in value:
        return "direct"
    return "other"


def graph_bic_entries(bug: dict[str, Any], *, roles: frozenset[str] | set[str] | None = None) -> list[dict[str, Any]]:
    """Return the bug's BIC entries as dicts.

    When ``roles`` is given, only entries whose normalized role (see
    :func:`normalize_bic_role`) is in that set are returned.
    """
    entries = []
    for raw in bug.get("bug_introducing_commits", []) or []:
        if isinstance(raw, str):
            entries.append({"commit": raw, "role": "direct"})
        elif isinstance(raw, dict):
            entries.append(raw)
    if roles is not None:
        entries = [entry for entry in entries if normalize_bic_role(entry.get("role")) in roles]
    return entries


def graph_bfc_entries(bug: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(bug.get("bug_fixing_commits"), list):
        entries = []
        for raw in bug.get("bug_fixing_commits", []) or []:
            if isinstance(raw, str):
                entries.append({"commit": raw, "role": "complete_fix"})
            elif isinstance(raw, dict):
                entries.append(raw)
        return entries
    if isinstance(bug.get("bug_fixing_commit"), str):
        return [{"commit": bug["bug_fixing_commit"], "role": "complete_fix"}]
    return []


def graph_faults(bug: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(bug.get("faults"), list):
        return [f for f in bug["faults"] if isinstance(f, dict)]
    if isinstance(bug.get("fault"), dict):
        return [bug["fault"]]
    return []


def graph_fixes(bug: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(bug.get("fixes"), list):
        return [f for f in bug["fixes"] if isinstance(f, dict)]
    if isinstance(bug.get("fix"), dict):
        return [bug["fix"]]
    return []


# ---------------------------------------------------------------------------
# graph.ref_lifecycle (issue #229)
# ---------------------------------------------------------------------------

#: The keys of ``graph.ref_lifecycle``, and of each of its tags.
REF_LIFECYCLE_KEYS = ("delete_branches", "tags")
REF_LIFECYCLE_TAG_KEYS = ("name", "commit")

#: The characters Git refuses anywhere in a ref name, besides the control
#: characters (refs.c ``refname_disposition``; ``*`` only outside refspec patterns).
_REF_NAME_FORBIDDEN = {" ": "a space", "~": "'~'", "^": "'^'", ":": "':'", "?": "'?'", "*": "'*'", "[": "'['",
                       "\\": "a backslash", "\x7f": "the control character DEL"}


def tag_name_problem(name: str) -> str | None:
    """Why ``git tag <name>`` refuses ``name``, or None when it accepts it.

    The rules of ``git check-ref-format refs/tags/<name>`` (refs.c
    ``check_refname_format``), and the two names ``git tag`` refuses on top of
    them: one that starts with ``-``, which it would read as an option, and
    ``HEAD``, which Git 2.50 refuses and Git 2.39 accepts.
    """
    if name == "":
        return "it is empty"
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return "it is not valid UTF-8"
    if name.startswith("-"):
        return "it starts with '-', which git tag reads as an option"
    if name == "HEAD":
        return "it is HEAD, which recent versions of git tag refuse"
    for char in name:
        if char in _REF_NAME_FORBIDDEN:
            return f"it contains {_REF_NAME_FORBIDDEN[char]}"
        if ord(char) < 0x20:
            return f"it contains the control character {char!r}"
    if ".." in name:
        return "it contains '..'"
    if "@{" in name:
        return "it contains '@{'"
    components = name.split("/")
    if "" in components:
        return "it has an empty component (a '/' at its start or end, or '//')"
    for component in components:
        if component.startswith("."):
            return f"its component '{component}' starts with '.'"
        if component.endswith(".lock"):
            return f"its component '{component}' ends with '.lock'"
        if file_system_key(component).endswith(".lock"):
            # Git accepts v1.LOCK, but on macOS and Windows its file is v1's lock file, so a
            # later tag v1 fails with Git's "File exists" after the first one was created (PR #231 review)
            return (f"its component '{component}' ends with '.lock' in another spelling, which a file system that "
                    "ignores letter case or Unicode normalization (macOS; Windows ignores case) reads as Git's lock file")
    if name.endswith("."):
        return "it ends with '.'"
    return None


def _non_text_label(value: Any) -> str:
    """``value``'s type as a message names it, with a hint for a value YAML read as a number."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{type_label(value)} (YAML reads an unquoted {value!r} as a number; quote it)"
    return type_label(value)


def _unknown_key_hint(key: Any, keys: tuple[str, ...]) -> str:
    """The near-miss hint GE048 gives for a misspelt key."""
    near = difflib.get_close_matches(key, keys, n=1) if isinstance(key, str) else []
    return f"the key is '{near[0]}'" if near else f"the keys are {' and '.join(keys)}"


def ref_lifecycle_problems(
    lifecycle: Any,
    *,
    commit_ids: Collection[str],
    branches: Collection[str],
    default_branch: str,
) -> list[tuple[str, str, str]]:
    """``(code, location, message)`` for every rule ``graph.ref_lifecycle`` breaks (GE152-GE158).

    ``commit_ids`` are the commits a tag may name, generated ``<owner>.g<N>``
    ones included; ``branches`` are the branches some commit is on.  Both
    ``validate-graph`` and the generator ask this, the generator before it
    changes the first ref (issue #229).  Only the generator read the section,
    and only when it was an object: a misspelt key or another type was
    ignored, a tag named like a branch made the branch's name ambiguous, and
    a name Git refuses or an entry listed twice stopped generation with Git's
    own message after the earlier entries had changed the refs.
    """
    where = "graph.ref_lifecycle"
    problems: list[tuple[str, str, str]] = []
    if not isinstance(lifecycle, dict):
        return [("GE152", where, f"{where} must be an object with the keys delete_branches and tags, "
                 f"not {type_label(lifecycle)}.")]
    for key in lifecycle:
        if key not in REF_LIFECYCLE_KEYS:
            problems.append(("GE152", f"{where}.{key}", f"{where} has an unknown key {key!r}; "
                             f"{_unknown_key_hint(key, REF_LIFECYCLE_KEYS)}."))

    deleted: dict[str, int] = {}                   # branch name -> its first position in delete_branches
    if "delete_branches" in lifecycle:
        loc = f"{where}.delete_branches"
        delete_branches = lifecycle["delete_branches"]
        if not isinstance(delete_branches, list):
            problems.append(("GE153", loc, f"{loc} must be a list of branch names, not {type_label(delete_branches)}."))
            delete_branches = []
        for i, name in enumerate(delete_branches):
            if not isinstance(name, str):
                problems.append(("GE153", f"{loc}[{i}]", f"{loc}[{i}] must be a branch name, not {_non_text_label(name)}."))
            elif name in deleted:
                problems.append(("GE153", f"{loc}[{i}]", f"{loc}[{i}] names branch '{name}' again "
                                 f"(also {loc}[{deleted[name]}]); a branch is deleted once."))
            else:
                deleted[name] = i
                if name not in branches:
                    problems.append(("GE154", f"{loc}[{i}]", f"{loc}[{i}] names branch '{name}', which no commit is "
                                     f"on (branches: {', '.join(sorted(branches)) or 'none'})."))

    if "tags" in lifecycle:
        loc = f"{where}.tags"
        tags = lifecycle["tags"]
        if not isinstance(tags, list):
            problems.append(("GE155", loc, f"{loc} must be a list of {{name, commit}} objects, not {type_label(tags)}."))
            tags = []
        names: list[tuple[int, str]] = []          # the well-formed tag names, for the collisions below
        branch_names = [b for b in (*branches, default_branch) if isinstance(b, str)]
        for i, tag in enumerate(tags):
            entry = f"{loc}[{i}]"
            if not isinstance(tag, dict):
                problems.append(("GE155", entry, f"{entry} must be an object with name and commit, not {type_label(tag)}."))
                continue
            for key in tag:
                if key not in REF_LIFECYCLE_TAG_KEYS:
                    problems.append(("GE155", f"{entry}.{key}", f"{entry} has an unknown key {key!r}; "
                                     f"{_unknown_key_hint(key, REF_LIFECYCLE_TAG_KEYS)}."))
            for key in REF_LIFECYCLE_TAG_KEYS:
                if key not in tag:
                    problems.append(("GE155", f"{entry}.{key}", f"{entry} has no '{key}'."))
                elif not isinstance(tag[key], str):
                    problems.append(("GE155", f"{entry}.{key}", f"{entry}.{key} must be a string, not {_non_text_label(tag[key])}."))
            commit, name = tag.get("commit"), tag.get("name")
            if isinstance(commit, str) and commit not in commit_ids:
                problems.append(("GE156", f"{entry}.commit", f"{entry}.commit names '{commit}', which is not a "
                                 "commit of the scenario (declared, or generated by commit_generator)."))
            if not isinstance(name, str):
                continue
            problem = tag_name_problem(name)
            if problem is not None:
                problems.append(("GE157", f"{entry}.name", f"{entry}.name {name!r} is not a tag name Git accepts: "
                                 f"{problem}."))
                continue
            collision = _tag_name_collision(name, names, loc, branch_names, deleted)
            if collision is not None:
                problems.append(("GE158", f"{entry}.name", f"{entry}.name '{name}' {collision}"))
            names.append((i, name))
    return problems


def _tag_name_collision(name: str, earlier: list[tuple[int, str]], loc: str, branches: list[str],
                        deleted: Collection[str]) -> str | None:
    """Why ``name`` cannot sit beside the earlier tags and the branches, or None.

    Names are compared by ``paths.file_system_key``, as the file systems of
    macOS and Windows compare the files Git stores refs in: there, ``V1`` is
    the tag ``v1``, ``café`` is ``café`` spelt with a combining accent, and a
    tag ``Main`` is what Git finds first for ``main`` (issue #175 made a
    case-only rename an error for the same reason; PR #231 review added
    normalization).
    """
    key = file_system_key(name)
    for j, other in earlier:
        if other == name:
            return f"is the name of {loc}[{j}] as well; Git keeps one tag per name."
        other_key = file_system_key(other)
        if other_key == key:
            return (f"differs from {loc}[{j}].name '{other}' only in letter case or Unicode normalization: macOS "
                    "(and Windows, for letter case) stores both as one ref, so generation would depend on the platform.")
        if key.startswith(other_key + "/") or other_key.startswith(key + "/"):
            return (f"and {loc}[{j}].name '{other}' cannot both be tags: Git stores a ref as a file, and the one "
                    "would be a directory of the other.")
    matches = sorted(branch for branch in set(branches) if file_system_key(branch) == key)
    if not matches:
        return None
    branch = name if name in matches else matches[0]
    same = "is the name of" if branch == name else "differs only in letter case or Unicode normalization from"
    if branch in deleted:
        return (f"{same} the branch '{branch}', which delete_branches deletes: commit-map.json records commits on "
                f"the branch '{branch}', and the repository would have a tag of that name instead.")
    where = "" if branch == name else " on macOS (and on Windows, for letter case)"
    return (f"{same} the branch '{branch}': the name would be ambiguous, and{where} Git reads a bare "
            f"'{branch}' as the tag (git log {branch} shows the tagged commit, not the branch tip).")
