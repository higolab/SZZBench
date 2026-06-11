# SZZG-0065: Rebase conflict resolution fixes bug

## Purpose

Evaluate whether SZZ can handle a BFC that is itself a rebase conflict resolution commit.

## Commit history

```text
c0: c0: create initial correct implementation
r1: r1: rebase feature bug commit onto main
m1: m1: main change before conflict-resolution fix
r2: r2: resolve rebase conflict and fix range bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase feature bug commit onto main |
| `m1` | `main` | r1 | `intermediate` | m1: main change before conflict-resolution fix |
| `r2` | `main` | m1 | `bug_fixing` | r2: resolve rebase conflict and fix range bug |

## Expected SZZ result

```text
Expected BIC(s): r1
```

## Key property

The fix is introduced by r2 during rebase conflict resolution.

## Difference from SZZG-0061

SZZG-0061 covers the basic case where a feature-branch BIC is replayed onto main. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Start from r2.
- Return r1.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.
