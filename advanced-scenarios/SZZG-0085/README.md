# SZZG-0085: Rebase with formatting rewrite noise

## Purpose

Evaluate formatting rewrite noise after rebase.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce range bug
r1: r1: rebase bug onto main
r2: r2: formatting rewrite during rebase cleanup
c3: c3: fix bug after formatting rewrite
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce range bug |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase bug onto main |
| `r2` | `main` | r1 | `formatting` | r2: formatting rewrite during rebase cleanup |
| `c3` | `main` | r2 | `bug_fixing` | c3: fix bug after formatting rewrite |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, r2
```

## Key property

r2 is formatting noise; r1 is the true BIC.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Avoid r2.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.
