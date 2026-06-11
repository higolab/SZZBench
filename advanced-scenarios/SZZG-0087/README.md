# SZZG-0087: Huge noisy rebased commit

## Purpose

Evaluate SZZ behavior on a large noisy rebased commit.

## Commit history

```text
c0: c0: create initial correct implementation
f1: f1: introduce bug and noisy feature files
r1: r1: rebase huge noisy feature commit
c2: c2: fix bug from huge noisy commit
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce bug and noisy feature files |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase huge noisy feature commit |
| `c2` | `main` | r1 | `bug_fixing` | c2: fix bug from huge noisy commit |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Key property

r1 contains one relevant source change and many unrelated files.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Report r1.
- Remain robust.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.
