# SZZ-0087: Unrelated method addition after BIC

## Purpose

An intermediate commit adds a second, unrelated method to the class that
contains the fault. The method is *not* removed by the fix, so the fix diff
touches only the faulty line. The scenario is an honest control: it measures
whether a tool reports the feature commit merely because it is the most
recent change to the same file or class.

## Commit structure

- `c0`: Adds `Scenario0087.check(int value, int min, int max)` with the
  inclusive test `return value >= min && value <= max;`.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Adds `public int width(int min, int max)` below `check`. `check` is
  not touched.
- `c3`: Restores `>=` and `<=` on the faulty line and keeps `width`. This is
  the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor for tools that work at file or class granularity.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 5 of
`src/main/java/example/Scenario0087.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly. To pass, a tool must map
the fix to the lines it actually changed and must *not* add `c2`, which only
appended a new method elsewhere in the file. `false_positives_allowed` is
empty, so returning `{c1, c2}` fails.

## Note on the Java

Before this repair, the `c2` snapshot declared `width` inside the body of
`check` and repeated it after the class, so `javac` rejected it with "illegal
start of expression" (issue #10). All four snapshots now compile with
`javac 25`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `unrelated-method-after-bic`
- `blame-reaches-bic`
