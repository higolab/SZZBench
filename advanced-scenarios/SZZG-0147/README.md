# SZZG-0147: A revert of a revert brings the unit change back, and a consumer is written after it

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `revert`, `revert-of-revert`, `origin-vs-direct`, `value-flow`, `wrong-constant`, `blame-unreachable-bic` |
| oracle | default: `reintroduction_direct`; required `c3`, `c4`; related origins `c1`; related but not correct `c2` · `origin-aware`: `exact_set`; required `c3`, `c4`; related origins `c1`; related but not correct `c2` · BFC `c5` |
| defeats | `blame`, `shape`, `position` |
| graph features | revert `c2`, `c3`; 3 BICs; 2 fault sites; policy `reintroduction_direct`; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in G6 (issue #35). It is the *value*
kind of the measured axis — a constant's unit changes together with its only
reader, and a later reader assumes the old unit — with G6's own theme as the
reason the second commit is out of reach: the unit change in force at the fix
was put there by a **revert of a revert**. A tool that follows the constant has
to attribute the change to the right one of three commits whose diffs are the
same change, its inverse, and the same change again.

## Commit structure

```text
c0  Add the retry backoff policy                          BACKOFF = 2 (seconds); waitSeconds() = BACKOFF * attempt
c1  Express the backoff in milliseconds                   BACKOFF = 2000; waitSeconds() divides by 1000     (origin)
c2  Revert "Express the backoff in milliseconds"          real git revert of c1: seconds again              (related, not correct)
c3  Revert "Revert "Express the backoff in milliseconds"" real git revert of c2: milliseconds again          <- BIC
c4  Report the first wait before a retry                  firstWaitSeconds() = BACKOFF                       <- BIC
c5  Report the first wait in seconds                      firstWaitSeconds() = BACKOFF / 1000                <- BFC
```

`c2` and `c3` are real `git revert` commits with the messages Git writes;
measured, `c2`'s diff is the inverse of `c1`'s and `c3`'s diff equals `c1`'s.

## Expected BIC / BFC

- BICs: `c3` and `c4` (`reintroduction_direct`, `required: [c3, c4]`)
- `c1` is the origin (`related_origins`), tolerated under the `origin-aware`
  variant and a false positive under the default; `c2` is
  `related_but_not_correct`
- BFC: `c5`

Both are necessary. Without `c4` nothing reads `BACKOFF` as seconds; without
`c3` the constant is 2 and `c4`'s report is right. The direct/origin contract
attributes a reintroduced change to the commit that reintroduced it, which is
`c3` and not `c1`.

## Measured behaviour

`waitSeconds(3)` and `firstWaitSeconds()` at each commit
(`tests/test_rebalance_scenarios.py`; `firstWaitSeconds` exists from `c4`):

| commit | waitSeconds(3) | firstWaitSeconds() |
|---|---|---|
| `c0`–`c3` | 6 | — |
| `c4` | 6 | **2000** |
| `c5` | 6 | 2 |

Neither `c1`, `c2` nor `c3` changes an answer: each converts the constant and
its only reader together. **Counterfactual, measured:** undoing `c3` on top of
`c4` — `BACKOFF = 2`, `waitSeconds()` multiplying directly — gives 2, the fixed
answer.

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"return BACKOFF;"    plain -> c4    -w -> c4    -w -C -C -> c4
```

Blame returns `{c4}`. `c3` is not reachable from the deleted line; the history
is linear (`git log --first-parent` lists all six commits), so no parent choice
helps.

## What a tool must do to pass

Report exactly `{c3, c4}`. Following `BACKOFF` from the fixed expression
reaches the constant's declaration, whose last change is `c3`; a tool that
then "sees through" the revert pair and reports the original `c1`, or reports
the undoing `c2`, fails — under the default because `c1` is a false positive,
under `origin-aware` because `c3` is still missing.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.
