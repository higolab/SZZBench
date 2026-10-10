# SZZG-0069: Rebase splits original BIC into multiple commits

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `branch`, `rebase`, `split-bic`, `multi-bic`, `origin-vs-direct`, `wrong-constant` |
| oracle | default: `exact_set`; required `r1`, `r2`; related origins `f1` · `origin-aware`: `relaxed_with_related`; required `r1`, `r2`; acceptable `f1` (credit 0.5) · BFC `c3` |
| defeats | `blame`, `shape`, `position` |
| graph features | 2 branches; rebase `r1`, `r2`; 3 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

One origin commit becomes two direct BICs. On the feature branch `f1` mistypes
both constants of the retry backoff on one line — base 100 ms written as 10, cap
30000 ms written as 3000 — while its message announces the intended values. The
rebase replays that one edit as two commits, `r1` (the base) and `r2` (the cap),
so the faulty line on `main` has two authors and the oracle requires both.
Blame of the line the fix deletes returns only `r2`, which is why this scenario
is in the discriminating tier: the first half of the answer is one step further
back in the line's history.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle, tier and coverage dimensions (`bic_depth` 2, two
distractors on the fault file, 5 commits, 2 refs) are unchanged.
The backoff expression clamps and shifts in `long` so that no snapshot — buggy
or fixed — overflows; only the two constants differ between them.

## Commit structure (generated)

```text
* 6d8f2e0  2024-06-21  Restore the backoff constants: 100 ms base, 30000 ms cap  <- BFC (c3)
* 4a55727  2024-06-19  Tune the backoff cap                                      <- BIC (r2, rebase_of f1: the cap half)
* d021e7b  2024-06-17  Tune the backoff base                                     <- BIC (r1, rebase_of f1: the base half)
| * bd9857e  2024-06-11  Tune the backoff to a 100 ms base and a 30 s cap        <- origin (f1, feature; both halves)
|/
* 6400cae  2024-06-05  Add the retry backoff                                     (c0)
```

## Expected BIC / BFC

- default: `required: [r1, r2]`, `related_origins: [f1]`
- `origin-aware`: `relaxed_with_related`, `f1` as `acceptable_related` at 0.5
- BFC: `c3`

## Measured behaviour and blame

| commit | `delayMillis(0)` | `delayMillis(10)` | `delayMillis(25)`, `(31)`, `(32)` |
|---|---|---|---|
| `c0` | 100 | 30000 | 30000 |
| `f1` | 10 | 3000 | 3000 |
| `r1` | **10** | 10240 (smaller base, still capped at 30000) | 30000 |
| `r2` | 10 | **3000** | 3000 |
| `c3` | 100 | 30000 | 30000 |

The doubling count is clamped to `[0, 30]` and shifted in `long` before the
cap, so the delay saturates at the cap for any attempt instead of wrapping
(PR #61 review: the first version overflowed at attempt 25 and shift-wrapped at
31). `c3` deletes one line (`return (int) Math.min(10L << doublings, 3000L);`,
line 7);
blame at `c3^` returns `r2` — half of the required set. Blaming the same line
at `r2^` returns `r1`.

## What a tool must do

Return both `r1` and `r2`: follow the line's history past the most recent
change (`git log -L`, or blame again at `r2^`) or read the rebase metadata
(`rebase_of: f1` on both). An answer of `r2` alone is a false negative; an
answer of `f1` names the origin, which the default oracle does not accept.
