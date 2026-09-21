# SZZG-0091: Multiple BICs with partial revert reintroducing one fault

## Purpose

Two original BICs in `InvoiceSummary.summarize`: `c1` adds the credit to the
amount due instead of subtracting it, `c2` swaps the `PAID`/`OPEN` labels. `c3`
fixes both. `c4` partially reverts `c3` and adds the credit again; `c5` fixes
that. For the final fix the direct BIC is the partial revert `c4`; `c1` is the
origin of the reintroduced fault; `c2` and `c3` are related history a tool must
not report.

Rewritten 2026-09-21 (issue #13) from the shared `aboveMin`/`belowMax` template;
the history shape, oracle and coverage dimensions (`bic_depth` 1, four
distractors on the fault file, 6 commits, 1 ref) are unchanged. The origin of
the reintroduced fault is now `c1` (the template version's was `c2`).

## Commit structure (generated)

```text
* 09b8bb9  2025-04-07  Subtract the credit from the amount due again                    <- BFC (c5)
* eac0824  2025-04-04  Revert the balance change                                        <- BIC (c4; partial revert of c3)
* 13925eb  2025-04-02  Subtract the credit and put the status labels the right way round (c3, prior fix)
* d368856  2025-03-31  Rename the status labels                                         (c2, second origin fault)
* a9ae55f  2025-03-25  Apply the credit to the amount due                               <- origin (c1)
* 0e66a70  2025-03-24  Add the invoice summary                                          (c0)
```

## Expected BIC / BFC

- default: `required: [c4]`, `related_but_not_correct: [c2, c3]`, `related_origins: [c1]`
- `origin-aware`: `relaxed_with_related`, `c1` at 0.5
- BFC: `c5`

## Measured behaviour and blame

`summarize(100, 30, false)`:

| commit | result |
|---|---|
| `c0` | `OPEN 70` |
| `c1` | **`OPEN 130`** |
| `c2` | **`PAID 130`** (both faults) |
| `c3` | `OPEN 70` |
| `c4` | **`OPEN 130`** |
| `c5` | `OPEN 70` |

`c5` deletes one line (`int due = amount + credit;`, line 5); blame at `c5^`
returns `c4` (verifier `GI703`).

## What a tool must do

Report `c4` alone. Reporting the original BIC set `{c1, c2}` — the answer to the
prior fix `c3` — is wrong for the final fix: `c2`'s fault never came back, and
`c1`'s came back through `c4`.

## Factors

- `revert`
- `partial-revert`
- `multi-bic`
- `single-fault-reintroduced`
- `re-bic`
- `wrong-operator`
