from __future__ import annotations

from datetime import datetime, timezone

from pathlib import Path
from typing import Any
import difflib
import re
import reprlib

from .evaluator import (_UNREAD_GRAPH_ORACLE_SECTIONS, _commit_level_policy, _is_int, _number_value,
                        _selected_evaluation_variant, _string_list, classify_prediction)
from .findings import ValidationResult
from .graph_operations import (PATH_FIELDS_BY_OPERATION, REQUIRED_FIELDS_BY_OPERATION, SUPPORTED_GRAPH_OPERATIONS,
                               WRITTEN_PATH_FIELDS_BY_OPERATION, commit_generator_changes, commit_generator_plan,
                               decode_content_base64)
from .graph_scenario import (branch_name_problems, commit_id_of, graph_bfc_entries, graph_bic_entries, graph_faults,
                             graph_fixes, load_graph_scenario, ref_lifecycle_problems)
from .graph_simulator import git_performed_features, simulate_graph_scenario, simulate_graph_scenario_with_git
from .gitutils import (REWRITE_SOURCE_KEYS, GitError, commit_branch, format_timestamp, history_graph, parse_timestamp,
                       planned_generated_commits, reachable_commit_ids, scenario_default_branch)
from .operations import OperationError, resolve_encoding, resolve_line_ending, type_label
from .paths import PathValidationError, file_system_key, validate_repo_relative_path
from .policies import SUPPORTED_EVALUATION_POLICIES
from .readme import GRAPH_CONTEXT_SECTIONS
from .validator import (ALLOWED_ROLES, COMMIT_MESSAGE_RULE, LINT_INPUT_ERRORS, check_commit_date_order,
                        check_commit_metadata, check_git_control_files, check_scheduled_dates, check_status,
                        classic_scenario_guard, commit_message_problem, lint_author_coincidence, lint_defeats,
                        lint_difficulty, lint_factors, lint_leakage, lint_readme_header, lint_tier, timestamp_problem)

GRAPH_ID_RE = re.compile(r"^SZZG-\d{4}$")

#: The schema_version of a graph scenario since the suite was frozen (README, issue #19);
#: every shipped one declares it (issue #152).
GRAPH_SCHEMA_VERSION = "graph-1.0"

#: The operations whose ``line_ending`` / ``encoding`` graph generation reads
#: (``graph_operations._apply_graph_operation``); GE061 checks them there (issue #152).
#: ``format_file``, ``move_entity`` and ``copy_entity`` read ``line_ending`` since issue #181.
#: ``encoding`` is ``utf-8`` or ``utf-8-sig``, the codecs the replay models, as in the
#: classic suite (E042): any other codec Python knows passed, and the replay, which did
#: not read the key, accepted what generation then refused (issue #240).
LINE_ENDING_OPERATIONS = frozenset({"write_file", "replace", "insert_after", "format_file", "move_entity", "copy_entity"})
ENCODING_OPERATIONS = frozenset({"write_file", "replace", "insert_after", "move_entity", "copy_entity",
                                 "write_generated_text_file", "format_file"})

# Shared with the evaluator via szzbench.policies (kept under the old name for callers).
ALLOWED_EVALUATION_POLICIES = SUPPORTED_EVALUATION_POLICIES

# History-rewrite metadata that must point at earlier commits (like GE043 for
# cherry_pick_of / backport_of).  rebase_of may be a list for squash-rebases.
REWRITE_REFERENCE_KEYS: dict[str, tuple[type, ...]] = {
    "rebase_of": (str, list),
    "squashes": (list,),
    "revert_of": (str,),
}

#: The keys by which a commit declares that it rewrites earlier commits, which a
#: branch may then leave behind (GW151); ``revert_of`` keeps its target.
REWRITE_DECLARATION_KEYS = ("rebase_of", "squashes")

#: The operation fields whose value is text generation writes or matches.  They
#: were read through str(): a blank `content:` wrote the text `None` into the file,
#: and the error came later, as "replace.old not found" on another operation (issue #151).
TEXT_FIELDS_BY_OPERATION = {"write_file": ("content",), "replace": ("old", "new"), "insert_after": ("anchor", "content")}

# Consumer-compatible role vocabulary (issue #19); see graph_verifier / evaluator.
ALLOWED_BIC_ROLES = frozenset({"direct", "origin", "contributing", "reintroducing"})
ALLOWED_BFC_ROLES = frozenset({"complete_fix", "partial_fix"})

# Operations whose generated result only approximates the declared intent.
#: Operations whose generated result only approximates the intent.  ``commit_generator``
#: and ``chmod`` used to be listed here; since the generator expands commit_generator into
#: real commits and enables core.filemode for chmod scenarios, both are faithful and the
#: codes GW441/GW442 are retired.
APPROXIMATE_OPERATIONS: dict[str, tuple[str, str]] = {
    "move_entity": ("GW440", "move_entity is a file-level approximation: the whole source file is copied under a marker header, no entity is extracted."),
    "copy_entity": ("GW440", "copy_entity is a file-level approximation: the whole source file is copied under a marker header, no entity is extracted."),
    "apply_patch": ("GW443", "apply_patch is recognized by the schema but not implemented; generation will fail."),
}

# expected_szz.commit_level lists that may name an origin BIC.
EXPECTED_SZZ_COMMIT_LISTS = ("required", "acceptable_related", "related_origins", "related_but_not_correct", "relevant")

#: The keys of a fault or fix location that hold a statement (GE104, issue #237).
LOCATION_STATEMENT_KEYS = ("statement", "added_statement", "removed_statement", "missing_statement")

#: Where generation takes the subject, the author date and the author of ``inherit_message``,
#: ``inherit_author_date`` and ``inherit_author`` from: the first of these that is a commit id
#: (``gitutils.rewrite_source_id``), GE074 (issue #179).
INHERIT_SOURCE_KEYS = REWRITE_SOURCE_KEYS
#: What each inherit option makes the commit take from its source.
INHERITED_FIELDS = {"inherit_message": "message", "inherit_author_date": "author_date", "inherit_author": "author"}

# --- the keys of a graph scenario (issue #160) --------------------------------
#
# The loader kept every key and the checks read the ones they knew, so a key
# nothing reads -- a misspelt `parent:`, a leftover such as `rebase_patch_modified`
# -- was neither reported nor used.  Each object below has the keys that
# generation, validation, simulation, verification or evaluation read, and those
# docs/graph-schema.md describes; any object may also carry `notes` and keys that
# start with `x-`, which are free-form.  Anything else is GW004.  What is inside the
# context sections (`scenario_design`, `issues`, `work_items`, ...) and the oracle
# sections the evaluator does not score (`line_level`, `entity_level`, `bug_level`,
# `work_item_level`, `bug_instances`) is free-form; `graph.ref_lifecycle` has its
# own check (GE152, GE155).  docs/graph-schema.md lists the same keys, and a test
# compares the two.

#: The key every object may carry as a free-form note, and the prefix of the others.
FREE_FORM_KEY = "notes"
FREE_FORM_PREFIX = "x-"

#: The top level: the sections every scenario has, ``scenario_design``, and the context
#: sections the README header lists (``readme.GRAPH_CONTEXT_SECTIONS``).
TOP_LEVEL_KEYS = frozenset({"schema_version", "meta", "repository", "graph", "commits", "bugs", "expected_szz",
                            "scenario_design", *GRAPH_CONTEXT_SECTIONS})
META_KEYS = frozenset({"id", "title", "slug", "description", "category", "category_code", "factors",
                       "difficulty", "status", "tier", "defeats"})
REPOSITORY_KEYS = frozenset({"name", "default_branch", "language", "build_system", "source_root", "base_date"})
GRAPH_KEYS = frozenset({"model", "history_summary", "ref_lifecycle"})
COMMIT_KEYS = frozenset({
    "id", "branch", "parents", "message", "role", "operations", "allow_empty",
    "author", "date", "author_date", "committer_date",
    "rebase_of", "squashes", "revert_of", "cherry_pick_of", "backport_of",
    "inherit_message", "inherit_author_date", "inherit_author", "cherry_pick_trailer",
    "apply_revert", "mainline", "resolution",
    # recorded in graph-map.json as written (generator-options.md section 4)
    "interactive_rebase", "rebase_conflict_resolution", "reverts", "revert_conflict_resolution",
})
#: The keys of each operation besides ``type``, as graph_operations, the simulator and the generator read them.
OPERATION_KEYS: dict[str, frozenset[str]] = {
    "write_file": frozenset({"path", "content", "line_ending", "encoding"}),
    "replace": frozenset({"path", "old", "new", "occurrence", "line_ending", "encoding"}),
    "insert_after": frozenset({"path", "anchor", "content", "occurrence", "line_ending", "encoding"}),
    "delete_file": frozenset({"path"}),
    "rename_file": frozenset({"from", "to", "overwrite"}),
    "move_file": frozenset({"from", "to", "overwrite"}),
    "copy_file": frozenset({"from", "to", "overwrite"}),
    "move_entity": frozenset({"entity", "from_file", "to_file", "overwrite", "append", "remove_source_file",
                              "line_ending", "encoding"}),
    "copy_entity": frozenset({"entity", "from_file", "to_file", "overwrite", "append", "line_ending", "encoding"}),
    "chmod": frozenset({"path", "mode"}),
    "write_binary_file": frozenset({"path", "content_base64"}),
    "write_generated_text_file": frozenset({"path", "lines", "template", "header", "footer", "encoding"}),
    "commit_generator": frozenset({"generator", "count", "files", "path"}),
    "apply_squash": frozenset({"from_commits"}),
    "apply_patch_from": frozenset({"commit", "mainline", "parent"}),
    "apply_patch": frozenset({"path", "patch"}),
    "format_file": frozenset({"path", "line_ending", "encoding"}),
}
BUG_KEYS = frozenset({"id", "title", "bug_introducing_commits", "bug_fixing_commits", "bug_fixing_commit",
                      "faults", "fault", "fixes", "fix", "origin_faults",
                      # the refactoring metadata and bug instances the README lists among the graph-only features
                      "refactorings", "bug_instances"})
#: A fault's or fix's keys: what verification reads, and the labels that tell a reader one entry from another.
LOCATION_KEYS = frozenset({"id", "commit", "file", "entity", *LOCATION_STATEMENT_KEYS,
                           "description", "role", "case", "location", "semantic_role"})
FAULT_KEYS = LOCATION_KEYS | {"change_type"}
FIX_KEYS = LOCATION_KEYS | {"fix_type"}
#: The scored oracle, and the sections the evaluator notes it does not score.
EXPECTED_SZZ_KEYS = frozenset({"commit_level", "evaluation_variants", "default_variant", "branch_level",
                               *_UNREAD_GRAPH_ORACLE_SECTIONS})
COMMIT_LEVEL_KEYS = frozenset({"evaluation_policy", *EXPECTED_SZZ_COMMIT_LISTS, "known_distractors",
                               "expect_no_bic", "minimum_required", "k_values", "status_k"})
EVALUATION_VARIANT_KEYS = frozenset({"name", "description", "commit_level"})
BRANCH_LEVEL_KEYS = frozenset({"bfc", "required"})


def validate_graph_scenario_file(
    path: Path,
    *,
    strict_paths: bool = False,
    simulate: bool = False,
    lint: bool = False,
) -> tuple[dict[str, Any] | None, ValidationResult]:
    """Validate a scenario.graph.yml.

    ``lint`` enables the opt-in GW4xx lints, which are static (they do not
    need the simulation) and run only when no error was found.
    """
    data, result = load_graph_scenario(path)
    if data is None:
        return None, result
    guard = classic_scenario_guard(data, path, "validate-graph")
    if guard.has_errors():
        # one finding that says what the file is and which command reads it, in place of GE001 (issue #155)
        return data, ValidationResult([f for f in result.findings if f.code != "GE001"] + guard.findings)
    result.extend(validate_graph_static(data, scenario_path=path, strict_paths=strict_paths))
    if simulate and not result.has_errors():
        # what generation lets Git compute is checked by generating with Git (#94)
        features = git_performed_features(data)
        if features:
            result.extend(simulate_graph_scenario_with_git(path, data, features))
        else:
            result.extend(simulate_graph_scenario(data))
    if lint and not result.has_errors():
        result.extend(lint_graph_scenario(data, scenario_path=path))
    return data, result


def validate_graph_static(data: dict[str, Any], *, scenario_path: Path | None = None, strict_paths: bool = False) -> ValidationResult:
    result = ValidationResult()
    for key in ["schema_version", "meta", "repository", "commits", "bugs"]:
        if key not in data:
            result.error("GE010", f"Missing required top-level field '{key}'.", key)
    schema_version = data.get("schema_version")
    if isinstance(schema_version, str) and "graph" in schema_version and schema_version != GRAPH_SCHEMA_VERSION:
        # any string containing "graph" passed GE001 (issue #152)
        result.error("GE002", f"schema_version is '{schema_version}'; a graph scenario declares "
                     f'schema_version: "{GRAPH_SCHEMA_VERSION}".', "schema_version")

    meta = data.get("meta") if isinstance(data.get("meta"), dict) else None
    repository = data.get("repository") if isinstance(data.get("repository"), dict) else None
    commits = data.get("commits") if isinstance(data.get("commits"), list) else []
    bugs = data.get("bugs") if isinstance(data.get("bugs"), list) else []

    if meta is None:
        result.error("GE011", "'meta' must be an object.", "meta")
    else:
        scenario_id = meta.get("id")
        if not isinstance(scenario_id, str):
            result.error("GE012", "meta.id is required and must be a string.", "meta.id")
        elif not GRAPH_ID_RE.match(scenario_id):
            result.error("GE013", "meta.id must use the SZZG-XXXX format.", "meta.id")
        if scenario_path is not None and scenario_path.name != "scenario.graph.yml":
            result.warning("GW014", "Graph scenarios should be stored in a file named scenario.graph.yml.", str(scenario_path))
        for key in ["title", "category", "factors"]:
            if key not in meta:
                result.warning("GW015", f"meta.{key} is missing.", f"meta.{key}")
            elif key != "factors" and not isinstance(meta[key], str):
                result.error("GE017", f"meta.{key} must be a string, not {type_label(meta[key])}.", f"meta.{key}")
        if "factors" in meta and not isinstance(meta.get("factors"), list):
            result.error("GE016", "meta.factors must be a list.", "meta.factors")
        check_status(meta, result, code="GW018")                                                          # issue #157

    if repository is None:
        result.error("GE020", "'repository' must be an object.", "repository")
    else:
        for key in ["name", "default_branch"]:
            if key not in repository:
                result.warning("GW021", f"repository.{key} is missing.", f"repository.{key}")
        for key in ["name", "default_branch", "language"]:
            if key in repository and not isinstance(repository[key], str):
                # default_branch: 1 reached git as an int (issue #152)
                result.error("GE022", f"repository.{key} must be a string, not {type_label(repository[key])}.",
                             f"repository.{key}")
        if "base_date" in repository:
            problem = timestamp_problem(repository["base_date"])
            if problem is not None:
                result.error("GE071", f"repository.base_date {problem}.", "repository.base_date")

    if not isinstance(data.get("commits"), list):
        result.error("GE030", "commits must be a list.", "commits")
        commits = []
    if not commits:
        result.error("GE031", "commits must not be empty.", "commits")

    commit_by_id: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for i, commit in enumerate(commits):
        loc = f"commits[{i}]"
        if not isinstance(commit, dict):
            result.error("GE032", "Each commit must be an object.", loc)
            continue
        cid = commit.get("id")
        if not isinstance(cid, str) or not cid:
            result.error("GE033", "commit.id is required and must be a non-empty string.", f"{loc}.id")
            cid = f"<commit[{i}]>"
        elif cid in seen:
            result.error("GE034", f"Duplicate commit id '{cid}'.", f"{loc}.id")
        else:
            seen.add(cid)
            commit_by_id[cid] = commit
        branch = commit.get("branch")
        if branch is not None and not isinstance(branch, str):
            result.error("GE035", "commit.branch must be a string when present.", f"{loc}.branch")
        if "message" in commit and not isinstance(commit["message"], str):
            # str() made `message: 123` the subject '123', and a blank one fell back to the
            # commit id; verification was the first to object, or nothing did (issue #151)
            result.error("GE040", f"commit.message must be a string when present, not {type_label(commit['message'])}.",
                         f"{loc}.message")
        elif isinstance(commit.get("message"), str):
            # the rule of E012: a trailing newline or a body failed generation at verification
            # (GE623); a commit without message (inherit_message, revert_of) is not affected (issue #163)
            problem = commit_message_problem(commit["message"])
            if problem is not None:
                result.error("GE070", f"Commit '{cid}' message {problem}. {COMMIT_MESSAGE_RULE}", f"{loc}.message")
        check_commit_metadata(commit, cid, loc, result, timestamp_code="GE071", author_code="GE072")   # issue #152
        parents = commit.get("parents", [])
        if not isinstance(parents, list):
            result.error("GE036", "commit.parents must be a list.", f"{loc}.parents")
            parents = []
        elif i > 0 and not parents:
            # Only the first commit is a root.  The generator used to commit a later
            # parentless commit on top of whatever it had checked out, and record it
            # as a root (issue #134); a misspelt key ended up the same way.
            near_miss = next((key for key in commit if isinstance(key, str) and key != "parents"
                              and key.lower().rstrip("s") == "parent"), None)
            hint = f"; it has a '{near_miss}' key, and the key is 'parents'" if near_miss else ""
            result.error(
                "GE048",
                f"Commit '{cid}' declares no parents, but only the first commit may be a root: "
                f"a second root is not supported{hint}.",
                f"{loc}.parents",
            )
        for parent in parents:
            if not isinstance(parent, str):
                result.error("GE037", "Each parent id must be a string.", f"{loc}.parents")
            elif parent not in seen:
                # Require topological order for the MVP graph generator.
                if parent in commit_by_id or any(isinstance(c, dict) and c.get("id") == parent for c in commits):
                    result.error("GE038", f"Parent '{parent}' must appear before commit '{cid}' for graph generation.", f"{loc}.parents")
                else:
                    result.error("GE039", f"Unknown parent commit '{parent}'.", f"{loc}.parents")
        role = commit.get("role")
        if role is not None and not isinstance(role, str):
            # The role vocabulary is a lint (GE405, issue #195), but a role is text: a list or a
            # mapping raised TypeError in the merge-like test below, and passed
            # without a finding on a commit with one parent (issue #150)
            result.error("GE041", f"commit.role must be a string when present, not {type_label(role)}.", f"{loc}.role")
        elif role == "merge" and len(parents) < 2:
            result.warning("GW040", f"Commit '{cid}' has role merge but fewer than two parents.", loc)
        elif len(parents) >= 2 and role not in {"merge", "bug_fixing", "bug_introducing", "squash_merge"}:
            result.warning("GW041", f"Commit '{cid}' has multiple parents but role is not explicitly merge-like.", loc)
        for ref_key in ["cherry_pick_of", "backport_of"]:
            ref = commit.get(ref_key)
            if ref is not None:
                if not isinstance(ref, str):
                    result.error("GE042", f"{ref_key} must be a string when present.", f"{loc}.{ref_key}")
                elif ref == cid:
                    # the commit is registered above, so it passed as "earlier" (issue #159; GE047 tests it)
                    result.error("GE043", f"{ref_key} names commit '{cid}' itself; it must name an earlier commit.",
                                 f"{loc}.{ref_key}")
                elif ref not in commit_by_id:
                    result.error("GE043", f"{ref_key} refers to unknown or later commit '{ref}'.", f"{loc}.{ref_key}")
        _validate_rewrite_references(commit, cid, commit_by_id, result, loc)
        operations = commit.get("operations", [])
        if operations is None:
            operations = []
        if not isinstance(operations, list):
            result.error("GE044", "commit.operations must be a list.", f"{loc}.operations")
            continue
        # A commit with no operations is not empty when git supplies its content:
        # `revert_of` runs `git revert`, `cherry_pick_of`/`backport_of` run `git cherry-pick`
        # (docs/generator-options.md §3).  Marking those `allow_empty` would be false.
        replayed = any(commit.get(k) for k in ("revert_of", "cherry_pick_of", "backport_of"))
        if not operations and not commit.get("allow_empty") and not replayed and len(parents) < 2:
            result.warning("GW045", f"Commit '{cid}' has no operations and is not allow_empty.", loc)
        for j, op in enumerate(operations):
            _validate_operation(op, result, f"{loc}.operations[{j}]", strict_paths=strict_paths)

    _validate_source_options(commits, result)                                                             # issue #179
    _warn_default_branch_without_commits(data, commits, result)                                           # issue #179
    check_scheduled_dates(data, result, code="GE071", graph=True)    # PR #236 review
    check_commit_date_order(data, result, code="GE073", timestamp_code="GE071", graph=True)    # issue #241
    check_git_control_files(data, result, code="GE063", written_fields=WRITTEN_PATH_FIELDS_BY_OPERATION)   # issue #164
    _validate_case_changes(commits, result)                                                               # issue #235
    _validate_binary_files(commits, result)                                                               # issue #277
    for code, location, message in branch_name_problems(data):                                            # issue #239
        result.error(code, message, location)
    result.extend(_validate_graph_acyclic(commits))
    result.extend(_validate_merge_parents(commits))
    if not result.has_errors():          # the history model needs well-formed commits
        result.extend(_validate_branch_rewinds(data))
    _validate_ref_lifecycle(data, result)

    if not isinstance(data.get("bugs"), list):
        result.error("GE080", "bugs must be a list.", "bugs")
        bugs = []
    bug_ids: set[str] = set()
    for i, bug in enumerate(bugs):
        loc = f"bugs[{i}]"
        if not isinstance(bug, dict):
            result.error("GE081", "Each bug must be an object.", loc)
            continue
        bid = bug.get("id")
        if not isinstance(bid, str):
            result.error("GE082", "bug.id is required and must be a string.", f"{loc}.id")
            bid = f"<bug[{i}]>"
        elif bid in bug_ids:
            result.error("GE083", f"Duplicate bug id '{bid}'.", f"{loc}.id")
        else:
            bug_ids.add(bid)

        # graph_bic_entries iterates the value as it comes: an int raised, and a
        # string became one commit per character (issue #127).
        raw_bics = bug.get("bug_introducing_commits")
        malformed_bics = raw_bics is not None and not isinstance(raw_bics, list)
        bic_entries = [] if malformed_bics else graph_bic_entries(bug)
        bfc_entries = graph_bfc_entries(bug)
        if malformed_bics:
            result.error("GE084", f"bug {bid}: bug_introducing_commits must be a list, not {type(raw_bics).__name__}.",
                         f"{loc}.bug_introducing_commits")
        elif not bic_entries:
            if _declares_expect_no_bic(data.get("expected_szz")):
                result.info(
                    "GI086",
                    f"bug {bid} declares no bug-introducing commits; accepted because expected_szz declares expect_no_bic.",
                    f"{loc}.bug_introducing_commits",
                )
            else:
                result.error("GE084", f"bug {bid} must define bug_introducing_commits.", f"{loc}.bug_introducing_commits")
        raw_bfcs, raw_bfc = bug.get("bug_fixing_commits"), bug.get("bug_fixing_commit")
        if raw_bfcs is not None and not isinstance(raw_bfcs, list):
            # graph_bfc_entries reads a list only, and the message said the field was missing (issue #160)
            result.error("GE085", f"bug {bid}: bug_fixing_commits must be a list, not {type_label(raw_bfcs)}.",
                         f"{loc}.bug_fixing_commits")
        elif raw_bfcs is None and raw_bfc is not None and not isinstance(raw_bfc, str):
            result.error("GE085", f"bug {bid}: bug_fixing_commit must be a commit id, not {type_label(raw_bfc)}.",
                         f"{loc}.bug_fixing_commit")
        elif not bfc_entries:
            result.error("GE085", f"bug {bid} must define bug_fixing_commits or bug_fixing_commit.", f"{loc}.bug_fixing_commits")
        for j, entry in enumerate(bic_entries):
            _validate_commit_ref_entry(entry, commit_by_id, result, f"{loc}.bug_introducing_commits[{j}]", "BIC")
        for j, entry in enumerate(bfc_entries):
            _validate_commit_ref_entry(entry, commit_by_id, result, f"{loc}.bug_fixing_commits[{j}]", "BFC")

        _validate_location_containers(bug, str(bid), result, loc)                                       # issue #160
        for j, fault in enumerate(graph_faults(bug)):
            _validate_location_entry(fault, commit_by_id, result, f"{loc}.faults[{j}]", kind="fault")
        for j, fix in enumerate(graph_fixes(bug)):
            _validate_location_entry(fix, commit_by_id, result, f"{loc}.fixes[{j}]", kind="fix")

    _validate_expected_szz(data.get("expected_szz"), commit_by_id, result)
    _warn_inferred_commit_level(data, result)
    _validate_context_sections(data, commit_by_id, result)
    _warn_unknown_keys(data, result)                                                                      # issue #160
    return result


def _validate_source_options(commits: list[Any], result: ValidationResult) -> None:
    """GE074 / GE075: a commit option that copies from a source commit has one (issue #179); GE076, GE077.

    Generation takes ``inherit_message`` / ``inherit_author_date`` /
    ``inherit_author`` from the first of ``rebase_of``, ``cherry_pick_of`` and
    ``backport_of`` that is a commit id, and the lines of ``cherry_pick_trailer`` from
    ``cherry_pick_of`` / ``backport_of`` and every ``apply_patch_from``
    operation (``_cherry_pick_trailer_sources``); a commit with none passed
    ``validate-graph``, ``--simulate`` included, and stopped generation.  A
    ``rebase_of`` list (a squash-rebase, GE046) is not a source: generation
    said the commit had no ``rebase_of``.  Whether a source is an earlier
    commit is GE043's and GE047's.

    GE076: ``inherit_author`` is ``true`` or ``false``, and a commit that
    inherits its author does not write one too, which one of the two would
    silently override (issue #180).  GE077: so is ``allow_empty`` (issue #160).
    """
    for i, commit in enumerate(commits):
        if not isinstance(commit, dict):
            continue
        cid = commit["id"] if isinstance(commit.get("id"), str) else f"<commit[{i}]>"
        loc = f"commits[{i}]"
        flags = [key for key in INHERITED_FIELDS if commit.get(key)]        # read as generation reads them: bool()
        if flags and not any(isinstance(commit.get(key), str) and commit.get(key) for key in INHERIT_SOURCE_KEYS):
            options = " and ".join(flags)
            if isinstance(commit.get("rebase_of"), list):
                fields = " and ".join(INHERITED_FIELDS[flag] for flag in flags)
                result.error("GE074", f"Commit '{cid}' sets {options}, but its rebase_of is a list (a squash-rebase), "
                             "and generation inherits from one commit: a rebase_of, cherry_pick_of or backport_of that "
                             f"is a commit id. Write the {fields} instead.", f"{loc}.{flags[0]}")
            else:
                result.error("GE074", f"Commit '{cid}' sets {options}, but has no rebase_of, cherry_pick_of or "
                             "backport_of to inherit from.", f"{loc}.{flags[0]}")
        if "inherit_author" in commit:
            inherit_author = commit["inherit_author"]
            if not isinstance(inherit_author, bool):
                shown = "a blank value" if inherit_author is None else repr(inherit_author)
                result.error("GE076", f"Commit '{cid}' inherit_author must be true or false, not {shown}.",
                             f"{loc}.inherit_author")
            elif inherit_author and commit.get("author") is not None:
                result.error("GE076", f"Commit '{cid}' sets both author and inherit_author: true, which takes the "
                             "author of its rewrite source; write only one of them.", f"{loc}.inherit_author")
        if "allow_empty" in commit and not isinstance(commit["allow_empty"], bool):
            # read as bool(): `allow_empty: "false"` let an empty commit through GW045 and GE202 (issue #160)
            allow_empty = commit["allow_empty"]
            shown = "a blank value" if allow_empty is None else repr(allow_empty)
            result.error("GE077", f"Commit '{cid}' allow_empty must be true or false, not {shown}, which generation "
                         f"and the checks read as {str(bool(allow_empty)).lower()}.", f"{loc}.allow_empty")
        if commit.get("cherry_pick_trailer"):
            operations = commit.get("operations") if isinstance(commit.get("operations"), list) else []
            sources = [commit.get("cherry_pick_of"), commit.get("backport_of"),
                       *(op.get("commit") for op in operations if isinstance(op, dict) and op.get("type") == "apply_patch_from")]
            if not any(isinstance(source, str) and source for source in sources):
                result.error("GE075", f"Commit '{cid}' sets cherry_pick_trailer, but has no cherry_pick_of, backport_of "
                             "or apply_patch_from operation to name in the trailer.", f"{loc}.cherry_pick_trailer")


def _warn_default_branch_without_commits(data: dict[str, Any], commits: list[Any], result: ValidationResult) -> None:
    """GW022: no commit is on ``repository.default_branch`` (issue #179).

    ``git init`` names the unborn branch after it, and a branch is born with
    its first commit: the generated repository had the other branches only,
    and ``verify-graph`` passed.  A branch name that is not a string is
    GE022's or GE035's.
    """
    default_branch = scenario_default_branch(data)
    branches = [commit_branch(commit, default_branch) for commit in commits if isinstance(commit, dict)]
    if isinstance(default_branch, str) and branches and default_branch not in branches:
        result.warning("GW022", f"No commit is on the default branch '{default_branch}' (repository.default_branch, "
                       "'main' without the key), so the generated repository will not have that branch.",
                       "repository.default_branch")


def _validate_operation(op: Any, result: ValidationResult, loc: str, *, strict_paths: bool) -> None:
    if not isinstance(op, dict):
        result.error("GE050", "Each operation must be an object.", loc)
        return
    op_type = op.get("type")
    if not isinstance(op_type, str):
        result.error("GE051", "operation.type is required and must be a string.", f"{loc}.type")
        return
    if op_type not in SUPPORTED_GRAPH_OPERATIONS:
        result.error("GE052", f"Unknown graph operation type '{op_type}'.", f"{loc}.type")
        return
    for key in REQUIRED_FIELDS_BY_OPERATION.get(op_type, []):
        if key not in op:
            result.error("GE053", f"Operation '{op_type}' is missing required field '{key}'.", f"{loc}.{key}")
    for key in PATH_FIELDS_BY_OPERATION.get(op_type, []):
        value = op.get(key)
        if isinstance(value, str):
            try:
                validate_repo_relative_path(value)
            except PathValidationError as exc:
                result.error("GE054", f"Invalid path '{value}': {exc}", f"{loc}.{key}")
        elif key in op:
            result.error("GE055", f"Operation field '{key}' must be a string path.", f"{loc}.{key}")
    if strict_paths and op_type in {"move_entity", "copy_entity"} and not isinstance(op.get("entity"), dict):
        result.error("GE056", f"Operation '{op_type}' must define an entity object.", f"{loc}.entity")
    _validate_operation_values(op, op_type, result, loc)


#: The values generation reads from three operations, checked before it runs (issue #172).
_OCTAL_MODE = re.compile(r"[0-7]{3,4}")
#: The operations that write the file at one path to another.  Two paths that differ only in
#: letter case are one file on a case-insensitive file system: a case-only rename failed on
#: macOS and succeeded on Linux (issue #175).  The paths are compared by
#: ``paths.file_system_key``, as the simulators compare the paths of a snapshot (issue #153).
_CASE_SENSITIVE_PAIRS = {
    "rename_file": ("from", "to"),
    "move_file": ("from", "to"),
    "copy_file": ("from", "to"),
    "move_entity": ("from_file", "to_file"),
    "copy_entity": ("from_file", "to_file"),
}


def _validate_operation_values(op: dict[str, Any], op_type: str, result: ValidationResult, loc: str) -> None:
    for key in TEXT_FIELDS_BY_OPERATION.get(op_type, ()):
        if key in op and not isinstance(op[key], str):
            result.error("GE053", f"Operation '{op_type}' field '{key}' must be a string, not {type_label(op[key])}.",
                         f"{loc}.{key}")
    if op_type == "chmod" and "mode" in op:
        mode = op["mode"]
        if not (isinstance(mode, str) and _OCTAL_MODE.fullmatch(mode)):
            hint = " (YAML reads an unquoted 0755 as the integer 493)" if isinstance(mode, int) else ""
            result.error("GE057", f"chmod mode must be a quoted string of octal digits such as '755', not {mode!r}{hint}.",
                         f"{loc}.mode")
    if op_type == "write_binary_file" and "content_base64" in op:
        try:
            decode_content_base64(op["content_base64"])   # the generator's own reading (PR #214 review)
        except ValueError as exc:
            result.error("GE058", f"write_binary_file content_base64 is not base64 ({exc}); ASCII whitespace is "
                         "ignored, any other character outside the alphabet is not.", f"{loc}.content_base64")
    if op_type == "write_generated_text_file" and "lines" in op:
        lines = op["lines"]
        if not (isinstance(lines, int) and not isinstance(lines, bool) and lines >= 0):
            result.error("GE059", f"write_generated_text_file lines must be a non-negative integer, not {lines!r}.",
                         f"{loc}.lines")
    # line_ending and encoding were read by generation only, and commit_generator's
    # count by --simulate and generation, which generate-graph does not simulate (issue #152)
    if op_type in LINE_ENDING_OPERATIONS:
        try:
            resolve_line_ending(op)                       # the generator's own reading
        except OperationError as exc:
            result.error("GE061", f"Operation '{op_type}' {exc}.", f"{loc}.line_ending")
    if op_type in ENCODING_OPERATIONS and op.get("encoding") is not None:
        try:
            resolve_encoding(op)                          # the rule of E042, which the replay models (issue #240)
        except (OperationError, ValueError):              # ValueError: a NUL in the name, which codecs.lookup refuses
            result.error("GE061", f"Operation '{op_type}' encoding must be 'utf-8' or 'utf-8-sig', got "
                         f"{op['encoding']!r}.", f"{loc}.encoding")
    if op_type == "commit_generator":
        for key, least in (("count", 0), ("files", 1)):
            value = op.get(key)
            if key in op and not (isinstance(value, int) and not isinstance(value, bool) and value >= least):
                what = "a non-negative integer" if least == 0 else "a positive integer"
                result.error("GE062", f"commit_generator {key} must be {what}, not {value!r}.", f"{loc}.{key}")
    if op_type in _CASE_SENSITIVE_PAIRS:
        source_key, target_key = _CASE_SENSITIVE_PAIRS[op_type]
        source, target = op.get(source_key), op.get(target_key)
        if (isinstance(source, str) and isinstance(target, str) and source != target
                and file_system_key(source) == file_system_key(target)):
            result.error("GE060", f"{op_type} from '{source}' to '{target}' changes only the letter case or the Unicode "
                         "normalization; macOS (and Windows, for letter case) sees one file there, so what generation "
                         "makes of it would depend on the platform.", f"{loc}.{target_key}")


#: The fields of the operations that can make a file the commit did not have; ``replace``,
#: ``insert_after`` and ``format_file`` rewrite one in place.
_CREATING_PATH_FIELDS = {op_type: fields for op_type, fields in WRITTEN_PATH_FIELDS_BY_OPERATION.items()
                         if op_type not in ("replace", "insert_after", "format_file")}
#: The fields that name a file an operation removes (and ``move_entity``'s ``from_file`` with
#: ``remove_source_file``).
_REMOVED_PATH_FIELDS = {"delete_file": ("path",), "rename_file": ("from",), "move_file": ("from",)}


def _validate_case_changes(commits: list[Any], result: ValidationResult) -> None:
    """GE064: a commit removes a file and writes one whose name differs only in letter case or normalization (issue #235).

    ``delete_file src/Range.java`` followed by ``write_file src/range.java``,
    or two ``rename_file`` through another name, left the replay of
    ``--simulate`` with ``src/range.java``.  Generation on macOS, where
    ``git init`` sets ``core.ignorecase``, kept the spelling the index had:
    the first committed ``src/Range.java`` with the new content, and
    verification passed; the second committed nothing (``commit would be
    empty``).  On Linux both commit ``src/range.java``.  GE060 refuses one
    operation's own two paths, which this leaves to it, and GE201 a write
    beside a file spelt otherwise; this is the route through a removal.  The
    operations of a commit are read in order: a path a later operation writes
    again is no longer removed, and one a later operation removes is no
    longer written.  Validation does not know which files the
    commit starts with, so a file the commit writes and then removes counts as
    removed.  The check is static: ``generate-graph``, which does not
    simulate, refuses the commit too, as does ``--simulate`` for a scenario
    it generates with Git.  Paths are compared whole, as Git compares index
    entries: ``Src/a.java`` and ``src/a.java`` are one entry on macOS, while
    ``Src/a.java`` removed and ``src/b.java`` written are committed as written.
    """
    for i, commit in enumerate(commits):
        if not isinstance(commit, dict) or not isinstance(commit.get("operations"), list):
            continue
        removed: dict[str, int] = {}                 # path -> the operation that removed it
        written: dict[str, tuple[int, str]] = {}     # path -> the operation and the field that wrote it
        for j, op in enumerate(commit["operations"]):
            if not isinstance(op, dict) or not isinstance(op.get("type"), str):
                continue
            op_type = op["type"]
            writes = [(True, key) for key in _CREATING_PATH_FIELDS.get(op_type, ())]
            removes = [(False, key) for key in _REMOVED_PATH_FIELDS.get(op_type, ())]
            if op_type == "move_entity" and op.get("remove_source_file"):
                removes = [(False, "from_file")]
            # a rename removes its source as it writes its target; move_entity writes before it removes
            for is_write, key in (writes + removes if op_type == "move_entity" else removes + writes):
                path = op.get(key)
                if not isinstance(path, str):
                    continue
                if is_write:
                    removed.pop(path, None)
                    written[path] = (j, f"commits[{i}].operations[{j}].{key}")
                else:
                    written.pop(path, None)
                    removed[path] = j
        for path, (j, location) in written.items():
            # one operation's own two paths are GE060's
            gone = next((other for other in sorted(removed) if other != path and removed[other] != j
                         and file_system_key(other) == file_system_key(path)), None)
            if gone is None:
                continue
            spelt = "" if (gone + path).isascii() else f" (spelt {gone!a} and {path!a})"
            result.error("GE064", f"Commit '{commit.get('id')}' removes '{gone}' and writes '{path}', which differ only "
                         f"in letter case or Unicode normalization{spelt}: Git on macOS (and on Windows, for letter case) "
                         f"keeps the spelling its index has, so the commit would record '{gone}' there, or nothing, and "
                         f"'{path}' on Linux. Delete the file in one commit and write it in a later one.", location)


#: The operations that read a file as text, and the fields that name it: the ones the replay
#: of ``--simulate`` refuses on a file ``write_binary_file`` wrote (``graph_simulator._require_text``).
#: ``move_entity`` and ``copy_entity`` read ``to_file`` only to append to it.
_TEXT_READ_FIELDS = {
    "replace": ("path",),
    "insert_after": ("path",),
    "format_file": ("path",),
    "move_entity": ("from_file", "to_file"),
    "copy_entity": ("from_file", "to_file"),
}
#: The operations after which the file at ``path`` is not binary: a text write, or a removal.
_TEXT_WRITE_OR_REMOVAL = ("write_file", "write_generated_text_file", "delete_file")

#: A commit's binary files: path -> the commit and the location of the write_binary_file that wrote it.
_BinaryFiles = dict[str, tuple[str, str]]
#: What a commit changes: path -> the binary file it leaves there, or None (a text file, or none).
_BinaryChanges = dict[str, "tuple[str, str] | None"]


def _validate_binary_files(commits: list[Any], result: ValidationResult) -> None:
    """GE065: a text operation on a file ``write_binary_file`` wrote (issue #277).

    The replay of ``--simulate`` kept such a file as bytes and refused a
    ``replace`` on it (GE201), while generation read the bytes as UTF-8 and
    committed the edit.  A file written as bytes now stays binary for the rest
    of the history: ``rename_file``, ``move_file`` and ``copy_file`` take it
    along, and only a text write (``write_file``, ``write_generated_text_file``,
    the ``to_file`` of ``move_entity`` / ``copy_entity``, the files of
    ``commit_generator``) or a removal ends it.  The operations the replay
    refuses on bytes are refused here: ``replace``, ``insert_after``,
    ``format_file``, and ``move_entity`` / ``copy_entity`` reading its
    ``from_file``, or its ``to_file`` to append.  A refused operation changes
    nothing, as in the replay.  The check is static, so ``generate-graph``
    refuses the scenario too.  What Git computes is not known before
    generation, so it only adds binary files: a merge keeps those of every
    parent, a cherry-pick (``cherry_pick_of`` / ``backport_of``,
    ``apply_patch_from``, ``apply_squash``) adds the ones its source writes as
    bytes, a ``git revert`` the ones its source rewrites, moves or removes; a
    ``resolution``, applied only where Git reports a conflict, is not read.
    Each commit records what it changes (``changes``) without comparing
    binary files, which a change Git makes to text leaves as they were: every
    path an operation writes or removes, what a cherry-pick or revert brought
    in, and, for a merge, every binary file of a parent.  Picking a
    cherry-pick of a commit then brings what picking the commit does, and so
    does reverting it, and a copy that restores the bytes a path already had
    here is a change (PR #281 review).
    """
    states: dict[str, _BinaryFiles] = {}
    changes: dict[str, _BinaryChanges] = {}
    parents_of: dict[str, list[str]] = {}
    for i, commit in enumerate(commits):
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        cid = commit["id"]
        parents = [p for p in commit["parents"] if isinstance(p, str)] if isinstance(commit.get("parents"), list) else []
        operations = commit["operations"] if isinstance(commit.get("operations"), list) else []
        parents_of[cid] = parents
        binary = dict(states.get(parents[0], {})) if parents else {}
        # generation commits the files of commit_generator first, as text, from the first parent
        plans = []
        for op in operations:
            if isinstance(op, dict) and op.get("type") == "commit_generator":
                try:
                    plans.append(commit_generator_plan(op, cid))
                except ValueError:        # GE062
                    pass
        for _, path, _ in commit_generator_changes(plans, lambda _: ""):
            binary.pop(path, None)
        for parent in parents[1:]:
            for path, origin in states.get(parent, {}).items():
                binary.setdefault(path, origin)
        # what this commit changes, in order: path -> (brought in by Git, what Git left there); a path an
        # operation writes or removes is its binary file at the end of the commit
        recorded: dict[str, tuple[bool, Any]] = {}
        revert = commit.get("revert_of")
        if isinstance(revert, str) and (not operations or commit.get("apply_revert")):
            _bring(binary, recorded, _brought_changes(revert, states, changes, parents_of, reverted=True))
        picked = commit.get("cherry_pick_of") or commit.get("backport_of")
        if isinstance(picked, str) and not operations:
            _bring(binary, recorded, _brought_changes(picked, states, changes, parents_of, reverted=False))

        for j, op in enumerate(operations):
            if not isinstance(op, dict) or not isinstance(op.get("type"), str):     # GE050, GE051
                continue
            op_type = op["type"]
            refused = False
            if op_type in ("apply_patch_from", "apply_squash"):
                sources = [op.get("commit")] if op_type == "apply_patch_from" else op.get("from_commits")
                for source in sources if isinstance(sources, list) else []:
                    if isinstance(source, str):
                        _bring(binary, recorded, _brought_changes(source, states, changes, parents_of, reverted=False))
            elif op_type in _TEXT_READ_FIELDS:
                for key in _TEXT_READ_FIELDS[op_type]:
                    path = op.get(key)
                    if not isinstance(path, str) or path not in binary:
                        continue
                    if key == "to_file" and not (op.get("append") and op.get("overwrite", True)):
                        continue          # overwritten, or refused as an existing target
                    refused = True
                    origin, location = binary[path]
                    reads = "appends to" if key == "to_file" else "reads"
                    result.error("GE065", f"Commit '{cid}' {op_type} {reads} '{path}' as text, but write_binary_file "
                                 f"wrote it in commit '{origin}' ({location}): a file written as bytes stays binary, "
                                 "and generation refuses a text operation on it, as the replay of --simulate does. "
                                 "Write the file with write_file (encoding and line_ending set its bytes) to edit it "
                                 "as text, or write its new bytes with write_binary_file.",
                                 f"commits[{i}].operations[{j}].{key}")
                if not refused and op_type in ("move_entity", "copy_entity"):
                    target, source = op.get("to_file"), op.get("from_file")
                    if isinstance(target, str):
                        binary.pop(target, None)
                    if op_type == "move_entity" and op.get("remove_source_file") and isinstance(source, str):
                        binary.pop(source, None)
            elif op_type == "write_binary_file" and isinstance(op.get("path"), str):
                binary[op["path"]] = (cid, f"commits[{i}].operations[{j}]")
            elif op_type in _TEXT_WRITE_OR_REMOVAL and isinstance(op.get("path"), str):
                binary.pop(op["path"], None)
            elif op_type in ("rename_file", "move_file", "copy_file"):
                source, target = op.get("from"), op.get("to")
                if isinstance(source, str) and isinstance(target, str):
                    origin = binary.pop(source, None) if op_type != "copy_file" else binary.get(source)
                    if origin is not None:
                        binary[target] = origin
                    else:
                        binary.pop(target, None)
            if not refused:
                for path in _changed_paths(op):
                    recorded[path] = (False, None)
        # a merge's result is not known here, nor its mainline: every binary file of a parent may be a change
        changes[cid] = ({path: binary.get(path) for parent in parents for path in states.get(parent, {})}
                        if len(parents) > 1 else {})
        changes[cid].update({path: left if brought else binary.get(path)
                             for path, (brought, left) in recorded.items()})
        states[cid] = binary


def _brought_changes(source: str, states: dict[str, _BinaryFiles], changes: dict[str, _BinaryChanges],
                     parents_of: dict[str, list[str]], *, reverted: bool) -> _BinaryChanges:
    """What Git changes in a commit that cherry-picks ``source``, or reverts it: the paths ``source`` changes.

    A cherry-pick leaves each path as ``source`` left it; a revert takes it
    back to the binary file a parent of ``source`` has there (the first that
    has one), or to None.  What ``source`` itself brought in by a cherry-pick
    or revert counts.  Comparing the binary files of ``source`` and its
    parents missed it: a pick kept the writer the path already had, so a pick
    of a pick, or its revert, brought nothing; and after a change Git made to
    text, which keeps the old writer here, a copy of the same bytes back
    looked like no change (PR #281 review).
    """
    changed = changes.get(source, {})
    if not reverted:
        return dict(changed)
    befores = [states.get(parent, {}) for parent in parents_of.get(source, [])]
    return {path: next((before[path] for before in befores if path in before), None) for path in changed}


def _bring(binary: _BinaryFiles, recorded: dict[str, tuple[bool, Any]], changed: _BinaryChanges) -> None:
    """Apply what a cherry-pick or revert changes, and record it in ``recorded``.

    A binary file replaces what was there.  A change to text leaves
    ``binary`` as it was, since Git's result is not known, but is recorded,
    so that a revert of the commit brings the binary file back and a pick of
    it brings none.
    """
    for path, origin in changed.items():
        if origin is not None:
            binary[path] = origin
        recorded[path] = (True, origin)


def _changed_paths(op: dict[str, Any]) -> list[str]:
    """The paths an operation writes or removes, whatever it writes there."""
    keys = [*WRITTEN_PATH_FIELDS_BY_OPERATION.get(op["type"], ()), *_REMOVED_PATH_FIELDS.get(op["type"], ())]
    if op["type"] == "move_entity" and op.get("remove_source_file"):
        keys.append("from_file")
    return [op[key] for key in keys if isinstance(op.get(key), str)]


def _validate_commit_ref_entry(entry: Any, commit_by_id: dict[str, dict[str, Any]], result: ValidationResult, loc: str, label: str) -> None:
    if isinstance(entry, str):
        cid = entry
    elif isinstance(entry, dict):
        cid = entry.get("commit")
        if "role" in entry and not isinstance(entry.get("role"), str):
            result.error("GE090", f"{label} role must be a string.", f"{loc}.role")
    else:
        result.error("GE091", f"{label} entry must be a string or object.", loc)
        return
    if not isinstance(cid, str):
        result.error("GE092", f"{label} entry must contain a commit id.", loc)
    elif cid not in commit_by_id:
        result.error("GE093", f"{label} refers to unknown commit '{cid}'.", loc)


def _validate_location_containers(bug: dict[str, Any], bid: str, result: ValidationResult, loc: str) -> None:
    """GE107: ``faults`` / ``fixes`` is a list of objects, and ``fault`` / ``fix`` an object (issue #160).

    ``graph_faults`` and ``graph_fixes`` read nothing else and skip the rest:
    ``faults: {commit: no-such-commit}`` passed, its unknown commit never
    checked (GE101), and so did an entry that is not an object.
    """
    for key, singular in (("faults", "fault"), ("fixes", "fix")):
        value = bug.get(key)
        if value is not None and not isinstance(value, list):
            result.error("GE107", f"bug {bid}: {key} must be a list of {singular} entries, not {type_label(value)}.",
                         f"{loc}.{key}")
        for j, entry in enumerate(value if isinstance(value, list) else []):
            if not isinstance(entry, dict):
                result.error("GE107", f"bug {bid}: {key}[{j}] must be an object, not {type_label(entry)}.",
                             f"{loc}.{key}[{j}]")
        if bug.get(singular) is not None and not isinstance(bug[singular], dict):
            result.error("GE107", f"bug {bid}: {singular} must be an object, not {type_label(bug[singular])}.",
                         f"{loc}.{singular}")


def _validate_location_entry(entry: dict[str, Any], commit_by_id: dict[str, dict[str, Any]], result: ValidationResult, loc: str, *, kind: str) -> None:
    commit = entry.get("commit")
    if not isinstance(commit, str):
        result.error("GE100", "Location entry must contain commit.", f"{loc}.commit")
    elif commit not in commit_by_id:
        result.error("GE101", f"Location entry refers to unknown commit '{commit}'.", f"{loc}.commit")
    file_value = entry.get("file")
    if file_value is not None:
        if isinstance(file_value, str):
            try:
                validate_repo_relative_path(file_value)
            except PathValidationError as exc:
                result.error("GE102", f"Invalid file path '{file_value}': {exc}", f"{loc}.file")
        else:
            result.error("GE103", "Location file must be a string when present.", f"{loc}.file")
    # A statement stays optional (a binary change, a deleted file, an omission), but one that is
    # there is text: verify-graph skipped the checks of an empty or non-string one, and found a
    # blank one anywhere (issue #237, the rule of E301 / E311)
    for key in LOCATION_STATEMENT_KEYS:
        if key not in entry:
            continue
        value = entry[key]
        if not isinstance(value, str):
            result.error("GE104", f"{kind} {key} must be a string, not {type_label(value)}.", f"{loc}.{key}")
        elif not value.strip():
            result.error("GE104", f"{kind} {key} is empty; write the statement.", f"{loc}.{key}")
    if kind == "fault" and entry.get("change_type") == "omission":
        # the counterparts of E351 and W350
        if "missing_statement" not in entry:
            result.error("GE104", "fault is an omission, but missing_statement is missing; write the statement "
                         "the fault omits.", f"{loc}.missing_statement")
        if "statement" in entry:
            result.warning("GW106", "fault is an omission, but statement is present.", f"{loc}.statement")
    if "entity" in entry and not isinstance(entry.get("entity"), dict):
        result.error("GE105", "Location entity must be an object when present.", f"{loc}.entity")


def _declares_expect_no_bic(expected: Any) -> bool:
    """True when expected_szz.commit_level or any evaluation variant sets expect_no_bic: true.

    Such a scenario intentionally has no bug-introducing commit in the repository
    (an externally caused fault), so an empty bug_introducing_commits list is valid.
    """
    if not isinstance(expected, dict):
        return False
    commit_level = expected.get("commit_level")
    if isinstance(commit_level, dict) and commit_level.get("expect_no_bic") is True:
        return True
    variants = expected.get("evaluation_variants")
    if isinstance(variants, list):
        for variant in variants:
            if isinstance(variant, dict):
                cl = variant.get("commit_level")
                if isinstance(cl, dict) and cl.get("expect_no_bic") is True:
                    return True
    return False


def _validate_expected_szz(expected: Any, commit_by_id: dict[str, dict[str, Any]], result: ValidationResult) -> None:
    if expected is None:
        result.warning("GW120", "expected_szz is missing.", "expected_szz")
        return
    if not isinstance(expected, dict):
        result.error("GE120", "expected_szz must be an object.", "expected_szz")
        return
    policies = []
    commit_level = expected.get("commit_level")
    if isinstance(commit_level, dict):
        policy = commit_level.get("evaluation_policy")
        if isinstance(policy, str):
            policies.append((policy, "expected_szz.commit_level.evaluation_policy"))
        elif "evaluation_policy" in commit_level:
            _report_policy_type(policy, "expected_szz.commit_level.evaluation_policy", result)
        _validate_oracle_lists(commit_level, commit_by_id, result, "expected_szz.commit_level")
    variants = expected.get("evaluation_variants")
    if variants is not None and not isinstance(variants, list):
        # read only as a list, so anything else passed unnoticed (issue #127)
        result.error("GE122", "expected_szz.evaluation_variants must be a list of evaluation variants.",
                     "expected_szz.evaluation_variants")
    if isinstance(variants, list):
        for i, variant in enumerate(variants):
            if not isinstance(variant, dict):
                result.error("GE122", "Each evaluation variant must be an object.", f"expected_szz.evaluation_variants[{i}]")
                continue
            name = variant.get("name")
            if not isinstance(name, str) or not name:
                # the evaluator selects a variant by its name; without one it is never scored (issue #127)
                result.error("GE122", "Each evaluation variant must have a non-empty string name.",
                             f"expected_szz.evaluation_variants[{i}].name")
            cl = variant.get("commit_level")
            if isinstance(cl, dict):
                _validate_oracle_lists(cl, commit_by_id, result, f"expected_szz.evaluation_variants[{i}].commit_level")
                variant_policy = cl.get("evaluation_policy")
                variant_loc = f"expected_szz.evaluation_variants[{i}].commit_level.evaluation_policy"
                if isinstance(variant_policy, str):
                    policies.append((variant_policy, variant_loc))
                elif "evaluation_policy" in cl:
                    _report_policy_type(variant_policy, variant_loc, result)
    for policy, loc in policies:
        if policy not in ALLOWED_EVALUATION_POLICIES:
            result.warning("GW123", f"Unknown evaluation_policy '{policy}'.", loc)
    # A default_variant the evaluator cannot resolve makes it score commit_level
    # instead, with at most a note at every evaluation (SZZG-0136).  What counts
    # is that the key is there: a blank `default_variant:` loads as None, and the
    # evaluator then falls back without any note (PR #105 review).
    if "default_variant" in expected and _selected_evaluation_variant(expected, None, []) is None:
        default_variant = expected["default_variant"]
        what = ("is blank (a YAML null)" if default_variant is None
                else f"{default_variant!r} names no evaluation variant")
        names = [v.get("name") for v in variants if isinstance(v, dict)] if isinstance(variants, list) else []
        result.error("GE129", f"default_variant {what} (declared: {', '.join(map(str, names)) or 'none'}); the "
                     "evaluator would score commit_level instead. Name a declared variant, or remove "
                     "default_variant to make commit_level the default.",
                     "expected_szz.default_variant")
    branch_level = expected.get("branch_level")
    if branch_level is not None:
        # Scored per declared BFC since 2026-09-22 (docs/evaluation-policies.md section 1.5).
        if not isinstance(branch_level, dict) or not branch_level:
            result.error("GE127", "expected_szz.branch_level must be a non-empty object mapping branch names to {bfc, required}.", "expected_szz.branch_level")
        else:
            for name, spec in branch_level.items():
                loc = f"expected_szz.branch_level.{name}"
                if not isinstance(spec, dict):
                    result.error("GE127", f"{loc} must be an object with bfc and required.", loc)
                    continue
                bfc = spec.get("bfc")
                if not isinstance(bfc, str):
                    result.error("GE127", f"{loc}.bfc is required and must be a commit id.", f"{loc}.bfc")
                elif bfc not in commit_by_id:
                    result.error("GE128", f"{loc}.bfc refers to unknown commit '{bfc}'.", f"{loc}.bfc")
                if not isinstance(spec.get("required"), list):
                    # a blank `required:` is None and would become an oracle that expects nothing
                    result.error("GE127", f"{loc}.required must be a list of commit ids (write [] for an intentionally empty answer).", f"{loc}.required")
                else:
                    _validate_commit_list(spec["required"], commit_by_id, result, f"{loc}.required")


def _report_policy_type(policy: Any, loc: str, result: ValidationResult) -> None:
    """GE123: an ``evaluation_policy`` that is not a string (issue #160).  The vocabulary
    check (GW123) read strings only, and the evaluator scores anything else as
    ``exact_set`` without the note an unknown name gets."""
    shown = type_label(policy) if policy is None else f"{type_label(policy)} {policy!r}"
    result.error("GE123", f"evaluation_policy must be a string, the name of a policy such as 'exact_set', not "
                 f"{shown}; the evaluator would score it as exact_set without a note.", loc)


def _warn_inferred_commit_level(data: dict[str, Any], result: ValidationResult) -> None:
    """GW130: a commit-level oracle the evaluator would have to infer (issue #118).

    With no ``required`` and no ``expect_no_bic: true``, the evaluator takes the
    required set from bugs[] and notes it at every evaluation: a warning about a
    scenario the user did not write, which no check had asked to declare.  As
    for GE129, the evaluator is asked, for each oracle it can score: every
    evaluation variant, and ``commit_level`` unless ``default_variant`` names a
    variant to score instead (SZZG-0022 keeps its whole oracle in variants).
    """
    expected = data.get("expected_szz")
    if not isinstance(expected, dict):
        return                                          # GW120 / GE120
    oracles = []
    if _selected_evaluation_variant(expected, None, []) is None:
        oracles.append((None, "expected_szz.commit_level", "expected_szz.commit_level"))
    variants = expected.get("evaluation_variants")
    for i, variant in enumerate(variants if isinstance(variants, list) else []):
        if isinstance(variant, dict) and isinstance(variant.get("name"), str):
            oracles.append((variant["name"], f"expected_szz.evaluation_variants[{i}].commit_level",
                            f"evaluation variant '{variant['name']}'"))
    for name, loc, subject in oracles:
        policy = _commit_level_policy(data, "advanced-scenarios", name)
        if policy.required_inferred:
            inferred = (f"take {', '.join(policy.required)} from bugs[]" if policy.required
                        else "find nothing in bugs[] and score an empty required set")
            result.warning("GW130", f"{subject} declares no required commits and no expect_no_bic: true, so the "
                           f"evaluator would {inferred} and note it at every evaluation. Declare required (or "
                           "expect_no_bic: true for an intentionally empty oracle).", loc)


def _validate_oracle_lists(commit_level: dict[str, Any], commit_by_id: dict[str, dict[str, Any]],
                           result: ValidationResult, loc: str) -> None:
    """The commit lists of one oracle, ``commit_level`` or a variant's: GW130
    hands either to the evaluator, which reads every one of them (PR #124
    review: ``acceptable_related: 5`` was neither checked nor survivable).
    ``known_distractors`` too: an unknown id never matched a prediction (issue #159)."""
    for key in ["required", "relevant", "related_origins", "related_but_not_correct", "known_distractors"]:
        _validate_commit_list(commit_level.get(key), commit_by_id, result, f"{loc}.{key}")
    acceptable = commit_level.get("acceptable_related")
    if acceptable is not None and not isinstance(acceptable, list):
        result.error("GE124", f"{loc}.acceptable_related must be a list when present.", f"{loc}.acceptable_related")
    for i, item in enumerate(acceptable if isinstance(acceptable, list) else []):
        if isinstance(item, str):
            if item not in commit_by_id:
                result.error("GE121", f"expected_szz acceptable_related refers to unknown commit '{item}'.", f"{loc}.acceptable_related[{i}]")
        elif isinstance(item, dict):
            cid = item.get("commit")
            if isinstance(cid, str) and cid not in commit_by_id:
                result.error("GE121", f"expected_szz acceptable_related refers to unknown commit '{cid}'.", f"{loc}.acceptable_related[{i}].commit")
            credit = item.get("credit")
            if credit is not None and _number_value(credit) is None:
                result.error("GE131", f"acceptable_related credit must be a number, not {_value_label(credit)}; "
                             "the evaluator would count 0.", f"{loc}.acceptable_related[{i}].credit")
    _validate_oracle_values(commit_level, result, loc)


def _value_label(value: Any) -> str:
    """A value as GE131 names it: a boolean in its YAML spelling, anything else shortened."""
    if isinstance(value, bool):
        return f"the boolean {str(value).lower()}"
    return reprlib.repr(value)


def _validate_oracle_values(commit_level: dict[str, Any], result: ValidationResult, loc: str) -> None:
    """GE131 and GE132: the values of one oracle that are not commit lists, read as the evaluator reads them.

    The evaluator ignores what it cannot read with a note at every evaluation; a
    boolean passed for an integer, so ``status_k: true`` decided a ``top_k`` oracle
    at the largest ``k`` instead of 1 (issue #146).  ``required`` beside
    ``expect_no_bic: true`` is resolved by ignoring the flag (issue #159).
    """
    k_values = commit_level.get("k_values")
    if k_values is not None and not isinstance(k_values, list):
        result.error("GE131", f"k_values must be a list of positive integers, not {type_label(k_values)}; the "
                     "evaluator would ignore it.", f"{loc}.k_values")
    for i, k in enumerate(k_values if isinstance(k_values, list) else []):
        if not (_is_int(k) and k > 0):
            result.error("GE131", f"k_values entries must be positive integers, not {_value_label(k)}; the "
                         "evaluator would ignore it.", f"{loc}.k_values[{i}]")
    status_k = commit_level.get("status_k")
    if status_k is not None and not (_is_int(status_k) and status_k > 0):
        result.error("GE131", f"status_k must be a positive integer, not {_value_label(status_k)}; the evaluator "
                     "would ignore it and decide at the largest of k_values (1 without them).", f"{loc}.status_k")
    minimum = commit_level.get("minimum_required")
    if minimum is not None and not (_is_int(minimum) and minimum >= 0):
        result.error("GE131", f"minimum_required must be a non-negative integer, not {_value_label(minimum)}; the "
                     "evaluator would ignore it.", f"{loc}.minimum_required")
    required = _string_list(commit_level.get("required"))
    if commit_level.get("expect_no_bic") is True and required:
        result.error("GE132", f"expect_no_bic is true, but required names {', '.join(required)}: an intentionally "
                     "empty oracle has no required commits. The evaluator would keep required and ignore "
                     "expect_no_bic, with a note at every evaluation; remove one of the two.", f"{loc}.expect_no_bic")


def _validate_commit_list(value: Any, commit_by_id: dict[str, dict[str, Any]], result: ValidationResult, loc: str) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        result.error("GE124", f"{loc} must be a list when present.", loc)
        return
    for i, cid in enumerate(value):
        if not isinstance(cid, str):
            result.error("GE125", f"{loc} entries must be commit ids.", f"{loc}[{i}]")
        elif cid not in commit_by_id:
            result.error("GE126", f"{loc} refers to unknown commit '{cid}'.", f"{loc}[{i}]")


def _validate_context_sections(data: dict[str, Any], commit_by_id: dict[str, dict[str, Any]], result: ValidationResult) -> None:
    for section_name in ["work_items", "issues", "developer_hints"]:
        section = data.get(section_name)
        if section is not None and not isinstance(section, list):
            result.error("GE140", f"{section_name} must be a list when present.", section_name)
    _validate_issue_documents(data, result)
    for i, hint in enumerate(data.get("developer_hints", []) or []):
        if not isinstance(hint, dict):
            continue
        commit = hint.get("commit")
        if isinstance(commit, str) and commit not in commit_by_id:
            result.error("GE141", f"developer_hints[{i}] refers to unknown commit '{commit}'.", f"developer_hints[{i}].commit")
        refs = hint.get("referenced_commits")
        if isinstance(refs, list):
            for j, ref in enumerate(refs):
                if isinstance(ref, str) and ref not in commit_by_id:
                    result.error("GE142", f"developer_hints[{i}] references unknown commit '{ref}'.", f"developer_hints[{i}].referenced_commits[{j}]")


def _warn_unknown_keys(data: dict[str, Any], result: ValidationResult) -> None:
    """GW004: a key that no object of the graph schema has (issue #160).

    Only objects are looked into: a section of the wrong type is another
    check's.  The hint names a key of the same object that is spelt nearly
    the same (``parent`` -> ``parents``).
    """
    def check(obj: Any, allowed: frozenset[str], loc: str, subject: str) -> None:
        if not isinstance(obj, dict):
            return
        for key in obj:
            if key in allowed or key == FREE_FORM_KEY or (isinstance(key, str) and key.startswith(FREE_FORM_PREFIX)):
                continue
            near = difflib.get_close_matches(key, sorted(allowed), n=1, cutoff=0.8) if isinstance(key, str) else []
            hint = f" (did you mean '{near[0]}'?)" if near else ""
            result.warning("GW004", f"{subject} has an unknown key {key!r}{hint}, which nothing reads. A free-form "
                           f"note goes under '{FREE_FORM_KEY}' or a key that starts with '{FREE_FORM_PREFIX}' "
                           "(docs/graph-schema.md).", f"{loc}.{key}" if loc else str(key))

    check(data, TOP_LEVEL_KEYS, "", "The scenario")
    check(data.get("meta"), META_KEYS, "meta", "meta")
    check(data.get("repository"), REPOSITORY_KEYS, "repository", "repository")
    check(data.get("graph"), GRAPH_KEYS, "graph", "graph")
    commits = data.get("commits")
    for i, commit in enumerate(commits if isinstance(commits, list) else []):
        if not isinstance(commit, dict):
            continue
        name = f"Commit '{commit['id']}'" if isinstance(commit.get("id"), str) else f"commits[{i}]"
        check(commit, COMMIT_KEYS, f"commits[{i}]", name)
        operations = commit.get("operations")
        for j, op in enumerate(operations if isinstance(operations, list) else []):
            op_type = op.get("type") if isinstance(op, dict) else None
            if isinstance(op_type, str) and op_type in OPERATION_KEYS:       # an unknown type is GE052
                check(op, OPERATION_KEYS[op_type] | {"type"}, f"commits[{i}].operations[{j}]",
                      f"{name}: operation '{op_type}'")
    bugs = data.get("bugs")
    for i, bug in enumerate(bugs if isinstance(bugs, list) else []):
        if not isinstance(bug, dict):
            continue
        name = f"bug {bug['id']}" if isinstance(bug.get("id"), str) else f"bugs[{i}]"
        check(bug, BUG_KEYS, f"bugs[{i}]", name)
        for key, allowed, kind in (("faults", FAULT_KEYS, "fault"), ("fixes", FIX_KEYS, "fix")):
            entries = bug.get(key)
            for j, entry in enumerate(entries if isinstance(entries, list) else []):
                check(entry, allowed, f"bugs[{i}].{key}[{j}]", f"{name}: {key}[{j}]")
            check(bug.get(kind), allowed, f"bugs[{i}].{kind}", f"{name}: {kind}")
    expected = data.get("expected_szz")
    if not isinstance(expected, dict):
        return
    check(expected, EXPECTED_SZZ_KEYS, "expected_szz", "expected_szz")
    check(expected.get("commit_level"), COMMIT_LEVEL_KEYS, "expected_szz.commit_level", "expected_szz.commit_level")
    variants = expected.get("evaluation_variants")
    for i, variant in enumerate(variants if isinstance(variants, list) else []):
        loc = f"expected_szz.evaluation_variants[{i}]"
        check(variant, EVALUATION_VARIANT_KEYS, loc, loc)
        if isinstance(variant, dict):
            check(variant.get("commit_level"), COMMIT_LEVEL_KEYS, f"{loc}.commit_level", f"{loc}.commit_level")
    branch_level = expected.get("branch_level")
    for branch, spec in (branch_level.items() if isinstance(branch_level, dict) else []):
        loc = f"expected_szz.branch_level.{branch}"
        check(spec, BRANCH_LEVEL_KEYS, loc, loc)


REPORTED_LINE_RE = re.compile(r"^Reported:\s*(\S+)\s*$", re.M)


def _canonical_timestamp(value: Any) -> str | None:
    """The instant as ISO 8601 in UTC (``...Z``), or None if ``value`` is not a timestamp.

    Accepts a str or the ``datetime`` PyYAML makes of an unquoted value.  The
    instant is converted to UTC first, so two spellings of one moment -- ``Z``
    and ``+09:00`` -- canonicalise to the same string and compare equal;
    ``format_timestamp`` alone keeps the offset and would not.
    """
    if not isinstance(value, (str, datetime)) or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return format_timestamp(parse_timestamp(value).astimezone(timezone.utc))
    except (GitError, ValueError, TypeError):
        return None


def _validate_issue_documents(data: dict[str, Any], result: ValidationResult) -> None:
    """GW470/GW471/GW472: an issue's tool-visible document must exist and state its report date.

    decisions/tool-visible-context.md: an ``issues[]`` entry may name the
    ``document`` a commit writes into the repository and the ``reported_at``
    timestamp that document states.  Both are copies of each other, so they are
    checked against the ``write_file`` operations rather than trusted.

    ``reported_at`` may arrive as a str or as the ``datetime`` PyYAML makes of an
    unquoted ISO 8601 value; both are normalised and compared as instants with
    the document's ``Reported:`` line.  Anything else is GW472, never silence.
    The containers are re-checked here because validate_graph_static has only
    *reported* their types (GE030/GE044); it has not replaced them.
    """
    issues = data.get("issues")
    if not isinstance(issues, list):
        return
    written: dict[str, str] = {}
    commits = data.get("commits")
    for commit in commits if isinstance(commits, list) else []:
        if not isinstance(commit, dict):
            continue
        operations = commit.get("operations")
        for op in operations if isinstance(operations, list) else []:
            if isinstance(op, dict) and op.get("type") == "write_file" and isinstance(op.get("path"), str) and isinstance(op.get("content"), str):
                written[op["path"]] = op["content"]
    for i, issue in enumerate(issues):
        if not isinstance(issue, dict):
            continue
        document, reported_at = issue.get("document"), issue.get("reported_at")
        canonical = _canonical_timestamp(reported_at) if reported_at is not None else None
        if reported_at is not None and canonical is None:
            result.warning("GW472", f"issues[{i}].reported_at is not an ISO 8601 timestamp: {reported_at!r} ({type(reported_at).__name__}).", f"issues[{i}].reported_at")
        if isinstance(document, str):
            if document not in written:
                result.warning("GW470", f"issues[{i}] names document '{document}', but no commit writes it (write_file).", f"issues[{i}].document")
            elif canonical is not None:
                match = REPORTED_LINE_RE.search(written[document])
                stated = _canonical_timestamp(match.group(1)) if match else None
                if match is None:
                    result.warning("GW471", f"issues[{i}] says reported_at {canonical}, but '{document}' has no 'Reported: <timestamp>' line.", f"issues[{i}].reported_at")
                elif stated is None:
                    result.warning("GW471", f"issues[{i}]: '{document}' states 'Reported: {match.group(1)}', which is not an ISO 8601 timestamp.", f"issues[{i}].reported_at")
                elif stated != canonical:
                    result.warning("GW471", f"issues[{i}] says reported_at {canonical}, but '{document}' states Reported: {stated}.", f"issues[{i}].reported_at")
        elif reported_at is not None:
            result.warning("GW470", f"issues[{i}] has reported_at but names no document a tool could read it from.", f"issues[{i}].reported_at")


def _validate_graph_acyclic(commits: list[Any]) -> ValidationResult:
    result = ValidationResult()
    parent_map: dict[str, list[str]] = {}
    for commit in commits:
        if isinstance(commit, dict) and isinstance(commit.get("id"), str):
            # GE036 reports parents that are not a list; iterating `parents: 42` raised (issue #152)
            parents = commit.get("parents")
            parent_map[commit["id"]] = [p for p in parents if isinstance(p, str)] if isinstance(parents, list) else []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(cid: str) -> None:
        if cid in visited:
            return
        if cid in visiting:
            result.error("GE150", f"Commit graph contains a cycle at '{cid}'.", f"commits.{cid}")
            return
        visiting.add(cid)
        for parent in parent_map.get(cid, []):
            if parent in parent_map:
                visit(parent)
        visiting.remove(cid)
        visited.add(cid)

    for cid in parent_map:
        visit(cid)
    return result


def _validate_merge_parents(commits: list[Any]) -> ValidationResult:
    """GE049: a merge parent that Git would not record (issue #173).

    ``git merge`` records each head once, and drops a head that is already
    reachable from another one -- from the first parent or from another head
    of the same merge.  A parent listed twice, or an extra parent that is an
    ancestor of another parent, therefore leaves the generated commit with
    fewer parents than declared, and verification fails (GE627/GE628).  The
    first parent is always recorded (the generator merges with ``--no-ff``).
    """
    result = ValidationResult()
    parent_map: dict[str, list[str]] = {}
    for commit in commits:
        if isinstance(commit, dict) and isinstance(commit.get("id"), str) and isinstance(commit.get("parents"), list):
            parent_map[commit["id"]] = [p for p in commit["parents"] if isinstance(p, str)]

    def reaches(starts: list[str], target: str) -> bool:
        stack, seen = list(starts), set()
        while stack:
            cid = stack.pop()
            if cid == target:
                return True
            if cid not in seen:
                seen.add(cid)
                stack.extend(parent_map.get(cid, []))
        return False

    for i, commit in enumerate(commits):
        if not isinstance(commit, dict) or not isinstance(commit.get("parents"), list):
            continue
        cid = commit.get("id")
        parents = [p for p in commit["parents"] if isinstance(p, str)]
        for k, parent in enumerate(parents[1:], start=1):
            if parent in parents[:k]:
                result.error(
                    "GE049",
                    f"Commit '{cid}' lists parent '{parent}' twice: Git records each parent once, "
                    "so it would not record this merge as declared.",
                    f"commits[{i}].parents",
                )
                continue
            covering = next((other for other in parents if other != parent and reaches([other], parent)), None)
            if covering is not None:
                result.error(
                    "GE049",
                    f"Commit '{cid}' lists parent '{parent}', which is already an ancestor of its parent '{covering}': "
                    "Git does not record an already merged parent, so it would not record this merge as declared.",
                    f"commits[{i}].parents",
                )
    return result


def _validate_branch_rewinds(data: dict[str, Any]) -> ValidationResult:
    """GW151: a first parent off the branch that leaves commits unreachable (issue #174).

    A branch's tip is the last commit declared on it.  When a commit's branch
    already exists and its first parent is not the branch's tip, the generator
    checks the branch out and resets it to that parent (``_checkout_for_commit``).
    If the tip is an ancestor of the parent, that is a fast-forward (SZZG-0052
    and SZZG-0128 ``c4``) and nothing is reported.  Otherwise the branch no
    longer contains the commits only its old tip reached, and those that no
    ref reaches once generation has finished (``gitutils.reachable_commit_ids``:
    no branch, tag or HEAD) are not in ``git log --all``.  Not reported: a
    commit on a branch ``graph.ref_lifecycle.delete_branches`` deletes, and one
    that a commit's ``rebase_of`` or ``squashes`` names -- they are left behind
    on purpose.  A commit two resets leave behind is named at the later one.
    """
    result = ValidationResult()
    graph = data.get("graph") if isinstance(data.get("graph"), dict) else {}
    lifecycle = graph.get("ref_lifecycle") if isinstance(graph.get("ref_lifecycle"), dict) else {}
    if any(lifecycle.get(key) is not None and not isinstance(lifecycle.get(key), list)
           for key in ("tags", "delete_branches")):
        return result                    # the generator refuses it before it moves a ref
    default_branch = str(scenario_default_branch(data))
    try:
        commits, parents_of = history_graph(data)
        reachable = reachable_commit_ids(data)
    except (TypeError, ValueError, OverflowError):
        # a value the generator refuses, such as a commit_generator count of .inf
        # (OverflowError); --simulate and generation report it
        return result
    deleted = {name for name in lifecycle.get("delete_branches") or [] if isinstance(name, str)}
    rewritten: set[str] = set()
    for commit in commits:
        for key in REWRITE_DECLARATION_KEYS:
            value = commit.get(key)
            rewritten.update(v for v in (value if isinstance(value, list) else [value]) if isinstance(v, str))

    def branch_of(commit: dict[str, Any]) -> str:
        return str(commit_branch(commit, default_branch))

    def ancestors(cid: str) -> set[str]:
        seen: set[str] = set()
        stack = [cid]
        while stack:
            current = stack.pop()
            if current not in seen:
                seen.add(current)
                stack.extend(parents_of.get(current, []))
        return seen

    tips: dict[str, str] = {}
    resets: list[tuple[int, str, str, str, str]] = []   # (index, commit, branch, old tip, first parent)
    left_behind_by: dict[str, int] = {}                 # commit -> the last reset that left it behind
    for i, commit in enumerate(data.get("commits") or []):
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        cid, branch = commit["id"], branch_of(commit)
        parents = [p for p in commit.get("parents") or [] if isinstance(p, str)]
        if parents and branch in tips and tips[branch] != parents[0]:
            behind = ancestors(tips[branch]) - ancestors(parents[0])
            for c in commits:
                if c["id"] in behind:
                    left_behind_by[c["id"]] = len(resets)
            resets.append((i, cid, branch, tips[branch], parents[0]))
        tips[branch] = cid

    lost = [c["id"] for c in commits
            if c["id"] in left_behind_by and c["id"] not in reachable
            and branch_of(c) not in deleted and c["id"] not in rewritten]
    for k, (i, cid, branch, old_tip, first_parent) in enumerate(resets):
        named = [c for c in lost if left_behind_by[c] == k]
        if not named:
            continue                     # a fast-forward, or nothing is lost
        them = "it" if len(named) == 1 else "them"
        result.warning(
            "GW151",
            f"Commit '{cid}' resets branch '{branch}' from its tip '{old_tip}' to its first parent "
            f"'{first_parent}', which is not a fast-forward: after generation no ref reaches "
            f"{', '.join(repr(c) for c in named)}, so git log --all does not show {them}. If the rewrite "
            f"is intended, name {them} in a later commit's rebase_of or squashes; otherwise keep {them} "
            f"with a graph.ref_lifecycle tag, or put '{cid}' on another branch.",
            f"commits[{i}].parents",
        )
    return result


def _validate_ref_lifecycle(data: dict[str, Any], result: ValidationResult) -> None:
    """GE152-GE158: ``graph.ref_lifecycle`` as the generator applies it (issue #229).

    Only the generator read the section, after every commit existed.  The
    rules are ``graph_scenario.ref_lifecycle_problems``, which the generator
    asks too before it changes a ref; here the commits are the scenario's
    and those its ``commit_generator`` operations plan, and the branches
    those some commit is on.
    """
    graph = data.get("graph")
    if not isinstance(graph, dict) or "ref_lifecycle" not in graph:
        return
    default_branch = str(scenario_default_branch(data))
    commit_ids: set[str] = set()
    branches: set[str] = set()
    for commit in data.get("commits") if isinstance(data.get("commits"), list) else []:
        if not isinstance(commit, dict) or not isinstance(commit.get("id"), str):
            continue
        commit_ids.add(commit["id"])
        branches.add(str(commit_branch(commit, default_branch)))
        try:
            commit_ids.update(planned_generated_commits(commit["id"], commit))
        except (TypeError, ValueError, OverflowError):
            pass                         # operations or a count the generator refuses (GE044, --simulate)
    for code, location, message in ref_lifecycle_problems(graph["ref_lifecycle"], commit_ids=commit_ids,
                                                          branches=branches, default_branch=default_branch):
        result.error(code, message, location)


def _validate_rewrite_references(
    commit: dict[str, Any],
    cid: str,
    commit_by_id: dict[str, dict[str, Any]],
    result: ValidationResult,
    loc: str,
) -> None:
    """GE046/GE047: rebase_of, squashes and revert_of must name earlier commits."""
    for ref_key, allowed_types in REWRITE_REFERENCE_KEYS.items():
        value = commit.get(ref_key)
        if value is None:
            continue
        if not isinstance(value, allowed_types):
            expected = " or ".join(t.__name__ for t in allowed_types)
            result.error("GE046", f"{ref_key} must be a {expected} when present.", f"{loc}.{ref_key}")
            continue
        refs = value if isinstance(value, list) else [value]
        for k, ref in enumerate(refs):
            ref_loc = f"{loc}.{ref_key}[{k}]" if isinstance(value, list) else f"{loc}.{ref_key}"
            if not isinstance(ref, str):
                result.error("GE046", f"{ref_key} entries must be commit ids.", ref_loc)
            elif ref == cid or ref not in commit_by_id:
                result.error("GE047", f"{ref_key} refers to unknown or later commit '{ref}'.", ref_loc)


# --- opt-in lints (graph suite) ---------------------------------------------

def lint_graph_scenario(data: dict[str, Any], *, scenario_path: Path | None = None) -> ValidationResult:
    """Run the GW4xx lints on a statically valid graph scenario.

    Ghost invariants (add-only BFC / delete-only BIC) are not implemented for
    the graph suite.

    ``scenario_path`` enables the lints that compare the scenario against its
    sibling README; without it they are skipped.
    """
    result = ValidationResult()
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    commits = [c for c in (data.get("commits") or []) if isinstance(c, dict)]
    bugs = [b for b in (data.get("bugs") or []) if isinstance(b, dict)]
    bfc_ids = {e["commit"] for b in bugs for e in graph_bfc_entries(b) if isinstance(e.get("commit"), str)}

    lint_factors(meta.get("factors"), result, prefix="GW")
    lint_tier(meta, result, prefix="GW")
    lint_difficulty(meta, result, prefix="GW")
    lint_defeats(meta, result, prefix="GW")
    for i, bug in enumerate(bugs):
        for j, entry in enumerate(graph_bic_entries(bug)):
            role = entry.get("role")
            if isinstance(role, str) and role not in ALLOWED_BIC_ROLES:
                result.error(
                    "GE403",
                    f"BIC role '{role}' is a non-canonical spelling; canonical roles are {sorted(ALLOWED_BIC_ROLES)}. "
                    "Consumers normalize known aliases, but a scenario declares the canonical spelling.",
                    f"bugs[{i}].bug_introducing_commits[{j}].role",
                )
        for j, entry in enumerate(graph_bfc_entries(bug)):
            role = entry.get("role")
            if isinstance(role, str) and role not in ALLOWED_BFC_ROLES:
                result.error("GE404", f"BFC role '{role}' is not in {sorted(ALLOWED_BFC_ROLES)}.", f"bugs[{i}].bug_fixing_commits[{j}].role")
    _lint_commit_roles(data, result)
    lint_leakage(commits, bfc_ids, result, prefix="GW")
    lint_author_coincidence(data, "advanced-scenarios", result, prefix="GW")
    _lint_approximate_operations(commits, result)
    _lint_origin_coverage(bugs, data, result)
    _lint_history_summary(data, result)
    if scenario_path is not None:
        _lint_readme_history(commits, scenario_path, result)
        lint_readme_header(data, "advanced-scenarios", scenario_path, result, prefix="GW")
    return result


def _lint_commit_roles(data: dict[str, Any], result: ValidationResult) -> None:
    """GE405: a commit's ``role`` is one of ``ALLOWED_ROLES``, the list the classic suite's E030 enforces.

    decisions/vocabulary.md section 2.2 made the list canonical for both suites
    and planned this check; until issue #195 the graph validator read a role
    only for GW040 / GW041, and 28 shipped commits kept 16 other spellings.  An
    error, like the other vocabulary lints (GE400-GE404), and a lint, so a role
    does not stop ``generate-graph``: no scorer reads it.
    """
    for i, commit in enumerate(data.get("commits") or []):
        role = commit.get("role") if isinstance(commit, dict) else None
        if isinstance(role, str) and role not in ALLOWED_ROLES:
            result.error("GE405", f"Commit role '{role}' is not one of the commit roles both suites share: "
                         f"{sorted(ALLOWED_ROLES)} (decisions/vocabulary.md section 2.2).", f"commits[{i}].role")


#: A line of ``graph.history_summary`` that describes a commit: ``c3: merge feature branch into main``.
HISTORY_SUMMARY_LINE = re.compile(r"^[ \t]*(?P<id>[A-Za-z]\w*):", re.M)
#: The placeholder ``new-graph-scenario`` writes, ``TODO: Summarize the intended commit graph.``
HISTORY_SUMMARY_PLACEHOLDER = "TODO"


def _lint_history_summary(data: dict[str, Any], result: ValidationResult) -> None:
    """GW456: ``graph.history_summary`` names a commit the scenario does not define.

    The summary is prose for a reader of the YAML, one ``<id>: <phrase>`` line
    per commit, and nothing read it: SZZG-0128, the fast-forward twin of
    SZZG-0043, kept its twin's ``c3: merge feature branch into main`` although
    it has no ``c3`` and no merge (issue #178).  Only the id that opens a line
    is checked; the phrase is the author's.  The skeleton's ``TODO:`` line is
    not a commit, and a summary that leaves a commit out is not reported.
    """
    graph = data.get("graph")
    summary = graph.get("history_summary") if isinstance(graph, dict) else None
    if not isinstance(summary, str):
        return
    ids = [c.get("id") for c in data.get("commits") or [] if isinstance(c, dict) and isinstance(c.get("id"), str)]
    for match in HISTORY_SUMMARY_LINE.finditer(summary):
        name = match.group("id")
        if name not in ids and name != HISTORY_SUMMARY_PLACEHOLDER:
            result.warning("GW456", f"graph.history_summary describes commit '{name}', which the scenario does not "
                           f"define; its commits are {ids}.", "graph.history_summary")


#: A line of a README ``## Expected history`` block: ``c1: introduce bug (replace A.java)``.
README_HISTORY_LINE = re.compile(r"^(?P<id>[A-Za-z]\w*): (?P<phrase>[^(]+?) \((?P<ops>.*)\)\s*$")
README_HISTORY_BLOCK = re.compile(r"^## Expected history\s*\n+```text\n(?P<body>.*?)\n```", re.S | re.M)


def _readme_operation_summary(commit: dict[str, Any]) -> str:
    """Render a commit's operations the way the README blocks spell them."""
    parts = []
    for op in commit.get("operations") or []:
        if not isinstance(op, dict):
            continue
        kind = op.get("type")
        if kind in ("rename_file", "copy_file", "move_file"):
            parts.append(f"{kind} {op.get('from')} -> {op.get('to')}")
        elif "path" in op:
            parts.append(f"{kind} {op['path']}")
        else:
            parts.append(str(kind))
    return "; ".join(parts)


def _lint_readme_history(commits: list[dict[str, Any]], scenario_path: Path, result: ValidationResult) -> None:
    """GW454: the README's ``## Expected history`` block contradicts the scenario.

    Only the parenthesised operation list is checked, because that part is
    mechanically derivable from ``commits``; the surrounding phrase is prose and
    is left to the author.  READMEs that describe the history in prose instead
    of this shape have no such block and are not linted.  The block is a copy of
    data that lives in the scenario file, so it drifts silently whenever a
    commit's operations change -- which is exactly how SZZG-0001, SZZG-0003 and
    SZZG-0017 went stale when their histories were repaired for the graph-1.0
    freeze.
    """
    readme = scenario_path.with_name("README.md")
    try:
        text = readme.read_text(encoding="utf-8")
    except OSError:
        return
    block = README_HISTORY_BLOCK.search(text)
    if block is None:
        return
    by_id = {c["id"]: c for c in commits if isinstance(c.get("id"), str)}
    for line in block.group("body").splitlines():
        if not line.strip():
            continue
        match = README_HISTORY_LINE.match(line)
        if match is None:
            continue
        commit = by_id.get(match.group("id"))
        if commit is None:
            result.warning(
                "GW454",
                f"README 'Expected history' names commit '{match.group('id')}', which the scenario does not define.",
                f"{readme.name}:## Expected history",
            )
            continue
        expected = _readme_operation_summary(commit)
        if match.group("ops") != expected:
            result.warning(
                "GW454",
                f"README 'Expected history' describes commit '{match.group('id')}' as "
                f"'({match.group('ops')})' but the scenario's operations are '({expected})'.",
                f"{readme.name}:## Expected history",
            )


def _lint_approximate_operations(commits: list[dict[str, Any]], result: ValidationResult) -> None:
    """GW440-GW443: operations whose generated result only approximates the intent."""
    for i, commit in enumerate(commits):
        for j, op in enumerate(commit.get("operations") or []):
            if not isinstance(op, dict):
                continue
            entry = APPROXIMATE_OPERATIONS.get(op.get("type"))
            if entry is not None:
                code, message = entry
                result.warning(code, f"Commit '{commit.get('id', f'<commit[{i}]>')}': {message}", f"commits[{i}].operations[{j}]")


def _expected_szz_commit_ids(expected: Any) -> set[str]:
    """Every commit id named by expected_szz.commit_level or any evaluation variant."""
    ids: set[str] = set()
    if not isinstance(expected, dict):
        return ids
    levels = [expected.get("commit_level")]
    variants = expected.get("evaluation_variants")
    for variant in variants if isinstance(variants, list) else []:
        if isinstance(variant, dict):
            levels.append(variant.get("commit_level"))
    for level in levels:
        if not isinstance(level, dict):
            continue
        for key in EXPECTED_SZZ_COMMIT_LISTS:
            values = level.get(key)
            if isinstance(values, list):
                ids.update(cid for cid in (commit_id_of(v) for v in values) if cid is not None)
    return ids


def _lint_origin_coverage(bugs: list[dict[str, Any]], data: dict[str, Any], result: ValidationResult) -> None:
    """The direct/origin contract, checked on the scenario file (issue #3, D10).

    GW450 an origin BIC that expected_szz never mentions, in any variant.
    GW451 an origin that the *default* variant does not list as related_origins,
          so predicting it is a plain false positive rather than a recognised
          origin (contract D2).
    GW452 a scenario with an origin and no ``origin-aware`` variant, so there is
          no way to score a tool that reports origins as context (D3).
    GW453 an ``origin-aware`` variant that does not in fact accept the origin.

    Which variant is the default, and whether a variant accepts a prediction,
    are the evaluator's questions: both come from ``_commit_level_policy`` and
    ``classify_prediction`` rather than from reading the YAML here.  An earlier
    version read ``expected_szz.commit_level`` directly and inspected
    ``acceptable_related`` membership, and was wrong twice - it ignored
    ``default_variant`` when a base commit_level existed, and it called a
    variant accepting when a leftover ``related_but_not_correct`` entry or
    ``expect_no_bic`` meant the evaluator rejected the same prediction
    (PR #45 review).

    An origin that is itself ``required`` is exempt from GW451-GW453: it is the
    answer, not context, and an origin-aware variant would be identical to the
    default (SZZG-0018).
    """
    expected = data.get("expected_szz")
    mentioned = _expected_szz_commit_ids(expected)
    try:
        default = _commit_level_policy(data, "advanced-scenarios", None)
    except LINT_INPUT_ERRORS as exc:
        # GW130 has asked the same of the evaluator, so this is a safety net; a lint
        # that cannot run says so rather than passing (issue #161)
        result.warning("GW450", f"the origin lint could not resolve the default oracle ({exc}); GW450-GW453 "
                       "were not checked.", "expected_szz")
        return
    required = set(default.required)
    related_origins = set(default.related_origins)
    variants = expected.get("evaluation_variants") if isinstance(expected, dict) else None
    variant_names = {v.get("name") for v in (variants if isinstance(variants, list) else [])
                     if isinstance(v, dict) and isinstance(v.get("name"), str)}

    origins: list[str] = []
    for i, bug in enumerate(bugs):
        for j, entry in enumerate(graph_bic_entries(bug)):
            role = entry.get("role")
            cid = entry.get("commit")
            if not (isinstance(role, str) and "origin" in role and isinstance(cid, str)):
                continue
            loc = f"bugs[{i}].bug_introducing_commits[{j}]"
            label = bug.get("id", f"<bug[{i}]>")
            if cid not in mentioned:
                result.warning("GW450", f"bug {label} BIC '{cid}' has role '{role}' but appears in no expected_szz list (commit_level or any variant).", loc)
                continue
            if cid in required:
                continue
            if cid not in origins:
                origins.append(cid)
            if cid not in related_origins:
                result.warning("GW451", f"bug {label} BIC '{cid}' has role '{role}' but the default commit_level does not list it under related_origins (direct/origin contract D2).", loc)
    if not origins:
        return
    if "origin-aware" not in variant_names:
        result.warning("GW452", "scenario declares an origin BIC but offers no 'origin-aware' evaluation variant (direct/origin contract D3).", "expected_szz.evaluation_variants")
        return
    try:
        variant = _commit_level_policy(data, "advanced-scenarios", "origin-aware")
    except LINT_INPUT_ERRORS as exc:
        result.warning("GW453", f"the origin lint could not resolve the 'origin-aware' variant ({exc}); GW453 "
                       "was not checked.", "expected_szz.evaluation_variants")
        return
    scored = classify_prediction(variant, sorted(required | set(origins)))
    if scored.status != "PASS":
        result.warning("GW453", f"the 'origin-aware' variant does not accept the direct BICs together with origin(s) {sorted(origins)}: the evaluator returns {scored.status} (direct/origin contract D3).", "expected_szz.evaluation_variants")
