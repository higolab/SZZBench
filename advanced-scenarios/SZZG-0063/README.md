# SZZG-0063: Rebase feature branch with BIC

## Purpose

Feature branch commits introduce and extend a bug, and those commits are then rebased onto `main` as new single-parent commits.

This scenario evaluates how SZZ handles a rebase-style workflow where the **direct BIC on main** is the rebased commit, while the original feature-branch commit is retained as **origin metadata**.

## Commit history

```text
c0: create initial correct implementation on main
f1: feature branch introduces range boundary bug
f2: feature branch adds code that uses the buggy range check
r1: rebase f1 onto main as a new main-line commit
r2: rebase f2 onto main as a new main-line commit
c3: fix the rebased range boundary bug on main
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | Create the initial correct implementation. |
| `f1` | `feature` | `c0` | `origin_bug_introducing` | Introduce the boundary bug on the feature branch. |
| `f2` | `feature` | `f1` | `intermediate` | Add feature code that uses the buggy range check. |
| `r1` | `main` | `c0` | `bug_introducing` | Rebased copy of `f1`; introduces the bug into the main-line history. |
| `r2` | `main` | `r1` | `intermediate` | Rebased copy of `f2`; adds the feature helper on main. |
| `c3` | `main` | `r2` | `bug_fixing` | Fix the range boundary bug on main. |

## Expected SZZ result

```text
Expected BIC: r1
Related but not correct: f1
```

## Scenario purpose

Evaluate how SZZ handles rebase-style history rewriting.

In a rebase workflow, the original feature-branch commits are replayed onto another base and receive new commit identities. Therefore, the commit that directly introduces the faulty code into the main-line history is `r1`, not the original feature-branch commit `f1`.

## Difference from nearby branch scenarios

- `SZZG-0043` uses a normal merge with a two-parent merge commit.
- `SZZG-0047` uses a squash merge, where multiple feature commits are collapsed into one single-parent commit on `main`.
- `SZZG-0063` uses rebase-style replay, where each feature commit is represented by a corresponding new single-parent commit on `main`.

## Notes

- The `rebase_of` metadata records which feature-branch commit each rebased main-line commit corresponds to.
- The direct BIC for generated main history is `r1`.
- The origin BIC is `f1`, but it is not the expected direct BIC for the main-line BFC.
