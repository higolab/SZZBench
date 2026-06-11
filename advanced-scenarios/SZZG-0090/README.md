# SZZG-0090: Partial revert of fix reintroduces one fault

## Purpose

Evaluate a partial revert where only part of a previous fix is undone.

## Commit history

```text
c0: create initial correct implementation
c1: introduce two boundary bugs
c2: fix both boundary bugs
c3: partially revert upper-bound fix
c4: fix reintroduced upper-bound bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `origin_bug_introducing` | c1: introduce two boundary bugs |
| `c2` | `main` | c1 | `prior_fix` | c2: fix both boundary bugs |
| `c3` | `main` | c2 | `bug_introducing` | c3: partially revert upper-bound fix |
| `c4` | `main` | c3 | `bug_fixing` | c4: fix reintroduced upper-bound bug |

## Expected SZZ result

```text
Expected BIC(s): c3
Related but not correct: c1, c2
```

## Key property

The direct BIC reintroduces only one of the previously fixed faults.

## Difference from existing revert scenarios

This scenario isolates a double-revert or revert-derived complication beyond the existing partial revert and reintroduction scenarios.

## Evaluation points

- Whether SZZ reports c3.
- Whether SZZ does not require c1 as the direct BIC.

## Notes

- This scenario models revert-related development history for SZZ evaluation.
- The direct BIC is the commit that reintroduces the bug in the history observed from the BFC.
