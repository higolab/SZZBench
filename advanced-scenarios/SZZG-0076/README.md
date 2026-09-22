# SZZG-0076: Multiple BICs replayed by rebase

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `discriminating` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `branch`, `rebase`, `multi-bic`, `rebased-bic`, `direct-bic`, `origin-bic`, `integer-overflow`, `wrong-operator` |
| oracle | default: `exact_set`; required `r1`, `r2`; related origins `f1`, `f2` · `origin-aware`: `relaxed_with_related`; required `r1`, `r2`; acceptable `f1` (credit 0.5), `f2` (credit 0.5) · BFC `c3` |
| graph features | 2 branches; rebase `r1`, `r2`; 4 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Two feature commits damage the same line in two different ways and a rebase
replays them one by one. `f1` narrows the elapsed milliseconds to an `int`,
which wraps for spans beyond about 24 days; `f2` turns the division by 60000
into a multiplication. On `main` the replays `r1` and `r2` are both required.
Blame of the line the fix deletes returns only `r2`, which keeps the scenario in
the discriminating tier.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle, tier and coverage dimensions (`bic_depth` 2, three
distractors on the fault file, 6 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* ca0f519  2024-02-29  Divide the long elapsed time by 60000 again    <- BFC (c3)
* b619235  2024-02-28  Simplify the minutes conversion                <- BIC (r2, rebase_of f2)
* d48f86a  2024-02-23  Narrow the elapsed milliseconds to an int      <- BIC (r1, rebase_of f1)
| * 29acbb2  2024-02-16  Simplify the minutes conversion              <- origin (f2, feature)
| * 0807995  2024-02-09  Narrow the elapsed milliseconds to an int    <- origin (f1, feature)
|/
* 7f0f1aa  2024-02-08  Add the elapsed-minutes helper                 (c0)
```

## Expected BIC / BFC

- default: `required: [r1, r2]`, `related_origins: [f1, f2]`
- `origin-aware`: `relaxed_with_related`, `f1` and `f2` at 0.5 each
- BFC: `c3`

## Measured behaviour and blame

| commit | `minutesBetween(0, 120000)` | `minutesBetween(0, 3000000000)` (≈35 days) |
|---|---|---|
| `c0` | 2 | 50000 |
| `f1`, `r1` | 2 | **-21582** (the `int` narrowing wraps) |
| `f2`, `r2` | **7200000000** | **-77698037760000** |
| `c3` | 2 | 50000 |

`c3` deletes one line (`return (int) (endMillis - startMillis) * 60000L;`,
line 6); blame at `c3^` returns `r2`; blaming the same line at `r2^` returns
`r1`.

## What a tool must do

Return both `r1` and `r2`. Each replay is a genuine fault of its own — the
overflow is there before the multiplication arrives and survives after the
multiplication is repaired — so a tool has to follow the line through two
edits, not stop at the most recent one.
