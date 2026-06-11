# SZZG-0094: Misleading revert commit message reintroduces bug

## Purpose

Evaluate context-aware SZZ robustness when a revert message understates or mislabels the actual bug reintroduction.

## Commit history

```text
c0: create initial correct implementation
c1: introduce boundary bug
c2: fix boundary bug
c3: revert cleanup changes
c4: fix regression after misleading revert
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `origin_bug_introducing` | c1: introduce boundary bug |
| `c2` | `main` | c1 | `prior_fix` | c2: fix boundary bug |
| `c3` | `main` | c2 | `bug_introducing` | c3: revert cleanup changes |
| `c4` | `main` | c3 | `bug_fixing` | c4: fix regression after misleading revert |

## Expected SZZ result

```text
Expected BIC(s): c3
Related but not correct: c1, c2
```

## Key property

The revert message looks like cleanup, but the patch reintroduces the boundary bug.

## Difference from existing revert scenarios

This scenario isolates a double-revert or revert-derived complication beyond the existing partial revert and reintroduction scenarios.

## Evaluation points

- Whether SZZ reports c3.
- Whether context-aware methods avoid being misled by the message.

## Notes

- This scenario models revert-related development history for SZZ evaluation.
- The direct BIC is the commit that reintroduces the bug in the history observed from the BFC.
