# SZZG-0084: Interactive rebase fixup combines buggy commits

## Purpose

Evaluate fixup/squash inside interactive rebase.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce range bug
f2: f2: fixup helper using buggy logic
r1: r1: interactive rebase fixup combines feature commits
c2: c2: fix bug from fixup commit
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce range bug |
| `f2` | `feature` | f1 | `intermediate` | f2: fixup helper using buggy logic |
| `r1` | `main` | c0 | `bug_introducing` | r1: interactive rebase fixup combines feature commits |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix bug from fixup commit |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1, f2
```

## Key property

f1 and f2 collapse into r1.

## Difference from SZZG-0073

SZZG-0073 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.
