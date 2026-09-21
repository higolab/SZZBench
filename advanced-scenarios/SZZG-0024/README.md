# SZZG-0024: Clone diverges before rebase

## Purpose

A cloned implementation is written on a feature branch, annotated there, and
replayed onto `main` by rebase. `Rate.percentOf` multiplies before it divides;
the clone `RateClone.percentOfClone` divides first (`cents / 100 * percent`),
which truncates the amount to whole hundreds before scaling — 199 cents at 10 %
give 10 instead of 19. `f2`/`r2` append a comment to that line and change no
behaviour. The fixed instance is the line `r1` replayed into `main`, so `r1` is
the direct BIC (D4); `r2` is the last commit to touch the line and is what plain
blame returns (D5).

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, three distractors
on the fault file, 6 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 712b8ea  2025-01-24  Multiply before dividing in the cloned percentage helper  <- BFC (c4)
* ccfab45  2025-01-20  Annotate the cloned percentage logic                      (r2, rebase_of f2; comment only)
* 6c1503d  2025-01-17  Add the cloned percentage helper                          <- direct BIC (r1, rebase_of f1)
| * eb9f55b  2025-01-08  Annotate the cloned percentage logic                    (f2, feature)
| * b62cf25  2025-01-03  Add the cloned percentage helper                        <- origin (f1, feature)
|/
* d02e458  2024-12-26  Add the percentage helper                                 (c0; Rate.java, correct)
```

## Expected BIC / BFC

- default: `required: [r1]`, `related_origins: [f1]`, `related_but_not_correct: [r2, f2]`
- `origin-aware`: `relaxed_with_related`, `f1` at 0.5, `r2`/`f2` still `related_but_not_correct`
- BFC: `c4`

## Measured behaviour and blame

| commit | `Rate.percentOf(199, 10)` | `RateClone.percentOfClone(199, 10)` |
|---|---|---|
| `c0` | 19 | — |
| `f1`, `f2`, `r1`, `r2` | 19 | **10** |
| `c4` | 19 | 19 |

The annotation commits change nothing: of 1152 reflective probe answers over
`Rate` and `RateClone` (every public method over a grid of inputs), 0 move
across `r2` and 0 across `f2`, while 660 move across the fix `c4`. `c4` deletes one
line (`return cents / 100 * percent; // cloned logic`, line 6); blame at `c4^`
returns **`r2`**, and `-w` does too (the comment is not whitespace). The
verifier reports `GW703` by design, as it did before the rewrite.

## What a tool must do

Report `r1`, not `r2`. The last textual touch of the line appended a comment;
the commit that put the faulty arithmetic into `main` is one step further back,
and it is the replay `r1`, not its feature-branch source `f1`.

## Factors

- `branch`
- `rebase`
- `copy-propagation`
- `clone-divergence`
- `direct-bic`
- `origin-bic`
- `wrong-operator`
