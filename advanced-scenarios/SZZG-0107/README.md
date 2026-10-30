# SZZG-0107: BFC includes generated files

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `generated-files`, `boolean-negation` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | operation `write_generated_text_file` |
<!-- /szzbench:header -->

## Purpose

`Retention.shouldKeep` keeps an entry while it is pinned or not yet expired.
`c1` "simplifies" the rule and drops the negation, so expired entries are kept
and unexpired ones discarded. The fix `c2` restores the negation and, in the
same commit, regenerates a five-line retention table under `build/generated/`.
The fix's diff therefore mixes one source line with generated noise.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 3 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* e4ba907  2023-06-22  Keep unexpired entries again and regenerate the retention table  <- BFC (c2; Retention.java + build/generated/retention-table.txt)
* 34814db  2023-06-20  Simplify the retention rule                                      <- BIC (c1)
* 90e7b09  2023-06-15  Add the retention rule                                           (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c2`

## Measured behaviour and blame

| commit | `shouldKeep(false, false)` | `shouldKeep(false, true)` | `shouldKeep(true, true)` |
|---|---|---|---|
| `c0` | true | false | true |
| `c1` | **false** | **true** | true |
| `c2` | true | false | true |

`c2` deletes one line (`return pinned || expired;`, line 5) and adds a five-line
generated file; blame at `c2^` returns `c1` (verifier `GI703`).

## What a tool must do

Report `c1`; the generated file has no deleted lines and no history, so it
contributes nothing to blame, but a tool that scores every file in the fix or
that weights commits by size has to ignore it.
