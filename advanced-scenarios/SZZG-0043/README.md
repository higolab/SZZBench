# SZZG-0043: Work item inference without issue ID

## Purpose

This scenario represents a work-item inference case where commit messages do not contain explicit issue IDs.

The commits `c1`, `c2`, and `c3` are part of the same inferred work item, but only `c2` is the BIC. The neighboring commits are related context and should not be reported as the bug-introducing commit.

## Commit history

```text
c0: create initial range filter
c1: start range filter cleanup without issue ID
c2: tighten boundary behavior during the same inferred work item and introduce bug
c3: wire range filter into request path without issue ID
c4: fix boundary regression from range filter work
```

## Commit table

| Commit | Branch | Parents | Role | Work item | Message |
|---|---|---|---|---|---|
| `c0` | `main` | none | initial | none | `c0: create initial range filter` |
| `c1` | `main` | `c0` | work_item_context | `INFERRED-WI-001` | `Start range filter cleanup` |
| `c2` | `main` | `c1` | bug_introducing | `INFERRED-WI-001` | `Tighten boundary behavior in range filter` |
| `c3` | `main` | `c2` | work_item_context | `INFERRED-WI-001` | `Wire range filter into request path` |
| `c4` | `main` | `c3` | bug_fixing | none | `Fix boundary regression from range filter work` |

## Inference signals

The intended work item is not given by an issue ID in the commit messages. It should be inferred from:

```text
- related range-filter terminology in commit messages
- consecutive commits in a short series
- changes to the same file or related behavior
- the fix message referring to a boundary regression from range filter work
```

## Code states

Correct condition before the BIC:

```java
return normalized >= min && normalized <= max;
```

Bug introduced in `c2`:

```java
return normalized > min && normalized < max;
```

Related but non-BIC context added in `c3`:

```java
public boolean acceptsRequestValue(int value) {
  return contains(value, 0, 100);
}
```

Fix in `c4`:

```java
return normalized >= min && normalized <= max;
```

## Oracle

Expected BIC:

```text
c2
```

Related but not correct BICs:

```text
c1
c3
```

Bug-fixing commit:

```text
c4
```

## Difference from SZZG-0042

`SZZG-0042` assumes an explicit work item with multiple candidate BICs.

`SZZG-0043` represents the case where the work item has to be inferred because no explicit issue ID appears in the commit messages.
