# SZZG-0024: Clone diverges before rebase

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `branch`, `rebase`, `copy-propagation`, `clone-divergence`, `direct-bic`, `origin-bic`, `wrong-operator` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`; related but not correct `r2`, `f2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5); related but not correct `r2`, `f2` · BFC `c4` |
| graph features | 2 branches; rebase `r1`, `r2`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

A cloned implementation is written on a feature branch, annotated there, and
replayed onto `main` by rebase. `Rate.percentOf` multiplies before it divides
(in `long`, so the product cannot overflow); the clone `RateClone.percentOfClone`
divides first (`cents / 100 * percent`), which truncates the amount to whole
hundreds before scaling — 199 cents at 10 % give 10 instead of 19. `f2`/`r2` append a comment to that line and change no
behaviour. The fixed instance is the line `r1` replayed into `main`, so `r1` is
the direct BIC (D4); `r2` is the last commit to touch the line and is what plain
blame returns (D5).

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, three distractors
on the fault file, 6 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* d0fb191  2025-01-24  Multiply before dividing in the cloned percentage helper  <- BFC (c4)
* e823b86  2025-01-20  Annotate the cloned percentage logic                      (r2, rebase_of f2; comment only)
* e6ef961  2025-01-17  Add the cloned percentage helper                          <- direct BIC (r1, rebase_of f1)
| * ad967cf  2025-01-08  Annotate the cloned percentage logic                    (f2, feature)
| * ae08f91  2025-01-03  Add the cloned percentage helper                        <- origin (f1, feature)
|/
* b88fbfb  2024-12-26  Add the percentage helper                                 (c0; Rate.java, correct)
```

## Expected BIC / BFC

- default: `required: [r1]`, `related_origins: [f1]`, `related_but_not_correct: [r2, f2]`
- `origin-aware`: `relaxed_with_related`, `f1` at 0.5, `r2`/`f2` still `related_but_not_correct`
- BFC: `c4`

## Measured behaviour and blame

| commit | `Rate.percentOf(199, 10)` | `RateClone.percentOfClone(199, 10)` | `percentOfClone(30000000, 100)` |
|---|---|---|---|
| `c0` | 19 | — | — |
| `f1`, `f2`, `r1`, `r2` | 19 | **10** | 30000000 |
| `c4` | 19 | 19 | 30000000 |

The large input shows that neither the original nor the fixed clone overflows
(both multiply in `long` before dividing; PR #62 review) — the faulty clone
happens to be right there because 30000000 is a multiple of 100.

The annotation commits change nothing: of 1152 reflective probe answers over
`Rate` and `RateClone` (every public method over a grid of inputs), 0 move
across `r2` and 0 across `f2`, while 624 move across the fix `c4`. `c4` deletes one
line (`return cents / 100 * percent; // cloned logic`, line 6) and writes
`return (int) ((long) cents * percent / 100); // cloned logic, reviewed`; blame
at `c4^` returns **`r2`**, and `-w` does too (the comment is not whitespace). The
verifier reports `GW703` by design, as it did before the rewrite.

## What a tool must do

Report `r1`, not `r2`. The last textual touch of the line appended a comment;
the commit that put the faulty arithmetic into `main` is one step further back,
and it is the replay `r1`, not its feature-branch source `f1`.
