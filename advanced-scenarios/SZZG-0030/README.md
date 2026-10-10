# SZZG-0030: Attempted fix followed by follow-up fix

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G3` Multiple BICs, multiple BFCs, and partial fixes |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `multi-bfc`, `attempted-fix`, `follow-up-fix`, `incorrect-fix` |
| oracle | `exact_set`; required `c1`, `c2` · BFCs `c2`, `c3` |
| graph features | 2 bugs |
<!-- /szzbench:header -->

## Purpose

This scenario represents an attempted fix followed by a follow-up fix.

The key point is that `c2` is not a correct partial fix. It is a failed repair attempt: it changes the boundary condition, but uses the wrong boolean operator. The follow-up commit `c3` then applies the correct condition.

Both of `c2`'s effects are observable, so the contract models them as two bugs (D6). Measured on the
generated repository: `contains(5, 5, 7)` goes `false -> true` at `c2` — the bounds are accepted again, which
is the repair — while `contains(99, 5, 7)` goes `false -> true` as well, because `||` replaced `&&` and a
value outside the range is now accepted. `c2` therefore fixes `B001` and introduces `B002`, and the scenario
oracle is the union of the two direct BICs `{c1, c2}` (D9).

This distinguishes `SZZG-0030` from `SZZG-0029`, where `c2` is intended to be a true partial fix.

## Commit history

```text
c0: create initial correct implementation
c1: introduce boundary exclusion bug
c2: attempt to fix the bug but introduce wrong boolean logic
c3: apply follow-up fix with the correct boundary condition
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates the initial correct implementation. |
| `c1` | `main` | `c0` | bug_introducing | Excludes boundary values by using strict comparisons. |
| `c2` | `main` | `c1` | bug_introducing | Attempts a fix, but uses `||` instead of `&&`. |
| `c3` | `main` | `c2` | bug_fixing | Replaces the failed attempted fix with the correct condition. |

## Code states

Initial correct code in `c0`:

```java
return value >= min && value <= max;
```

Bug introduced in `c1`:

```java
return value > min && value < max;
```

Attempted but wrong fix in `c2`:

```java
return value >= min || value <= max;
```

This is still incorrect because the `||` condition accepts almost all integer values.

Follow-up fix in `c3`:

```java
return value >= min && value <= max;
```

## Oracle

Expected BIC:

```text
c1, c2
```

Bug-fixing commits:

```text
c2: attempted fix
c3: follow-up fix
```

The expected SZZ result is `{c1, c2}`. `c1` is the original bug-introducing commit; `c2` is a fix-like commit
that is nonetheless the bug-introducing commit of the fault `c3` repairs. Reporting `c1` alone leaves that
second fault unattributed.

## Difference from SZZG-0029

`SZZG-0029` represents a partial fix: one part of the boundary condition is correctly repaired while another part remains buggy.

`SZZG-0030` represents a failed attempted fix: the code is changed in a fix-like direction, but the new condition is logically wrong and requires a follow-up fix.
