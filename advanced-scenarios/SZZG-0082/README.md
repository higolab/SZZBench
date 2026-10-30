# SZZG-0082: Rebase with generated file update

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `generated-files`, `generated-code-noise`, `origin-vs-direct`, `boolean-negation` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`; related but not correct `r2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5); related but not correct `r2` · BFC `c3` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 branches; rebase `r1`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

A generated file is regenerated during the rebase, after the replayed BIC and
before the fix. The fault drops the negation of the kill switch from the feature
gate — `flag && !killSwitch` becomes `flag && killSwitch` — so the feature is on
exactly when it should be off. `r2` touches only `generated/feature.properties`
and is a distractor by adjacency, not by content.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, two distractors on
the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 3d3afcb  2023-09-15  Negate the kill switch in the feature gate again   <- BFC (c3)
* b8c7f43  2023-09-12  Regenerate the derived feature metadata            (r2; generated/feature.properties only)
* cb00258  2023-09-11  Honour the kill switch in the feature gate         <- BIC (r1, rebase_of f1)
| * ac680fb  2023-09-06  Honour the kill switch in the feature gate       <- origin (f1, feature)
|/
* b6ec159  2023-08-28  Add the feature gate                               (c0)
```

## Expected BIC / BFC

- default: `required: [r1]`, `related_but_not_correct: [r2]`, `related_origins: [f1]`
- `origin-aware`: `relaxed_with_related`, `f1` at 0.5
- BFC: `c3`

## Measured behaviour and blame

| commit | `isEnabled(true, false)` | `isEnabled(true, true)` | `isEnabled(false, false)` |
|---|---|---|---|
| `c0` | true | false | false |
| `f1`, `r1`, `r2` | **false** | **true** | false |
| `c3` | true | false | false |

`c3` deletes one line (`return flag && killSwitch;`, line 6); blame at `c3^`
returns `r1` (verifier `GI703`).

## What a tool must do

Report `r1`; ignore `r2`, which changed no source file. A tool that treats
"the commit before the fix" as a candidate, or that scores generated-file churn,
picks up `r2`.
