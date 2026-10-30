# SZZG-0065: Rebase conflict resolution introduces bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `rebase`, `rebase-conflict-resolution`, `conflict-resolution-bic`, `fault-in-neither-parent` |
| oracle | `exact_set`; required `r1` · BFC `c2` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 branches; rebase `r1`; cherry-pick `r1` |
<!-- /szzbench:header -->

## Purpose

Evaluate a bug that is created by the **manual resolution of a rebase
conflict**. The fault exists in none of the commits that were merged: it is
written by the developer while resolving the conflict, so the resolved commit
is the only bug-introducing commit.

## Commit graph

```text
        feature
           |
c0 ─────── f1                 f1: extract the comparison into a helper
 │
 └── m1 ── r1 ── c2           main
                              m1: guard + low-to-high comparison (same line as f1)
                              r1: replay of f1 onto m1, conflicted, resolved by hand
```

`r1` is an ordinary single-parent commit (`git rev-list --parents`):
`r1 <- m1 <- c0` and `f1 <- c0`. A rebase does not create a merge commit.

Refs after generation (`git for-each-ref`):

```text
refs/heads/feature -> f1
refs/heads/main    -> c2
```

## Commit table

| Commit | Branch | Parents | Role | Subject |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Add the Range class with an inclusive contains check |
| `m1` | `main` | c0 | `intermediate` | Reject inverted bounds and read the comparison from low to high |
| `f1` | `feature` | c0 | `intermediate` | Extract the bounds comparison into a helper method |
| `r1` | `main` | m1 | `bug_introducing` | Combine the inverted-bounds guard with the extracted bounds helper |
| `c2` | `main` | r1 | `bug_fixing` | Restore the inclusive comparison inside Range.withinBounds |

## The conflict is real

`m1` and `f1` both rewrite the line `return value >= min && value <= max;` of
`src/main/java/example/Range.java`:

* `m1` turns it into a `min > max` guard plus `return min <= value && value <= max;`
* `f1` turns it into `return withinBounds(value, min, max);` plus a new private
  helper that holds the inclusive comparison.

`r1` declares `cherry_pick_of: f1` and has **no operations**, so the generator
runs `git cherry-pick --no-commit <f1>` on top of `m1`. Git reports a content
conflict and the scenario's `resolution:` block supplies the resolved file.
Evidence from the generated repository:

* `metadata/generation.log`:
  `Cherry-pick of 'f1' for commit r1 reported conflicts in ['src/main/java/example/Range.java']; applying resolution`
* `metadata/commit-map.json`, entry `r1`:
  `"resolved_conflicts": ["src/main/java/example/Range.java"]`
* `git show --stat r1`: 5 insertions, 1 deletion in `Range.java`.

The resolution keeps `m1`'s guard and `f1`'s helper but writes the helper body
as `return value > min && value < max;` — the fault.

Counted with `git show <commit>:src/main/java/example/Range.java | grep -c`,
the faulty statement occurs **0 times at `c0`, `m1` and `f1`, and once at `r1`**.

## Expected SZZ result

```text
Expected BIC(s): r1
```

There is no origin BIC: `f1` is not a bug-introducing commit, so no commit of
the feature branch belongs in the answer. A tool that follows the
`rebase_of` / `cherry_pick_of` link to `f1` is wrong.

## Measured blame at `c2^`

`c2` deletes exactly one line:

```text
-    return value > min && value < max;
```

`git blame <c2^> -- src/main/java/example/Range.java` attributes that line to
**`r1`** (`d35d875…`); `git blame -w` gives the same answer. The lines of the
guard are attributed to `m1`, the helper signature and the delegating call to
`r1`. The generator's verifier reports `GI703`.

## Measured behaviour

Snapshots `c0` (initial), `r1` (BIC) and `c2` (BFC) were compiled with
`javac 25` and the public method `Range.contains(int, int, int)` was executed
over the full grid of all 9³ = 729 combinations of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`:

* `c0` vs `r1`: **81 of 729 inputs differ** (every input with `value == min`
  or `value == max` inside a valid range).
* `c0` vs `c2`: **identical on all 729 inputs** — the guard added by `m1` and
  the helper extracted by `f1` are behaviour preserving, so the fixed snapshot
  agrees with the initial one everywhere.

`withinBounds` is private and is exercised through `contains`. All 5 commit
snapshots compile with `javac` without errors.

## What a tool must do to pass

1. Return exactly `{r1}`.
2. Not return `f1` or `m1`: neither ever contained the faulty statement, even
   though `r1` is derived from `f1` and sits on top of `m1`.
3. Tools that special-case conflict resolutions must still keep `r1` in the
   answer — the conflict resolution *is* the bug-introducing change here.

## Notes

- `r1` declares `rebase_of` (the rewrite relation) and `cherry_pick_of` (the
  mechanism: a rebase replays a commit by cherry-picking it onto the new base).
- `validate-graph --simulate` does not model cherry-picks or `resolution`, so
  `r1` carries `allow_empty: true` for the in-memory simulation. In the
  generated repository `r1` is a normal, non-empty commit; the BFC is written
  as a whole-file `write_file` so that the simulated state and the generated
  state agree.
