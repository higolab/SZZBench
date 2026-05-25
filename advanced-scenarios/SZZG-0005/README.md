# SZZG-0005: BFC is a merge commit

## Purpose

This scenario evaluates a case where the bug-fixing commit is itself a merge commit.

The important point is that the merge commit `c3` has two parents and also contains the edit that fixes the bug. This distinguishes this scenario from cases where a feature branch is merged first and a normal commit on `main` fixes the bug later.

## Commit graph

```text
main:    c0 ---- c2 ---- c3(BFC)
           \            /
feature:    c1(BIC) ----
```

## Commit sequence

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates the initial correct implementation. |
| `c1` | `feature` | `c0` | BIC | Introduces a range-boundary bug on the feature branch. |
| `c2` | `main` | `c0` | intermediate | Adds an unrelated main-branch note. |
| `c3` | `main` | `c2`, `c1` | BFC / merge commit | Merges the feature branch and fixes the bug in the merge commit itself. |

## Bug

The original correct implementation is:

```java
return value >= min && value <= max;
```

The bug-introducing commit `c1` changes it to:

```java
return value > min && value < max;
```

This incorrectly excludes boundary values equal to `min` or `max`.

The merge commit `c3` fixes the bug by restoring the inclusive boundary check:

```java
return value >= min && value <= max;
```

## Oracle

Expected BIC:

```text
c1
```

Bug-fixing commit:

```text
c3
```

`c3` is intentionally both:

```text
- a merge commit
- the bug-fixing commit
```

## Evaluation purpose

This scenario checks whether an SZZ method can correctly identify a feature-branch BIC when the BFC is a merge commit.

A method may fail if it assumes that bug-fixing commits are ordinary linear commits, or if it does not handle merge commits with actual fixing edits.

## Notes for generator / verifier

This scenario requires `generate-graph` to support operations on merge commits. In this scenario, `c3` has two parents and also applies a `replace` operation.

If the current generator assumes that merge commits must have empty `operations`, then `graph_generator.py` should be updated before this scenario is generated.
