# SZZ-0086: Logging insertion after BIC

## Purpose

An intermediate commit adds a diagnostic print statement directly above the
faulty line. The statement is *not* removed by the fix, so it neither shifts
the faulty line out of the BIC's blame nor appears in the fix diff. The
scenario is an honest control: it measures whether a tool reports the logging
commit merely because it is the closest neighbour of the fix.

## Commit structure

- `c0`: Adds `Scenario0086.check(int value, int min, int max)` with the
  inclusive test `return value >= min && value <= max;`.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Inserts
  `System.out.println("check " + value + " in [" + min + ", " + max + "]");`
  above that line. Nothing else changes.
- `c3`: Restores `>=` and `<=` on the faulty line and keeps the print
  statement. This is the BFC.

## Behaviour contract after the fix

The fix restores the *return value* of `check`, not the absence of logging.
From `c2` onwards `check` prints one diagnostic line per call; that side
effect is intentional and outlives the fix. `check` returns the same boolean
as in `c0` for every input.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor: it owns the line immediately above the fix hunk.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 6 of
`src/main/java/example/Scenario0086.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly. To pass, a tool must *not*
add `c2`: it must not blame the context lines around the fix hunk, and it must
not treat the most recent commit in the method as a candidate.
`false_positives_allowed` is empty, so returning `{c1, c2}` fails.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `logging-insertion-after-bic`
- `blame-reaches-bic`
