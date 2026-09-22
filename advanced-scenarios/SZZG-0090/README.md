# SZZG-0090: Repeated revert toggling before final fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `revert`, `revert-of-revert`, `repeated-toggling`, `reintroduced-bug`, `re-bic` |
| oracle | default: `exact_set`; required `c5`; related origins `c1`; related but not correct `c3`, `c2`, `c4` · `origin-aware`: `relaxed_with_related`; required `c5`; acceptable `c1` (credit 0.5); related but not correct `c3`, `c2`, `c4` · BFC `c6` |
| graph features | 3 BICs; 2 fault sites; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate repeated toggling where the latest reintroducing revert should be identified as the direct BIC.

## Commit history

```text
c0: create initial correct implementation
c1: introduce boundary bug
c2: fix boundary bug
c3: revert c2 and reintroduce bug
c4: revert c3 and restore fix
c5: revert c4 and reintroduce bug again
c6: final explicit fix after repeated toggling
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `origin_bug_introducing` | c1: introduce boundary bug |
| `c2` | `main` | c1 | `bug_fixing` | c2: fix boundary bug |
| `c3` | `main` | c2 | `bug_introducing` | c3: revert c2 and reintroduce bug |
| `c4` | `main` | c3 | `bug_fixing` | c4: revert c3 and restore fix |
| `c5` | `main` | c4 | `bug_introducing` | c5: revert c4 and reintroduce bug again |
| `c6` | `main` | c5 | `bug_fixing` | c6: final explicit fix after repeated toggling |

## Expected SZZ result

```text
Expected BIC(s): c5
Related but not correct: c1, c3, c2, c4
```

## Key property

Multiple earlier BIC-like and fix-like commits exist, but the final fix should blame the latest re-BIC.

## Difference from existing revert scenarios

This scenario isolates a double-revert or revert-derived complication beyond the existing partial revert and reintroduction scenarios.

## Evaluation points

- Whether SZZ reports c5.
- Whether older origin/reintroducing commits are not counted as exact direct answers.

## Notes

- This scenario models revert-related development history for SZZ evaluation.
- The direct BIC is the commit that reintroduces the bug in the history observed from the BFC.
