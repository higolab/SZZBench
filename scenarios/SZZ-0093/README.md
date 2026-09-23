# SZZ-0093: If-else to guard clause after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `guard-clause-after-bic`, `plain-blame-control` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario is the honest **control** of the refactoring-after-BIC family: an
intermediate commit converts the if-else of the faulty method into a guard
clause, but it does not touch the faulty condition line. Plain blame therefore
still reaches the BIC, and the scenario measures whether a tool is distracted by
a structural change *around* the fault.

## Commit structure

- `c0`: Adds `DiscountCalculator` with `discountCents(int)` (an if-else over the
  minimum order value) and `payableCents(int)`.
- `c1`: Changes the guard from `orderTotalCents < MIN_ORDER_CENTS` to
  `orderTotalCents <= MIN_ORDER_CENTS`, so an order that exactly meets the
  minimum loses its discount. This is the BIC.
- `c2`: Converts the if-else into a guard clause: the `} else {` line and the
  else block's closing brace disappear and the discount expression is
  re-indented. The faulty condition line is left byte identical.
- `c3`: Changes the guard back to `orderTotalCents < MIN_ORDER_CENTS`. This is
  the BFC. Its first-parent diff is `+1 -1` on a single line.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (`if (orderTotalCents <= MIN_ORDER_CENTS) {`).
`git blame` at `c3^` on that line returns **`c1`**: **exact**. The generator's
verification reports `I700` (basic blame reaches the expected BIC).

## What a tool must do

To pass, a tool only has to blame the deleted line and stop there. It must *not*
extend the candidate set to `c2` because `c2` rewrote the enclosing if-else, and
it must not follow the line history further back to `c0`.

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`.
- Behaviour probe over 18 edge values (`Integer.MIN_VALUE`, `Integer.MIN_VALUE + 1`,
  `-100000`, `-5000`, `-1`, `0`, `1`, `4998`…`5002`, `9999`, `10000`, `21474836`,
  `21474837`, `Integer.MAX_VALUE - 1`, `Integer.MAX_VALUE`; the two values around
  21474836 and the two maxima used to exercise an `orderTotalCents * DISCOUNT_PERCENT`
  overflow that `c0` and `c3` shared — the product is taken in 64 bits since
  2026-09-23, so the discount is exact for every `int` order total and those
  probes now check that), every value in `[4900, 5100]`, and a sweep
  of `[-20000, 200000]` in steps of 137 — 1825 outputs in total. The `c1`
  snapshot differs from `c0` at `orderTotalCents == 5000`; the `c3` snapshot
  agrees with `c0` on every probed input.
