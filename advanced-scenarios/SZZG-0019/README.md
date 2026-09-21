# SZZG-0019: Bug propagates into generated code

## Purpose

The fault enters through generated code. The template `templates/Limits.tpl`
carries `return 30;` where the generated method's contract says at most 3
retries; `c1` regenerates `GeneratedLimits.java` from it and thereby writes the
fault into the file the fix later repairs. The direct BIC is the regeneration
commit; the template commit is the origin — and the template is not fixed, so
the next regeneration would bring the fault back.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 3 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* 672e8a4  2024-10-28  Retry at most 3 times in the generated limits     <- BFC (c2; GeneratedLimits.java only)
* 3d68ed9  2024-10-21  Regenerate the limits code from the template      <- direct BIC (c1)
* 02b3ed1  2024-10-17  Add the limits code template                      <- origin (c0; templates/Limits.tpl)
```

## Expected BIC / BFC

- default: `required: [c1]`, `related_origins: [c0]`
- `origin-aware`: `relaxed_with_related`, `c0` at 0.5
- BFC: `c2`

## Measured behaviour and blame

`GeneratedLimits.maxRetries()` is **30** at `c1` and 3 at `c2` (the class does
not exist at `c0`). `c2` deletes one line (`return 30;`, line 6); blame at
`c2^` returns `c1` (verifier `GI703`).

## What a tool must do

Report `c1`, the commit that wrote the fault into the fixed file. A tool that
knows `files[].generated_from` may add the template commit `c0` as context; the
default oracle counts it as a false positive, the origin-aware variant tolerates
it.

## Factors

- `single-bic`
- `single-bfc`
- `copy-propagation`
- `generated-file`
- `wrong-constant`
