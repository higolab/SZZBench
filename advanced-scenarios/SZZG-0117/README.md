# SZZG-0117: The unit change arrives through a merge, the consumer is written after it

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `merge`, `release-branch`, `value-flow`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c4` · BFC `c5` |
| graph features | 2 branches; merge commit `c3`; 2 BICs; 2 fault sites |
<!-- /szzbench:header -->

## Purpose

A discriminating-tier scenario on the measured axis: the answer is two commits,
and only one of them is reachable by blaming what the fix deletes. It is the
third instance of the *value* kind — after [SZZ-0190](../../scenarios/SZZ-0190/README.md)
(a constant) and [SZZ-0195](../../scenarios/SZZ-0195/README.md) (a stored field)
— and the first where the history's **shape** hides the commit as well: it sits
on the second parent of a merge.

## Commit structure

```text
* f5297ed  Warn five seconds before the poll        INTERVAL / 1000 - 5          <- BFC (c5)
* 633cf0c  Warn shortly before the next poll        adds warnAfterSeconds()      <- BIC (c4)
*   ac7b67b  Merge the release branch                                            (c3)
|\
| * 12aeb6a  Express the poll interval in milliseconds  INTERVAL = 30000         <- BIC (c1, branch release)
* | cc12e3d  Note when the schedule is consulted    docs only (c2)
|/
* 50b551a  Add the poll schedule                    INTERVAL = 30 (seconds) (c0)
```

`c1` converts the constant and its only reader together on the release branch.
`c4`, written after the merge, subtracts five from the constant as if it still
held seconds.

## Expected BIC / BFC

- BICs: `c1` and `c4` (`exact_set`, `required: [c1, c4]`)
- BFC: `c5`

## Measured behaviour (from the generated repository)

```text
c0  Add the poll schedule                     nextPollSeconds()=30
c2  Note when the schedule is consulted       nextPollSeconds()=30
c1  Express the poll interval in milliseconds nextPollSeconds()=30   <- unchanged
c3  Merge the release branch                  nextPollSeconds()=30
c4  Warn shortly before the next poll         warnAfterSeconds()=29995   <- the bug
c5  Warn five seconds before the poll         warnAfterSeconds()=25
```

**Both commits are necessary, measured rather than argued.** Undoing `c1`'s
conversion on top of `c4` — the tree in which the faulty subtraction exists but
the unit change does not — gives `warnAfterSeconds() = 25`, the fixed answer.

## Measured history shape

`c1` is **not** on the first-parent history of the fix:

```text
git log --first-parent HEAD
  f5297ed Warn five seconds before the poll
  633cf0c Warn shortly before the next poll
  ac7b67b Merge the release branch
  cc12e3d Note when the schedule is consulted
  50b551a Add the poll schedule
```

A tool that walks `--first-parent` — a common way to keep a release history
readable — never visits the commit it has to report.

## Measured blame outcome at BFC^

The fix deletes exactly one line:

```text
"return INTERVAL - 5;"   plain -> c4   -w -> c4   -w -C -C -> c4
```

Blame returns `{c4}` — half the answer — and `c1` is not reachable from the
deleted line by any blame variant.

## What a tool must do to pass

Report exactly `{c1, c4}`. That needs two steps a line-based walk does not
take: following `INTERVAL` from the fixed expression to the commit that changed
its unit, and following the merge's second parent to find that commit at all.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario. It is declared
`tier: discriminating` and `szzbench baselines` confirms the declaration.
