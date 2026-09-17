# SZZ-0091: Dead code removal after BIC

## Purpose

The intermediate commit is a pure deletion: it removes dead code that `c0`
had left behind. It adds no line, so the fix cannot possibly undo it, and it
does not touch the faulty line. The scenario is an honest control: it
measures whether a tool treats a deleting commit as a suspect on its own.

## Commit structure

- `c0`: Adds `Scenario0091` with `check(int value, int min, int max)` using
  the inclusive test `return value >= min && value <= max;`, and a private
  `isPositive(int)` helper that no caller ever reaches.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Deletes `isPositive`. This is a real removal of dead code: the helper
  is private and unused, so removing it cannot change behaviour. `check` is
  not touched.
- `c3`: Restores `>=` and `<=` on the faulty line. It does not bring the
  deleted helper back. This is the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor for tools that follow deleted lines or that suspect cleanup
commits.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 5 of
`src/main/java/example/Scenario0091.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly. To pass, a tool must *not*
add `c2`: the lines `c2` removed were written by `c0`, are unrelated to the
fault and are not part of the fix. `false_positives_allowed` is empty, so
returning `{c1, c2}` fails.

## Note on the dead code

Before this repair, `c2` removed nothing: it inserted the comment
`// dead code removed; boundary remains faulty`, which both contradicted the
title and leaked the oracle (issue #5). `c0` now contains real dead code and
`c2` really removes it.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `dead-code-removal-after-bic`
- `deletion-only-intermediate`
- `blame-reaches-bic`
