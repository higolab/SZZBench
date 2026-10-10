# SZZ-0088: Class body reformat after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `formatting-noise`, `blame-reaches-bic` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

An intermediate commit reformats the class body without changing behaviour,
and without touching the faulty line. The fix therefore does not have to undo
the reformat. The scenario is an honest control: it measures whether a tool
reports the formatting commit merely because it is the last commit that
touched the file.

It stays distinct from SZZ-0081 and SZZ-0083, where the formatting commit
rewrites the faulty line itself.

## Commit structure

- `c0`: Adds `Scenario0088` with a `label` field, a constructor and an
  accessor whose bodies are written on one line, plus
  `check(int value, int min, int max)` with the inclusive test
  `return value >= min && value <= max;`.
- `c1`: Changes the test to `return value > min && value < max;`, so both
  bounds are now excluded. This is the BIC.
- `c2`: Expands the single-line bodies of the constructor and of `label()` to
  the project's brace style. The change is whitespace-only: the token
  sequence of the file is identical before and after (62 tokens either way),
  and `check` is not touched.
- `c3`: Restores `>=` and `<=` on the faulty line and keeps the new layout.
  This is the BFC.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor for tools that suspect the last commit that touched the file.

## Plain blame outcome

Measured on the generated repository: `git diff -U0 c3^ c3` deletes exactly
one line, `        return value > min && value < max;` (line 15 of
`src/main/java/example/Scenario0088.java`). `git blame` at `c3^` on that line
returns **`c1`**: **exact**.

## What a tool must do

Plain line-based blame already answers correctly. To pass, a tool must *not*
add `c2`. A formatting filter is not required here; what is required is that
the tool does not widen the fix beyond the lines it changed.
`false_positives_allowed` is empty, so returning `{c1, c2}` fails.

## Note on the reformat

Before this repair, `c2` changed `public class` to `public final class`,
which is a semantic modifier and not a reformat (issue #5), and the BFC
removed it again. `c2` is now a genuine behaviour-preserving reformat.
