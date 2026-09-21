# SZZG-0067: Rebase conflict resolution fixes bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `branch`, `rebase`, `rebase-conflict-resolution`, `conflict-resolution-bfc`, `rebased-bic` |
| oracle | default: `exact_set`; required `r1`; related origins `f1`; related but not correct `f2` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5); related but not correct `f2` · BFC `r2` |
| graph features | 2 branches; rebase `r1`, `r2`; 2 BICs; origin faults; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ can handle a bug-fixing commit that is itself a rebase
conflict-resolution commit. The fix never existed on the feature branch; it
appears only in the commit that resolves the conflict during the rebase.

## Commit history

```text
c0 (main)    : Add Range.contains with inclusive bounds
m1 (main)    : Add MAX_SPAN constant for range validation
f1 (feature) : Use strict comparisons in Range.contains          <- origin BIC
f2 (feature) : Add DEFAULT_MIN constant for range validation
r1 (main)    : replay of f1 onto m1                              <- direct BIC (rebase_of: f1)
r2 (main)    : replay of f2 with conflict resolution; keeps both  <- BFC (rebase_of: f2,
               constants and restores inclusive bounds              rebase_conflict_resolution)
```

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | inclusive `contains` |
| `m1` | `main` | c0 | `intermediate` | inserts `MAX_SPAN` at the top of the class |
| `f1` | `feature` | c0 | `origin_bug_introducing` | `>=`/`<=` → `>`/`<` |
| `f2` | `feature` | f1 | `intermediate` | inserts `DEFAULT_MIN` at the same position as `MAX_SPAN` |
| `r1` | `main` | m1 | `bug_introducing` | replay of f1 (applies cleanly) |
| `r2` | `main` | r1 | `bug_fixing` | replay of f2; the resolution keeps both constants and fixes the comparison |

## Why `scenario.graph.yml` is needed

Two branches, `rebase_of` metadata on the replayed commits, and an origin BIC
that is not an ancestor of the BFC.

## Conflict model

The generator does not execute a `git rebase`; it writes r2's resolved content
directly. `f2` and `m1` insert a constant at the same position of `Range.java`,
which is what conflicts during a real rebase, and r2's content is the
resolution a developer would commit (both constants plus the restored
comparison). Executing the conflict for real needs the generator's
`resolution` support (issue #17).

## Expected SZZ result

- Bug-fixing commit: `r2`
- Required BIC: `r1` (direct)
- Related but not correct: `f1` (origin of the fault), `f2` (pre-rebase source of r2)

## Plain blame outcome

`git blame` at `r2^` on the fixed line returns `r1`: the scenario is
blame-trivial for the main-line history. It becomes non-trivial only for tools
that also scan the retained `feature` branch (`git log --all`) and report `f1`,
or that treat the conflict-resolution commit itself as suspicious.

## Difference from SZZG-0058

SZZG-0058 rebases a feature bug and a feature fix that both applied cleanly.
Here the feature branch never contained the fix; it is introduced by the
conflict resolution.
