# SZZ-0218: Blame names every required commit and one more: the fix also removes an instrumentation counter

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `tangled-bfc`, `multi-hunk-bfc`, `blame-over-reports`, `off-by-one`, `wrong-variable` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The suite's first `discriminating` scenario whose failure is a **false
positive**. The thirty-two that preceded it all ask a tool to reach a commit
blame does not name; this one asks it to reject a commit blame does name. The
fix repairs two independent faults and, in the same commit, drops an unused
call counter a third commit had added, so blaming what it deletes returns a
strict superset of the answer. It is the first `blame_class: extra` scenario in
the tier — of the other 33, one is `addition-only` and the rest are `miss`.

Issue #80 asked for a second discriminating mechanism. This is one of the two;
the other is [SZZG-0148](../../advanced-scenarios/SZZG-0148/README.md), where
the failure is a credit threshold.

## Commit structure

```text
c0  Add the batch summary                    boxes() rounds up in 64 bits; describe() reports the box count
c1  Simplify the box count                   items / PER_BOX  (rounds down)                      <- BIC
c2  Count how often a batch is described     adds a private counter field and its increment      (distractor)
c3  Report the batch size on the label        describe() returns the item count                   <- BIC
c4  Count a partly filled box, label the box count again, and drop the unused counter            <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

`c2` is not a BIC. Its counter is written and never read, so removing it
changes nothing; the fix removes it because it is dead, not because it is
faulty.

## Measured behaviour

`boxes(24)`, `boxes(25)`, `boxes(Integer.MAX_VALUE)`, `describe(24)` and
`describe(25)` at each commit (`tests/test_second_mechanism.py`):

| commit | boxes(24) | boxes(25) | boxes(MAX_VALUE) | describe(24) | describe(25) |
|---|---|---|---|---|---|
| `c0` | 2 | 3 | 178956971 | 2 boxes | 3 boxes |
| `c1` | 2 | **2** | **178956970** | 2 boxes | **2 boxes** |
| `c2` | 2 | 2 | **178956970** | 2 boxes | 2 boxes |
| `c3` | 2 | 2 | **178956970** | **24 boxes** | **25 boxes** |
| `c4` | 2 | 3 | 178956971 | 2 boxes | 3 boxes |

The largest item count is probed because `boxes()` rounds up: the sum
`items + PER_BOX - 1` leaves the `int` range there, so the method adds in 64
bits. Written as a plain `int` sum it would answer −178956969 at `c0` and `c4`
— a negative box count in the *correct* snapshots, and the faulty floor
division would be the more sensible of the two.

`c2` moves no answer. Both faults are needed, measured by the partial fix at
`c3`: restoring the ceiling division alone still labels the batch `25 boxes`,
and restoring the label alone reports `2 boxes` for 25 items, because the label
then asks a `boxes()` that is still wrong.

## Measured blame outcome at BFC^

The fix deletes five lines in one file:

```text
"    private int described;"              plain -> c2   -w -> c2   -w -C -C -> c2
""                                        plain -> c2   -w -> c2   -w -C -C -> c2
"        return items / PER_BOX;"         plain -> c1   -w -> c1   -w -C -C -> c1
"        described++;"                    plain -> c2   -w -> c2   -w -C -C -> c2
"        return items + \" boxes\";"      plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame returns **`{c1, c2, c3}`** — every required commit and one more. Under
`exact_set` that is a false positive and the scenario fails; no blame variant
removes `c2`, because `c2` really did write those lines.

## What a tool must do to pass

Report exactly `{c1, c3}`. Reaching both answers is what plain blame already
does; the work is deciding that one of the three hunks repairs nothing. The
counter is written and never read, its removal changes no measured answer, and
the fix's message says it is dropped as unused. A tool that treats every
deleted line as evidence reports `c2` and fails.

## Difficulty

`hard`, above the `medium` floor its `extra` blame class sets
(`decisions/vocabulary.md` §4). The floor grades how far a tool must travel to
reach the answer, and here it travels nowhere: the whole difficulty is in
rejecting a commit that blame hands over with the right ones.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.
