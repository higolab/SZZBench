# SZZG-0014: Multiple BFCs progressively fix the same bug

## Overview

This scenario represents a single bug that is repaired progressively by multiple bug-fixing commits.

The implementation uses two helper methods:

```text
aboveMin(value, min)
belowMax(value, max)
```

The BIC `c1` breaks both helper methods. The first BFC `c2` fixes only the lower-bound helper. The second BFC `c3` fixes the upper-bound helper and completes the repair.

## Commit history

```text
c0: create range check with separate lower-bound and upper-bound helpers
c1: introduce the same boundary bug in both helper methods
c2: first BFC fixes only the lower-bound helper
c3: second BFC fixes the upper-bound helper and completes the repair
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates the correct helper-method based implementation. |
| `c1` | `main` | `c0` | bug_introducing | Changes both boundary helpers from inclusive to exclusive checks. |
| `c2` | `main` | `c1` | bug_fixing | Partially fixes the bug by repairing the lower-bound helper. |
| `c3` | `main` | `c2` | bug_fixing | Completes the fix by repairing the upper-bound helper. |

## Code states

Correct state in `c0`:

```java
return value >= min;
return value <= max;
```

Bug introduced in `c1`:

```java
return value > min;
return value < max;
```

Partial fix in `c2`:

```java
return value >= min;
return value < max;
```

Complete fix in `c3`:

```java
return value >= min;
return value <= max;
```

## Oracle

Expected BIC:

```text
c1
```

Bug-fixing commits:

```text
c2: partial fix for the lower-bound helper
c3: complete fix for the upper-bound helper
```

## Difference from SZZG-0003

`SZZG-0003` represents a partial-fix sequence on one condition expression.

`SZZG-0014` represents multiple BFCs for the same bug, with two separate faulty helper methods and two separate fixing commits.
