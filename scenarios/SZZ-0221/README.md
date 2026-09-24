# SZZ-0221: A guard narrowed while nothing reached the narrowed case, and a caller written later that does

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `prerequisite-bic`, `boundary-condition`, `wrong-operator`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

S1's second `discriminating` scenario, after [SZZ-0215](../SZZ-0215/README.md),
and a different reason for the answer to be out of blame's reach. SZZ-0215 hides
a fault behind a *correct* edit to the same line; here the unreachable commit
narrowed a guard at a time when nothing took the narrowed branch, so it moved no
answer when it landed, and the commit that made it matter is in another file
that the fix never opens.

## Commit structure

```text
c0  Add the cent rounding helper and the order total   toNearestTen (package-private): negative branch when value < 0;
                                                       roundedTotal refuses a negative order total
c1  Take the negative branch only below a ten-cent magnitude   cents < -10          <- BIC
c2  Document what the order total includes             a Javadoc line (distractor)
c3  Quote a refund as a negative order total           roundedRefund passes a negative   <- BIC
c4  Round every negative amount through the negative branch again                   <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

Both are necessary. Without `c3` no method of the package reaches the narrowed
guard: `roundedTotal` is the only route to the helper and it throws on a
negative total, and `Rounding` is not part of the package's public surface.
Without `c1` the refund path rounds correctly.

## Measured behaviour

`roundedTotal(1234, 66)`, `roundedTotal(2147483643, 0)`, `roundedTotal(-8, 0)`,
`roundedRefund(3, 3)`, `roundedRefund(8, 8)` and `roundedRefund(2147483643, 0)`
at each commit (`tests/test_deepened_categories.py`; the refund methods exist
from `c3`):

| commit | total | total at the domain's edge | negative total | refund(3,3) | refund(8,8) | refund at the edge |
|---|---|---|---|---|---|---|
| `c0` | 1300 | 2147483640 | refused | — | — | — |
| `c1`, `c2` | 1300 | 2147483640 | refused | — | — | — |
| `c3` | 1300 | 2147483640 | refused | **0** | -20 | -2147483640 |
| `c4` | 1300 | 2147483640 | refused | -10 | -20 | -2147483640 |

`c1` moves nothing, and the row is identical to `c0`'s: the only route to the
helper refuses a negative total outright, so nothing in the package can take the
narrowed branch. The supported domain is an order total of at most 2 147 483 644
cents, the largest magnitude whose rounded value still fits `int`; the rounding
takes its sum in 64 bits and `tests/test_reference_arithmetic.py` holds the
bound.
`roundedRefund(8, 8)` rounds a −16-cent refund, which is below −10 and so takes
the negative branch even while the guard is narrowed — the fault is confined to
amounts between one and ten cents below zero, which is why it survived review.

**Counterfactual, measured:** widening the guard on top of `c3` — that is, `c4`
itself — turns `refund(3,3)` from 0 into −10 and leaves every other probe alone.

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"if (cents < -10) {"    plain -> c1    -w -> c1    -w -C -C -> c1
```

Blame returns `{c1}`: the commit that narrowed the guard, and nothing else.
`c3` wrote `Quote.java`, which the fix does not touch.

## What a tool must do to pass

Report exactly `{c1, c3}`. `c1` is what blame gives. Reaching `c3` means asking
which commit first sent a value into the branch the guard controls — a question
about callers, not about the fixed line.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.
