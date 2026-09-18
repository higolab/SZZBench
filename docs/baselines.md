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

215 generated scenarios, measured on this branch (2026-09-18):

| baseline | family | solves |
|---|---|---|
| `position-1` | position | **146/215 = 67.9%** |
| `blame-deleted-lines` | blame | 141/215 = 65.6% |
| `shape-last-toucher` | shape | 107/215 = 49.8% |
| `position-before-fix` | position | 95/215 = 44.2% |
| `position-2` | position | 18/215 = 8.4% |
| `position-3` | position | 17/215 = 7.9% |
| `position-0`, `position-4` | position | 7/215 = 3.3% each |
| `position-all-non-fix` | position | 6/215 = 2.8% |
| best `author:…` | metadata | 11/215 = 5.1% (chance) |
| `message-admits-fault` | metadata | **0/215** |

**A fixed rule versus the union.** Each row is one rule applied to every
scenario, which is what an attacker can actually do. The union of the rows is
*not* an attacker's score: choosing which rule to use per scenario needs the
oracle. The union is reported below as an upper bound on how much of the suite
a cheap rule could explain — headroom, not a result.

Read this table before reading any result reported on SZZBench:

- **A rule that opens no file beats the classic B-SZZ baseline.** "Report the
  second commit of the history" solves 67.9% against B-SZZ's 65.6%, because
  most scenarios are four commits long with a single-commit oracle in second
  position.
- **Upper bound (oracle-aware): 203 of 215 scenarios are solved by *some*
  cheap rule.** Twelve resist all of them — SZZ-0132, SZZ-0136, SZZ-0190 to
  SZZ-0194, SZZG-0028, SZZG-0038, SZZG-0040, SZZG-0069, SZZG-0076 — and every
  one of them has a **multi-commit oracle**. Split by oracle size:

  | | best fixed rule | union over all rules |
  |---|---|---|
  | 194 scenarios with a one-commit oracle | 145/194 = 74.7% | **194/194** |
  | 21 scenarios with a two-commit oracle | 1/21 | 9/21 |

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

## The two tiers

Every scenario declares `meta.tier`, which says what it is for:

| tier | meaning | count |
|---|---|---|
| `control` | checks that a method handles a specific input condition; a cheap rule may well solve it | **203** |
| `discriminating` | designed so that none of the declared cheap baselines solves it | **12** |

Every one of the twelve has a multi-commit oracle. Seven are pre-existing
scenarios that turned out to resist the baselines; SZZ-0190 to SZZ-0194 were
**designed** against the measured axis, each on the same skeleton — the answer
is two commits, one of which the fix's deleted lines do not blame to — with a
different reason for the unreachability:

| scenario | why the second commit is out of blame's reach |
|---|---|
| SZZ-0190 | it changed the *unit* of a constant the fixed expression reads |
| SZZ-0191 | it changed the *callee* the fixed line calls |
| SZZ-0192 | an equivalence-preserving rewrite owns the line, so blame returns the rewrite instead |
| SZZ-0193 | it removed a guard, a *precondition* the later commit made reachable |
| SZZ-0194 | it is in a *file the fix never opens* |

A control being cheaply solvable is not a defect: a benchmark needs cases that
verify the basics, and a method that fails one of them is broken on that input
condition. What the tier does is stop a control from being read as evidence
that a method *discriminates*.

`szzbench baselines` checks the declaration against the measurement and reports
any scenario declared `discriminating` that a cheap rule solves, and any
`control` that no cheap rule solves — the latter is a promotion candidate. The
vocabulary is in [decisions/vocabulary.md](decisions/vocabulary.md) and
`validate --lint` enforces it (`W460` / `GW460`).

The two checks need different evidence, so `--family` affects them differently.
Finding *a* solver refutes a `discriminating` declaration whichever families
ran, so that check stays valid in a filtered run. A promotion candidate asserts
that **no** declared baseline solves the scenario, which only a complete run can
establish: a filtered run reports `declared_control_but_unsolved: null` and says
the assessment was not made, and its "solved by no selected baseline" count is
scoped to the families that ran.

Raising the discriminating count is the work tracked in issues #13, #14 and
#35; the measured axis is oracle size.

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
tier                   control:203, discriminating:12
oracle_size            1:194, 2:21
bic_depth              1:94, 2:97, 3:20, 4:1, 5:1, 6:1, 1003:1
fault_file_distractors 0:9, 1:99, 2:77, 3:23, 4:6, 5:1
commit_count           2:4, 3:55, 4:98, 5:43, 6:11, 7:2, 8:1, 1005:1
ref_count              1:176, 2:36, 3:3

83 distinct signatures; 40 groups of two or more, covering 172 scenarios
```

The largest groups are 27 S3, 10 S4, 9 S2, 8 S1 and 8 G1 scenarios that agree
on every dimension; 43 scenarios have a signature of their own. Read together with the baseline table, the suite concentrates
in one cell — a one-commit answer, one or two commits before the fix, in a
three- or four-commit single-branch history — and **that cell is where the
cheap rules win**.

## Adding a baseline

Add a predictor to `src/szzbench/baselines.py` and register it in
`build_predictors` with the family whose inputs it stays within. A predictor
returns logical commit ids; the runner turns them into `Prediction` records and
hands them to `evaluate_prediction_map`, so nothing in a baseline decides what
counts as a correct answer.
