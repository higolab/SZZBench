# SZZG-0017: One BFC fixes multiple independent bugs

## Purpose

This scenario represents one bug-fixing commit that fixes two independent bugs.

The two bugs are in different files and different functional areas:

```text
B001: Range boundary bug in Range.java
B002: Discount calculation bug in DiscountCalculator.java
```

Both are fixed by the same BFC `c3`.

## Commit history

```text
c0: create correct Range and DiscountCalculator implementations
c1: introduce a range boundary bug in Range.java
c2: introduce an independent discount calculation bug in DiscountCalculator.java
c3: one BFC fixes both independent bugs
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates correct implementations of both files. |
| `c1` | `main` | `c0` | bug_introducing | Introduces the range boundary bug. |
| `c2` | `main` | `c1` | bug_introducing | Introduces the discount calculation bug. |
| `c3` | `main` | `c2` | bug_fixing | Fixes both bugs in one commit. |

## Bug B001

File:

```text
src/main/java/example/Range.java
```

Fault introduced in `c1`:

```java
return value > min && value < max;
```

Fix in `c3`:

```java
return value >= min && value <= max;
```

## Bug B002

File:

```text
src/main/java/example/DiscountCalculator.java
```

Fault introduced in `c2`:

```java
return price + discount;
```

Fix in `c3`:

```java
return price - discount;
```

## Oracle

Commit-level expected BICs:

```text
c1
c2
```

Bug-level expected BICs:

```text
B001: c1
B002: c2
```

Bug-fixing commit:

```text
c3
```

## Difference from SZZG-0015

`SZZG-0015` represents one composite bug with multiple BICs.

`SZZG-0017` represents two independent bugs that happen to be fixed by one shared BFC.
