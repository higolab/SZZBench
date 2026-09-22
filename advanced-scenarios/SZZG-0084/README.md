# SZZG-0084: Partial revert reintroduces bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `linear-history`, `revert`, `partial-revert`, `reintroduced-bug`, `re-bic`, `origin-bic`, `revert-footer` |
| oracle | default: `reintroduction_direct`; required `c3`; related origins `c1` · `origin-aware`: `relaxed_with_related`; required `c3`; acceptable `c1` (credit 0.5) · BFC `c4` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | revert `c3`; 2 BICs; origin faults; policy `reintroduction_direct`; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate a **real partial revert**: a commit that carries two independent
changes is reverted with `git revert`, but only one half of the revert is
kept. The resulting commit carries the standard
`This reverts commit <hash>.` footer while its diff undoes only half of what it
claims to revert, and it is the direct BIC for the final fix.

## Commit graph

```text
c0 ── c1 ── c2 ── c3 ── c4      main (linear, no branches)
      BIC   fix   partial fix
                  revert
```

`git rev-list --parents` (each commit has exactly one parent):

```text
c4 <- c3 <- c2 <- c1 <- c0
```

Refs after generation (`git for-each-ref`): `refs/heads/main -> c4 (8cac81b)`.

## Commit table

| Commit | Parents | Role | Subject |
|---|---|---|---|
| `c0` | none | `initial` | Add the Range class with an inclusive contains check and a clamp helper |
| `c1` | c0 | `bug_introducing` | Use strict comparisons for the interval bounds |
| `c2` | c1 | `bug_fixing` | Restore the inclusive bounds and simplify clamp |
| `c3` | c2 | `bug_reintroducing` | Revert "Restore the inclusive bounds and simplify clamp" |
| `c4` | c3 | `bug_fixing` | Restore the inclusive comparison in Range.contains |

`c3` declares no `message`: the subject is the one `git revert` writes itself.

## `c2` really carries two independent changes

`git show -U0 c2` (`1 file changed, 2 insertions(+), 8 deletions(-)`):

```text
@@ -5 +5 @@                                  <- change 1: the boundary fix
-    return value > min && value < max;
+    return value >= min && value <= max;
@@ -9,7 +9 @@                                <- change 2: simplify clamp
-    if (value < min) {
-      return min;
-    }
-    if (value > max) {
-      return max;
-    }
-    return value;
+    return value < min ? min : (value > max ? max : value);
```

The second change is behaviour preserving (measured below), which is why it is
worth keeping when the first one is given up.

## `c3` is a real, partial `git revert`

`c3` declares `revert_of: c2` with `apply_revert: true`, so the generator runs
`git revert --no-commit <hash of c2>` and applies the commit's operations
afterwards. `metadata/generation.log` records

```text
Reverting c2 6fdbfd516a7a7124be0195ce139d522e6dc67ac7 without committing
```

`git log -1 --format=%B c3`:

```text
Revert "Restore the inclusive bounds and simplify clamp"

This reverts commit 6fdbfd516a7a7124be0195ce139d522e6dc67ac7.
```

but `git show c3` contains a **single hunk**:

```text
-    return value >= min && value <= max;
+    return value > min && value < max;
```

The clamp simplification of `c2` survives — the revert is partial. That is
directly visible in blame: at `c4^` the clamp line is still attributed to
`c2` (`6fdbfd51…`) while the comparison line is attributed to `c3`.

## Expected SZZ result

```text
Evaluation policy: reintroduction_direct
Expected BIC(s): c3
Related but not correct: c1
```

## Measured blame at `c4^`

`c4` deletes exactly one line:

```text
-    return value > min && value < max;
```

`git blame <c4^> -- src/main/java/example/Range.java` attributes that line to
**`c3`** (`292bd065…`), the clamp line to `c2` (`6fdbfd51…`) and everything
else to `c0`. `git blame -w` gives the same answer. The generator's verifier
reports `GI703`.

## Measured behaviour

Snapshots `c0` (initial), `c3` (reintroducing BIC) and `c4` (BFC) were compiled
with `javac 25`; every public `int`-only method was executed over the full grid
of all 9³ = 729 combinations of
`{Integer.MIN_VALUE, Integer.MIN_VALUE+1, -1000, -1, 0, 1, 1000, Integer.MAX_VALUE-1, Integer.MAX_VALUE}`:

| method | `c0` vs `c3` | `c0` vs `c4` |
|---|---|---|
| `contains(int,int,int)` | **81 of 729 inputs differ** | **0 differ** |
| `clamp(int,int,int)` | **0 differ** | **0 differ** |

`clamp` is identical in all three snapshots although `c2` rewrote it and `c3`
kept the rewrite: the conditional expression evaluates its tests in the same
order as the original `if` chain. All 5 commit snapshots compile with `javac`
without errors.

## What a tool must do to pass

1. Return exactly `{c3}` under the `reintroduction_direct` policy.
2. Treat `c1` as related history, not as the required answer, although `c1` is
   where the same faulty statement first appeared.
3. Revert-aware tools must not conclude from the footer that the whole of `c2`
   was undone: only one of its two changes was. A tool that maps
   "`c3` reverts `c2`" to "the state before `c2`" is wrong about `clamp`.

## Notes

- `factors` was empty before this repair; it now names the shape
  (`linear_history`, `revert`, `partial_revert`, `revert_footer`) and the
  oracle situation (`reintroduced_bug`, `re_bic`, `origin_bic`).
- `validate-graph --simulate` does not model `git revert`, so the operations of
  `c3` write the whole file. The simulated state and the state Git produces are
  identical, and the resulting Git diff is the single hunk shown above.
- SZZG-0085 uses the same five-commit shape but a hand-written partial revert
  and an `evaluation_variants` oracle; this scenario is the one that exercises
  a real `git revert`.
