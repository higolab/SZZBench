# SZZG-0071: Copy propagation with direct and origin BIC evaluation variants

## Purpose

This scenario represents a copy-propagated bug.

A bug is first introduced in the original file `A.java`. Later, the buggy logic is copied into `B.java`. The fix is applied to `B.java`.

For the fix in `B.java`, there are two meaningful BIC notions:

```text
direct BIC: c2
origin BIC: c1
```

The direct BIC is the commit that copied the faulty logic into the fixed file. The origin BIC is the commit where the faulty logic first appeared.

This scenario is the renumbered successor of the former `SZZG-0073` and also absorbs the relaxed-with-credit policy from the former `SZZG-0071`.

## Commit history

```text
c0: create original correct implementation in A.java
c1: introduce boundary bug in original A.java
c2: copy buggy implementation from A.java to B.java, creating the direct BIC for B.java
c3: fix the copied bug in B.java
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates correct `A.java`. |
| `c1` | `main` | `c0` | origin_bug_introducing | Introduces the bug in `A.java`. |
| `c2` | `main` | `c1` | bug_introducing | Copies the buggy logic into `B.java`. |
| `c3` | `main` | `c2` | bug_fixing | Fixes the copied bug in `B.java`. |

## Code states

Correct original code in `c0`:

```java
return value >= min && value <= max;
```

Origin bug introduced in `c1`:

```java
return value > min && value < max;
```

Copied bug in `c2`:

```text
A.java contains the buggy logic.
B.java is created with the same buggy logic.
```

Fix in `c3`:

```java
return value >= min && value <= max;
```

## Oracle

Bug-fixing commit:

```text
c3
```

Direct BIC:

```text
c2
```

Origin BIC:

```text
c1
```

## Evaluation variants

### direct-only

Only the direct BIC is accepted.

```text
required: c2
```

### origin-aware

The direct BIC is required, and the origin BIC is accepted as related context.

```text
required: c2
acceptable_related: c1
```

### relaxed-with-credit

Compatibility variant equivalent to the former `SZZG-0071` policy.

```text
required: c2
acceptable_related: c1, credit 0.5
```

## Renumbering note

Before public release, the old `SZZG-0071` and old `SZZG-0073` were found to use the same repository history. The old `SZZG-0073` evaluation-variant design was retained, expanded to include the old `SZZG-0071` relaxed-with-credit policy, and renumbered to `SZZG-0071`.
