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
| commit has `author` | used verbatim; it must be `Name <email>` (E014 / GE072) |
| commit has no `author` | one of six pool authors, chosen by a stable hash of `(meta.id, commit index)` |
| commit has `date` | used verbatim for both author and committer date |
| commit has no `date` | the scenario's base date plus irregular weekday gaps (see below) |

A scenario that pins **any** timestamp (`date`, `author_date` or
`committer_date` on any commit) keeps the plain schedule, `base_date + commit
index` days, for the commits it leaves to the generator: spreading only some of
them over the irregular gaps would place them after the pinned ones and invert
the history. A date the scenario writes still has to come after the dates of
the commit's parents, written or scheduled: validation refuses a commit that
would be committed before one of its parents (E016 / GE073, issue #241), and
the classic verify checks the order of the generated commits (E610), as the
graph verify does (GE630). The schedule below therefore applies to scenarios whose timeline is
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

A default applies only where the key is absent. A key that is present must hold
a value generation can record: an `author` that is a number, a list or a blank
value used to be replaced by a pool author without a word, and an `author`
without `<email>` became a name with the benchmark's own address; the
validators now reject both (E014 / GE072), as they reject a blank or unreadable
date (E013 / GE071) (issue #152).

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
whatever date Git makes of it; `validate` / `validate-graph` report it (E013 /
GE071), and so they do a date Git does not record as written: Git 2.39 and 2.50
record an instant from 1970-01-01T00:00:00Z up to 2099-12-31T23:59:59Z, in a
year from 1970 to 2099 where it is written, and refuse the others or record
another date (both read `0001-01-01` as `2001-01-01`) (issue #152).

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

The committer of every commit is its author: both generators give Git the
effective author's name and e-mail as the committer's too, so
`git log --format='%an <%ae> | %cn <%ce>'` shows the same identity twice, and
`commit-map.json` has no separate committer field. `committer_date` is the only
committer field a scenario controls. The `user.name` / `user.email` in the
generated repository's `.git/config` (`SZZ Benchmark
<szz-benchmark@example.com>`) are not the identity of any generated commit;
Git uses them only where it records an identity without a commit, such as the
reflog entry of a checkout (issue #170).

## 2. Operations and placeholders (#18)

### `core.filemode` and `chmod` (*graph*)

Repositories are initialised with `core.filemode=false` for Windows
compatibility. When any commit of a graph scenario contains a `chmod`
operation, the generator switches the repository to `core.filemode=true`
after `git init`, so the mode change is recorded (`100644` -> `100755`) and a
chmod-only commit is no longer empty. No scenario key is needed.

`validate-graph --simulate` keeps the mode Git records (`100755` when the
owner may execute the file, `100644` otherwise) and counts a change of it, so
a chmod-only commit passes it without `allow_empty` too. Until issue #175 it
modelled `chmod` as a no-op and reported such a commit as empty (`GE202`).

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
* The graph operations `format_file`, `move_entity` and `copy_entity` do
  not take the key and keep a convention by the same rule. `format_file`
  writes the file back in its own: a CRLF file stays CRLF, and a missing
  final newline is added as CRLF. `move_entity` / `copy_entity` write the
  destination, header line included, in the source file's convention, or,
  with `append`, in the destination's own, into which the source text is
  re-encoded. The three used to write LF always, so a `format_file` on a
  CRLF file also rewrote every line ending, which the simulator, working on
  LF text, did not see (issue #181).

Any other value is an error in `validate` / `validate-graph` (E042 / GE061),
read as generation reads it (`operations.resolve_line_ending`); `--simulate`
does not read the key, so `line_ending: cr` used to pass it and fail
generation (issue #152).

Limitations: the in-memory simulators (`validate --simulate`,
`validate-graph --simulate`) always work on LF text, so `old`/`anchor`
matching is line-ending agnostic. So is the matching of statements in `bugs`
after generation: the verifiers read a file's content through Git as text
(`gitutils.run_git`), and that reading turns every `\r\n`, and a lone `\r`,
into `\n`, so `\r` never takes part in matching. A statement is matched against
the LF text, whatever the blob holds; one that spans lines, written with `\n`,
is found in a CRLF file as in an LF one (no E301 / GE663). The basic blame
check looks for the statement inside a single line of the BFC's parent, so it
cannot follow a statement that spans lines, whatever the line endings: such a
statement gets W700 / GW701 ("not present in BFC parent"), or I701 / GI701
when the scenario declares a rewrite factor (issue #170). A BOM is not handled
by this key; see `encoding`.

`line_ending` describes the bytes written to the working tree. What Git stores
-- the blob that `git show`, the verifier and SZZ tools read -- is decided when
the file is staged, by the repository's attributes. Without a `.gitattributes`
the blob holds the bytes written (`core.autocrlf` is `false`, section 5). A rule
such as `* text=auto` or `*.txt text eol=crlf` marks the file as text, and Git
converts its CRLF to LF on the way into the index; `eol=crlf` sets what a
checkout writes, not what the blob holds. So with such a rule a
`line_ending: crlf` file is an LF blob while the working tree keeps CRLF. A
scenario may write `.gitattributes` only when it declares the factor
`gitattributes-bic` (E051 / GE063, see *Files Git reads* below), as SZZG-0134
does: its `c1` rewrites `modes.txt` with CRLF, and the blob stays LF,
byte-identical to `c0`'s (issue #164).

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
`utf-8-sig` in any spelling Python accepts, anything else an error (E042).
The classic in-memory simulator applies the codec's read and write behaviour
to the simulated text, which stores a BOM as a leading U+FEFF: `utf-8-sig`
strips one on read and writes one, `utf-8` keeps it as text. A BOM added or
removed by either operation is therefore a change (not `E250`), statements
stay substrings of the decoded text, and the simulator accepts a history
exactly when Git would record it as distinct commits. The graph operations
pass any codec name to Python unchecked and the graph simulator does not model
it; a graph commit that changes only the encoding needs another change or
`allow_empty` to pass `GE202`. `validate-graph` checks that the name is a text
encoding Python knows (GE061): `encoding: bogus` used to pass it and fail
generation (issue #152).

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
* The owner's `parents` (in both files) and `parent_hashes` (graph-map) are
  its **declared** parents, as for every other commit: for `c2` above,
  `parents: [c1]` and `parent_hashes: [<hash of c1>]`. In Git, the owner's
  first parent is its last generated commit, `c2.g500`. The chain is in
  `generated_commits`, and each generated entry's `parents` in commit-map
  names the previous one (`c2.g1`'s names `c1`). To follow Git's history,
  insert the owner's `generated_commits` between the owner and its first
  declared parent, as `gitutils.history_graph` does. Walking `parent_hashes`
  alone gives the scenario's DAG, not Git's.

`verify-graph` checks both ends of the chain. The owner's first parent must
be its last generated commit (GE627). Every generated commit must be in the
commit map and in the repository, and its only parent must be the previous
one; for `g1`, that is the owner's declared first parent. Its author, dates
and subject must also be what the commit map records (GE629, GE633-GE636;
issue #176). Commits whose declared parent owns generated commits still
point at that parent's own hash.

Defaults and compatibility: `path` defaults to `generated`; a file-like
value such as `generated/unrelated-batch-1.txt` (the old placeholder file)
means its parent directory, and a root-level file such as `notes.txt` means
the repository root (files are then named `<generator>-<NN>.txt` without a
directory). `files` defaults to 1. `count` larger than 2000
is capped (a note is written to `generation.log`). `count` must be a
non-negative integer and `files` a positive one (GE062): generation read
`count: 1.5` as 1 and `files: 0` as 1, and `count: many` was found by
`--simulate` and generation only (issue #152).

`validate-graph --simulate` writes the same files with the same content -- the
generator and the simulator take the names and contents from one function,
`graph_operations.commit_generator_changes` -- so a later commit may edit a
generated file. Like generation, it does not report an owner of generated
commits as empty; `count: 0` generates nothing, so an owner without another
change is `GE202`, where generation stops with `commit would be empty`. Until
issue #175 the simulator wrote one placeholder file at `path` instead, and a
commit that edited a generated file failed `--simulate` (`GE201`).

### File names that differ only in letter case (*both*)

Generation writes to a file system, which has directories and, on macOS
(and on Windows, for letter case), takes two names that differ only in
letter case or Unicode normalization for one. `src/a.java` written beside
`src/A.java` overwrote it on macOS and was a second file on Linux, and
`src/A.java/B.java` beside the file `src/A.java` failed with `File exists`
everywhere. Both simulators refuse these writes (`E2XX`, `GE201`; issue
#153): a file below a file or at a directory, and a path that meets a file
or directory of the snapshot in another spelling, compared name by name
(`paths.file_system_key`, the comparison of tag names, GE158). The graph
generator, which `generate-graph` runs without the simulation, refuses an
operation whose path reaches an entry of the worktree spelt otherwise, before
the operation changes anything (every operation with a path, `format_file`
included), and a `commit_generator` file that meets another file of the same
import in another spelling (`generated/` and `Generated/`, `noise-01.txt` and
`Noise-01.txt`), which `git fast-import` would otherwise have written as one
file on macOS.

To rename a file in its letter case, delete it in one commit and write it in
a later one. Within one commit the rename still depends on the platform, and
neither simulator says so: Git on macOS keeps the spelling its index has, so
a `delete_file` of `src/Range.java` followed by a `write_file` of
`src/range.java` commits `src/Range.java` there, and a `rename_file` through
another name commits nothing (`commit would be empty`). A `rename_file` that
changes only the letter case is GE060.

### Files Git reads: `.gitignore`, `.gitattributes`, `.gitmodules` (*both*)

Git reads some files of the working tree itself. Both simulators take a file
an operation writes to be committed as written, but the generators stage with
`git add -A`, which reads the `.gitignore` and `.gitattributes` the scenario
wrote. A file a `.gitignore` matched was in no tree, while `validate
--simulate` and the verification reported nothing; a commit whose only change
was such a file failed with `commit would be empty`; and `* text=auto` stored a
`line_ending: crlf` file as LF (see `line_ending` above). `validate` and
`validate-graph` therefore refuse an operation that writes `.gitignore` or
`.gitmodules`, in any directory, and `.gitattributes` unless `meta.factors`
declares `gitattributes-bic` (E051 / GE063, issue #164). The last name of the
path is compared as file names are above (`paths.file_system_key`), so
`.GITIGNORE`, which Git on macOS reads as `.gitignore` and Git on Linux does
not, is refused too. A graph operation writes the file at its `path`, or at
the `to` / `to_file` of a move or a copy
(`graph_operations.WRITTEN_PATH_FIELDS_BY_OPERATION`).

Behind that check both generators stop a commit when `git add -A` leaves out a
file its operations wrote, and name the file and the rule that ignores it
(`logs/app.log ('*.log' in .gitignore, line 1)`), instead of committing without
it or reporting the commit as empty. The global ignore files are withheld
(section 5), so such a rule can only come from the repository. A file already
in the repository stays in it whatever a later rule says, as in Git. The files
of `commit_generator` are written with `git fast-import`, which reads no ignore
rule, and their names (`<generator>-NN.txt`) are never one of these files.

### Unchanged limitations

* `apply_patch` is still not implemented (validation accepts it; generation
  raises).
* `format_file` only strips trailing whitespace from every line; a CRLF file
  stays CRLF (see `line_ending` above).
* `move_entity` / `copy_entity` remain the whole-file approximation with a
  `// SZZBench move_entity: ...` header (issue #2), written in the line
  endings of the source file, or with `append` of the destination (see
  `line_ending` above).

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
* The source is the first of `rebase_of`, `cherry_pick_of` and `backport_of`
  that is a commit id. A `rebase_of` list (a squash-rebase) is not a source,
  since it names several commits: a commit that sets either option and has no
  source is refused by `validate-graph` (GE074), which says so for a list.
  Generation used to stop at such a commit, and for a list its message said
  that the commit had no `rebase_of` (issue #179).
* `commit-map.json` records `inherits: {source, source_hash, message,
  author_date, subject?}`.

`rebase_of` still does not replay the source commit: the `operations` (or an
`apply_patch_from`) describe the rebased content, exactly as before.

### A commit's `branch` and its first parent (*graph*)

A commit without `branch`, or with a blank `branch:` (YAML null), is on the
default branch, `repository.default_branch` (`main` without the key). An empty
`branch: ""` is an error (GE023), not the default branch: until issue #239 the
validator, the generator and the verifiers read an empty name in three ways,
and `gitutils.commit_branch` is now the one reading. A branch name, and the
default branch of either suite (E015, GE023), is one Git accepts
(`git check-ref-format --branch`, which also refuses `HEAD` and a name that
starts with `-`) and one every platform keeps as written: in Unicode
normalization form C (Git on macOS converts the name it is given to NFC), with
no component that ends with `.lock` in another letter case, and neither `HEAD`
in another letter case nor `@`; with no whitespace character (Git refuses the
space and accepts U+00A0 and the other spaces of Unicode, which SZZBench cannot
read back from Git's list of refs); and with no component longer than a file
name may be: 255 bytes of UTF-8 (Linux), or of UTF-16 code units of the
decomposed name (HFS+), whichever is more, and 250 for the last component,
which Git writes through a lock file `<name>.lock`. The branch names of one scenario, the default
branch included, are compared as macOS compares the files Git stores refs in
(letter case ignored, as for file names above): `Feature` beside `feature`,
or `feature` beside `feature/x`, is an error (GE024), since macOS made one
branch of the first pair and Git refuses the second. The generators check
both rules before `git init`, so a name never reaches `git branch -M` or
`git checkout -B`.

`git init` names the unborn branch after the default branch, and a branch is
born with its first commit. A scenario none of whose commits is on the default
branch therefore generates a repository without it; `validate-graph` warns
(GW022, issue #179).

The generator keeps one branch per `branch` name, and **a branch's tip is the
last commit declared on it**. A commit whose branch does not exist yet creates
the branch at its first parent. A commit whose branch exists and whose first
parent is not the branch's tip **moves the branch**: the generator checks it
out, resets it to the first parent (`git reset --hard`) and commits on top.

```yaml
- id: c4
  branch: main
  parents: [a3]     # main's tip is c0, an ancestor of a3: main fast-forwards to a3
```

* When the old tip is an ancestor of the first parent, the move is a
  fast-forward and nothing is lost. SZZG-0052 and SZZG-0128 integrate a
  feature branch into `main` this way (`c4`), which keeps `main` a straight
  line.
* Otherwise the branch no longer contains its old tip. A commit that no other
  branch, no tag and not `HEAD` reaches once generation has finished (after
  `graph.ref_lifecycle`) is not in `git log --all`, and no tool that walks refs
  sees it, although `commit-map.json` lists it and `verify-graph` finds it by
  its hash. `validate-graph` warns (GW151) and names those commits, unless the
  scenario gives them up on purpose: a commit on a branch that
  `graph.ref_lifecycle.delete_branches` deletes, or one that a commit's
  `rebase_of` or `squashes` names.
* `generation.log` records every reset, with the old and the new tip and
  whether it is a fast-forward:
  `Reset branch main from c1 (<hash>) to f1 (<hash>), the first parent of c2 (fast-forward: no; the branch no longer contains 1 commit(s))`.

To keep the old history, tag it (`graph.ref_lifecycle.tags`) or put the new
commits on a branch of their own: the shipped rebase scenarios write the
rewritten commits on another branch than the originals, and SZZG-0072 and
SZZG-0122 then delete the original branch. Until issue #174 the rule was not
written down, and a reset that left commits unreachable passed validation,
generation and verification without a word.

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
  first. If the default branch is deleted too, or has no commits, HEAD
  detaches at the last commit instead. `verify-graph` expects HEAD there
  (GE644).
* `validate-graph` checks the section before anything is generated
  (GE152-GE158, [validation.md](validation.md); issue #229): it is an object
  with no other keys than `delete_branches` and `tags` (a misspelt key is
  named with the key it stands for); `delete_branches` lists, once each,
  branches some commit is on; `tags` lists `{name, commit}` objects whose
  `commit` is a commit of the scenario or a `<owner>.g<N>` commit its
  `commit_generator` operations plan, and whose `name` is one `git tag`
  accepts, is listed once, and is no branch name of the scenario, deleted or
  kept. A tag named like a branch would make the name ambiguous: Git reads a
  bare `main` as the tag `main`, not the branch. Names are compared ignoring
  letter case and Unicode normalization, as macOS compares the files Git
  stores refs in (Windows ignores letter case), and a component that ends with
  `.lock` in any spelling is refused, since its file would be another tag's
  lock file there. The name rule is that of branch names (above; issue #239),
  `@` aside.
  Until issue #229 only the generator read the section: a value that was not
  an object, or a misspelt key, was ignored, and unknown branch names or
  commit ids were errors at generation only.
* The generator checks the same rules before it creates the first tag, so it
  never stops halfway, with some refs changed and Git's own message.
* `graph-map.json` records the final refs for **every** graph scenario:
  `refs: {branches: {name: hash}, tags: {name: hash}}`, and
  `ref_lifecycle: {deleted_branches: [...], tags: {name: {commit, hash}}}` when
  the section was present. `branches` no longer lists deleted branches.
  `verify-graph` compares the repository's refs with `refs`. A missing or
  moved branch or tag is an error, and so is any ref that generation did not
  leave (GE640-GE643, issue #176).
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
`apply_patch_from` operation of the commit (one line each). A commit with
none of them has nothing to name, and `validate-graph` refuses it (GE075);
generation used to be the first to stop (issue #179). The subject stays
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
the generator writes the `resolution` entries, runs `git add -A` and continues
with the remaining operations and the commit. The keys must be exactly the
conflicted paths. Every conflicted path must be covered by `resolution`;
otherwise, or when the key is absent, generation fails with a message that
lists the conflicted paths. An entry for a path Git did not report as
conflicted fails generation too, with a message that names it and the
conflicted paths: writing it would add a change to the commit that the
scenario does not declare and `resolved_conflicts` does not list. A change to
such a file belongs in `operations`, which run after the resolution. Until
issue #182 the entry was written without a word. Conflicted paths are
read from Git NUL-separated (`--name-only -z`) and compared verbatim with the
`resolution` keys, so non-ASCII names such as `src/main/java/example/範囲.java`
or names containing spaces work. Merges stay merge commits (all parents),
cherry-picks/reverts become ordinary commits and no
`CHERRY_PICK_HEAD`/`REVERT_HEAD` is left behind. `commit-map.json` records
the conflicted paths, which are the keys, as `resolved_conflicts: [paths]`.

A commit with **three or more parents** is generated as a real octopus merge:
all extra parents are passed to a single `git merge --no-ff --no-commit`, because
a second `git merge --no-commit` while `MERGE_HEAD` exists is refused. Git's
octopus strategy merges the extra parents into the first one at a time, in the
order they are listed, and stops at the first conflict:

* a conflict with the **last** parent stays in the index like the conflict of
  a two-parent merge, and `resolution` resolves it: the commit gets all its
  parents, and `resolved_conflicts` lists the paths;
* a conflict with an earlier parent makes Git give up ("Merge with strategy
  octopus failed") and restore the tree, so there is no conflict to resolve,
  and generation fails, whatever `resolution` holds, with a message that says
  so. Listing the conflicting parent last, or merging in two commits, avoids it.

Git 2.39.5 and 2.50.1 behave the same and generate the same hashes.
SZZG-0129 is the in-suite example of a clean octopus, and
`tests/test_merge_resolution.py` generates a resolved one. Until issue #177
this section said that an octopus with a conflict always fails generation.

Git records each merge head once and drops a head that is already merged, so a
commit that lists a parent twice, or an extra parent that is an ancestor of
another of its parents, would get fewer parents than declared. Validation
rejects such a parent list (GE049), and the generator, if it gets one, stops
with a message that names the parent Git dropped, e.g. `merge of c1, c0 for
commit 'm1' recorded no second parent: c0 is already merged` (issue #173).

Limitations: `resolution` is applied only when Git reports a conflict; if the
merge, cherry-pick or revert is clean the entries are ignored. `apply_squash`
and `apply_patch_from` do not use `resolution`. `validate-graph --simulate`
checks a scenario with a `resolution` by generating it with Git in a temporary
directory, like any scenario with a merge, a real cherry-pick or revert, or a
patch operation, so it reports the generation errors above as GE203; until
2026-09-29 it reported the resolved conflict as an error (issue #94).

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
`revert_conflict_resolution` when a commit declares them. A commit's
`parents` and `parent_hashes` are its declared parents, also for a
`commit_generator` owner (see `commit_generator` above).

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
| **every `GIT_*` variable of the caller except `GIT_EXEC_PATH`**: configuration injected through the environment (`GIT_CONFIG_COUNT` with `GIT_CONFIG_KEY_<n>` / `GIT_CONFIG_VALUE_<n>`, `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`), the repository Git works on (everything `git rev-parse --local-env-vars` lists, such as `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`), the format of a new repository (`GIT_DEFAULT_HASH`, `GIT_DEFAULT_REF_FORMAT`), `GIT_TEMPLATE_DIR`, `GIT_NAMESPACE`, diff and pathspec behaviour (`GIT_EXTERNAL_DIFF`, `GIT_DIFF_OPTS`, `GIT_*_PATHSPECS`), and the caller's `GIT_AUTHOR_*` / `GIT_COMMITTER_*` | removed from the environment; the generators set the identity and dates of every commit themselves, the committer's identity being the author's (section 1) |
| the init template (`init.templateDir`, the templates the installation ships) | `git init --template=` copies no hooks |
| a Git whose built-in default object or ref format differs | `git init --object-format=sha1` (Git 2.29 and later) and `--ref-format=files` (2.45 and later) |

Signing (`commit.gpgSign`, `tag.gpgSign`), hooks, global ignores and
attributes, clean/smudge filters, `rerere`, rename and diff settings, and
output settings such as `color.ui` therefore cannot change what a scenario
generates or what SZZBench measures on it. A `.gitignore` or `.gitattributes`
inside the repository would; validation refuses a scenario that writes one,
unless it declares its `.gitattributes` (section 2, *Files Git reads*; issue
#164). What a generated repository needs
is written into its own `.git/config` (`user.name`, `user.email`,
`core.autocrlf=false`, `core.filemode`, `i18n.*`); its `user.name` and
`user.email` are not the identity of any generated commit (section 1, *What is
recorded*).

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

A generation that fails writes no manifest: it writes `generation.log` and
`generation-error.json` instead, and one that fails verification also keeps
`verify-result.json`. Until issue #163 the classic generator wrote neither of
the first two when the verification failed. `generate-all-repos` leaves them
in `<id>/default.tmp`, beside the output (see below).

An output is **stale** when it has no manifest -- an interrupted generation,
or one made before 2026-09-29 --, when its manifest cannot be read or parsed or
holds no JSON object (the reason says so: "its manifest
(metadata/manifest.json) is unreadable: ..."; it used to read as no manifest,
issue #171), or when its scenario file or the generator's code has changed
since it was generated; for a run with verification, an unverified output is
stale too. Any edit to the scenario file counts, metadata
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

`verify-graph` likewise asks whether the repository is still the one generation
left. It reports a missing, moved or extra branch or tag, a moved `HEAD`, and a
dirty index or working tree as errors (issue #176). To verify an output again
after a tool has worked in it, regenerate it (`generate-graph --force`, or
`generate-all-repos --overwrite`).

- `generate-all-repos` regenerates a stale output instead of skipping it and
  prints why ("Regenerated ... the old output was stale: ..."). An up-to-date
  output is still skipped. With verification, an output whose
  `metadata/verify-result.json` is missing or unreadable is regenerated too:
  `generate-all-repos` reports, and `--strict` judges, the verification each
  output recorded (issue #169). Until 2026-09-29 an output counted as done as soon
  as `repo/.git` existed: an edited scenario kept its old repository, and a
  generation that failed half way -- a `repo/.git` with no commits -- was
  reported as Skipped.
- `generate-all-repos` generates each output into `<out-root>/<id>/default.tmp`
  and puts it in place of `<id>/default` only once the generation, and the
  verification unless `--no-verify` was given, has succeeded; `--overwrite`
  replaces an output the same way (issue #168). A failed generation therefore
  leaves no partial output in `<id>/default`: the previous output stays as it
  was, manifest included, and the attempt's own files (`generation.log`,
  `generation-error.json`, and `verify-result.json` after a failed
  verification) stay in `default.tmp`, which the `Failed` line names
  ("Generated repository failed verification; the previous output was left in
  place, and the files of this attempt are in .../SZZ-0005/default.tmp").
  `evaluate`, `baselines` and `coverage` read `*/default` and never see it. The
  next generation of that scenario removes it first; a run that skips the
  scenario leaves it.

  The replacement itself removes nothing until the new output is in place. The
  previous output is renamed to `<id>/default.old`, `default.tmp` is renamed
  to `default`, and only then is `default.old` removed. When either rename
  fails, the scenario fails and the previous output is in `default` again
  (renamed back after a failure of the second rename); should renaming it back
  fail too, the error says where it is, and the next run moves it back. When
  `default.old` cannot be removed, the new output stays in place and counts
  as generated; the item's `leftover` (in `--json`) names `default.old` and
  why, and the next run that visits the scenario removes it. Until it is
  gone, a replacement of that output fails at the first rename and leaves the
  output in place.

  `default`, `default.tmp` and `default.old` are replaced or removed only
  when they hold a generated output or nothing but `repo/` and `metadata/`,
  the rule `generate --force` follows (issue #165). The first line of
  `generation.log` names the repository where it was initialized, in
  `default.tmp`. Until issue #168 the old output was removed before the
  regeneration began, so a regeneration that failed left a partial output,
  without its manifest, where a complete one had been. `generate --force` and
  `generate-graph --force` still remove the old output first.
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
