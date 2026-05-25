# SZZG-0034: Squash merge

## Purpose

Feature branch commits introduce and extend a bug, but main receives them through a single-parent squash-merge commit.

## Commit history

```text
c0: create initial correct implementation on main
c1: feature branch introduces bug
c2: feature branch extends code using the buggy method
c3: squash-merge feature branch into main as a single-parent commit
c4: fix bug on main after squash merge
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `feature` | c0 | `source_bug_introducing` | c1: introduce range boundary bug on feature |
| `c2` | `feature` | c1 | `intermediate` | c2: extend feature branch code using range check |
| `c3` | `main` | c0 | `bug_introducing` | c3: squash merge feature branch into main |
| `c4` | `main` | c3 | `bug_fixing` | c4: fix squashed range boundary bug |

## Expected SZZ result

```text
Expected BIC: c3
```

## Scenario purpose

Evaluate how SZZ handles a squash merge where the main-line BIC is the squash commit, even though the origin of the faulty change is on the feature branch.

## Notes

- The direct BIC for the generated main history is c3; c1 is recorded as origin metadata.
