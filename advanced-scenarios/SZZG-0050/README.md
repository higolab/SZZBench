# SZZG-0050: Backport fix

## Purpose

`Greeting.forName` trims the name after a null guard; `c1` "trims the name
directly" and drops the guard, so a missing name throws
`NullPointerException`. A release branch is cut from the buggy state and
receives release-specific changes; `main` fixes the bug and moves on; the fix is
then backported to `release`. Seven commits, two branches, two fixes, one BIC —
and the release branch is not a linear correct-buggy-fixed sequence.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 5, one distractor on
the fault file, 7 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 0012a46  2025-02-10  Backport the guest greeting fix to release        <- BFC (r2, release; backport_of c2)
* b6e83ba  2025-02-03  Add the release compatibility configuration       (r1, release; release/config.properties)
* 9432994  2025-01-13  Cut the 1.0.0 release branch                      (r0, release; release/version.txt)
| * 7ec9f77  2025-01-24  Continue main development                       (c3; docs/main-development.md)
| * ba86e75  2025-01-15  Greet anonymous users as guests again           <- BFC (c2, main)
|/
* 72438a8  2025-01-06  Trim the name directly                            <- BIC (c1)
* f71a6d7  2024-12-31  Add the greeting                                  (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`); `branch_level` names `c1` for `main` (`bfc: c2`) and `release` (`bfc: r2`)
- BFCs: `c2` on `main`, `r2` on `release` (`backport_of: c2`)

## Measured behaviour and blame

| commit | `forName(" Ada ")` | `forName(null)` |
|---|---|---|
| `c0` | `Hello, Ada!` | `Hello, guest!` |
| `c1`, `r0`, `r1` | `Hello, Ada!` | **throws `NullPointerException`** |
| `c2`, `c3`, `r2` | `Hello, Ada!` | `Hello, guest!` |

Both fixes delete the same line (`return "Hello, " + name.trim() + "!";`,
line 5); blame at `c2^` and at `r2^` returns `c1` (verifier `GI703`).

## What a tool must do

From either fix, report `c1`. From `r2` the walk back passes `r1` and `r0`,
which touch only release files, before reaching the shared history; the
backport metadata (`backport_of: c2`) points at a fix, not at a cause.

## Factors

- `branch`
- `backport`
- `release-branch`
- `release-specific-changes`
- `copy-propagation`
- `null-check-omission`
