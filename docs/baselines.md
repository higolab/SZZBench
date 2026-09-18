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

**A fixed rule versus the union.** Each row is one rule applied to every
scenario, which is what an attacker can actually do. The union of the rows is
*not* an attacker's score: choosing which rule to use per scenario needs the
oracle. The union is reported below as an upper bound on how much of the suite
a cheap rule could explain — headroom, not a result.

Read this table before reading any result reported on SZZBench:

- **A rule that opens no file beats the classic B-SZZ baseline.** "Report the
  second commit of the history" solves 69.5% against B-SZZ's 67.1%, because
  most scenarios are four commits long with a single-commit oracle in second
  position.
- **Upper bound (oracle-aware): 203 of 210 scenarios are solved by *some*
  cheap rule.** Seven resist all of them: SZZ-0132, SZZ-0136, SZZG-0028,
  SZZG-0038, SZZG-0040, SZZG-0069, SZZG-0076 — and every one of them has a
  **multi-commit oracle**. Split by oracle size, the contrast is sharper still:

  | | best fixed rule | union over all rules |
  |---|---|---|
  | 194 scenarios with a one-commit oracle | 145/194 = 74.7% | **194/194** |
  | 16 scenarios with a two-commit oracle | 1/16 | 9/16 |

  A one-commit answer inside a three- or four-commit history is reachable by
  *some* cheap rule in every single case, at every depth — 94/94 at depth 1,
  82/82 at depth 2, 14/14 at depth 3 and 4/4 beyond. Oracle size is the
  dimension that separates them, and a longer or deeper history on its own
  will not raise the floor.
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

## Coverage: what each scenario contributes

`szzbench coverage` measures every scenario along the dimensions that decide
how hard its bug-introducing commit is to find, and groups the scenarios that
agree on all of them. A large group is redundancy; an empty combination is a
gap. It replaces the 2026-09-17 review's merge/delete list (issue #12), whose
50 candidates have all been rebuilt since and no longer describe the suite.

```bash
szzbench coverage --out studies/coverage
```

| dimension | meaning |
|---|---|
| `oracle_size` | how many commits the answer contains |
| `bic_depth` | commits between the deepest required BIC and the fix |
| `fault_file_distractors` | commits before the fix that touch a file the fault lives in and are **not** the answer |

`oracle_size` and `bic_depth` come from the evaluator's own policy resolution
(`_commit_level_policy`), so a default evaluation variant and an inferred
direct BIC are read the same way a scored run reads them. `bic_depth` measures
the **farthest** required BIC — the deepest commit a tool has to reach.
| `commit_count`, `ref_count` | size and branchiness of the history |

Measured on the shipped suite (210 scenarios):

```text
oracle_size            1:194, 2:16
bic_depth              1:94, 2:97, 3:15, 4:1, 5:1, 6:1, 1003:1
fault_file_distractors 0:9, 1:99, 2:73, 3:22, 4:6, 5:1
commit_count           2:4, 3:55, 4:98, 5:39, 6:10, 7:2, 8:1, 1005:1
ref_count              1:171, 2:36, 3:3

81 distinct signatures; 39 groups of two or more, covering 168 scenarios
```

The largest groups are 27 S3, 10 S4, 9 S2, 8 S1 and 8 G1 scenarios that agree
on every dimension; 42 scenarios have a signature of their own. Read together with the baseline table, the suite concentrates
in one cell — a one-commit answer, one or two commits before the fix, in a
three- or four-commit single-branch history — and **that cell is where the
cheap rules win**.

## Adding a baseline

Add a predictor to `src/szzbench/baselines.py` and register it in
`build_predictors` with the family whose inputs it stays within. A predictor
returns logical commit ids; the runner turns them into `Prediction` records and
hands them to `evaluate_prediction_map`, so nothing in a baseline decides what
counts as a correct answer.
