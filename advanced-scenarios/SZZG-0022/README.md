# SZZG-0022: Copy propagation with direct and origin BIC evaluation variants

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `copy-propagation`, `direct-bic`, `origin-bic`, `evaluation-variant`, `relaxed-with-credit` |
| oracle | default (`direct-only`): `exact_set`; required `c2`; related origins `c1` · `origin-aware`: `relaxed_with_related`; required `c2`; acceptable `c1` (credit 0.5) · `relaxed-with-credit`: `relaxed_with_credit`; required `c2`; acceptable `c1` (credit 0.5) · BFC `c3` |
| graph features | 2 BICs; origin faults; 3 evaluation variants (`direct-only`, `origin-aware`, `relaxed-with-credit`); `clone_relationships`; `copy_relationships` |
<!-- /szzbench:header -->

## Purpose

This scenario represents a copy-propagated bug.

A bug is first introduced in the original file `A.java`. Later, the buggy logic is copied into `B.java`. The fix is applied to `B.java`.

For the fix in `B.java`, there are two meaningful BIC notions:

```text
direct BIC: c2
origin BIC: c1
```

The direct BIC is the commit that copied the faulty logic into the fixed file. The origin BIC is the commit where the faulty logic first appeared.

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

Compatibility variant equivalent to the former `SZZG-0022` policy.

```text
required: c2
acceptable_related: c1, credit 0.5
```
