# Baselines: what SZZBench does not test

A result on a benchmark only means something against a floor. `szzbench baselines`
runs a declared family of cheap predictors over the generated repositories and
scores them with the ordinary evaluator, so their numbers come from exactly the
policies a real tool run is scored with.

```bash
szzbench generate-all-repos
szzbench baselines
szzbench baselines --family position --family blame --out studies/baselines
```

## The families

Ordered by how much of the repository each one reads.

| family | reads | expectation |
|---|---|---|
| `metadata` | author, date, commit message | **must stay at chance.** A metadata predictor that recovers the oracle means the oracle leaked — see [decisions/oracle-leakage.md](decisions/oracle-leakage.md) |
| `position` | the shape of the history: a commit's index, its distance from the fix. No file is opened | a legitimate signal, and the floor a real method must beat |
| `shape` | which files the commits touch, without interpreting them | as above |
| `blame` | `git blame` on the lines the fix deletes — the classic SZZ baseline | the reference point |

## What a predictor sees

A predictor is handed the **materialized Git history**, not the scenario file:
the commits of `git rev-list --all --topo-order --reverse`, each with the
author and subject Git records. That order is deterministic and puts a parent
before its children, and it includes the commits `commit_generator` expands,
which never appear in a scenario's `commits:` list — SZZG-0114 has five of
those entries and 1005 real commits. Messages likewise come from Git, so a
rebased commit that inherits its source's subject is read with that subject.

A predictor names a commit by its **hash**; mapping a hash back to a logical id
is the evaluator's job, which is also what a real tool run does.

The `metadata` family enumerates one rule per author in the suite and reports
each separately. An attacker picks **one** rule and applies it everywhere;
choosing the matching author per scenario would need the oracle, and with most
oracles being a single commit it succeeds by coincidence rather than by signal.

## Measured on the shipped suite

210 generated scenarios, measured on this branch (2026-09-18):

| baseline | family | solves |
|---|---|---|
| `position-second` | position | **146/210 = 69.5%** |
| `blame-deleted-lines` | blame | 141/210 = 67.1% |
| `shape-last-toucher` | shape | 107/210 = 51.0% |
| `position-before-fix` | position | 95/210 = 45.2% |
| `position-third` | position | 18/210 = 8.6% |
| `position-first` | position | 7/210 = 3.3% |
| `position-all-non-fix` | position | 6/210 = 2.9% |
| best `author:…` | metadata | 11/210 = 5.2% (chance) |
| `message-admits-fault` | metadata | **0/210** |

Read this table before reading any result reported on SZZBench:

- **A rule that opens no file beats the classic B-SZZ baseline.** "Report the
  second commit of the history" solves 69.5% against B-SZZ's 67.1%, because
  most scenarios are four commits long with a single-commit oracle in second
  position.
- **203 of 210 scenarios are solved by at least one baseline.** Seven resist all
  of them: SZZ-0132, SZZ-0136, SZZG-0028, SZZG-0038, SZZG-0040, SZZG-0069,
  SZZG-0076 — and every one of them has a **multi-commit oracle**.
- **Thirteen of the seventeen categories are 100% solvable** by a cheap
  baseline (S1, S2, S3, S4, S5, S7, S8, G1, G4, G6, G7, G8, G9); only G2
  (93.3%), G3 (84.6%), G5 (88.2%) and S6 (80.0%) have any headroom at all.
- The metadata family is at chance, which is the leakage guarantee holding: the
  best author rule (5.2%) sits *below* the mean of a label-shuffled null, and
  the message rule scores zero.

This is a property of how the scenarios are **shaped**, not of what they
disclose, and it is tracked in [#13](https://github.com/YoshikiHigo/SZZBench/issues/13),
[#14](https://github.com/YoshikiHigo/SZZBench/issues/14) and
[#35](https://github.com/YoshikiHigo/SZZBench/issues/35). The design lever the
data points at is **oracle size and the depth of the bug-introducing commit**,
not more scenarios of the current shape.

## Output

`--json` and `--out DIR` (which writes `baselines.json` and `baselines.md`)
report, per baseline, the scenarios it solved, plus the union across families,
the scenarios nothing solves, and a per-category breakdown. The exit code is
non-zero only when a scenario or commit map could not be read.

## Adding a baseline

Add a predictor to `src/szzbench/baselines.py` and register it in
`build_predictors` with the family whose inputs it stays within. A predictor
returns logical commit ids; the runner turns them into `Prediction` records and
hands them to `evaluate_prediction_map`, so nothing in a baseline decides what
counts as a correct answer.
