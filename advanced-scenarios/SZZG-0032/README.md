# SZZG-0032: BIC in merge commit

## Purpose

The merge commit itself introduces the bug during merge resolution; a later normal commit fixes it.

## Commit history

```text
c0: create initial correct implementation on main
c1: add feature branch helper without changing the range logic
c2: add unrelated main branch note
c3: merge feature into main and introduce bug in the merge commit
c4: fix the merge-introduced bug
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `feature` | c0 | `intermediate` | c1: add feature helper without bug |
| `c2` | `main` | c0 | `intermediate` | c2: add unrelated main branch note |
| `c3` | `main` | c2, c1 | `bug_introducing` | c3: merge feature and introduce boundary bug |
| `c4` | `main` | c3 | `bug_fixing` | c4: fix merge-introduced range boundary bug |

## Expected SZZ result

```text
Expected BIC: c3
```

## Scenario purpose

Evaluate whether SZZ can identify a merge commit as the BIC when the merge resolution itself introduces the bug.

## Notes

- This scenario requires support for operations on merge commits.
