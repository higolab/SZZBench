# SZZG-0073: Release branch change rebased onto main

## Purpose

Evaluate rebase from release branch to main.

## Commit history

```text
c0: c0: create initial correct implementation
rel1: rel1: introduce release-specific range bug
m1: m1: continue main development
r1: r1: rebase release change onto main
c2: c2: fix release-origin bug on main
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `rel1` | `release` | c0 | `origin_bug_introducing` | rel1: introduce release-specific range bug |
| `m1` | `main` | c0 | `intermediate` | m1: continue main development |
| `r1` | `main` | m1 | `bug_introducing` | r1: rebase release change onto main |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix release-origin bug on main |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: rel1
```

## Key property

rel1 is origin, r1 is direct on main.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.
