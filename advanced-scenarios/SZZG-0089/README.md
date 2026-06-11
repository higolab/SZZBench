# SZZG-0089: Revert of revert with conflict resolution

## Purpose

Evaluate a revert-of-revert BFC that includes conflict resolution after intervening code changes.

## Commit history

```text
c0: create initial correct implementation
c1: introduce boundary bug
c2: fix boundary bug
c3: revert c2 and reintroduce boundary bug
c4: add description before resolving revert conflict
c5: revert c3 with conflict resolution and restore boundary fix
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `origin_bug_introducing` | c1: introduce boundary bug |
| `c2` | `main` | c1 | `prior_fix` | c2: fix boundary bug |
| `c3` | `main` | c2 | `bug_introducing` | c3: revert c2 and reintroduce boundary bug |
| `c4` | `main` | c3 | `intermediate` | c4: add description before resolving revert conflict |
| `c5` | `main` | c4 | `bug_fixing` | c5: revert c3 with conflict resolution and restore boundary fix |

## Expected SZZ result

```text
Expected BIC(s): c3
Related but not correct: c1, c2, c4
```

## Key property

The BFC restores the earlier fix while preserving unrelated intervening changes.

## Difference from existing revert scenarios

This scenario isolates a double-revert or revert-derived complication beyond the existing partial revert and reintroduction scenarios.

## Evaluation points

- Whether SZZ reports c3.
- Whether the intermediate c4 is not selected.

## Notes

- This scenario models revert-related development history for SZZ evaluation.
- The direct BIC is the commit that reintroduces the bug in the history observed from the BFC.
