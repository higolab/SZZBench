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

## Saying nothing

A rule is credited **only on the scenarios it names a commit for**. A scenario
it is silent about counts as unsolved by it, even when silence would score:
under `expect_no_bic` the correct answer *is* the empty set, so a rule that
never reaches that history — `position-5` on a four-commit one — would
otherwise pass it for free, and so would every other silent rule.

Predicting nothing is a strategy, so it is published as one: `abstain` is the
single rule scored on its silence. It is the honest version of that free pass —
one rule with one number, rather than an invisible bonus spread across the
family. It scores **0/225** on the shipped suite, because no scenario's default
evaluation has an empty oracle.

## Measured on the shipped suite

225 generated scenarios, measured on this branch (2026-09-18):

| baseline | family | solves |
|---|---|---|
| `position-1` | position | **146/225 = 64.9%** |
| `blame-deleted-lines` | blame | 141/225 = 62.7% |
| `shape-last-toucher` | shape | 107/225 = 47.6% |
| `position-before-fix` | position | 95/225 = 42.2% |
| `position-2` | position | 18/225 = 8.0% |
| `position-3` | position | 17/225 = 7.6% |
| `position-0`, `position-4` | position | 7/225 = 3.1% each |
| `position-all-non-fix` | position | 6/225 = 2.7% |
| `position-5` | position | 1/225 = 0.4% |
| best `author:…` | metadata | 11/225 = 4.9% (chance) |
| `abstain` | position | **0/225** |
| `message-admits-fault` | metadata | **0/225** |

**A fixed rule versus the union.** Each row is one rule applied to every
scenario, which is what an attacker can actually do. The union of the rows is
*not* an attacker's score: choosing which rule to use per scenario needs the
oracle. The union is reported below as an upper bound on how much of the suite
a cheap rule could explain — headroom, not a result.

Read this table before reading any result reported on SZZBench:

- **A rule that opens no file beats the classic B-SZZ baseline.** "Report the
  second commit of the history" solves 64.9% against B-SZZ's 62.7%, because
  most scenarios are four commits long with a single-commit oracle in second
  position.
- **Upper bound (oracle-aware): 203 of 225 scenarios are solved by *some*
  cheap rule.** Twenty-two resist all of them — SZZ-0132, SZZ-0136, SZZ-0190 to
  SZZ-0199, SZZG-0028, SZZG-0038, SZZG-0040, SZZG-0069, SZZG-0076 and
  SZZG-0117 to SZZG-0121 — and every one of them has a **multi-commit oracle**.
  Split by oracle size:

  | | best fixed rule | union over all rules |
  |---|---|---|
  | 194 scenarios with a one-commit oracle | 145/194 = 74.7% (`position-1`) | **194/194** |
  | 31 scenarios with a two-commit oracle | 9/31 = 29.0% (`blame-deleted-lines`) | 9/31 |

  A one-commit answer inside a three- or four-commit history is reachable by
  *some* cheap rule in every single case, at every depth — 94/94 at depth 1,
  82/82 at depth 2, 14/14 at depth 3 and 4/4 beyond. Oracle size is the
  dimension that separates them, and a longer or deeper history on its own
  will not raise the floor.

  The nine two-commit oracles a cheap rule does solve are all solved by the
  *same* rule, `blame-deleted-lines`, and for the same reason: their fix
  deletes one line from each of the two commits, so naive blame returns both.
  That is the shape the discriminating tier is built to avoid.

  (An earlier revision of this table reported `1/21` as the best fixed rule on
  two-commit oracles. That figure was wrong: recomputed on the same 215-scenario
  measurement, it is `9/21`, by `blame-deleted-lines`. The union was right.)
- **Ten of the seventeen categories are 100% solvable** by a cheap baseline
  (S1, S2, S3, S4, S5, S7, G6, G7, G8, G9); the rest have headroom — S6 42.1%,
  G3 78.6%, S8 80.0%, G2 87.5%, G5 88.2%, G4 91.3%, G1 92.9%.
- The metadata family is at chance, which is the leakage guarantee holding: the
  best author rule (4.9%) sits *below* the mean of a label-shuffled null, and
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
| `discriminating` | designed so that none of the declared cheap baselines solves it | **22** |

Every one of the twenty-two has a multi-commit oracle. Seven are pre-existing
scenarios that turned out to resist the baselines; the other fifteen were
**designed** against the measured axis, on one skeleton — the answer is two
commits, one of which the fix's deleted lines do not blame to. There are five
reasons that half can be out of reach, and three scenarios for each:

| why the second commit is out of blame's reach | | | |
|---|---|---|---|
| **value** — it changed what a value *means* | SZZ-0190 a constant's unit | SZZ-0195 a stored field's scale | SZZG-0117 a unit change behind a merge |
| **callee** — it changed what the fixed line *calls* | SZZ-0191 the callee's accepted input | SZZ-0196 which overload is selected | SZZG-0118 a reduced copy of the callee |
| **rewrite** — a behaviour-preserving commit owns the line | SZZ-0192 extract variable | SZZ-0197 extract method | SZZG-0119 move and inline |
| **guard** — it changed a precondition a later commit reaches | SZZ-0193 the guard is deleted | SZZ-0198 the guard substitutes a different value | SZZG-0120 guard and caller on different branches |
| **file** — it is somewhere the fix never opens | SZZ-0194 another Java file | SZZ-0199 a properties file | SZZG-0121 another file, reached by cherry-pick |

The classic instances isolate the code-level reason; the graph instances add a
history-level one on top, so that the same reason has to be found across a
merge, a copy, a move, two branches or a cherry-pick. Each README reports the
blame result for every deleted line under three variants, the probe answers
that move at each commit, and a counterfactual: reverting the unreachable
commit on top of the faulty one reproduces the fixed behaviour.

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

The check earns its keep. `SZZG-0118` was first declared `discriminating` and
the measurement refused it: the generator's author rotation had given its two
bug-introducing commits the same author and no other commit that author, so
"report every commit by Elena Rossi" returned exactly the oracle. The scenario
now names five distinct authors. A coincidence is not a signal, but a benchmark
cannot tell the difference — only the measurement can.

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
| `commit_count`, `ref_count` | size and branchiness of the history |

`oracle_size` and `bic_depth` come from the evaluator's own policy resolution
(`_commit_level_policy`), so a default evaluation variant and an inferred
direct BIC are read the same way a scored run reads them. `bic_depth` measures
the **farthest** required BIC — the deepest commit a tool has to reach.

Measured on the shipped suite (225 scenarios):

```text
tier                   control:203, discriminating:22
oracle_size            1:194, 2:31
bic_depth              1:94, 2:98, 3:27, 4:2, 5:2, 6:1, 1003:1
fault_file_distractors 0:11, 1:100, 2:82, 3:24, 4:7, 5:1
commit_count           2:4, 3:55, 4:98, 5:50, 6:13, 7:3, 8:1, 1005:1
ref_count              1:183, 2:39, 3:3

92 distinct signatures; 41 groups of two or more, covering 174 scenarios
```

The largest groups are 27 S3, 10 S4, 9 S2, 8 S1 and 8 G1 scenarios that agree
on every dimension; 51 scenarios have a signature of their own. Read together
with the baseline table, the suite still concentrates in one cell — a
one-commit answer, one or two commits before the fix, in a three- or
four-commit single-branch history — and **that cell is where the cheap rules
win**.

The discriminating tier is deliberately spread out of it: its 22 scenarios
occupy **16** distinct signatures, where the first twelve occupied 8. The ten
added in this round introduced eight signatures the suite did not have,
including the first two-commit oracles with no distracting commit on the fault
file at all (SZZ-0198, SZZ-0199) and the first seven-commit history with a
two-commit oracle (SZZ-0197). Two pairs still share a signature —
SZZG-0028/SZZG-0118 and SZZ-0132/SZZ-0136 — which the signature cannot
distinguish although their mechanisms differ; that is a limit of the proxy, not
a claim that they are redundant.

## Adding a baseline

Add a predictor to `src/szzbench/baselines.py` and register it in
`build_predictors` as a `Baseline(name, family, description, predict)`, with the
family whose inputs it stays within. A predictor returns commit **hashes**; the
runner turns them into `Prediction` records and hands them to
`evaluate_prediction_map`, so nothing in a baseline decides what counts as a
correct answer. Leave `scores_on_abstention` at `False` unless the rule *is*
silence — see [Saying nothing](#saying-nothing).
