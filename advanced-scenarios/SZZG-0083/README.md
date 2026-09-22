# SZZG-0083: Huge noisy rebased commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `large-noisy-commit`, `generated-file`, `multi-file`, `robustness`, `direct-bic`, `origin-bic`, `wrong-variable` |
| oracle | default: `exact_set`; required `r1`; related origins `f1` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5) · BFC `c2` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches; rebase `r1`; operation `write_generated_text_file`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

The rebased bug-introducing commit changes one line of application code and,
in the same commit, regenerates a machine-written status code table — a
5006-line Java class and a 2000-line properties file. The one relevant line is
a ternary whose branches were swapped: `describe` now returns the fallback when
a phrase exists and `null` when it does not. The size burdens tools that read
whole patches or scan the repository; deleted-line blame is unaffected.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, two distractors on
the fault file, 4 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 19c847b  2024-01-09  Return the phrase when it exists and the fallback when it does not   <- BFC (c2)
* d4dc7a0  2024-01-02  Regenerate the status code table and tidy the reason lookup          <- BIC (r1, rebase_of f1; ~7000 lines)
| * 5829f9f  2024-01-02  Regenerate the status code table and tidy the reason lookup        <- origin (f1, feature)
|/
* 878d8fd  2024-01-01  Add the status text helper                                           (c0)
```

## Expected BIC / BFC

- default: `required: [r1]`, `related_origins: [f1]`
- `origin-aware`: `relaxed_with_related`, `f1` at 0.5
- BFC: `c2`

## Measured behaviour and blame

| commit | `describe("OK", "Unknown")` | `describe(null, "Unknown")` |
|---|---|---|
| `c0` | `OK` | `Unknown` |
| `f1`, `r1` | **`Unknown`** | **`null`** |
| `c2` | `OK` | `Unknown` |

`c2` deletes one line (`return phrase != null ? fallback : phrase;`, line 6 of
`StatusText.java`); blame at `c2^` returns `r1` (verifier `GI703`). The
generated files are never touched by the fix.

## What a tool must do

Report `r1`, within time and memory limits, on a commit whose patch is about
7000 lines. The fix deletes exactly one line, so line-level blame is cheap; a
tool that feeds whole patches to a classifier or a model pays for the table.
