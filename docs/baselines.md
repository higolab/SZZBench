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
family. It scores **2/277** on the shipped suite: SZZG-0135 and SZZG-0136 are
the two scenarios whose default oracle is empty by contract — an externally
caused fault and an import boundary (issue #24, D11) — and abstaining is the
correct answer there. Everywhere else it scores nothing.

## Measured on the shipped suite

277 generated scenarios, measured 2026-09-24 (after the history-rewriting scenarios of
issue #22, SZZG-0122–0129, the tool-visible-context scenarios of issue #23, SZZG-0130–0134,
the Python scenarios of issue #24, SZZ-0200–0206, and its root-commit-contract and
policy-family scenarios, SZZG-0135–0142, the two configuration scenarios that closed
issue #23, SZZ-0207 and SZZ-0208, the divergent-fix scenario of issue #22, SZZG-0143, and
the three multi-hop line histories of issue #24, SZZ-0209–0211, the ten discriminating
scenarios of issue #35's rebalance, SZZ-0212–0217 and SZZG-0144–0147, the two
second-mechanism scenarios of issue #80, SZZ-0218 and SZZG-0148, the three it
added to the largest cheaply-solved pockets, SZZ-0219, SZZ-0220 and SZZG-0149, and
the three that gave S1, S2 and S5 a second one, SZZ-0221 to SZZ-0223, and the two
that did the same for S7 and S8, SZZ-0224 and SZZ-0225):

| baseline | family | solves |
|---|---|---|
| `blame-deleted-lines` | blame | **157/277 = 56.7%** |
| `position-1` | position | **162/277 = 58.5%** |
| `shape-last-toucher` | shape | 121/277 = 43.7% |
| `position-before-fix` | position | 106/277 = 38.3% |
| `position-2` | position | 23/277 = 8.3% |
| `position-3` | position | 22/277 = 7.9% |
| `position-4` | position | 7/277 = 2.5% |
| `position-all-non-fix` | position | 6/277 = 2.2% |
| `position-0` | position | 6/277 = 2.2% |
| `position-5` | position | 2/277 = 0.7% |
| best `author:…` | metadata | 12/277 = 4.3% (chance) |
| `abstain` | position | **2/277** (the two empty oracles) |
| `message-admits-fault` | metadata | **0/277** |

**A fixed rule versus the union.** Each row is one rule applied to every
scenario, which is what an attacker can actually do. The union of the rows is
*not* an attacker's score: choosing which rule to use per scenario needs the
oracle. The union is reported below as an upper bound on how much of the suite
a cheap rule could explain — headroom, not a result.

Read this table before reading any result reported on SZZBench:

- **A rule that opens no file is level with the classic B-SZZ baseline.**
  "Report the second commit of the history" solves **162 of 277** and
  `blame-deleted-lines` **157 of 277**; on the 253-scenario suite the two were
  exactly tied at 158, as they had been at 142 on the 225-scenario suite. The eight history-rewriting scenarios of issue
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
  answer — so blame led by two; and the two configuration scenarios that closed
  issue #23 (SZZ-0207, SZZ-0208) both put the BIC second and both hide it from
  blame, because the line the fix deletes belongs to the initial commit, so the
  two rules were exactly tied again; then the three multi-hop line histories of
  issue #24 (SZZ-0209–0211) and the divergent-fix scenario of issue #22
  (SZZG-0143) all put the BIC second and none is blame-solvable — a multi-hop
  line blames to its last rewrite, and blaming both of SZZG-0143's fixes returns
  the release reformat as well — while SZZG-0089's real revert-of-revert took one
  scenario away from blame (its fix's deleted lines now belong to the rename
  before it), so the position rule leads by five; the ten discriminating
  scenarios of issue #35's rebalance (SZZ-0212–0217 and SZZG-0144–0147) and the
  two of issue #80 (SZZ-0218, SZZG-0148) and its three for the largest pockets
  (SZZ-0219, SZZ-0220, SZZG-0149) and its three for S1, S2 and S5 (SZZ-0221 to
  SZZ-0223) are solved by neither rule, by design, so both counts stand. Most scenarios are still four commits long with a single-commit oracle in
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
- **Upper bound (oracle-aware): 235 of 277 scenarios are solved by *some*
  cheap rule.** Forty-two resist all of them — SZZ-0132, SZZ-0136, SZZ-0190 to
  SZZ-0199, SZZ-0212 to SZZ-0225, SZZG-0028, SZZG-0038, SZZG-0040, SZZG-0069,
  SZZG-0076, SZZG-0117 to SZZG-0121 and SZZG-0144 to SZZG-0149 — and every one of
  them has a **multi-commit oracle**, which the next section shows is not a
  coincidence but the only thing the declared family leaves open.
  Split by oracle size:

  | | best fixed rule | union over all rules |
  |---|---|---|
  | 218 scenarios with a one-commit oracle | 160/218 = 73.4% (`position-1`) | **218/218** |
  | 54 scenarios with a two-commit oracle | 13/54 = 24.1% (`blame-deleted-lines`) | 14/54 |
  | 3 scenarios with a three-commit oracle (SZZG-0138, SZZG-0148 and SZZG-0149, all `minimum_required: 2`) | 1/3 (`blame-deleted-lines`) | 1/3 |
  | 2 scenarios with an empty oracle (SZZG-0135, SZZG-0136) | 2/2 (`abstain`) | 2/2 |

  A one-commit answer inside a three- or four-commit history is reachable by
  *some* cheap rule in every single case, at every depth — 105/105 at depth 1,
  87/87 at depth 2, 18/18 at depth 3 and 8/8 beyond. Oracle size is the
  dimension that separates them, and a longer or deeper history on its own
  will not raise the floor.

  Thirteen of the fourteen two-commit oracles a cheap rule solves fall to the
  same rule, `blame-deleted-lines`, and for the same reason: their fix deletes one
  line from each of the two commits, so naive blame returns both. That is the
  shape the discriminating tier is built to avoid.

  The fourteenth is **SZZG-0007**, and blame cannot reach it: both files the fix
  touches were created by `c2`, so blame answers `{c2}` and misses `c1`. It
  falls instead to `position-all-non-fix`, which predicts `{c1, c2}` — the
  history is three commits long and the two non-fix commits *are* the answer.
  (Until 2026-09-21 `author:Aiko Tanaka` solved it as well, because the
  generator's rotation had given those two commits one author who wrote nothing
  else; that coincidence is now `GW413` — issue #43 — and `c2` carries an
  explicit author.) `shape-last-toucher` does **not** solve it (it answers `{c2}`); the
  six two-commit scenarios it does solve are all solved by blame as well.

  (An earlier revision of this table reported `1/21` as the best fixed rule on
  two-commit oracles. That figure was wrong: recomputed on the same 215-scenario
  measurement, it is `9/21`, by `blame-deleted-lines`. The union was right.)
- **No category is 100% solvable** by a cheap baseline any more: S6 42.1%
  (8/19), S7 71.4% (5/7), S8 75.0% (6/8), S5 77.8% (7/9), G3 78.6% (11/14),
  G9 83.3% (10/12), S1 86.7% (13/15), G2 87.5% (14/16), S2 88.2% (15/17),
  G5 88.9% (16/18), S4 88.9% (16/18), G4 90.0% (27/30), G6 90.0% (9/10),
  G8 90.9% (10/11), G1 92.9% (13/14), S3 92.9% (39/42) and G7 94.1% (16/17). Ten of these (S1, S2, S3, S4, S5, S7, G6, G7, G8,
  G9) were 100% until 2026-09-22, when each received its first discriminating
  scenario (issue #35).
- The metadata family is at chance, which is the leakage guarantee holding: the
  best author rule (4.3%) sits *below* the mean of a label-shuffled null, and
  the message rule scores zero.

  This family is the sharpest illustration of the fixed-rule-versus-union
  distinction above. The *union* over all author rules solves **95/277 =
  34.3%**: in more than a third of the scenarios *some* author's set of commits
  happens to be exactly the oracle, usually because the oracle is one commit and
  the generator's author rotation gave that commit an author it gave no other.
  An attacker cannot use that — they must fix one author and apply it
  everywhere, which is the 4.3%. The coincidence is common; exploiting it needs
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
| `control` | checks that a method handles a specific input condition; a cheap rule may well solve it | **235** |
| `discriminating` | designed so that none of the declared cheap baselines solves it | **42** |

Every one of the forty-two has a multi-commit oracle, which section *Why a
discriminating scenario needs a multi-commit oracle* below shows is forced.
Seven are pre-existing scenarios that turned out to resist the baselines;
twenty-five were **designed** against one axis, on one skeleton — the answer is
two commits, one of which the fix's deleted lines do not blame to — and the
remaining ten come from issue #80: SZZ-0218 and SZZG-0148 fail the cheap rules
in two further ways (*Two mechanisms inside that room* below), three shrink the
two largest cheaply-solved pockets (*Three for the largest pockets*), and five
give a category that rested on a single history a second one (*A second scenario
where a category had only one*). The first fifteen of the twenty-five were built
from five reasons that half the answer can be out of reach, three scenarios for
each:

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

Ten more were added on 2026-09-22 (issue #35, the rebalance): ten of the
seventeen categories had no discriminating scenario, and every one of them now
has one, on the same skeleton, with the category's own theme as the reason the
second commit is out of reach:

| category | scenario | why the second commit is out of blame's reach |
|---|---|---|
| S3 | SZZ-0212 | **rewrite** by noise: a whitespace-only re-indentation between the two faults owns the first one's line (`-w` reaches it) |
| S4 | SZZ-0213 | **ghost hunk** of a tangled fix: the hunk that repairs the omission adds lines only, and a cleanup hunk blames a bystander |
| S2 | SZZ-0214 | **ghost fix**: the check was deleted while nothing reached it, the fix puts it back by adding lines only, so no deleted line exists at all |
| G7 | SZZG-0144 | **value**, reached through evidence: the fix message names the issue whose closing commit changed the constant's unit |
| S1 | SZZ-0215 | **rewrite** by an ordinary edit: a correct single-token change on the faulty line (a threshold) keeps the wrong operator and owns the line; no variant of blame helps |
| G8 | SZZG-0145 | **file**, generated and large: the unit change rewrites every one of a table's 5,001 lines plus one reader line the fix does not touch |
| G9 | SZZG-0146 | **callee**, under two contracts: the default variant requires the callee change and the exposing commit, the `observable-only` variant only the latter — blame passes the second and fails the first |
| G6 | SZZG-0147 | **value**, put in force by a revert of a revert: the constant's last change is `c3`, whose diff is the original change again; reporting the origin or the undoing revert fails |
| S5 | SZZ-0216 | **rewrite** by a move: the fare method is moved token for token into a new class between the two faults; blame stops at the move under every default setting, and only a lowered copy score (`-C10`) or `git log --follow` on the new file reaches the fault |
| S7 | SZZ-0217 | **callee**, reached through evidence: the fix message quotes the subject of the commit that changed what the callee returns |

Their evidence follows the two forms below: SZZG-0144, SZZG-0145, SZZG-0146,
SZZG-0147 and SZZ-0217 are interactions (undoing the unreachable commit on top of
the later one gives the fixed answers on every probe), SZZ-0214 is an interaction
whose counterfactual coincides with the fix (the deleted check, put back), and
SZZ-0212, SZZ-0213, SZZ-0215 and SZZ-0216 are independent faults shown necessary
by the partial fix — repairing one at the last faulty commit leaves the other's
answers wrong.

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

### Why a discriminating scenario needs a multi-commit oracle

That every scenario of the tier names two or three commits is not a habit of
whoever wrote them. It is the only thing the declared family leaves open, and
the argument is short:

- **A one-commit oracle is always solved by a positional rule.** `position-k`
  reports the commit at index *k*, and `position_indices` enumerates *k* for
  the index of every answer in the suite — deliberately, so that a scenario
  cannot look discriminating merely by sitting deeper. So whatever index the
  single required commit occupies, the rule for that index names it and nothing
  else, and passes.
- **An empty oracle is always solved by `abstain`.** `expect_no_bic` passes
  exactly when the prediction is empty, which is what `abstain` predicts.

Measured on the shipped suite: all 218 one-commit oracles are solved by some
`position-k`, both empty oracles by `abstain`, and every one of those 220
scenarios is declared `control`.
`tests/test_second_mechanism.py::test_only_a_multi_commit_oracle_can_discriminate`
fails the build if a scenario ever declares otherwise.

The consequence worth stating plainly: **the tier does not measure "hard", it
measures "needs more than one commit and the cheap rules cannot assemble the
set"**. Raising the floor by adding a deeper single-commit answer is not
possible; the only room is inside multi-commit oracles.

### Two mechanisms inside that room (issue #80)

Until 2026-09-22 all of them failed the cheap rules the same way: two commits,
one of them not reachable from the lines the fix deletes. Two scenarios added
that day fail differently, so that a method which handles the first kind does
not thereby pass the tier:

| scenario | mechanism | what blame answers |
|---|---|---|
| SZZ-0218 (S4) | **a false positive, not a false negative.** The fix repairs two faults and drops a dead instrumentation counter a third commit added, so blame names every required commit *and* the counter's author. The work is rejecting a commit blame hands over. | `{c1, c2, c3}` ⊋ `{c1, c3}` |
| SZZG-0148 (G9) | **a credit threshold.** Three contributing causes under `partial_credit` with `minimum_required: 2`; only one repair deletes a line, the other two add a guard and a `case`. Blame is right about what it names and still short. | `{c1}` of `{c1, c3, c4}` |

SZZ-0218 is the tier's first `blame_class: extra` scenario and SZZG-0148 its
first three-commit oracle. SZZG-0138 is the control twin of SZZG-0148: the same
policy and threshold, with two of its three causes on deleted lines, so blame
passes it.

A third candidate does not exist and cannot: an `expect_no_bic` scenario that
makes the cheap rules *answer* rather than abstain would still be passed by
`abstain` itself, for the reason given above.

### Three for the largest pockets (issue #80, proposal 3)

S3 held 39 of its 40 scenarios in the cheaply-solved set and G4 27 of 29, the
two largest such pockets. Every one of those had a one-commit oracle, which the
section above shows a positional rule names by construction, so the pocket could
only shrink by adding scenarios whose oracle names more than one commit:

| scenario | category | how it fails the cheap rules |
|---|---|---|
| SZZ-0219 | S3 | **two** behaviour-preserving rewrites separate the first fault from the fix — a comparison extracted into a named local, then that local renamed — so recursion has to run twice and no blame variant shortens it |
| SZZ-0220 | S3 | the fix also drops a deprecated alias, so blame returns `{c0, c1, c2, c3}` against an answer of `{c1, c3}` and a tool has to reject **two** commits |
| SZZG-0149 | G4 | three causes on three branches under `partial_credit` with a threshold of two, of which the fix's deleted line reaches one |

S3 is now 39/42 and G4 27/30. SZZG-0149 earned its final shape from the check
rather than from the design: written with a two-file fix and no commit between
the last cause and the fix, the **shape** rule named the newest commit to touch
each of those files — two of the three required commits, exactly the threshold —
and `szzbench baselines` refused the `discriminating` declaration. The scenario
now has a documentation commit between them, so the shape rule answers a commit
that introduced nothing.

### A second scenario where a category had only one (issue #80, proposal 2)

A category whose claim to discriminate rests on a single history gives a method
one example to overfit to, and nine categories were in that position. Five now
have a second, each failing the cheap rules for a reason its first one does not:

| scenario | category | the category's first one | the new reason |
|---|---|---|---|
| SZZ-0221 | S1 | SZZ-0215: a *correct* edit to the faulty line owns it | a guard narrowed while nothing took the narrowed branch, and a caller in another file written later that does |
| SZZ-0222 | S2 | SZZ-0214: the fix deletes nothing, so blame has nothing to say | the fix deletes a duplicated guard, so blame answers **one commit and it is not in the oracle at all** |
| SZZ-0223 | S5 | SZZ-0216: a method moved to a new class | a signature change that copies the faulty constant into the caller's argument, so the value crosses a file with no commit editing it |
| SZZ-0224 | S7 | SZZ-0217: the changed contract is quoted in the fix's commit message | the contract that changed is a **Javadoc** — the evidence is in the source, on a line no commit in the answer touches after it, and the second cause is a new caller that reads the new meaning |
| SZZ-0225 | S8 | SZZ-0199: the fault is in a properties file the fix never opens | the first cause is a **test-only** commit — the wrong expectation is written into `LateFeeTest` and a later production change satisfies it, so blame on the fix's deleted lines answers a rename of the test's helper and the production change, and never the test |

SZZ-0222 is the first scenario in the suite whose blame answer contains **no**
required commit. Everywhere else blame either reaches part of the answer or is
silent; here it names the initial commit, confidently and wrongly, which is a
harder answer to discard because nothing in it is right to anchor on.

SZZ-0225's first cause is visible without being a wrong answer: its test is red
from `c1` until `c3` changes the product to agree with it. Its evidence is
therefore the **disjoint-effects** kind of the two described above — `c1` owns
the expectation, `c3` owns the fee, and the fix restores exactly their union —
and not the interaction kind, where the unreachable commit is harmless until a
later one reaches it. The red window is itself a route back to `c1` for a tool
that runs the suite, and the trap is concluding that the commit which turned it
green is the whole answer. (The scenario first claimed the fault was latent
until `c3`; running its test at each commit refuted that, in the review of
PR #86.)

S1 is now 13/15, S2 15/17, S5 7/9, S7 5/7 and S8 6/8. Four categories still
rest on one: G1, G6, G7 and G8.

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

Between the two tiers sits a finer declaration, `meta.defeats`: the cheap-rule
**families** a scenario is built to make fail (`blame`, `shape`, `position`;
`decisions/vocabulary.md` §8), with the wrong step spelled out in
`scenario_design.failure_mode`. A `discriminating` scenario defeats all three;
a control may defeat one or two — SZZG-0081 defeats `blame` and `shape`
because its formatting rewrite absorbs the blame, yet `position-1` still finds
its BIC — or none. `szzbench baselines` reports every declared family that
some rule of that family solves after all (`declared_defeated_but_solved`),
scoped to the families that ran. The 82 G4–G8 scenarios declare it since
2026-09-22 (blame defeated in 19, shape in 28, position in 4), and the twenty
discriminating scenarios added since declare all three, so 102 scenarios declare
it, with no contradiction.

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
| `blame_class` | what plain first-parent blame on the lines the fix deletes does with the oracle: `exact` (returns exactly the required set), `extra` (the required set and more), `miss` (a required commit is not blamed), `addition-only` (the fix deletes nothing) or `empty-first-parent` (the fix is a merge whose first-parent diff is empty). Measured, never hand-edited; not part of the redundancy signature |
| `difficulty_floor` | the least `difficulty` the blame class allows (`exact` → `easy`, `extra` / `addition-only` → `medium`, `miss` / `empty-first-parent` → `hard`); the report lists declarations below it as contradictions and above it as overrides |

`oracle_size` and `bic_depth` come from the evaluator's own policy resolution
(`_commit_level_policy`), so a default evaluation variant and an inferred
direct BIC are read the same way a scored run reads them. `bic_depth` measures
the **farthest** required BIC — the deepest commit a tool has to reach.

Measured on the shipped suite (277 scenarios):

```text
tier                   control:235, discriminating:42
blame_class            addition-only:16, empty-first-parent:1, exact:156, extra:18, miss:86
oracle_size            0:2, 1:218, 2:54, 3:3
bic_depth              1:105, 2:108, 3:48, 4:8, 5:3, 6:2, 1003:1, none:2
fault_file_distractors 0:15, 1:115, 2:103, 3:31, 4:11, 5:2
commit_count           2:3, 3:60, 4:109, 5:73, 6:23, 7:6, 8:2, 1005:1
ref_count              1:225, 2:47, 3:4, 4:1

128 distinct signatures; 47 groups of two or more, covering 196 scenarios
```

The largest groups are 30 S3, 13 S1, 10 S4, 8 S2 and 8 G1 scenarios that agree
on every dimension; 81 scenarios have a signature of their own (`bic_depth`
is `none` for the two empty oracles).

`blame_class` is the `blame-deleted-lines` baseline read per scenario rather
than as a pass count, and the two agree: the 156 `exact` scenarios are exactly
the ones that baseline solves, except SZZG-0138, which it solves although its
class is `miss` — blame reaches two of the three required commits, and the
scenario's `partial_credit` policy with `minimum_required: 2` accepts that. Of the
42 `discriminating` scenarios, 39 are `miss`, SZZ-0214 is `addition-only` (its fix
puts a deleted check back and deletes nothing) and SZZ-0218 and SZZ-0220 are
`extra` (their fixes also remove dead code, so blame names commits that are not
answers). The same run prints **declared
difficulty by measured blame class**, the table the grading rule of
`decisions/vocabulary.md` §4 is checked against. On the classic suite the
authors' judgement and the measurement mostly agree: `miss` is `hard` 30 times
and `medium` 7; `exact` is `easy` 31, `medium` 27 and `hard` 5 (S6, S7, S8
scenarios whose difficulty lies elsewhere than in blame); `extra` is `medium`
7; `addition-only` is `medium` 7, `hard` 6 and `easy` once — that table was
measured before the grading of 2026-09-22. Since then `difficulty` has a
**floor** set by the blame class (`exact` → `easy`, `extra` → `medium`,
`addition-only` → `medium`, `miss` → `hard`, `empty-first-parent` → `hard`;
`decisions/vocabulary.md` §4): the graph suite was graded from it (93 `easy`,
10 `medium`, 33 `hard`, from `advanced` throughout), the eight classic
scenarios below their floor were raised (SZZ-0203 to `medium`; SZZ-0081,
0082, 0083, 0136, 0204, 0205, 0206 to `hard`), and the 41 classic scenarios
above their floor keep the author's grade as an override. Three were added
after the grading: SZZ-0214, whose fix is addition-only, floor `medium`,
declared `hard` because its README names the ghost fix as the failure mode; and
SZZ-0218 and SZZ-0220, whose blame class is `extra`, floor `medium`, each
declared `hard` in a `## Difficulty` section saying that the difficulty is in
rejecting a commit blame hands over rather than in reaching one. The same run
reports the check: **0 below the floor, 41 above, 0 ungraded.**

The same run prints the **fault statement reuse** block (issue #13), which
counts how many scenarios declare each fault statement (`fault.statement`,
`faults[].statement`, `origin_faults[].statement`, whitespace-normalised):

```text
214 distinct statement(s) over 258 scenario(s); 12 shared by two or more
 57x  return value > min && value < max;   (advanced-scenarios 39, scenarios 18)
  6x  return value > min;                  (advanced-scenarios 2, scenarios 4)
  5x  return value > 0;                    (scenarios 5)
most reused statement per category: G1 4/14, G2 5/16, G3 4/14, G4 9/30, G5 6/18,
  G6 3/10, G7 4/17, G8 3/11, G9 2/12, S3 11/42, S4 3/18, S6 3/19
```

(After the 28 rewrites of issue #13 — G4, G5, G2, then G1/G8/G6/G3; before them
the statement had 83 carriers, 65 of them graph, and G4 read 17/28, G5 13/18,
G2 10/16, G1 7/14, G8 5/10, G3 5/14, G6 5/9 on `boolean belowMax = value < max;`.)
Every graph category is now at or below one third on its most reused statement.
One statement is still a declared fault of 21% of the suite and 27% of the graph
suite;
`decisions/fault-library.md` catalogues the kinds a rewrite can draw on and the
rules a rewrite follows, and the per-category share above — at most one third
in every graph category, reached on 2026-09-21 — is the number a rewrite is
measured by. Read together
with the baseline table, the suite still concentrates in one cell — a
one-commit answer, one or two commits before the fix, in a three- or
four-commit single-branch history — and **that cell is where the cheap rules
win**.

The discriminating tier is deliberately spread out of it: its 42 scenarios
occupy **34** distinct signatures, where the original twelve occupy **7**. The
ten designed against the measured axis introduce **ten** signatures the suite
did not have — no two of them, and none of them reusing an existing one —
including the first two-commit oracles with no distracting commit on the fault
file at all (SZZ-0198, SZZ-0199) and the first seven-commit history with a
two-commit oracle (SZZ-0197). (Before the oracle corrections of issue #3 this
read 16 and nine, because SZZG-0118 then shared a signature with SZZG-0028;
correcting SZZG-0028's oracle moved it.) The twelve scenarios of 2026-09-22
(SZZ-0212 to SZZ-0218, SZZG-0144 to SZZG-0148) each add a signature the suite did
not have, as do SZZ-0219, SZZ-0221, SZZ-0222, SZZ-0225 and SZZG-0149.

Six signatures inside the tier are shared by more than one scenario:
SZZ-0190/0191/0193/0194, SZZ-0132/SZZ-0136, SZZG-0038/SZZG-0040,
SZZ-0212/SZZ-0220, SZZ-0216/SZZ-0223 and SZZ-0217/SZZ-0224. The last three are
the deliberate kind: a category's second discriminating scenario reuses the
shape of its first and changes the mechanism, which is exactly what the
signature cannot see. Those scenarios differ in mechanism — which is the point
of the tier — and the signature does not distinguish them; that is a limit of
the proxy, not a claim that they are redundant.

## Adding a baseline

Add a predictor to `src/szzbench/baselines.py` and register it in
`build_predictors` as a `Baseline(name, family, description, predict)`, with the
family whose inputs it stays within. A predictor returns commit **hashes**; the
runner turns them into `Prediction` records and hands them to
`evaluate_prediction_map`, so nothing in a baseline decides what counts as a
correct answer. Leave `scores_on_abstention` at `False` unless the rule *is*
silence — see [Saying nothing](#saying-nothing).
