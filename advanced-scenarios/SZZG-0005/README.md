# SZZG-0005: Method move between classes

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G1` Refactoring, move, rename, and semantic rewrite |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `refactoring`, `method-move`, `post-bic-refactoring`, `wrong-variable` |
| oracle | `exact_set`; required `c1`; related but not correct `c2` · BFC `c3` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

`Shipping.cost` floors the cost at a configured minimum; `c1` "simplifies" the
floor and makes it the per-kilogram rate instead — a wrong variable. `c2` moves
the method, unchanged, from `Shipping` to a new `ShippingUtils` class: the
faulty line leaves one file and appears in another. `c3` fixes it where it now
lives. Plain blame on the fixed line stops at the move commit; reaching the BIC
means following the method across files (`git blame -C`, or matching the moved
body). Compare SZZG-0006, where the move is an extract-class refactoring.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, two distractors on
the fault file, 4 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* f4b08cf  2023-07-10  Floor the shipping cost at the configured minimum in ShippingUtils.cost  <- BFC (c3)
* e178322  2023-07-03  Move cost from Shipping to ShippingUtils                                 (c2, move; related_but_not_correct)
* 20351fe  2023-06-30  Simplify the shipping cost floor                                         <- BIC (c1)
* 6ba0ece  2023-06-23  Add Shipping with cost and volumetric weight helpers                     (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`); `related_but_not_correct: [c2]`
- BFC: `c3`

## Measured behaviour and blame

| commit | `cost(500, 10, 8)` | `cost(3000, 10, 8)` | `cost(30000, 100000, 8)` | where `cost` lives |
|---|---|---|---|---|
| `c0` | 8 | 30 | 3000000 | `Shipping` |
| `c1` | **10** | 30 | 3000000 | `Shipping` |
| `c2` | **10** | 30 | 3000000 | `ShippingUtils` |
| `c3` | 8 | 30 | 3000000 | `ShippingUtils` |

Below the floor the faulty version returns the rate (10) instead of the minimum
(8); above it nothing changes. The product is taken in `long` before the
division (`(int) ((long) weightGrams * ratePerKg / 1000)`), so the large input
does not overflow in any snapshot (PR #63 review). `c3` deletes one line (line 5 of
`ShippingUtils.java`); blame at `c3^` returns `c2`, which created the file. The
declared fault statement is no longer in `Shipping.java` at `c3^`, so the
verifier reports `GI701` (declared by the refactoring factors).

## What a tool must do

Report `c1`, not `c2`. The moved method is byte-for-byte identical before and
after the move and `Shipping.java` shrinks in the same commit that creates
`ShippingUtils.java`, so move-aware blame can follow the line back.
