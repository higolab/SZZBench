# Generator options

This document describes the scenario keys that control *how* the generators
turn a scenario into a Git repository. It covers the options introduced for
GitHub issues #9 (deterministic metadata), #18 (placeholder operations) and
#17 (history-rewriting fidelity), the Git environment every generation
runs in (#96, section 5), and the manifest that says what an output was made
from (#93, section 6). Keys marked *graph* exist only in
`scenario.graph.yml`; keys marked *both* work in `scenario.yml` and
`scenario.graph.yml`.

All keys are optional. Scenarios that do not use them generate exactly the
same trees, subjects and refs as before, with three exceptions where the
semantics of an *existing* key changed:

* the default author/date of commits without `author`/`date` is now
  deterministic instead of the generation time (first section);
* `chmod` now records the mode change because `core.filemode` is enabled for
  scenarios that use it (SZZG-0111), and `commit_generator` creates real
  commits instead of a placeholder file (SZZG-0114), so the trees of those
  commits differ;
* every `revert_of` commit gets the `This reverts commit <hash>.` body footer
  (SZZG-0084/0085); subjects are unchanged.

Commits with explicit `author` and `date` keep byte-identical hashes.

## 1. Commit metadata (#9)

### Deterministic defaults

| Situation | Effective value |
|---|---|
| commit has `author` | used verbatim |
| commit has no `author` | one of six pool authors, chosen by a stable hash of `(meta.id, commit index)` |
| commit has `date` | used verbatim for both author and committer date |
| commit has no `date` | the scenario's base date plus irregular weekday gaps (see below) |

A scenario that pins **any** timestamp (`date`, `author_date` or
`committer_date` on any commit) keeps the plain schedule, `base_date + commit
index` days, for the commits it leaves to the generator: spreading only some of
them over the irregular gaps would place them after the pinned ones and invert
the history. The schedule below therefore applies to scenarios whose timeline is
entirely generated, which is most of the graph suite.

The commit index is the 0-based position of the commit in the `commits` list.
The first commit of a scenario without dates sits **exactly** on the base date;
each later commit adds one to nine days, skips weekends, and takes a
working-hour time (08:00-18:00). All of it is derived from a stable hash of the
scenario id, so dates are reproducible, strictly increasing in the commit index
- a commit is always newer than its parents - and no longer the one-per-day ramp
at a single time that every scenario used to share. Without `repository.base_date`
the base date itself is derived from the scenario id inside a 2023..mid-2025
window, so repositories do not all start on the same day. The author pool is

```
Aiko Tanaka <aiko.tanaka@example.com>     Dana Okafor <dana.okafor@example.com>
Bruno Fischer <bruno.fischer@example.com> Elena Rossi <elena.rossi@example.com>
Chen Wei <chen.wei@example.com>           Farid Haddad <farid.haddad@example.com>
```

The hash only uses the scenario id and the commit index, never the role, so a
predictor cannot infer "bug-introducing" from the author. Generation is fully
reproducible: two runs of the same scenario yield identical commit hashes.
The policy behind this is [docs/decisions/oracle-leakage.md](decisions/oracle-leakage.md).

### `repository.base_date` (*both*)

```yaml
repository:
  name: SZZG-0200-example
  default_branch: main
  base_date: "2024-06-01T10:00:00Z"   # ISO 8601, quote it so YAML keeps a string
```

Default: derived from the scenario id (a weekday between 2023-01-09 and
mid-2025). Only used for commits without `date`. The first commit of the
scenario reproduces this timestamp verbatim; later ones add the gaps described
above.

### `author_date` / `committer_date` (*both*)

Each falls back to `date`, then to the deterministic default. This makes the
"author date < committer date" signal of rebased/cherry-picked commits
expressible.

```yaml
- id: r1
  message: "r1: rebased feature commit"
  author_date: "2024-01-02T10:00:00Z"      # when the change was written
  committer_date: "2024-01-05T09:30:00Z"   # when it was replayed onto main
```

Dates must be ISO 8601 (`2024-01-02T10:00:00Z` or with an offset such as
`+09:00` or `+0900`). Quote them in YAML; unquoted timestamps are also accepted.
A value without a zone (`2024-01-02T10:00:00`) is **UTC**, quoted or not: every
pinned value is parsed and handed to Git with its zone, so the hashes do not
depend on the time zone of the machine that generates them. Until issue #133 a
quoted value without a zone reached Git verbatim and Git read it in local time,
while the same value unquoted (a YAML timestamp) was already UTC. A value that
is not ISO 8601 (`yesterday`) is an error that names the field, rather than
whatever date Git makes of it.

### What is recorded

`commit-map.json` now records the *effective* values for every commit:

```json
"c1": {
  "hash": "...",
  "message": "c1: introduce bug",
  "author": "Chen Wei <chen.wei@example.com>",
  "date": null,
  "author_date": "2024-01-02T10:00:00Z",
  "committer_date": "2024-01-02T10:00:00Z",
  "role": "bug_introducing"
}
```

`date` keeps the value written in the scenario (or `null`); `author_date` and
`committer_date` are what Git was given, always with a zone (`Z` or an offset);
`author` is the effective author (pool author when the scenario had none).

## 2. Operations and placeholders (#18)

### `core.filemode` and `chmod` (*graph*)

Repositories are initialised with `core.filemode=false` for Windows
compatibility. When any commit of a graph scenario contains a `chmod`
operation, the generator switches the repository to `core.filemode=true`
after `git init`, so the mode change is recorded (`100644` -> `100755`) and a
chmod-only commit is no longer empty. No scenario key is needed.

Limitation: on file systems without an executable bit (most Windows setups)
the chmod still has no effect and such a commit needs `allow_empty: true`.

### `line_ending: lf | crlf` (*both*)

Available on `write_file`, `replace` and `insert_after` (the latter is graph
only). Text is normalised to LF internally and re-encoded when written.

```yaml
- type: write_file
  path: src/Config.java
  line_ending: crlf          # bytes on disk use \r\n
  content: |
    package example;
    public class Config {}
- type: replace
  path: src/Config.java
  old: "class Config {}"
  new: "class Config { int x; }"
  # no line_ending: the file is CRLF, so it stays CRLF
- type: replace
  path: src/Config.java
  old: "int x;"
  new: "int x = 1;"
  line_ending: lf            # rewrites the whole file with \n (a real "CRLF -> LF" commit)
```

Defaults:

* `write_file` without the key writes LF (unchanged behaviour).
* `replace` / `insert_after` without the key keep the file's existing
  convention: a file whose every newline is CRLF stays CRLF; anything else
  (LF or mixed) is written as LF, as before.

Limitations: the in-memory simulators (`validate --simulate`,
`validate-graph --simulate`) always work on LF text, so `old`/`anchor`
matching is line-ending agnostic. Statements in `bugs` are matched against the
file content as Git stores it; a statement that spans lines must therefore not
be used for CRLF files. A BOM is not handled by this key; see `encoding`.

### `encoding` (*both*)

Available on `write_file` and `replace` in both suites (and on the graph
`insert_after`). It names the codec used for the bytes on disk; the default
is `utf-8`. Its one intended use is `utf-8-sig`, which reads and writes a
UTF-8 byte order mark: a `write_file` with `encoding: utf-8-sig` and otherwise
unchanged content — or a `replace` with `encoding: utf-8-sig` whose `old`
equals `new` — is a *BOM-only re-save*, the commit shape of SZZ-0206.

```yaml
- type: write_file
  path: src/limits/upload.py
  encoding: utf-8-sig        # bytes start with EF BB BF
  content: |
    MAX_UPLOAD_KB = 6144
- type: replace
  path: src/limits/upload.py
  old: "MAX_UPLOAD_KB = 6144"
  new: "MAX_UPLOAD_KB = 61440"
  # no encoding: read and written as UTF-8, so the BOM survives as U+FEFF
- type: replace
  path: src/limits/upload.py
  encoding: utf-8-sig        # strips the BOM on read, writes one back: still exactly one
  old: "61440"
  new: "20480"
```

In the classic suite the key is closed like `line_ending`: `utf-8` or
`utf-8-sig` in any spelling Python accepts, anything else an operation error.
The classic in-memory simulator applies the codec's read and write behaviour
to the simulated text, which stores a BOM as a leading U+FEFF: `utf-8-sig`
strips one on read and writes one, `utf-8` keeps it as text. A BOM added or
removed by either operation is therefore a change (not `E250`), statements
stay substrings of the decoded text, and the simulator accepts a history
exactly when Git would record it as distinct commits. The graph operations
pass any codec name to Python unchecked and the graph simulator does not model
it; a graph commit that changes only the encoding needs another change or
`allow_empty` to pass `GE202`.

### `write_generated_text_file.header` / `.footer` (*graph*)

```yaml
- type: write_generated_text_file
  path: src/main/java/example/LargeRange.java
  lines: 10000
  template: "  public int value_${line} = ${line};"
  header: |
    package example;
    public class LargeRange {
  footer: "}"
```

Both are optional strings written before/after the generated lines. A missing
trailing newline is added, so `footer: "}"` and `footer: "}\n"` are
equivalent. Defaults: empty. The simulator ignores `header`/`footer`, so
`replace` operations that target header text pass generation but not
`validate-graph --simulate`.

### `commit_generator` (*graph*) - real expansion

```yaml
- id: c2
  branch: main
  parents: [c1]
  message: "c2: unrelated churn"
  role: intermediate
  operations:
  - type: commit_generator
    generator: unrelated_changes   # free-form name, used in file names and messages
    count: 500                     # number of real commits (capped at 2000)
    files: 10                      # number of files that are touched in rotation
    path: generated                # directory of the generated files
```

Behaviour:

* `count` real commits are created **before** the owning commit (`c2`), on the
  same branch, as a linear chain: `c1 <- c2.g1 <- ... <- c2.g500 <- c2`.
* Generated commit *k* appends one line to file
  `<path>/<generator>-<NN>.txt` where `NN = (k-1) mod files + 1`; a file keeps
  at most 50 lines so blobs stay small. Content, authors (pool) and dates are
  deterministic. Author dates and committer dates are placed **separately**,
  each spaced evenly *strictly inside* the interval between the actual
  parent's and the owner's *effective* date of that kind (the
  `author_date` / `committer_date` recorded in commit-map, including an
  inherited author date), so `parent < g1 < ... < gN < owner` holds for the
  author sequence and for the committer sequence even when the two intervals
  do not overlap or the commits are only minutes apart; without a parent the
  day before the owner is used. When an interval is shorter than `count + 1`
  seconds a strict order is impossible at Git's one-second resolution: that
  date kind is clamped to the parent's timestamp (non-decreasing, never after
  the owner), `generation.log` says so, and every generated entry records
  `timestamp_placement: clamped` (with the per-kind detail in
  `timestamp_placement_detail: {author, committer}`) instead of `spaced`.
* The ids `<owner>.g1 … <owner>.g<count>` are **reserved**. If a scenario
  commit (declared before or after the owner) already uses one of them,
  generation fails before touching the repository instead of overwriting the
  logical commit in `commit-map.json`.
* Messages are neutral: `Update generated/unrelated_changes-03.txt (unrelated_changes 3/500)`.
* The owning commit is created afterwards with its remaining operations; when
  it has none it is committed with `--allow-empty` automatically.
* The commits are written with `git fast-import` in one process (1000 commits
  take about one second).

Recorded metadata:

* `commit-map.json`: one entry per generated commit, keyed `<owner>.g<N>`,
  with `role: generated`, `generated_by: <owner>`, `path`, author and dates;
  the owner gets `generated_commits: [<owner>.g1, ...]`.
* `graph-map.json`: `generated_commits: {<owner>: [ids]}` at the top level and
  in the owner's commit entry.

The verifier expects the first parent of the owning commit to be its last
generated commit; commits whose declared parent owns generated commits still
point at that parent's own hash.

Defaults and compatibility: `path` defaults to `generated`; a file-like
value such as `generated/unrelated-batch-1.txt` (the old placeholder file)
means its parent directory, and a root-level file such as `notes.txt` means
the repository root (files are then named `<generator>-<NN>.txt` without a
directory). `files` defaults to 1. `count` larger than 2000
is capped (a note is written to `generation.log`). The simulator still models
the old placeholder file, so `validate-graph --simulate` does not report the
owning commit as empty.

### Unchanged limitations

* `apply_patch` is still not implemented (validation accepts it; generation
  raises).
* `format_file` only strips trailing whitespace from every line.
* `move_entity` / `copy_entity` remain the whole-file approximation with a
  `// SZZBench move_entity: ...` header (issue #2).

## 3. History-rewriting fidelity (#17)

### `inherit_message` / `inherit_author_date` (*graph*)

For commits that declare `rebase_of` (or `cherry_pick_of` / `backport_of`).

```yaml
- id: r1
  branch: main
  parents: [c1]
  role: bug_introducing
  rebase_of: f1
  inherit_message: true        # subject of f1, because r1 has no message
  inherit_author_date: true    # author date of f1; committer date stays default/explicit
  operations:
  - type: replace
    path: src/main/java/example/Range.java
    old: return value >= min && value <= max;
    new: return value > min && value < max;
```

* `inherit_message: true` uses the source's subject **only when the commit
  has no `message`**; an explicit `message` always wins.
* `inherit_author_date: true` copies the source's author date; the committer
  date is the commit's own `committer_date`/`date` or the deterministic
  default, which reproduces the `author date < committer date` pattern of a
  real rebase.
* Defaults: both `false` (nothing inherited, as before).
* `commit-map.json` records `inherits: {source, source_hash, message,
  author_date, subject?}`.

`rebase_of` still does not replay the source commit: the `operations` (or an
`apply_patch_from`) describe the rebased content, exactly as before.

### `graph.ref_lifecycle` (*graph*, top level)

Applied after all commits exist.

```yaml
graph:
  model: commit_dag
  ref_lifecycle:
    delete_branches: [feature]           # the pre-rebase branch disappears
    tags:
    - name: v1.0                         # lightweight tags on logical commits
      commit: c0
    - name: pre-rebase/feature
      commit: f1                         # keeps the original reachable through a tag
```

* Deleting the currently checked-out branch switches to the default branch
  first (or detaches HEAD when the default branch is deleted too).
* Unknown branch names or commit ids are errors.
* `graph-map.json` records the final refs for **every** graph scenario:
  `refs: {branches: {name: hash}, tags: {name: hash}}`, and
  `ref_lifecycle: {deleted_branches: [...], tags: {name: {commit, hash}}}` when
  the section was present. `branches` no longer lists deleted branches.
* Default: no section, refs are unchanged from today (all branches remain).

Commits that become unreachable are not garbage-collected; the hashes stay
valid for `commit-map.json`, but tools that walk from refs will not see them.

### `cherry_pick_trailer` (*graph*)

```yaml
- id: r1
  branch: release
  parents: [c0]
  message: "r1: backport boundary fix"
  role: cherry_pick
  cherry_pick_of: c1
  cherry_pick_trailer: true
```

Appends `(cherry picked from commit <hash>)` as a body line, like
`git cherry-pick -x`. Sources are `cherry_pick_of`/`backport_of` and every
`apply_patch_from` operation of the commit (one line each). The subject stays
exactly `message`, so the verifier's subject check is unaffected. Default:
`false`. The body is recorded in `commit-map.json` under `body`.

### `revert_of`, `apply_revert` and `mainline` (*graph*)

```yaml
- id: c2
  branch: main
  parents: [c1]
  role: bug_fixing
  revert_of: c1                # no operations -> git revert --no-commit <hash of c1>
  # message: omitted -> 'Revert "<subject of c1>"'
- id: c5
  branch: main
  parents: [m1]
  role: bug_fixing
  revert_of: m1
  mainline: 1                  # required to revert a merge commit
  apply_revert: true           # run git revert first, then the operations below
  message: "c5: back out feature merge"
  operations:
  - type: replace
    path: CHANGELOG.md
    old: "## Unreleased"
    new: "## Unreleased\n- reverted feature"
- id: c7
  branch: main
  parents: [c6]
  role: bug_reintroducing
  revert_of: c6                # operations without apply_revert: hand-written (partial) revert,
  message: "c7: partially revert c6"   # git revert is NOT run (existing SZZG-0084/0085 style)
  operations:
  - type: replace
    path: src/main/java/example/Range.java
    old: return value >= min && value <= max;
    new: return value > min && value < max;
```

* The real `git revert --no-commit [--mainline N] <hash>` runs when the commit
  has **no `operations`**, or when `apply_revert: true` is set; in the latter
  case the `operations` are applied after the revert. This mirrors
  `cherry_pick_of`, which only cherry-picks when there are no operations, and
  keeps the existing scenarios SZZG-0084/0085 (hand-written partial reverts)
  working.
* Subject: `message` when present, otherwise `Revert "<source subject>"`.
* The body always ends with `This reverts commit <hash>.` whenever `revert_of`
  is declared (also for hand-written reverts), which revert-aware tools look
  for.
* Defaults: `apply_revert: false`; `mainline` unset (only needed for merges).
* `graph-map.json` records `revert_of` (and passes `reverts` /
  `revert_conflict_resolution` through); `commit-map.json` records the
  effective `message` and `body`.
* `validate-graph --simulate` checks a scenario with a real revert by
  generating it with Git in a temporary directory (GE203 on failure, GI203
  otherwise; `docs/validation.md`), because the in-memory model does not
  compute reverts. Until 2026-09-29 it reported such a commit as "would be
  empty" (issue #94).

### `resolution` (*graph*) - conflict resolution

```yaml
- id: m1
  branch: main
  parents: [c1, f1]
  message: "m1: merge feature"
  role: merge
  resolution:
    src/main/java/example/Range.java: |
      package example;
      public class Range {
        public boolean contains(int value, int min, int max) {
          return value >= min && value <= max; // resolved
        }
      }
    docs/OLD.md: null            # null deletes the path (delete/modify conflicts)
```

When `git merge`, the implicit `git cherry-pick` of a `cherry_pick_of` /
`backport_of` commit without operations, or `git revert` reports conflicts,
the generator writes every `resolution` entry, runs `git add -A` and continues
with the remaining operations and the commit. Every conflicted path must be
covered by `resolution`; otherwise, or when the key is absent, generation
fails with a message that lists the conflicted paths. Conflicted paths are
read from Git NUL-separated (`--name-only -z`) and compared verbatim with the
`resolution` keys, so non-ASCII names such as `src/main/java/example/範囲.java`
or names containing spaces work. Merges stay merge commits (both parents),
cherry-picks/reverts become ordinary commits and no
`CHERRY_PICK_HEAD`/`REVERT_HEAD` is left behind. `commit-map.json` records
`resolved_conflicts: [paths]`.

A commit with **three or more parents** is generated as a real octopus merge:
all extra parents are passed to a single `git merge --no-ff --no-commit`, because
a second `git merge --no-commit` while `MERGE_HEAD` exists is refused. Git's
octopus strategy does not resolve conflicts, so `resolution` applies to
two-parent merges only; an octopus whose branches touch the same lines fails
generation (SZZG-0129 is the in-suite example of a clean one).

Limitations: `resolution` is applied only when Git reports a conflict; if the
merge is clean the entries are ignored. `apply_squash` and `apply_patch_from`
do not use `resolution`. `validate-graph --simulate` checks a scenario with a
`resolution` by generating it with Git in a temporary directory, like any
scenario with a merge, a real cherry-pick or revert, or a patch operation;
until 2026-09-29 it reported the resolved conflict as an error (issue #94).

## 4. Summary of new keys

| Key | Where | Suite |
|---|---|---|
| `repository.base_date` | top level | both |
| `author_date`, `committer_date` | commit | both |
| `line_ending` | `write_file`, `replace`, `insert_after` operations | both (`insert_after`: graph) |
| `encoding` | `write_file`, `replace`, `insert_after` operations | both (`insert_after`: graph) |
| `header`, `footer` | `write_generated_text_file` operation | graph |
| `commit_generator.path` (directory), `count` (capped 2000), `files` | operation (semantics) | graph |
| `inherit_message`, `inherit_author_date` | commit with `rebase_of`/`cherry_pick_of`/`backport_of` | graph |
| `cherry_pick_trailer` | commit | graph |
| `revert_of`, `apply_revert`, `mainline` | commit | graph |
| `resolution` | commit | graph |
| `graph.ref_lifecycle.delete_branches`, `graph.ref_lifecycle.tags[].name/commit` | top level | graph |

New metadata fields: `commit-map.json` -> `author_date`, `committer_date`,
`body`, `generated_commits`, `inherits`, `resolved_conflicts`, and
`<owner>.g<N>` entries (`role: generated`, `generated_by`, `path`);
`graph-map.json` -> `generated_commits`, `refs`, `ref_lifecycle`, per-commit
`revert_of` and `generated_commits`, and pass-through of `squashes`,
`interactive_rebase`, `rebase_conflict_resolution`, `reverts`,
`revert_conflict_resolution` when a commit declares them.

## 5. The Git environment (#96)

Every Git command SZZBench runs -- generation and verification, and the
measurements `evaluate`, `baselines` and `coverage` take on a generated
repository -- goes through `gitutils.run_git`, which runs Git isolated from the
caller's own Git setup:

| Withheld | How |
|---|---|
| the system configuration (`/etc/gitconfig`; Git for Windows' `etc/gitconfig`) | `GIT_CONFIG_NOSYSTEM=1` |
| the global configuration (`~/.gitconfig`, `$XDG_CONFIG_HOME/git/config`) and the files Git reads without being told to (`$XDG_CONFIG_HOME/git/ignore`, `$XDG_CONFIG_HOME/git/attributes`) | `HOME` and `XDG_CONFIG_HOME` name an empty temporary directory |
| the system attributes file | `GIT_ATTR_NOSYSTEM=1` |
| **every `GIT_*` variable of the caller except `GIT_EXEC_PATH`**: configuration injected through the environment (`GIT_CONFIG_COUNT` with `GIT_CONFIG_KEY_<n>` / `GIT_CONFIG_VALUE_<n>`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`), the repository Git works on (everything `git rev-parse --local-env-vars` lists, such as `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`), the format of a new repository (`GIT_DEFAULT_HASH`, `GIT_DEFAULT_REF_FORMAT`), `GIT_TEMPLATE_DIR`, `GIT_NAMESPACE`, diff and pathspec behaviour (`GIT_EXTERNAL_DIFF`, `GIT_DIFF_OPTS`, `GIT_*_PATHSPECS`), and the caller's `GIT_AUTHOR_*` / `GIT_COMMITTER_*` | removed from the environment; the generators set the identity and dates of every commit themselves (section 1) |
| the init template (`init.templateDir`, the templates the installation ships) | `git init --template=` copies no hooks |
| a Git whose built-in default object or ref format differs | `git init --object-format=sha1` (Git 2.29 and later) and `--ref-format=files` (2.45 and later) |

Signing (`commit.gpgSign`, `tag.gpgSign`), hooks, global ignores and
attributes, clean/smudge filters, `rerere`, rename and diff settings, and
output settings such as `color.ui` therefore cannot change what a scenario
generates or what SZZBench measures on it. What a generated repository needs
is written into its own `.git/config` (`user.name`, `user.email`,
`core.autocrlf=false`, `core.filemode`, `i18n.*`).

Before 2026-09-29 Git inherited all of this. Reproduced for issue #96 on
SZZ-0006, SZZG-0107 and SZZG-0124: an unavailable signing program, an ignore
file listing `*.java`, a global clean filter and an init template with a
commit-msg hook each made the scenarios fail. Four settings changed the result
without any finding -- verification reported 0 errors and 0 warnings: a working
(SSH) signing key and a global commit-msg hook changed every hash; a default
ignore file listing `build/` dropped the generated file SZZG-0107 is about; and
with `GIT_DIR` set in the environment every commit was written into the
repository `GIT_DIR` named. The review of PR #98 added one more: with
`GIT_DEFAULT_HASH=sha256` generation verified with 64-character hashes (and
`GIT_DEFAULT_REF_FORMAT=reftable` wrote a reftable repository), which is why
the rule is now every `GIT_*` variable rather than a list of known ones.
`tests/test_git_isolation.py` injects each of these through the test process's
environment only.

Where no such setting was present the isolation changes nothing: all 279
scenarios generate the same 2,208 commit hashes as before, so existing
generated repositories stay valid.

What it gives up: no setting of your own reaches SZZBench's Git commands,
`safe.directory` included. Git refuses a generated repository owned by another
user as "dubious ownership" -- in a container running as root over a mounted
directory, for example; run SZZBench as the owner of the output directory.

SZZBench needs Git 2.29 or later: it passes `--object-format=sha1` from 2.29,
and `--ref-format=files` from 2.45, where Git has the option; an older Git
knows no other ref format, so leaving it out changes nothing. CI runs the test
suite on both sides of that branch and prints the Git version it used
(`.github/workflows/tests.yml`): with the current Git of GitHub's
`ubuntu-latest` runner, and with Debian 12's Git 2.39. SZZBench is developed
with Git 2.50.1. Other versions from 2.29 on take one of the two tested paths
but are not tested themselves.

## 6. The generation manifest (#93)

A generation writes `metadata/manifest.json` **last**: after the commits, the
metadata files and, unless `--no-verify` was given, a verification with no
error. Its presence says the output is complete, and its fields say what the
output was made from:

| field | value |
|---|---|
| `scenario_sha256` | SHA-256 of the scenario file (CRLF read as LF) |
| `generator` | SHA-256 over the source of the modules that decide what a repository contains: `generator`, `graph_generator`, `gitutils`, `operations`, `graph_operations`, `scenario`, `graph_scenario`, `paths` |
| `repository_id` | the first 16 hex digits of a digest over every logical commit and its hash -- equal exactly when two histories are |
| `verified` | whether verification ran and passed |
| `scenario_id`, `format`, `git_version` | for the record |

An output is **stale** when it has no manifest -- an interrupted generation,
or one made before 2026-09-29 -- or when its scenario file or the generator's
code has changed since it was generated; for a run with verification, an
unverified output is stale too. Any edit to the scenario file counts, metadata
included, because the output carries a copy of the scenario and the adapters
read the bug-fixing commits from it. The validation, verification and
reporting modules the generators also import are left out of the fingerprint:
they decide whether a generation is accepted, not what it writes.
`tests/test_generation_manifest.py` checks that every module the generators
import is on one side or the other.

An output is also stale when it has lost part of what its manifest describes,
since the manifest stays behind when the rest is moved, deleted or replaced:

| checked | stale when |
|---|---|
| `repo/.git` | missing, or not a repository |
| the commits | a commit of the commit map is not in the repository (one `git cat-file --batch-check`), or no ref reaches it any more (one `git rev-list --all`: every branch and tag, and `HEAD`; not the reflog). A graph scenario's `graph.ref_lifecycle` may leave commits unreachable on purpose (SZZG-0072, SZZG-0122); only the commits it leaves reachable are asked for |
| `metadata/commit-map.json` | missing, unreadable, or its digest is not the recorded `repository_id` |
| `metadata/scenario.yml` or `metadata/scenario.graph.yml` | missing, or not the scenario file the manifest records |
| `metadata/graph-map.json` (graph scenarios) | missing |

Extra commits, branches and tags do not make an output stale, and neither does
a moved `HEAD`: an SZZ tool may check out, commit or branch in the repository
it analyses, and every commit the output was generated with is still there and
still reachable from a ref. Moving a ref back past one of those commits is
different. After `git reset --hard HEAD~2` the last two commits are dangling,
and after `git commit --amend` the replaced one is: `git log --all` no longer
shows them, so a tool cannot find them, and `git gc` prunes them once their
reflog entries expire. Until issue #167 such an output stayed fresh, and was
scored, until the pruning; now it is stale as soon as no ref reaches one of its
commits ("its repository no longer reaches N of the M commits it was generated
with").

The commit map's other fields (`author`, the dates, `role`) are not part of the
repository id, which digests the history alone, so editing them does not make
an output stale. `szzbench verify` compares the author and the dates with the
commits.

`szzbench verify` asks a stricter question than staleness: whether the
repository is still as the generator left it -- the default branch at the last
commit and checked out, every commit reachable, the index and the working tree
clean, and the commit map's author and dates those of the commits (E604-E609 in
[validation.md](validation.md)). An output an SZZ tool has checked out or
committed in fails `verify` and is still fresh.

- `generate-all-repos` regenerates a stale output instead of skipping it and
  prints why ("Regenerated ... the old output was stale: ..."). An up-to-date
  output is still skipped. Until 2026-09-29 an output counted as done as soon
  as `repo/.git` existed: an edited scenario kept its old repository, and a
  generation that failed half way -- a `repo/.git` with no commits -- was
  reported as Skipped.
- `evaluate`, `baselines` and `coverage` refuse to score a stale output. The
  report gets an error naming the scenario and the reason, and the scenario is
  left out. Scoring the current oracle against an old repository is what went
  wrong: in one checkout, 190 outputs from an older suite were all stale, 11
  of them with a changed oracle, and the stale repository's own correct answer
  FAILed without a warning. `baselines`, `coverage` and
  `evaluate --include-generated` go through every output directory, so an
  output that has lost its repository is reported, not left out.
- Prediction records carry the `repository_id` of the output the tool ran on.
  The adapters in `tools/adapters/` write it, and `evaluate` compares it with
  the generated repository's (`docs/evaluation-policies.md` §1.6). Regenerating
  an unchanged scenario gives the same history and therefore the same id, so a
  regeneration alone does not invalidate earlier predictions.
