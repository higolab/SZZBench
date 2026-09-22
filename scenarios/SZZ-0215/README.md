# SZZ-0215: A correct change on the faulty line takes ownership of it: two single-token faults, one fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `deep-line-history`, `candidate-selection-distractor`, `off-by-one`, `wrong-operator`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

The first discriminating-tier scenario in S1 (issue #35). S1's controls are the
single-token semantic slips — an operator, a constant, a negation — each fixed
where it was made, so blame's last-toucher answer and the answer coincide. Here
two such slips are fixed by one commit, and between them a **correct**
single-token change edits the first faulty line: it raises a threshold and
keeps the wrong operator. Blame names that correct commit. No formatting, no
refactoring, no noise — only ordinary edits — and last-toucher is still not
fault-author.

## Commit structure

```text
c0  Add the loyalty points and the visit bonus      points = cents / 100; bonus = visits >= 5
c1  Tidy the bonus condition                        visits > 5     (the equality is lost)        <- BIC
c2  Raise the bonus threshold to eight visits       visits > 8     (correct intent, operator kept)  (distractor)
c3  Adjust the points computation                   cents % 100    (remainder instead of quotient)  <- BIC
c4  Award one point per whole euro and the bonus from the eighth visit   visits >= 8; cents / 100   <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

`c2` is not a BIC: raising the threshold is what the message says and what the
fixed line does too (`>= 8`); the fault on that line is the operator `c1` left.

## Measured behaviour

`bonus(visits)` for 4, 5, 6, 8 and 9 visits and `points(cents)` for 250 and
199 cents, at each commit (`tests/test_rebalance_scenarios.py`):

| commit | bonus 4 | bonus 5 | bonus 6 | bonus 8 | bonus 9 | points 250 | points 199 |
|---|---|---|---|---|---|---|---|
| `c0` | F | T | T | T | T | 2 | 1 |
| `c1` | F | **F** | T | T | T | 2 | 1 |
| `c2` | F | F | F | **F** | T | 2 | 1 |
| `c3` | F | F | F | F | T | **50** | **99** |
| `c4` | F | F | F | T | T | 2 | 1 |

`c1` takes the bonus from the fifth visit. `c2` moves three answers, two of
them on purpose (5 and 6 visits no longer qualify under the new threshold) and
one because it kept `c1`'s operator: the eighth visit, which the new threshold
means to include, does not qualify. `c3` turns the points into the cents left
over. The two faults are independent, and the partial fix measured at `c3`
shows both are necessary: restoring `>=` alone leaves the points at 50 and 99;
restoring `/` alone leaves the eighth visit without its bonus.

## Measured blame outcome at BFC^

The fix deletes two lines:

```text
"return cents % 100;"    plain -> c3   -w -> c3   -w -C -C -> c3
"return visits > 8;"     plain -> c2   -w -> c2   -w -C -C -> c2
```

Blame returns `{c2, c3}`: it misses `c1` and names `c2`, a correct commit. No
variant helps, because `c2` changed a token on the line.

## What a tool must do to pass

Report exactly `{c1, c3}`. The commit blame names for the bonus line changed
the constant and not the operator; the operator that the fix repairs was
written by the commit before it. Reaching `c1` means asking *which token* the
fix changed and who last changed that token, not who last touched the line.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.
