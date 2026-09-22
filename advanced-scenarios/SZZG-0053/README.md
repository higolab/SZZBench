# SZZG-0053: Release-branch-only bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `release-branch`, `branch-only-bug`, `boolean-negation` |
| oracle | `exact_set`; required `c2` · BFC `c4` |
| graph features | 2 branches |
<!-- /szzbench:header -->

## Purpose

A bug that exists only on the `release` branch: `c2` means to keep serving
administrators during maintenance and drops the negation from
`!maintenance || admin`, so outside maintenance nobody but administrators is
served. `c4` restores it on `release`; `main` never contains the fault and keeps
receiving unrelated correct commits.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* a8d91b8  2023-07-18  Serve everyone outside maintenance again on release  <- BFC (c4, release)
* 37f7f31  2023-07-03  Serve administrators during maintenance on release   <- BIC (c2, release)
| * c0b6709  2023-07-10  Add a main branch note                             (c3, main; docs/main-notes.md)
| * eb11590  2023-06-27  Record the main version                            (c1, main; docs/main-version.md)
|/
* 6a9d916  2023-06-19  Add the request gate                                 (c0)
```

## Expected BIC / BFC

- BIC: `c2` (`exact_set`, `required: [c2]`)
- BFC: `c4`

## Measured behaviour and blame

`canServe(maintenance, admin)`:

| commit | `(false, false)` | `(true, false)` | `(false, true)` | `(true, true)` |
|---|---|---|---|---|
| `c0`, `c1`, `c3` (main) | true | false | true | true |
| `c2` (release) | **false** | **true** | true | true |
| `c4` (release) | true | false | true | true |

Both administrator cases stay true, so a test that only checks administrators
passes on the faulty release. `c4` deletes one line (`return maintenance ||
admin;`, line 6); blame at `c4^` returns `c2` (verifier `GI703`).

## What a tool must do

Report `c2`. `main` offers no candidate at all; a tool that mines only the
default branch never sees this bug or its fix.
