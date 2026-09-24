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

A cheap-rule floor for the same suite is in [docs/baselines.md](../../docs/baselines.md): some
declared cheap rule solves 235 of the 281 scenarios, none of them a `discriminating` one. PyDriller
lands below that union and above any single cheap rule, which is the shape the benchmark is built
to show — a real implementation is not a cheap rule, and it is not yet a method that handles the
hard half.

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
policy and its status, after a summary and the warnings the evaluator raised. The warnings are
about scenario metadata the commit-level evaluation does not use (`bug_level`, `work_item_level`,
`entity_level`), not about the predictions.

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
