# SZZ-0085: Comment insertion after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `comment-noise`, `blame-reaches-bic` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

An intermediate commit inserts a comment line directly above the faulty line.
The comment is *not* removed by the fix, so it neither shifts the faulty line
out of the BIC's blame nor appears in the fix diff. The scenario is an honest
control: it measures whether a tool reports the comment commit merely because
it is the closest neighbour of the fix.

## Commit structure

- `c0`: Adds `Scenario0085.check(int value, int min, int max)` with the
  inclusive test `return value >= min && value <= max;`.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Inserts the comment `// boundary check` above that line. Nothing else
  changes.
- `c3`: Restores `>=` and `<=` on the faulty line and keeps the comment. This
  is the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor: it owns the line immediately above the fix hunk.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 6 of
`src/main/java/example/Scenario0085.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly. To pass, a tool must *not*
add `c2`: it must not blame the context lines around the fix hunk, and it must
not treat the most recent commit in the method as a candidate.
`false_positives_allowed` is empty, so returning `{c1, c2}` fails.
