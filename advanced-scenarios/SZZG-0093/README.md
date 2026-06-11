# SZZG-0093: Multiple BICs with partial revert reintroducing one fault

## Purpose

Evaluate multiple original BICs when a later partial revert reintroduces only one of them.

## Commit history

```text
c0: create initial correct implementation
c1: introduce lower-bound bug
c2: introduce upper-bound bug
c3: fix both boundary bugs
c4: partially revert fix for upper boundary only
c5: fix reintroduced upper-bound bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `origin_bug_introducing` | c1: introduce lower-bound bug |
| `c2` | `main` | c1 | `origin_bug_introducing` | c2: introduce upper-bound bug |
| `c3` | `main` | c2 | `prior_fix` | c3: fix both boundary bugs |
| `c4` | `main` | c3 | `bug_introducing` | c4: partially revert fix for upper boundary only |
| `c5` | `main` | c4 | `bug_fixing` | c5: fix reintroduced upper-bound bug |

## Expected SZZ result

```text
Expected BIC(s): c4
Related but not correct: c1, c2, c3
```

## Key property

The direct BIC for the final fix is the partial revert, not the older original BIC set.

## Difference from existing revert scenarios

This scenario isolates a double-revert or revert-derived complication beyond the existing partial revert and reintroduction scenarios.

## Evaluation points

- Whether SZZ reports c4.
- Whether SZZ avoids reporting both old BICs as exact direct answers.

## Notes

- This scenario models revert-related development history for SZZ evaluation.
- The direct BIC is the commit that reintroduces the bug in the history observed from the BFC.
