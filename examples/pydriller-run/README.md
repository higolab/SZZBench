# A complete run: PyDriller over the shipped suite

This directory holds one run of a third-party SZZ implementation over every scenario SZZBench
ships, with the commands that produced it, the predictions it made and the report SZZBench wrote.
It exists so that a reader can see what a real run looks like before setting one up, and so that an
installation can be checked against numbers someone else measured.

- **Tool**: [PyDriller](https://github.com/ishepard/pydriller) 2.12, through
  `tools/adapters/pydriller_to_predictions.py`
- **Suite**: 279 scenarios (133 classic, 146 graph)
- **Measured**: 2026-09-28, Python 3.14, git 2.x, macOS; re-run 2026-09-29 with the adapter that writes a
  record for every scenario (issue #95) -- the same 311 predictions, and 19 more records, all empty --
  and again with every record carrying the `repository_id` of the output it was made on (issue #93)

## The commands

```bash
python -m pip install pydriller
szzbench generate-all-repos

tools/adapters/pydriller_to_predictions.py \
    --generated-root generated-input-repos \
    --out predictions.jsonl

szzbench evaluate \
    --predictions predictions.jsonl \
    --generated-root generated-input-repos \
    --include-generated \
    --out results/pydriller
```

The adapter took about fifteen seconds over the 279 repositories, `generate-all-repos` about three
minutes.
`predictions.jsonl` here is that output with the `raw_file` path and the repeated `scenario_id` removed
from every prediction, and
`evaluation-results.md` is the report the last command wrote.

## What it scores

| | |
|---|---|
| scenarios | 279 |
| PASS / FAIL | **161 / 118** |
| true positives | 235 |
| false positives | 66 (52 of them *hard*) |
| false negatives | 106 |
| precision / recall | **0.781 / 0.689** |

Split by `meta.tier`, which is what the tier is for:

| tier | PASS | share |
|---|---|---|
| `control` | 160 / 233 | 68.7 % |
| `discriminating` | **1 / 46** | **2.2 %** |

## How that compares with the naive rules

A naive-rule floor for the same suite is in [docs/baselines.md](../../docs/baselines.md): some
declared naive rule solves 233 of the 279 scenarios, none of them a `discriminating` one. PyDriller
lands below that union, and one scenario above the best individual rule — a margin worth less than
the detail under it:

| | passes | shared with PyDriller | only PyDriller | only the rule |
|---|---|---|---|---|
| PyDriller 2.12 | 161 | — | — | — |
| `position-1` (opens no file) | 160 | 97 | 64 | 63 |
| `blame-deleted-lines` | 156 | 154 | 7 | 2 |
| `shape-last-toucher` | 120 | 106 | 55 | 14 |

**PyDriller beats `position-1` by one scenario and shares only 97 with it.** "Report the second
commit of the history" and a real blame-based implementation are within a point of each other on
the scoreboard while solving different halves of the suite, which is the reason this document
reports sets and not only totals. (Until 2026-09-28 the two were exactly level at 162 each; the
retirement of SZZ-0082 and SZZ-0120 in issue #90 removed one scenario from each side of that tie
and one more from `position-1`.)

Against `blame-deleted-lines` the overlap is 154 of 161, because
`Git.get_commits_last_modified_lines` **is** the same step as that baseline. It differs in three
ways, and each difference is visible in the scenarios where the two disagree:

1. it blames with `git blame -w` rather than plain blame — six gains and one loss;
2. for a renamed or deleted file it blames the *old* path — one gain;
3. it reports no modified files for a merge commit, where the baseline diffs the merge against its
   first parent — one loss.

The seven it adds:

- six are whitespace, formatting or line-ending noise, where `-w` carries the blame across a commit
  that plain blame stops at — SZZ-0083 (whitespace-only rewrite), SZZ-0100 (a try block that
  re-indents its body), SZZ-0108 (CRLF-like full-file rewrite), SZZ-0185 (comment and blank-line
  deletion), SZZ-0212 (a whitespace-only reformat between two faults) and SZZG-0081 (formatting
  rewrite after a rebase);
- the seventh, **SZZG-0002**, is a *file move*: the fix renames the file and repairs it in the same
  commit, so blaming the path the fix touched finds nothing at `BFC^`, while PyDriller blames
  `old_path` and lands on the required commit.

It loses two that plain blame solves — one to the first difference, one to the third:

- **SZZ-0028**: the same `-w` that wins the six above. The fix deletes lines 5–8 at `BFC^`, and
  both tools blame all four. Plain blame assigns every one of them to `c1`; with `-w`, line 8
  (`return value >= 0;`) goes to `c0`, because `c1` only re-indented it. PyDriller therefore answers
  `{c0, c1}` and `exact_set` fails it on the false positive. Ignoring whitespace is not free.
- **SZZG-0046**: it predicts **nothing at all**. That scenario's bug-fixing commit is a *merge*;
  PyDriller reports no modified files for a merge (measured: `merge=True`, `modified_files=0`,
  `get_commits_last_modified_lines` returns `{}`), so there are no deleted lines to blame, while the
  baseline diffs the merge against its first parent and finds them. A tool that never answers on a
  merge BFC is a failure mode this suite is built to surface.

## The one discriminating scenario it passes

`SZZ-0212`, and for a reason worth knowing: PyDriller blames with `git blame -w` (see
`Git._get_blame` in PyDriller 2.12), and SZZ-0212 puts a **whitespace-only re-indentation** between
its two faults. Plain blame stops at the re-indentation — which is why SZZBench's own
`blame-deleted-lines` baseline, which does not pass `-w`, fails it — and a whitespace-insensitive
blame crosses it and reaches both required commits.

The same suite therefore separates two configurations of the same idea. That is the use the
`discriminating` tier is for: 45 of the other 46 scenarios in it need something this
implementation does not do, and the README of each says what.

## Reading the report

`evaluation-results.md` lists every scenario with its expected and actual BICs, its evaluation
policy and its status, after a summary and four notes under `## Information`. The run raises no
warning. The four notes are about metadata this evaluation does not read: SZZG-0034 declares
`bug_level`, SZZG-0097 `work_item_level`, SZZG-0116 `entity_level` and `line_level`, SZZG-0133
`line_level`. Commit-level scoring ignores those sections. Nothing in those scenarios is wrong, so
the notes are information rather than warnings, but each scenario's result still carries its note.

Until 2026-10-07 the four were warnings (issue #126). Until 2026-10-06 there were three more
warnings. SZZG-0115, SZZG-0116 and SZZG-0140 left
`expected_szz.commit_level.required` empty or missing, so the evaluator derived it from
`bugs[].bug_introducing_commits` — `c1` in each of the three — and said so at every evaluation. They
now declare `required: [c1]`, which changes no verdict, and `validate-graph` warns about an oracle
the evaluator would have to infer (GW130). Until 2026-09-29 there was one more still. SZZG-0136
declared `default_variant: default`, a variant it does not have, so the evaluator fell back to
`expected_szz.commit_level` — the scenario's intended default — and said so at every evaluation. The
scenario no longer declares it, and the graph validator now rejects a `default_variant` that names
no variant (GE129).

PyDriller named at least one commit for 260 scenarios and none for the other 19. The adapter writes
a record for all 279, the 19 with an empty prediction list: that is PyDriller's answer "no commit",
scored like any other answer. `--include-generated` keeps the denominator at 279 even when a record
is missing: a scenario that no record names **fails** as a missing record (`run_status: missing`),
so a tool can neither be graded only on the scenarios it answered nor pass an empty oracle by never
reaching it. A scenario on which the tool raised is written as `status: error` and fails the same
way (`run_status: error`); the summary counts both, and this run has neither.

So a wrong `--predictions` path no longer looks like a result: every scenario fails as a missing
record, the summary reads `PASS: 0` and `Missing records: 279`, and SZZBench reports
`[ERROR] Cannot read predictions file` with a non-zero exit status. Until 2026-09-29 a missing record
counted as an empty prediction, and the same mistake read `PASS: 2` -- the two scenarios whose
oracle is empty.

## Reproducing it

The generator is deterministic — the same scenario file produces the same commit hashes — so the
hashes in `predictions.jsonl` match a fresh `generate-all-repos` on the same scenarios, and the
last command above re-scores this file without PyDriller being installed at all. That is the
cheapest check that an installation behaves: run it and compare with the table above.

Re-running the adapter reproduces the predictions themselves. A scenario edited after this run
would change its hashes, and then its record here no longer matches; the suite size and date at the
top of this file say what this run was measured on.

## What this is not

PyDriller is not a full SZZ implementation. `Git.get_commits_last_modified_lines`, which the adapter
calls, is the first step of line-based SZZ — blame the lines a fix deleted — without the filtering
that B-SZZ and its successors add. Read the numbers as "what the blame step alone achieves here",
and see [docs/baselines.md](../../docs/baselines.md) for how that compares with rules that do no
analysis at all.
