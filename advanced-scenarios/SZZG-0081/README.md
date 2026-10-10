# SZZG-0081: Rebase with formatting rewrite noise

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `branch`, `rebase`, `formatting-noise`, `whitespace-only-change`, `blame-stops-at-formatting`, `direct-bic`, `origin-bic`, `null-check-omission` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`; related but not correct `r2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5); related but not correct `r2` · BFC `c3` |
| defeats | `blame`, `shape` |
| graph features | 2 branches; rebase `r1`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

A whitespace-only reformatting commit sits between the rebased bug-introducing
commit and the fix and rewrites the faulty line itself. `Label.text` loses its
null guard on the feature branch (`f1`), the change is rebased onto `main`
(`r1`), the project formatter re-indents the whole file from two to four spaces
(`r2`), and the fix restores the guard (`c3`). Plain `git blame` at the fix
stops at `r2`; `git blame -w` reaches `r1`.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 2, three distractors
on the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* b66373f  2024-01-11  Guard the label name against null again                        <- BFC (c3)
* e6f4f03  2024-01-05  Apply the four-space indentation of the project formatter      (r2, formatting; rewrites every line)
* f10638e  2024-01-02  Trim the label name directly                                   <- BIC (r1, rebase_of f1)
| * 95fefe5  2024-01-02  Trim the label name directly                                 <- origin (f1, feature)
|/
* 08497c4  2024-01-01  Add the label helper                                           (c0)
```

## Expected BIC / BFC

- default: `required: [r1]`, `related_but_not_correct: [r2]`, `related_origins: [f1]`
- `origin-aware`: `relaxed_with_related`, `f1` at 0.5, `r2` still `related_but_not_correct`
- BFC: `c3`

## Measured behaviour and blame

| commit | `text(" x ")` | `text(null)` |
|---|---|---|
| `c0` | `x` | `""` |
| `f1`, `r1`, `r2` | `x` | **throws `NullPointerException`** |
| `c3` | `x` | `""` |

`r2` is token-identical to `r1`'s tree: only leading whitespace changes.
`c3` deletes one line (`return name.trim();`, line 5); plain blame at `c3^`
returns **`r2`**, `git blame -w` returns `r1`. The verifier therefore reports
`GW703` for this scenario by design — the warning is the scenario.

## What a tool must do

Report `r1`. Ignore whitespace when attributing the line (`git blame -w`,
`--ignore-rev` for the formatter commit, or a token-level comparison); a tool
that takes plain blame's answer reports a reformatting.
