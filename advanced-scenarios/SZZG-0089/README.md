# SZZG-0089: Revert of revert with conflict resolution

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `revert`, `revert-of-revert`, `conflict-resolution`, `intermediate-change`, `variable-rename`, `revert-footer`, `origin-vs-direct` |
| oracle | default: `exact_set`; required `c3`; related origins `c1`; related but not correct `c2`, `c4` · `origin-aware`: `relaxed_with_related`; required `c3`; acceptable `c1` (credit 0.5); related but not correct `c2`, `c4` · BFC `c5` |
| defeats | `blame`, `shape` |
| graph features | revert `c3`, `c5`; 2 BICs; 2 fault sites; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

The bug-fixing commit is a real `git revert` of the bug-introducing commit, and
the bug-introducing commit is itself a real `git revert` of an earlier fix. The
second revert does not apply cleanly: an intervening commit renamed the two
variables on exactly the lines being reverted, so the BFC is the revert plus a
hand-made conflict resolution. A tool has to see through two `Revert "…"`
subjects, two `This reverts commit …` footers and a conflict-resolved diff to
name the commit that reintroduced the fault.

Until 2026-09-22 the two reverts were prose subjects with hand-written
operations and the "conflict" of the title never happened (issue #22). Both are
now produced by `git revert`, and the conflict is real.

## Commit history

```text
c0: create initial correct implementation
c1: introduce boundary bug
c2: fix boundary bug
c3: git revert of c2, reintroducing the boundary bug
c4: rename the bound checks on the reverted lines and add a description
c5: git revert of c3, conflicting with c4 and resolved by hand
```

| Commit | Role | Subject | Body |
|---|---|---|---|
| `c0` | `initial` | Add the range check helpers | |
| `c1` | `origin_bug_introducing` | Make both helpers strict | |
| `c2` | `bug_fixing` | Accept both bounds again | |
| `c3` | `bug_introducing` | Revert "Accept both bounds again" | `This reverts commit <hash of c2>.` |
| `c4` | `intermediate` | Name the bound checks after what they check and add a description | |
| `c5` | `bug_fixing` | Revert "Revert "Accept both bounds again"" | `This reverts commit <hash of c3>.` |

`c3` carries no operations: the generator runs `git revert --no-commit` on `c2`
and the diff is exactly `c2` undone (`>=` → `>`, `<=` → `<`). `c4` rewrites
`aboveMin` / `belowMax` into `lowerOk` / `upperOk` on those same two lines and
adds `description()`. `git revert` of `c3` on top of `c4` therefore conflicts
in `Range.java`; `c5`'s `resolution:` supplies the file with `c4`'s names, the
inclusive bounds restored and the description changed to `"inclusive range"`.

## Expected BIC / BFC

- BIC: `c3` (`exact_set`, `required: [c3]`); `c1` is the origin (`related_origins`), `c2` and `c4` are
  `related_but_not_correct`
- BFC: `c5`
- `origin-aware` variant: `relaxed_with_related`, `c1` accepted with credit 0.5

The direct BIC is `c3` even though the BFC is a revert-of-revert of it: in the
history observed from `c5`, `c3` is the commit that made the bounds exclusive
again (`decisions/origin-direct-contract.md`, D6).

## Measured behaviour and blame

`Range.contains(0, 0, 10)`, `contains(5, 0, 10)`, `contains(10, 0, 10)` at each
commit (`tests/test_revert_scenarios.py`):

| commit | result |
|---|---|
| `c0` | true true true |
| `c1` | **false** true **false** |
| `c2` | true true true |
| `c3` | **false** true **false** |
| `c4` | **false** true **false** |
| `c5` | true true true |

`c5` deletes the two lines `boolean lowerOk = value > min;` and
`boolean upperOk = value < max;`; `git blame` at `c5^` attributes both to
**`c4`**, the rename, which is `related_but_not_correct`. The declared fault
statements (`boolean aboveMin = value > min;`, `boolean belowMax = value < max;`)
are no longer present at `c5^` because `c4` renamed them, so the verifier
reports `GI701` (fault line rewritten, declared by the `variable-rename`
factor) rather than a blame result.

## What a tool must do

Report exactly `{c3}`. Blame on what the fix deletes answers `c4`; following
the `This reverts commit` footer of `c5` answers `c3` directly, and following
`c3`'s own footer one step further reaches `c2` (the earlier fix, not the
answer) and then `c1` (the origin, accepted only under `origin-aware`). A
tool that treats a revert-of-revert as "restoring `c2`" and reports `c2` is
wrong: `c2` fixed the bug, it did not introduce it.

## Difference from existing revert scenarios

SZZG-0084 is a *partial* revert as the reintroduction with a hand-written
revert diff; SZZG-0086 and SZZG-0090 reintroduce by prose commits; SZZG-0126
and SZZG-0127 are real reverts without an intervening change on the reverted
lines. This scenario is the only double revert, and the only revert that
conflicts and needs a resolution.
