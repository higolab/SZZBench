# SZZ-0094: Annotation addition after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `annotation-after-bic`, `plain-blame-control` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario is an honest **control** for language-specific noise: between the
BIC and the BFC a commit adds a single Java annotation and nothing else. The
annotation lands four lines above the faulty statement, so it is a plausible
blame distraction, but it does not touch the faulty line.

## Commit structure

- `c0`: Adds `StockLevel` with the legacy alias `lowStock(int)` and
  `needsRestock(int)`, which returns `onHand < 5`.
- `c1`: Extracts the literal into `LOW_STOCK_THRESHOLD` and rewrites the check as
  `LOW_STOCK_THRESHOLD < onHand`, swapping the operands. This is the BIC; the
  commit adds the constant and changes the one comparison line.
- `c2`: Adds `@Deprecated` above `lowStock(int)`. This is a pure one-line
  insertion: no rename, no parameter change, no other edit.
- `c3`: Rewrites the check as `onHand < LOW_STOCK_THRESHOLD`. This is the BFC.
  Its first-parent diff is `+1 -1` on a single line; the annotation and the
  constant introduced earlier stay in place.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (`return LOW_STOCK_THRESHOLD < onHand;`).
`git blame` at `c3^` on that line returns **`c1`**: **exact**. The generator's
verification reports `I700` (basic blame reaches the expected BIC).

## What a tool must do

To pass, a tool only has to blame the deleted line. It must not widen the
candidate set to `c2` because `c2` is the most recent commit that touched the
file or the enclosing class, and it must not stop at `c0` (which introduced the
method but not the fault).

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`. The
  annotation is `java.lang.Deprecated`, so no snapshot depends on an external
  library.
- Behaviour probe over 16 edge values (`Integer.MIN_VALUE`, `Integer.MIN_VALUE + 1`,
  `-100`, `-1`, `0`…`7`, `100`, `1000`, `Integer.MAX_VALUE - 1`,
  `Integer.MAX_VALUE`) and every value in `[-50, 50]` for both `needsRestock` and
  `lowStock`: the `c1` snapshot differs from `c0` for every probed input except
  `onHand == 5` (the one value at which both comparisons are false), and the `c3`
  snapshot agrees with `c0` on all 117 probe outputs.
