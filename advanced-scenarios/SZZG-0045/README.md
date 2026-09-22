# SZZG-0045: BIC in merge commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `branch`, `merge`, `merge-commit-bic`, `string-comparison` |
| oracle | `exact_set`; required `c3` · BFC `c4` |
| graph features | 2 branches; merge commit `c3` |
<!-- /szzbench:header -->

## Purpose

The merge commit itself introduces the bug: while merging the feature branch into
`main`, `c3` rewrites `"admin".equals(role)` as `role == "admin"`. Java compares
the two strings by identity, which is true for the interned literal a unit test
would pass and false for any role that arrives from input. A later ordinary
commit restores `equals`. The point is the shape — a two-parent commit that is
the BIC — and a tool that skips merge commits when walking back, or that blames
only first parents, cannot name it.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 99fe061  2024-12-30  Compare roles by value again                              <- BFC (c4)
*   2d9b563  2024-12-25  Merge the feature branch and compare roles by identity  <- BIC (c3, merge of c2 and c1)
|\
| * 03b5120  2024-12-13  Add the role reporter                                   (c1, feature; RoleReporter.java)
* | d93e3be  2024-12-20  Add a release note on main                              (c2; docs/main-note.md)
|/
* 59c07d4  2024-12-10  Add the role check                                        (c0; RoleCheck.java with equals)
```

## Expected BIC / BFC

- BIC: `c3` (`exact_set`, `required: [c3]`) — the merge commit
- BFC: `c4`

## Measured behaviour and blame

| commit | `isAdmin(new String("admin"))` | `isAdmin("admin")` | `isAdmin("user")` |
|---|---|---|---|
| `c0`, `c1`, `c2` | true | true | false |
| `c3` | **false** | true | false |
| `c4` | true | true | false |

The literal case stays true throughout: identity comparison of interned literals
happens to work, which is how such a change passes review. `c4` deletes one line
(`return role == "admin";`, line 5); blame at `c4^` returns `c3`, the merge
(verifier `GI703`). Neither parent of `c3` contains the identity comparison.

## What a tool must do

Report `c3`, a two-parent commit. A tool that excludes merges from the candidate
set, or diffs a merge only against its first parent and finds "no change" there
for this file, has nothing to report — the change exists only in the merge
commit's own diff against both parents.
