# SZZG-0010: Extract class after BIC

## Purpose

This scenario represents an extract-class refactoring after a bug-introducing commit.

The bug is first introduced in `RangeService.java`. After that, a new `RangeValidator.java` class is extracted, and the buggy validation logic is moved into the extracted class. The bug is then fixed in the extracted class.

This distinguishes `SZZG-0010` from `SZZG-0009`, which represents a method move between classes. In this scenario, a new class is created and responsibility is split after the BIC.

## Commit history

```text
c0: create RangeService with validation and reporting responsibilities
c1: introduce boundary bug in RangeService.contains
c2: extract RangeValidator class after the BIC and move the buggy validation logic there
c3: fix the boundary bug in the extracted RangeValidator class
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates `RangeService` with validation and reporting responsibilities. |
| `c1` | `main` | `c0` | bug_introducing | Introduces a boundary bug in `RangeService.contains`. |
| `c2` | `main` | `c1` | intermediate | Extracts `RangeValidator` and moves the buggy validation logic there. |
| `c3` | `main` | `c2` | bug_fixing | Fixes the boundary bug in `RangeValidator`. |

## Code states

Correct validation in `c0`:

```java
return value >= min && value <= max;
```

Bug introduced in `c1`:

```java
return value > min && value < max;
```

After `c2`, the buggy logic is moved from:

```text
src/main/java/example/RangeService.java
```

to:

```text
src/main/java/example/RangeValidator.java
```

The follow-up fix in `c3` restores the correct condition in `RangeValidator.java`:

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

The extraction commit `c2` is not the BIC. It moves the buggy logic to a new class after the bug has already been introduced.

## Difference from SZZG-0009

`SZZG-0009` is intended to represent a method move between classes.

`SZZG-0010` is intended to represent extract class after BIC:

```text
RangeService.java
  validation + reporting responsibilities
        ↓
RangeService.java
  reporting / orchestration

RangeValidator.java
  extracted validation responsibility
```

The BIC and BFC occur in different files because the buggy code is moved by the extract-class refactoring.
