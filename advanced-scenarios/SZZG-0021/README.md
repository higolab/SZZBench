# SZZG-0021: Clone removal as fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `copy-propagation`, `boolean-negation` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | operation `delete_file` |
<!-- /szzbench:header -->

## Purpose

`Access.canView` serves a document when it is public or the viewer is a member.
`c1` adds a second copy, `AccessCopy`, whose visibility flag is negated
(`!isPublic || member`): private documents become viewable by everyone and
public ones only by members. The fix `c2` does not edit the copy — it deletes
the file and points callers at the original. The bug-fixing commit therefore
removes the file the fault lived in, and its diff deletes every line of it.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, no distractor on
the fault file, 3 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* ce2a4e3  2023-08-21  Remove AccessCopy and point callers at Access   <- BFC (c2; delete_file + docs/clone-removal.md)
* e365061  2023-08-14  Add a second access check in AccessCopy         <- BIC (c1)
* 4f088a3  2023-08-07  Add the access check                            (c0; Access.java, correct)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c2` (`fix_type: file_deletion`)

## Measured behaviour and blame

| commit | `Access.canView(true, false)` / `(false, false)` | `AccessCopy.canView(true, false)` / `(false, false)` |
|---|---|---|
| `c0` | true / false | — |
| `c1` | true / false | **false / true** — the inverse |
| `c2` | true / false | class removed |

`c2`'s diff deletes all eight lines of `AccessCopy.java` (and adds a note);
every deleted line blames to `c1` (verifier `GI661` for the deletion, `GI703`
for blame).

## What a tool must do

Report `c1`. A tool that only follows modified lines has nothing to follow;
one that blames deleted lines of a deleted file gets the answer at once.
