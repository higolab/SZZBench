from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Any
import difflib

from .operations import type_label
from .gitutils import scenario_default_branch
from .paths import file_system_key, ref_name_problem, ref_names_clash
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
# Branch names (issue #239)
# ---------------------------------------------------------------------------

def branch_name_problems(scenario: dict[str, Any]) -> list[tuple[str, str, str]]:
    """``(code, location, message)`` for every branch name generation cannot create as written (GE023, GE024).

    The names are ``repository.default_branch`` (``main`` without the key)
    and every commit's ``branch``, read as ``gitutils.commit_branch`` reads
    them: without the key, or with a blank value (null), a commit is on the
    default branch; an empty string is a name, and not a valid one.  Each
    name is checked once, where the scenario first names it: GE023 when it is
    not a branch name the generator can create (``paths.ref_name_problem``),
    GE024 when it cannot sit beside a name before it
    (``paths.ref_names_clash``): the two differ only in letter case (or in
    code points HFS+ ignores; a name not in NFC is GE023 already), which
    macOS (and Windows, for letter case) reads as one name, or one is a
    directory of the other.  A value that is not a
    string is GE022's or GE035's.  ``validate-graph`` and the generator ask
    this, the generator before ``git init`` (issue #239): both fields were
    checked for their type only, a name Git refuses stopped generation with
    Git's message, and on macOS ``Feature`` beside ``feature`` became one
    branch while verification passed.  The tag names of
    ``graph.ref_lifecycle`` are compared with these names by GE158.
    """
    named: list[tuple[str, Any]] = [("repository.default_branch", scenario_default_branch(scenario))]
    commits = scenario.get("commits") if isinstance(scenario.get("commits"), list) else []
    for i, commit in enumerate(commits):
        if isinstance(commit, dict) and commit.get("branch") is not None:
            named.append((f"commits[{i}].branch", commit["branch"]))
    problems: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    valid: list[tuple[str, str]] = []              # (name, where it is first named), for the clashes
    for where, name in named:
        if not isinstance(name, str) or name in seen:
            continue
        seen.add(name)
        problem = ref_name_problem(name, "branch")
        if problem is not None:
            hint = "; without the key the commit is on the default branch" if name == "" and where != named[0][0] else ""
            problems.append(("GE023", where, f"{where} {name!r} is not a valid branch name: {problem}{hint}."))
            continue
        for other, other_where in valid:
            clash = ref_names_clash(name, other)
            if clash is None:
                continue
            them = (f"the default branch '{other}'" if other_where == named[0][0]
                    else f"the branch '{other}' ({other_where})")
            if clash == "spelling":
                spelt = "" if (name + other).isascii() else f" (spelt {name!a} and {other!a})"
                problems.append(("GE024", where, f"{where} '{name}' differs only in letter case or Unicode normalization "
                                 f"from {them}{spelt}: macOS (and Windows, for letter case) stores both as one ref, so "
                                 "generation would depend on the platform."))
            else:
                problems.append(("GE024", where, f"{where} '{name}' and {them} cannot both be branches: Git stores a "
                                 "ref as a file, and the one would be a directory of the other."))
            break
        else:
            valid.append((name, where))
    return problems


# ---------------------------------------------------------------------------
# graph.ref_lifecycle (issue #229)
# ---------------------------------------------------------------------------

#: The keys of ``graph.ref_lifecycle``, and of each of its tags.
REF_LIFECYCLE_KEYS = ("delete_branches", "tags")
REF_LIFECYCLE_TAG_KEYS = ("name", "commit")


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
            problem = ref_name_problem(name, "tag")
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
        clash = ref_names_clash(name, other)
        if clash == "spelling":
            return (f"differs from {loc}[{j}].name '{other}' only in letter case or Unicode normalization: macOS "
                    "(and Windows, for letter case) stores both as one ref, so generation would depend on the platform.")
        if clash == "directory":
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
