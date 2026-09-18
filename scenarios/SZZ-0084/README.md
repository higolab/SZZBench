# SZZ-0084: Whitespace-only rewrite after BIC with preserved line

## Purpose

A whitespace-only reformat lands between the bug-introducing and the
bug-fixing commit, but it leaves the faulty line byte-identical. The scenario
is the *preserved-line* counterpart of SZZ-0081 and SZZ-0083, in which the
same kind of whitespace rewrite does touch the faulty line and therefore
hides the BIC from plain blame. Here nothing hides the BIC, so the scenario
is an honest control: it measures whether a tool reports the reformatting
commit even when blame does not point at it.

## Commit structure

- `c0`: Adds `Scenario0084.check(int value, int min, int max)` with the
  inclusive test `return value >= min && value <= max;`.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Whitespace-only reformat: the class header and the method signature
  move to Allman brace style and the parameter list is wrapped over three
  lines. The token sequence is unchanged, and the faulty `return` line is
  left exactly as it was.
- `c3`: Restores `>=` and `<=` on that one line and keeps the new formatting.
  This is the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor: it is the most recent commit that touched the surrounding lines,
so tools that widen the fix hunk with context lines can reach it.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 10 of
`src/main/java/example/Scenario0084.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly. To pass, a tool must *not*
add `c2`: it must not extend the blame region to the reformatted context
lines, and it must not treat "the most recent commit in this method" as a
candidate. `false_positives_allowed` is empty, so returning `{c1, c2}` fails.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `whitespace-preserved-after-bic`
- `blame-reaches-bic`
- `matched-control`
