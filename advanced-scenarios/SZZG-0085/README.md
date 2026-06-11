# SZZG-0085: Old BIC and re-BIC are both plausible

## Purpose

This scenario represents a bug that is introduced, fixed, reintroduced by a partial revert, and fixed again.

The direct BIC for the final fix is the reintroducing commit `c3`. However, the original old BIC `c1` is also a plausible origin-related answer under an origin-aware evaluation policy.

## Commit history

```text
c0: create initial correct implementation
c1: introduce original range boundary bug
c2: fix original bug and perform a small refactoring
c3: partially revert c2 and reintroduce the boundary bug while keeping the refactoring
c4: fix the reintroduced bug
```

## Code states

Correct state in `c0`:

```java
return value >= min && value <= max;
return "main";
```

Original bug in `c1`:

```java
return value > min && value < max;
return "main";
```

Fix and unrelated refactoring in `c2`:

```java
return value >= min && value <= max;
return "range-service";
```

Partial revert / reintroduction in `c3`:

```java
return value > min && value < max;
return "range-service";
```

Final fix in `c4`:

```java
return value >= min && value <= max;
return "range-service";
```

## Oracle

Default expected BIC:

```text
c3
```

Related old origin BIC:

```text
c1
```

## Evaluation variants

### reintroduction-direct

Only `c3` is considered correct for the final fix.

### origin-aware

`c3` is required, while `c1` is accepted as an origin-related BIC with partial credit.

## Difference from SZZG-0084

`SZZG-0084` should focus on the direct reintroduction case.

`SZZG-0085` explicitly models the evaluation question where both the reintroducing BIC and the old origin BIC may be considered plausible depending on evaluation policy.
