# SZZG-0077: Rebased BIC fixed by multiple BFCs

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G5` Rebase-specific history rewriting |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `branch`, `rebase`, `rebased-bic`, `multi-bfc`, `partial-fix`, `complete-fix` |
| oracle | default: `exact_set`; required `r1`; related origins `f1` · `origin-aware`: `relaxed_with_related`; required `r1`; acceptable `f1` (credit 0.5) · BFCs `c3`, `c4` |
| graph features | 2 branches; rebase `r1`; 2 BICs; 2 BFCs; origin faults; 2 fault sites; 1 evaluation variant (`origin-aware`) |
<!-- /szzbench:header -->

## Purpose

Evaluate progressive repair of a rebased BIC.

## Commit history

```text
c0: create initial correct implementation
f1: introduce both boundary bugs
r1: rebase feature BIC onto main
c3: partially fix lower boundary
c4: complete boundary fix
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | `initial` | c0: create initial correct implementation |
| `f1` | `feature` | c0 | `origin_bug_introducing` | f1: introduce both boundary bugs |
| `r1` | `main` | c0 | `bug_introducing` | r1: rebase feature BIC onto main |
| `c3` | `main` | r1 | `bug_fixing` | c3: partially fix lower boundary |
| `c4` | `main` | c3 | `bug_fixing` | c4: complete boundary fix |

## Expected SZZ result

```text
Expected BIC(s): r1
Related but not correct: f1
```

## Key property

The rebased BIC introduces separate lower-bound and upper-bound faults. The partial fix repairs only the lower-bound fault, while the upper-bound fault remains until the complete fix.

## Code states

Correct implementation in `c0`:

```java
boolean aboveMin = value >= min;
boolean belowMax = value <= max;
return aboveMin && belowMax;
```

Rebased bug in `r1`:

```java
boolean aboveMin = value > min;
boolean belowMax = value < max;
return aboveMin && belowMax;
```

Partial fix in `c3`:

```java
boolean aboveMin = value >= min;
boolean belowMax = value < max;
return aboveMin && belowMax;
```

Complete fix in `c4`:

```java
boolean aboveMin = value >= min;
boolean belowMax = value <= max;
return aboveMin && belowMax;
```

## Difference from SZZG-0064

SZZG-0064 covers a rebased BIC followed by a non-BIC rebased intermediate commit. This scenario adds a distinct rebase-related complication.

## Evaluation points

- Return r1 from final fix.

## Notes

- This scenario models a rebase-related development history for SZZ evaluation.
- Rebase relationships are recorded using metadata such as rebase_of, interactive_rebase, or rebase_conflict_resolution.
