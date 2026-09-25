# A complete run: PyDriller over the shipped suite

This directory holds one run of a third-party SZZ implementation over every scenario SZZBench
ships, with the commands that produced it, the predictions it made and the report SZZBench wrote.
It exists so that a reader can see what a real run looks like before setting one up, and so that an
installation can be checked against numbers someone else measured.

- **Tool**: [PyDriller](https://github.com/ishepard/pydriller) 2.12, through
  `tools/adapters/pydriller_to_predictions.py`
- **Suite**: 281 scenarios (135 classic, 146 graph)
- **Measured**: 2026-09-25, Python 3.14, git 2.x, macOS

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

The adapter took 14 seconds over the 281 repositories, `generate-all-repos` about three minutes.
`predictions.jsonl` here is that output with the per-scenario `raw_file` paths removed, and
`evaluation-results.md` is the report the last command wrote.

## What it scores

| | |
|---|---|
| scenarios | 281 |
| PASS / FAIL | **162 / 119** |
| true positives | 236 |
| false positives | 67 (53 of them *hard*) |
| false negatives | 107 |
| precision / recall | **0.779 / 0.688** |

Split by `meta.tier`, which is what the tier is for:

| tier | PASS | share |
|---|---|---|
| `control` | 161 / 235 | 68.5 % |
| `discriminating` | **1 / 46** | **2.2 %** |

## How that compares with the cheap rules

A cheap-rule floor for the same suite is in [docs/baselines.md](../../docs/baselines.md): some
declared cheap rule solves 235 of the 281 scenarios, none of them a `discriminating` one. PyDriller
lands below that union — but not above the individual rules, and the detail is worth more than the
headline:

| | passes | shared with PyDriller | only PyDriller | only the rule |
|---|---|---|---|---|
| PyDriller 2.12 | 162 | — | — | — |
| `position-1` (opens no file) | 162 | 98 | 64 | 64 |
| `blame-deleted-lines` | 157 | 155 | 7 | 2 |
| `shape-last-toucher` | 121 | 107 | 55 | 14 |

**PyDriller ties `position-1` exactly on count and shares only 98 scenarios with it.** "Report the
second commit of the history" and a real blame-based implementation are level on the scoreboard
while solving different halves of the suite, which is the reason this document reports sets and not
only totals.

Against `blame-deleted-lines` the overlap is 155 of 162, because
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
policy and its status, after a summary and the eight warnings the evaluator raised. None of them is
about the predictions, and they are not all the same kind:

- **Four are about metadata this evaluation does not read.** SZZG-0034 declares `bug_level`,
  SZZG-0097 `work_item_level`, SZZG-0116 `entity_level` and `line_level`, SZZG-0133 `line_level`.
  Commit-level scoring ignores those sections; nothing about the scenario changes.
- **Three say the required set was inferred, not read.** SZZG-0115, SZZG-0116 and SZZG-0140 have an
  empty or missing `expected_szz.commit_level.required`, so the evaluator derived it from
  `bugs[].bug_introducing_commits`, taking the commits whose role is `contributing`, `direct` or
  `reintroducing` — `c1` in each of the three. Those scenarios were scored against a set the
  evaluator computed, which is worth knowing before quoting their results.
- **One is a variant fallback.** SZZG-0136 declares `default_variant: default`, but its only
  declared variant is `boundary-commit`, so the name resolves to nothing and the evaluator falls
  back to `expected_szz.commit_level` — which is `expect_no_bic: true`. The scenario is scored
  correctly against its own oracle; the declaration names a variant that does not exist, which is a
  metadata defect in the scenario rather than a property of this run.

`--include-generated` is what makes the denominator 281: PyDriller produced predictions for 262
scenarios, and the flag tells SZZBench to score the remaining 19 as empty predictions rather than
skip them. Without it a tool would silently be graded only on the scenarios it answered.

The same flag makes one mistake look like a result: if `--predictions` names a file that is not
there, every scenario is scored with no predictions and the summary reads `PASS: 2` — the two
scenarios whose oracle is empty — with recall 0.000. SZZBench does say so, on stderr
(`[ERROR] Cannot read predictions file`) and with a non-zero exit status, but the summary is
printed first. A recall of exactly zero is worth checking the path over.

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
