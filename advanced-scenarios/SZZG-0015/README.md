# SZZG-0015: One BFC fixes multiple BICs for one composite bug

## Purpose

This scenario represents one composite bug that is created by two separate bug-introducing commits and fixed by one bug-fixing commit.

The range check is split into two helper methods:

```text
lowerOk(value, min)
upperOk(value, max)
```

The first BIC `c1` breaks the lower-bound helper. The second BIC `c2` breaks the upper-bound helper. Together, these two commits create one composite range-boundary bug. The BFC `c3` fixes both faults at once.

## Commit history

```text
c0: create correct range check with separate lower and upper helpers
c1: first BIC breaks the lower-bound helper
c2: second BIC breaks the upper-bound helper, completing one composite bug
c3: one BFC fixes both lower and upper boundary faults
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates the correct helper-based range check. |
| `c1` | `main` | `c0` | bug_introducing | Changes `lowerOk` from inclusive to exclusive. |
| `c2` | `main` | `c1` | bug_introducing | Changes `upperOk` from inclusive to exclusive. |
| `c3` | `main` | `c2` | bug_fixing | Fixes both helper methods in one commit. |

## Oracle

Expected BICs:

```text
c1
c2
```

Bug-fixing commit:

```text
c3
```

## Difference from SZZG-0017

`SZZG-0015` has one bug record with two BICs.

`SZZG-0017` is intended to represent two independent bugs fixed by one shared BFC.
