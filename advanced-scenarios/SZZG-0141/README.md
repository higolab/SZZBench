# SZZG-0141: Credit that saturates: two origins at half credit each can fill a two-commit oracle without full recall

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `relaxed-credit`, `origin-vs-direct`, `copy-propagation`, `multi-bic`, `single-bfc`, `evaluation-variant` |
| oracle | default (`direct-only`): `exact_set`; required `c3`, `c4`; related origins `c1`, `c2` · `origin-aware`: `relaxed_with_related`; required `c3`, `c4`; acceptable `c1` (credit 0.5), `c2` (credit 0.5) · `relaxed-with-credit`: `relaxed_with_credit`; required `c3`, `c4`; acceptable `c1` (credit 0.5), `c2` (credit 0.5) · BFC `c5` |
| graph features | 4 BICs; origin faults; 2 fault sites; 3 evaluation variants (`direct-only`, `origin-aware`, `relaxed-with-credit`); `copy_relationships` |
<!-- /szzbench:header -->

## Purpose

Second member of the `relaxed_with_credit` family ([SZZG-0022](../SZZG-0022/README.md):
one origin at 0.5; [SZZG-0142](../SZZG-0142/README.md): one origin at 1.0). Two
helper classes carry faulty formulas — `Money.cents` truncates instead of rounding
(`c1`), `Percent.of` divides before multiplying (`c2`) — and `InvoiceLine` copies
both inline in two commits (`c3`, `c4`, the direct BICs). One fix repairs the two
copies. The `relaxed-with-credit` variant gives each origin credit 0.5 towards a
possible credit of 2, which lets an answer with one direct and both origins reach
the cap — full credit — while it still fails for the missing direct. Credit
measures overlap; status measures recall.

## Commit structure (generated)

```text
* 71329d9  2024-09-09  Round cents and multiply before dividing in InvoiceLine  <- BFC (c5)
* d7a9009  2024-09-02  Add the discounted total to InvoiceLine                  <- direct BIC (c4, copies c2's formula)
* 8cd61ac  2024-08-26  Add InvoiceLine with an inline cent conversion            <- direct BIC (c3, copies c1's formula)
* 9cdede7  2024-08-19  Divide first in Percent.of to avoid overflow             <- origin (c2)
* 3970756  2024-08-12  Drop the rounding call from Money.cents                  <- origin (c1)
* 25f8b01  2024-08-05  Add the money and percentage helpers                     (c0)
```

## Expected BIC / BFC

- default (`direct-only`): `required: [c3, c4]`, `related_origins: [c1, c2]`
- `origin-aware`: `relaxed_with_related`, origins as `acceptable_related` at 0.5 (D3)
- `relaxed-with-credit`: `relaxed_with_credit`, the same lists — the point is the arithmetic
- BFC: `c5`. The helpers keep their faults; they are the origins and are not fixed here.

## Measured behaviour and blame

| commit | `Money.cents(0.29)` | `Percent.of(199, 10)` | `netCents(0.29)` | `discountedCents(199, 10)` |
|---|---|---|---|---|
| `c0` | 29 | 19 | — | — |
| `c1` | **28** | 19 | — | — |
| `c2` | 28 | **10** | — | — |
| `c3` | 28 | 10 | **28** | — |
| `c4` | 28 | 10 | 28 | **189** |
| `c5` | 28 | 10 | 29 | 180 |

(`0.29 * 100` is `28.999…`, so the cast truncates to 28; `199 / 100 * 10` is 10.)
`c5` deletes lines 5 and 9 of `InvoiceLine.java`; blame at `c5^` returns `c3` and
`c4`.

## What the evaluator says (`tests/test_policy_families.py`, variant `relaxed-with-credit`)

| answer | `weighted_credit` / `possible_credit` | status |
|---|---|---|
| `{c3, c4}` | 2.0 / 2.0 | PASS |
| `{c3, c4, c1, c2}` | min(2, 2 + 0.5 + 0.5) = 2.0 / 2.0 | PASS |
| `{c3, c1, c2}` | min(2, 1 + 0.5 + 0.5) = **2.0** / 2.0 | **FAIL** (`c4` missing) |
| `{c1, c2}` | 1.0 / 2.0 | FAIL |

Under the default variant any origin in the answer is a false positive
(`{c3, c4, c1}` fails).
