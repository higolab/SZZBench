# SZZG-0138: Partial credit with a majority threshold: two of three contributing BICs suffice

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `partial-credit`, `multi-bic`, `single-bfc`, `addition-only-fix` |
| oracle | `partial_credit`; required `c1`, `c2`, `c3`; minimum 2 · BFC `c4` |
| graph features | 3 BICs; 3 fault sites; policy `partial_credit` |
<!-- /szzbench:header -->

## Purpose

Second member of the `partial_credit` family ([SZZG-0033](../SZZG-0033/README.md):
one of two; [SZZG-0139](../SZZG-0139/README.md): one of two across a merge). One
bug report — discounts come out wrong — has three contributing causes committed
separately: two inline percentage formulas that divide before multiplying and so
truncate (`cents / 100 * 5`, `cents / 100 * percent`), and a discount dispatcher
that never handles `BULK`. One commit fixes all three. `minimum_required: 2`
makes the policy a majority vote: two of the three pass, one does not, and a
false positive still fails.

## Commit structure (generated)

```text
* 4fd4019  2024-03-04  Compute every discount through percentOf and handle bulk orders  <- BFC (c4)
* 1750b8f  2024-02-26  Dispatch discounts by kind                                       <- BIC (c3, omission: no BULK case)
* 32d0c0b  2024-02-19  Apply the seasonal discount                                      <- BIC (c2)
* 68d9c75  2024-02-12  Apply the loyalty discount at checkout                           <- BIC (c1)
* a7bddfb  2024-02-05  Add the discount helper                                          (c0)
```

## Expected BIC / BFC

- `partial_credit`, `required: [c1, c2, c3]`, `minimum_required: 2`
- BFC: `c4`

## Measured behaviour and blame

| commit | `loyalty(199)` | `seasonal(199, 20)` | `forKind(BULK, 1000)` |
|---|---|---|---|
| `c1` | **5** | — | — |
| `c2` | 5 | **20** | — |
| `c3` | 5 | 20 | **0** |
| `c4` | 9 | 39 | 100 |

`c4`'s diff deletes exactly two lines (`return cents / 100 * 5;`, line 9, and
`return cents / 100 * percent;`, line 13) and adds the `BULK` case. Blame at
`c4^` returns `c1` for line 9 and `c2` for line 13; `c3`'s fault is an omission
and its fix is addition-only, so blame cannot reach it.

## What the evaluator says (`tests/test_policy_families.py`)

| answer | status | reported |
|---|---|---|
| `{c1, c2}` — what plain blame finds | PASS | `false_negatives: [c3]`, `weighted_credit 2.0 / 3.0` |
| `{c1, c2, c3}` | PASS | full credit |
| `{c1}` | FAIL | below the threshold |
| `{c1, c2, c0}` | FAIL | a false positive is never tolerated |
