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
family. It scores **2/251** on the shipped suite: SZZG-0135 and SZZG-0136 are
the two scenarios whose default oracle is empty by contract — an externally
caused fault and an import boundary (issue #24, D11) — and abstaining is the
correct answer there. Everywhere else it scores nothing.

## Measured on the shipped suite

251 generated scenarios, measured 2026-09-21 (after the history-rewriting scenarios of
issue #22, SZZG-0122–0129, the tool-visible-context scenarios of issue #23, SZZG-0130–0134,
the Python scenarios of issue #24, SZZ-0200–0206, and its root-commit-contract and
policy-family scenarios, SZZG-0135–0142):

| baseline | family | solves |
|---|---|---|
| `blame-deleted-lines` | blame | **158/251 = 62.9%** |
| `position-1` | position | **156/251 = 62.2%** |
| `shape-last-toucher` | shape | 121/251 = 48.2% |
| `position-before-fix` | position | 106/251 = 42.2% |
| `position-2` | position | 23/251 = 9.2% |
| `position-3` | position | 22/251 = 8.8% |
| `position-4` | position | 7/251 = 2.8% |
| `position-all-non-fix` | position | 6/251 = 2.4% |
| `position-0` | position | 6/251 = 2.4% |
| `position-5` | position | 2/251 = 0.8% |
| best `author:…` | metadata | 11/251 = 4.4% (chance) |
| `abstain` | position | **2/251** (the two empty oracles) |
| `message-admits-fault` | metadata | **0/251** |

**A fixed rule versus the union.** Each row is one rule applied to every
scenario, which is what an attacker can actually do. The union of the rows is
*not* an attacker's score: choosing which rule to use per scenario needs the
oracle. The union is reported below as an upper bound on how much of the suite
a cheap rule could explain — headroom, not a result.

Read this table before reading any result reported on SZZBench:

- **A rule that opens no file is level with the classic B-SZZ baseline.**
  "Report the second commit of the history" solves **156 of 251** and
  `blame-deleted-lines` **158 of 251**; on the 225-scenario suite the two were
  exactly tied at 142. The eight history-rewriting scenarios of issue
  #22 are all blame-solvable and only two of them put the BIC second, which
  opened a gap of six; the five tool-visible-context scenarios of issue #23
  closed half of it the other way — four put the BIC second and only one is
  blame-solvable, because in the others the fault line was rewritten, the fault
  is a binary blob, or the fix's deleted line belongs to the initial commit;
  and the seven Python scenarios of issue #24 all put the BIC second while only
  three are blame-solvable (SZZ-0203's fix deletes nothing, and in SZZ-0204,
  SZZ-0205 and SZZ-0206 a type-annotation pass, an f-string conversion and a
  BOM re-save rewrote the faulty line), which handed the position rule a lead of
  one; the eight root-commit-contract and policy-family scenarios of the same
  issue (SZZG-0135–0142) handed it back — five are blame-solvable, two put the
  BIC second, two have an empty oracle and one has the root commit as its
  answer — so blame leads by two. Most scenarios are still four commits long with a single-commit oracle in
  second position, so the floor a real method has to beat is set by either
  rule, and a method that only matches B-SZZ has not shown it uses anything
  blame does not.

  Until the oracle work of issue #3 this row read the other way round (64.9%
  against 62.7%, so the position rule won). Correcting eight oracles that
  contradicted the direct/origin contract cost the position rule four scenarios
  and gained blame two; applying the contract to the rest then cost blame one
  more, by making SZZG-0016's origin a false positive in its default variant
  where it had been accepted unconditionally. The conclusion that a file-blind
  rule is *competitive with* blame survives every one of those changes. The
  conclusion that either rule *beats* the other does not: the 2026-09-19 lead
  of the position rule was an artefact of oracles that named the wrong commit,
  and the lead has since changed hands with every batch of five to eight
  scenarios — a property of the last batch's composition, not of the suite.
- **Upper bound (oracle-aware): 229 of 251 scenarios are solved by *some*
  cheap rule.** Twenty-two resist all of them — SZZ-0132, SZZ-0136, SZZ-0190 to
  SZZ-0199, SZZG-0028, SZZG-0038, SZZG-0040, SZZG-0069, SZZG-0076 and
  SZZG-0117 to SZZG-0121 — and every one of them has a **multi-commit oracle**.
  Split by oracle size:

  | | best fixed rule | union over all rules |
  |---|---|---|
  | 212 scenarios with a one-commit oracle | 154/212 = 72.6% (`position-1`) | **212/212** |
  | 36 scenarios with a two-commit oracle | 13/36 = 36.1% (`blame-deleted-lines`) | 14/36 |
  | 1 scenario with a three-commit oracle (SZZG-0138, `minimum_required: 2`) | 1/1 (`blame-deleted-lines`) | 1/1 |
  | 2 scenarios with an empty oracle (SZZG-0135, SZZG-0136) | 2/2 (`abstain`) | 2/2 |

  A one-commit answer inside a three- or four-commit history is reachable by
  *some* cheap rule in every single case, at every depth — 105/105 at depth 1,
  85/85 at depth 2, 18/18 at depth 3 and 4/4 beyond. Oracle size is the
  dimension that separates them, and a longer or deeper history on its own
  will not raise the floor.

  Thirteen of the fourteen two-commit oracles a cheap rule solves fall to the
  same rule, `blame-deleted-lines`, and for the same reason: their fix deletes one
  line from each of the two commits, so naive blame returns both. That is the
  shape the discriminating tier is built to avoid.

  The fourteenth is **SZZG-0007**, and blame cannot reach it: both files the fix
  touches were created by `c2`, so blame answers `{c2}` and misses `c1`. It
  falls instead to `position-all-non-fix` and to `author:Aiko Tanaka`, each of
  which predicts `{c1, c2}` — the history is three commits long and the two
  non-fix commits *are* the answer, and the same two commits happen to share an
  author. `shape-last-toucher` does **not** solve it (it answers `{c2}`); the
  six two-commit scenarios it does solve are all solved by blame as well.

  (An earlier revision of this table reported `1/21` as the best fixed rule on
  two-commit oracles. That figure was wrong: recomputed on the same 215-scenario
  measurement, it is `9/21`, by `blame-deleted-lines`. The union was right.)
- **Ten of the seventeen categories are 100% solvable** by a cheap baseline
  (S1, S2, S3, S4, S5, S7, G6, G7, G8, G9); the rest have headroom — S6 42.1%,
  G3 78.6%, S8 80.0%, G2 87.5%, G5 88.9%, G1 92.9%, G4 92.9%.
- The metadata family is at chance, which is the leakage guarantee holding: the
  best author rule (4.4%) sits *below* the mean of a label-shuffled null, and
  the message rule scores zero.

  This family is the sharpest illustration of the fixed-rule-versus-union
  distinction above. The *union* over all author rules solves **91/251 =
  36.3%**: in more than a third of the scenarios *some* author's set of commits
  happens to be exactly the oracle, usually because the oracle is one commit and
  the generator's author rotation gave that commit an author it gave no other.
  An attacker cannot use that — they must fix one author and apply it
  everywhere, which is the 4.4%. The coincidence is common; exploiting it needs
  the answer.

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
| `control` | checks that a method handles a specific input condition; a cheap rule may well solve it | **214** |
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
merge, a copy, a move, two branches or a cherry-pick.

Every README reports the blame result for each deleted line under three
variants and the probe answers that move at each commit. **How each one shows
that both commits are necessary depends on which kind it is**, and the two
forms of evidence must not be read as one:

- In the *value*, *callee*, *guard* and *file* kinds the two commits
  **interact**: the unreachable one is harmless on its own, and the fault
  appears only once the later commit reaches it. There the evidence is a
  counterfactual — undoing the unreachable commit on top of the faulty one
  reproduces the fixed behaviour on every probed argument: all 63 keys for
  SZZ-0195, all 25 for SZZ-0196, all 30 for SZZ-0198, all 98 for SZZG-0118, and
  every key SZZ-0199 and SZZG-0117 probe. SZZG-0121 agrees on every key except
  the seven belonging to `ratePerMille` itself, the accessor whose unit the
  commit changed, which cannot agree by construction. SZZG-0120 makes the same
  claim in the shape of the history instead: the bug is in neither parent of
  the merge.
- In the *rewrite* kind the two commits are **independent faults** that the
  same fix repairs; the rewrite between them only moves the blame. There a
  counterfactual would fail by construction — undoing one fault leaves the
  other — so the evidence is instead that their effects are disjoint and the
  fix restores exactly their union: 4 + 3 = 7 answers for SZZ-0197,
  379 + 62 = 441 for SZZG-0119.

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

Measured on the shipped suite (251 scenarios):

```text
tier                   control:229, discriminating:22
oracle_size            0:2, 1:212, 2:36, 3:1
bic_depth              1:105, 2:105, 3:33, 4:2, 5:2, 6:1, 1003:1, none:2
fault_file_distractors 0:13, 1:106, 2:95, 3:28, 4:8, 5:1
commit_count           2:3, 3:60, 4:107, 5:58, 6:17, 7:4, 8:1, 1005:1
ref_count              1:201, 2:46, 3:3, 4:1

106 distinct signatures; 43 groups of two or more, covering 188 scenarios
```

The largest groups are 30 S3, 13 S1, 10 S4, 8 S2 and 8 G1 scenarios that agree
on every dimension; 63 scenarios have a signature of their own (`bic_depth`
is `none` for the two empty oracles). Read together
with the baseline table, the suite still concentrates in one cell — a
one-commit answer, one or two commits before the fix, in a three- or
four-commit single-branch history — and **that cell is where the cheap rules
win**.

The discriminating tier is deliberately spread out of it: its 22 scenarios
occupy **17** distinct signatures, where the original twelve occupy **7**. The
ten designed against the measured axis introduce **ten** signatures the suite
did not have — no two of them, and none of them reusing an existing one —
including the first two-commit oracles with no distracting commit on the fault
file at all (SZZ-0198, SZZ-0199) and the first seven-commit history with a
two-commit oracle (SZZ-0197). (Before the oracle corrections of issue #3 this
read 16 and nine, because SZZG-0118 then shared a signature with SZZG-0028;
correcting SZZG-0028's oracle moved it.)

Three signatures inside the tier are still shared by more than one scenario:
SZZ-0190/0191/0193/0194, SZZ-0132/SZZ-0136 and SZZG-0038/SZZG-0040. Those
scenarios differ in mechanism — which is the point of the tier — and the
signature cannot see it; that is a limit of the proxy, not a claim that they
are redundant.

## Adding a baseline

Add a predictor to `src/szzbench/baselines.py` and register it in
`build_predictors` as a `Baseline(name, family, description, predict)`, with the
family whose inputs it stays within. A predictor returns commit **hashes**; the
runner turns them into `Prediction` records and hands them to
`evaluate_prediction_map`, so nothing in a baseline decides what counts as a
correct answer. Leave `scores_on_abstention` at `False` unless the rule *is*
silence — see [Saying nothing](#saying-nothing).
