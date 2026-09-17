# SZZ-0095: Generic type change after BIC

## Purpose

This scenario is an honest **control** for language-specific noise: between the
BIC and the BFC a commit narrows a generic type argument (and the loop variable
that depends on it) in the same file, without touching the faulty statement.

## Commit structure

- `c0`: Adds `TagIndex` with `acceptsMore(int)` (`currentCount < MAX_TAGS`, with
  `MAX_TAGS == 8`) and `join(List<Object>)`.
- `c1`: Rewrites the check as `currentCount + 1 < MAX_TAGS`, so the eighth tag is
  rejected. This is the BIC.
- `c2`: Changes `join(List<Object>)` to `join(List<String>)` and the loop
  variable from `Object tag` to `String tag`. Two lines in `join`, none of them
  in `acceptsMore`.
- `c3`: Restores `currentCount < MAX_TAGS`. This is the BFC. Its first-parent
  diff is `+1 -1` on a single line; the narrowed generic type stays.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (`return currentCount + 1 < MAX_TAGS;`).
`git blame` at `c3^` on that line returns **`c1`**: **exact**. The generator's
verification reports `I700` (basic blame reaches the expected BIC).

## What a tool must do

To pass, a tool only has to blame the deleted line. It must not add `c2` to the
candidate set because `c2` is the most recent change to the file, and it must not
follow the line history back to `c0`, which wrote the correct check.

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`; only
  `java.util.List` is imported, so no snapshot needs an external library.
- Behaviour probe over 14 edge values for `acceptsMore` (`Integer.MIN_VALUE`,
  `Integer.MIN_VALUE + 1`, `-1`, `0`, `1`, `5`…`9`, `100`, `Integer.MAX_VALUE - 2`,
  `Integer.MAX_VALUE - 1`, `Integer.MAX_VALUE`), every value in `[-20, 20]`, and
  six tag lists for `join` (empty, single, two, a list with an empty element,
  three elements) passed through a raw `List` so that the same probe compiles
  against both parameter types — 61 outputs in total. The `c1` snapshot differs
  from `c0` at `currentCount == 7` (the eighth tag is refused) and at
  `Integer.MAX_VALUE`, where `currentCount + 1` overflows and wrongly reports
  free capacity; the `c3` snapshot agrees with `c0` on every probed input.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `generic-type-after-bic`
- `plain-blame-control`
