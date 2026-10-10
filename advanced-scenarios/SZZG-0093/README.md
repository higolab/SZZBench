# SZZG-0093: BIC occurs during feature work

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `work-item`, `feature-work`, `bic-inside-work-item`, `commit-series` |
| oracle | `exact_set`; required `c2`; related but not correct `c1`, `c3` · BFC `c4` |
| defeats | `shape` |
| graph features | `work_items` |
<!-- /szzbench:header -->

## Purpose

This scenario represents a bug-introducing commit that occurs in the middle of a multi-commit feature work item.

The feature work item `WI-001` consists of three commits:

```text
c1: start feature work
c2: introduce bug during feature implementation
c3: continue feature work using the buggy method
```

Only `c2` is the BIC. Commits `c1` and `c3` are related to the same work item, but they are not the bug-introducing commit.

## Commit history

```text
c0: create base range filter
c1: start feature work by adding feature metadata without introducing a bug
c2: implement feature logic and introduce boundary bug during the work item
c3: continue the same feature work by adding a caller that uses the buggy logic
c4: fix the boundary bug after the feature work
```

## Commit table

| Commit | Branch | Parents | Role | Work item | Description |
|---|---|---|---|---|---|
| `c0` | `main` | none | initial | none | Creates the base range filter. |
| `c1` | `main` | `c0` | intermediate | `WI-001` | Starts the range filtering feature without introducing a bug. |
| `c2` | `main` | `c1` | bug_introducing | `WI-001` | Introduces the boundary bug during feature implementation. |
| `c3` | `main` | `c2` | intermediate | `WI-001` | Adds a caller that uses the buggy method. |
| `c4` | `main` | `c3` | bug_fixing | none | Fixes the boundary bug. |

## Code states

Correct range check in `c0` and `c1`:

```java
return value >= min && value <= max;
```

Bug introduced in `c2`:

```java
return value > min && value < max;
```

Feature work continues in `c3` by adding:

```java
public boolean acceptsUserInput(int value) {
  return contains(value, 0, 100);
}
```

Fix in `c4`:

```java
return value >= min && value <= max;
```

## Oracle

Expected BIC:

```text
c2
```

Related but not correct:

```text
c1
c3
```

Bug-fixing commit:

```text
c4
```

## Evaluation purpose

This scenario checks whether SZZ identifies the specific BIC inside a feature work item. A work-item-aware method should not simply blame all commits in the work item, and a line-based method may be affected by the later caller added in `c3`.
