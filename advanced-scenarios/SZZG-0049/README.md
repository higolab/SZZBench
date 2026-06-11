# SZZG-0049: Cherry-pick BFC

## Purpose

This scenario represents a bug-fixing commit that is cherry-picked from `main` to a `release` branch.

The bug is introduced on `main` before the release branch is cut. The release branch is created from the buggy state. The bug is then fixed on `main`, and that BFC is cherry-picked onto `release`.

This distinguishes `SZZG-0049` from `SZZG-0048`.

```text
SZZG-0048: cherry-pick BIC
SZZG-0049: cherry-pick BFC
```

## Commit graph

```text
main:     c0 ---- c1(BIC) ---- c2(BFC)
                    \
release:             r1 ---- r2(BFC, cherry-pick of c2)
```

## Commit history

```text
c0: create initial correct implementation on main
c1: introduce bug on main before the release branch is cut
r1: create release branch from the buggy state
c2: fix bug on main
r2: cherry-pick the main BFC onto release
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates the correct range check. |
| `c1` | `main` | `c0` | bug_introducing | Introduces the range boundary bug. |
| `r1` | `release` | `c1` | release_branch_point | Creates the release branch from the buggy state. |
| `c2` | `main` | `c1` | bug_fixing | Fixes the bug on main. |
| `r2` | `release` | `r1` | bug_fixing | Cherry-picks the main-line fix `c2` onto release. |

## Code states

Correct range check in `c0`:

```java
return value >= min && value <= max;
```

Bug introduced in `c1`:

```java
return value > min && value < max;
```

Main-line fix in `c2`:

```java
return value >= min && value <= max;
```

Release fix in `r2`:

```text
r2 cherry-picks the fixing patch from c2.
```

## Oracle

Expected BIC:

```text
c1
```

Bug-fixing commits:

```text
c2: main-line fix
r2: release-branch cherry-picked fix
```

## Evaluation purpose

This scenario checks whether SZZ can handle a BFC that is cherry-picked onto another branch.

When SZZ starts from the release-branch BFC `r2`, the expected BIC is still `c1`. A tool should not report `c2` as the BIC merely because `r2` is derived from `c2`.

## Notes for generator / verifier

`r2` uses:

```yaml
cherry_pick_of: c2
operations:
  - type: apply_patch_from
    commit: c2
```

If the current verifier has limited support for `apply_patch_from`, `r2` can be rewritten as an explicit `replace` operation equivalent to the patch in `c2`.
