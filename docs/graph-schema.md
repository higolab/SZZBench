# The keys of a graph scenario (`scenario.graph.yml`)

This page lists the keys a graph scenario may have, object by object. They are
the keys that generation, validation, the in-memory simulation, verification
or evaluation read, and those the documentation describes as scenario fields.
`validate-graph` reports any other key as `GW004`, with its location and,
when a key of the same object is spelt nearly the same, that key: a commit
whose `parents` is misspelt `parent` gets `GW004` at `commits[1].parent`
(`did you mean 'parents'?`), besides `GE048` for the missing parents. Until
[issue #160](https://github.com/higolab/SZZBench/issues/160) the loader kept
every key and the checks read the ones they knew, so a key nothing reads was
neither reported nor used.

`src/szzbench/graph_validator.py` holds the same lists (`TOP_LEVEL_KEYS`,
`COMMIT_KEYS`, `OPERATION_KEYS`, ...), and `tests/test_schema_and_index.py`
compares them with the tables below. The values are checked by the codes of
[validation.md](validation.md); this page only says which keys exist.

## Free-form keys

Every object below may also carry:

- `notes`, prose for a reader (a string, or a list of strings);
- any key that starts with `x-`, such as `x-work_item: WI-001` on a commit: a
  note in a structured form.

Nothing reads either. Nine shipped scenarios carried such notes without the
prefix (`rebase_patch_modified`, `rebase_split_part`, `rebase_cleanup`,
`generated_files`, `large_noisy_rebased_commit`, a commit's and a bug's
`work_item`, the top-level `files` and `encoding`, and the `encoding` of
SZZG-0112's fault and fix); since issue #160 they are `x-` keys. SZZG-0114's top-level `commit_generators`, a copy of its two
`commit_generator` operations, was removed.

The keys inside the context sections of the top level, and inside the oracle
sections the evaluator does not score, are not listed: any key may be used
there. `graph.ref_lifecycle` has its own keys, which GE152 and GE155 check.

## Top level

| key | |
|---|---|
| `schema_version` | `"graph-1.0"` (GE001, GE002) |
| `meta` | the scenario's identity and labels (below) |
| `repository` | the generated repository (below) |
| `graph` | the shape of the history (below) |
| `commits` | the commits, in topological order |
| `bugs` | the bugs, with their BICs, BFCs, faults and fixes |
| `expected_szz` | the oracle (below, and [evaluation-policies.md](evaluation-policies.md)) |
| `scenario_design` | context for a reader: the purpose, key property, evaluation points and failure mode ([decisions/vocabulary.md](decisions/vocabulary.md) §8) |
| `issues`, `work_items`, `developer_hints` | context a tool may be given ([decisions/tool-visible-context.md](decisions/tool-visible-context.md)); GE140–GE142 and GW470–GW472 check some of their fields |
| `clone_relationships`, `copy_relationships`, `bug_instances`, `bug_groups`, `semantic_rewrites`, `fix_series`, `context` | context for a reader; the README header lists the sections a scenario has |

## `meta`

| key | |
|---|---|
| `id` | `SZZG-XXXX` (GE012, GE013) |
| `title`, `slug`, `description` | copied into the index (`title`, `slug`) and the README header (`title`) |
| `category`, `category_code` | [decisions/vocabulary.md](decisions/vocabulary.md) §3 |
| `factors` | §1 |
| `difficulty`, `status` | §4 |
| `tier`, `defeats` | §7, §8 |

## `repository`

| key | |
|---|---|
| `name` | the repository's name |
| `default_branch` | the branch `git init` starts on, `main` without the key |
| `language`, `build_system`, `source_root` | what the sources are, and how they are built ([decisions/vocabulary.md](decisions/vocabulary.md) §4) |
| `base_date` | the first commit's date ([generator-options.md](generator-options.md) §1) |

`new-graph-scenario` used to write a `default_branch` into `graph` as well;
nothing read it, and the default branch is the one of `repository`.

## `graph`

| key | |
|---|---|
| `model` | a label, `commit_dag` |
| `history_summary` | one `<id>: <phrase>` line per commit, for a reader (GW456) |
| `ref_lifecycle` | tags and branch deletions applied after the last commit ([generator-options.md](generator-options.md) §3) |

## A commit

An entry of `commits`.

| key | |
|---|---|
| `id`, `parents`, `branch` | the commit's place in the history (GE033–GE039, GE048) |
| `message` | the subject (GE040, GE070) |
| `role` | a label from the list both suites share (GE405) |
| `operations` | the file operations (below) |
| `allow_empty` | `true` lets the commit be empty (GE077, GW045, GE202) |
| `author`, `date`, `author_date`, `committer_date` | [generator-options.md](generator-options.md) §1 |
| `rebase_of`, `squashes`, `revert_of`, `cherry_pick_of`, `backport_of` | what the commit rewrites or replays (GE042–GE047) |
| `inherit_message`, `inherit_author_date`, `inherit_author`, `cherry_pick_trailer` | [generator-options.md](generator-options.md) §3 |
| `apply_revert`, `mainline`, `resolution` | §3 |
| `interactive_rebase`, `rebase_conflict_resolution`, `reverts`, `revert_conflict_resolution` | copied into `graph-map.json` as written (§4) |

## An operation

An entry of a commit's `operations`. Each operation has a `type`, and the keys
of its type; an unknown type is GE052.

| operation | keys besides `type` |
|---|---|
| `write_file` | `path`, `content`, `line_ending`, `encoding` |
| `replace` | `path`, `old`, `new`, `occurrence`, `line_ending`, `encoding` |
| `insert_after` | `path`, `anchor`, `content`, `occurrence`, `line_ending`, `encoding` |
| `delete_file` | `path` |
| `rename_file` | `from`, `to`, `overwrite` |
| `move_file` | `from`, `to`, `overwrite` |
| `copy_file` | `from`, `to`, `overwrite` |
| `move_entity` | `entity`, `from_file`, `to_file`, `overwrite`, `append`, `remove_source_file`, `line_ending`, `encoding` |
| `copy_entity` | `entity`, `from_file`, `to_file`, `overwrite`, `append`, `line_ending`, `encoding` |
| `chmod` | `path`, `mode` |
| `write_binary_file` | `path`, `content_base64` |
| `write_generated_text_file` | `path`, `lines`, `template`, `header`, `footer`, `encoding` |
| `commit_generator` | `generator`, `count`, `files`, `path` |
| `apply_squash` | `from_commits` |
| `apply_patch_from` | `commit`, `mainline`, `parent` |
| `apply_patch` | `path`, `patch` |
| `format_file` | `path`, `line_ending`, `encoding` |

## A bug

An entry of `bugs`.

| key | |
|---|---|
| `id`, `title` | |
| `bug_introducing_commits` | a list of commit ids or of objects with `commit` and `role` (GE084) |
| `bug_fixing_commits`, `bug_fixing_commit` | a list like the above, or one commit id (GE085) |
| `faults`, `fixes`, `fault`, `fix` | lists of fault and fix entries, or one entry (GE107; below) |
| `origin_faults` | the faults at an origin BIC ([decisions/fault-library.md](decisions/fault-library.md)) |
| `refactorings`, `bug_instances` | the refactoring metadata and bug instances the README names among the graph-only features |

The entries of `bug_introducing_commits` and `bug_fixing_commits` are not
listed: their `commit` and `role` are read, and anything else is the author's.

## A fault or a fix

An entry of a bug's `faults` or `fixes`, or its `fault` or `fix`.

| key | |
|---|---|
| `id` | |
| `commit`, `file`, `entity` | where the fault or fix is (GE100–GE103, GE105) |
| `statement`, `added_statement`, `removed_statement`, `missing_statement` | the statement verification looks for (GE104) |
| `change_type` | a fault's kind of change |
| `fix_type` | a fix's kind of change |
| `description`, `role`, `case`, `location`, `semantic_role` | labels that tell a reader one entry from another |

## `expected_szz`

| key | |
|---|---|
| `commit_level`, `evaluation_variants`, `default_variant`, `branch_level` | the scored oracle ([evaluation-policies.md](evaluation-policies.md)) |
| `line_level`, `entity_level`, `bug_level`, `work_item_level`, `bug_instances` | oracle sections the evaluator does not score; any key may be used inside them |

## A `commit_level`

The `commit_level` of `expected_szz` and of each evaluation variant.

| key | |
|---|---|
| `evaluation_policy` | the name of a policy (GE123, GW123) |
| `required`, `acceptable_related`, `related_origins`, `related_but_not_correct`, `relevant`, `known_distractors` | the commit lists (GE121, GE124–GE126) |
| `expect_no_bic`, `minimum_required`, `k_values`, `status_k` | (GE131, GE132) |

## An evaluation variant

An entry of `evaluation_variants`.

| key | |
|---|---|
| `name` | how `--evaluation-variant` and `default_variant` name it (GE122) |
| `description` | for a reader |
| `commit_level` | the variant's oracle (above) |

## A `branch_level` entry

The value of each branch name in `branch_level`.

| key | |
|---|---|
| `bfc`, `required` | GE127, GE128 |
