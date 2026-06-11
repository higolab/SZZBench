# SZZG-0066: Rebase changes patch content during replay

## Purpose

Evaluate direct/origin handling when rebase changes patch content.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce exclusive bug on feature
m1: m1: add main note
r1: r1: rebase feature bug with adjusted patch content
c2: c2: fix adjusted lower-bound bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce exclusive bug on feature |
| `m1` | `main` | c0 | `intermediate` | m1: add main note |
| `r1` | `main` | m1 | `bug_introducing` | r1: rebase feature bug with adjusted patch content |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix adjusted lower-bound bug |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Key property

Patch equality alone is insufficient.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Treat f1 as origin.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.
