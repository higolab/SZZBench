# SZZ-0090: Guard clause addition after BIC

## Purpose

An intermediate commit adds an early-return guard directly above the faulty
line. The guard is semantically redundant: when `min > max` the conjunction
that follows is already false for every value. It therefore makes `c2` a
*blame candidate* without making it a cause of the fault, which is exactly
the distinction the oracle has to draw. The guard is kept by the fix, so the
fix diff touches only the faulty line.

## Commit structure

- `c0`: Adds `Scenario0090.check(int value, int min, int max)` with the
  inclusive test `return value >= min && value <= max;`.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Inserts `if (min > max) { return false; }` above that line.
  Behaviour-neutral: over a probe of 2197 `(value, min, max)` triples, `c2`
  returns the same value as `c1` for every triple.
- `c3`: Restores `>=` and `<=` on the faulty line and keeps the guard. This
  is the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor, not a BIC: its guard cannot make `check` wrong for any input, so
by fault causality it stays out of the required set.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 8 of
`src/main/java/example/Scenario0090.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly. To pass, a tool must *not*
add `c2`: it must not blame the guard lines that sit immediately above the
fix hunk. `false_positives_allowed` is empty, so returning `{c1, c2}` fails.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `guard-clause-after-bic`
- `redundant-guard`
- `blame-reaches-bic`
