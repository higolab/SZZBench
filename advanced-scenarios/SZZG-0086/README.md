# SZZG-0086: Revert of fix reintroduces bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G6` Revert-specific reintroduction |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `revert`, `revert-of-fix`, `reintroduced-bug`, `origin-vs-direct` |
| oracle | default: `exact_set`; required `c3`; related origins `c1`; related but not correct `c2` · `origin-aware`: `relaxed_with_related`; required `c3`; acceptable `c1` (credit 0.5); related but not correct `c2` · BFC `c4` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | 2 BICs; 2 fault sites; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ returns the revert commit that reintroduced the bug rather than the original historical BIC.

## Commit history

```text
c0: create initial correct implementation
c1: introduce boundary bug
c2: fix boundary bug
c3: revert c2 and reintroduce boundary bug
c4: fix boundary bug again
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `c1` | `main` | c0 | `origin_bug_introducing` | c1: introduce boundary bug |
| `c2` | `main` | c1 | `bug_fixing` | c2: fix boundary bug |
| `c3` | `main` | c2 | `bug_introducing` | c3: revert c2 and reintroduce boundary bug |
| `c4` | `main` | c3 | `bug_fixing` | c4: fix boundary bug again |

## Expected SZZ result

```text
Expected BIC(s): c3
Related but not correct: c1, c2
```

## Key property

The bug was fixed once, but reverting that fix creates the direct BIC for the later BFC.

## Difference from existing revert scenarios

This scenario isolates a double-revert or revert-derived complication beyond the existing partial revert and reintroduction scenarios.

## Evaluation points

- Whether SZZ reports c3.
- Whether c1 is treated as origin rather than the direct answer.
- Whether the prior fix c2 is not reported as BIC.

## Notes

- This scenario models revert-related development history for SZZ evaluation.
- The direct BIC is the commit that reintroduces the bug in the history observed from the BFC.
