# SZZ-0089: Import addition after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `import-addition-after-bic`, `line-number-shift`, `blame-reaches-bic` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

An intermediate commit adds an import to the file that contains the fault.
Every line below the import shifts down by two, including the faulty line,
but the faulty line itself is not rewritten. The import is *not* removed by
the fix. The scenario is an honest control: it measures whether a tool tracks
line *content* rather than line *numbers*, and whether it reports the import
commit merely because it touched the same file last.

## Commit structure

- `c0`: Adds `Scenario0089` with `check(int value, int min, int max)` using
  the inclusive test `return value >= min && value <= max;` and
  `describe(String label)` returning `label == null ? "range" : label`.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Adds `import java.util.Objects;` and rewrites `describe` to
  `return Objects.requireNonNullElse(label, "range");`. This is
  behaviour-preserving and does not touch `check`. The faulty line moves from
  line 5 to line 7.
- `c3`: Restores `>=` and `<=` on the faulty line and keeps the import. This
  is the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor: it is the last commit that touched the file, and it shifted the
faulty line.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 7 of
`src/main/java/example/Scenario0089.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly, because blame follows the
line through the shift. A tool that maps the fix hunk back by line number
instead of by blame lands on a `describe` line owned by `c2` and fails.
`false_positives_allowed` is empty, so returning `{c1, c2}` fails.
