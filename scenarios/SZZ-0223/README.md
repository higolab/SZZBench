# SZZ-0223: A signature change moves the faulty constant out of the method and into its caller's argument

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S5` Refactoring, move, and rename after BIC |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `method-signature-extension`, `refactoring-after-bic`, `multi-file-bfc`, `candidate-selection-distractor`, `wrong-constant`, `wrong-operator`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

## Purpose

S5's second `discriminating` scenario, after
[SZZ-0216](../SZZ-0216/README.md). SZZ-0216 moves a *method* to a new class;
here a refactoring changes a **signature**, turning a constant into a parameter
and copying its value — already mistyped — to the one call site. The faulty
value therefore crosses a file boundary without any commit editing it, and the
line the fix repairs was written by the refactoring's successor.

## Commit structure

```text
c0  Add the shipping fee helper and the quote   RATE_PER_KG = 300, read inside feeCents
c1  Correct the per-kilogram rate               RATE_PER_KG = 30                         <- BIC
c2  Pass the per-kilogram rate to feeCents instead of reading a constant   the 30 moves to the call site  (refactor)
c3  Take the handling surcharge off the quote   ... feeCents(grams, 30) - HANDLING_CENTS  <- BIC
c4  Charge three hundred cents a kilogram and add the handling surcharge                  <- BFC
```

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

`c2` is not a BIC: it copies the value it found, changes no answer, and the
refactoring itself is what a reviewer would approve.

## Measured behaviour

`totalCents(2000, 5000)` and `totalCents(500, 1000)` at each commit
(`tests/test_deepened_categories.py`):

| commit | 2000 g, 5000 c | 500 g, 1000 c |
|---|---|---|
| `c0` | 5600 | 1150 |
| `c1` | **5060** | **1015** |
| `c2` | 5060 | 1015 |
| `c3` | **4910** | **865** |
| `c4` | 5750 | 1300 |

`c1` charges a tenth of the rate, `c2` moves nothing, `c3` subtracts the
handling surcharge instead of adding it. The two faults are independent, and the
partial fix at `c3` shows both are needed: correcting the rate alone leaves the
surcharge subtracted, and correcting the sign alone leaves the rate at a tenth.

## Measured blame outcome at BFC^

The fix deletes one line:

```text
"return goodsCents + shipping.feeCents(grams, 30) - HANDLING_CENTS;"   plain -> c3   -w -> c3   -w -C -C -> c3
```

Blame returns `{c3}`. That one line carries **both** faults — the sign `c3` got
wrong and the rate `30` the refactoring copied — but only one commit wrote it.
`c1` is in `Shipping.java`, on a constant `c2` deleted, so no blame variant on
`Quote.java` can reach it.

## What a tool must do to pass

Report exactly `{c1, c3}`. Reaching `c1` means noticing that the literal `30` in
the argument did not originate there: `c2` wrote it, copying the value of a
constant in another file, and the commit that made that constant wrong is the
answer. Following the line's history stops at `c3`; following the *value* is
what crosses the signature change.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.
