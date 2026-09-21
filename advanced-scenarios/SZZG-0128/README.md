# SZZG-0128: Feature branch integrated by fast-forward, no merge commit (twin of SZZG-0043)

## Purpose

The same feature commits as [SZZG-0043](../SZZG-0043/README.md), integrated
into `main` by a fast-forward instead of a `--no-ff` merge. There is no merge
commit: `main` is a straight line and the `feature` ref still points at the
branch tip. The oracle is identical in both twins.

## Commit structure (generated)

```text
* e8aa2ed  Accept the range bounds again          <- BFC (c4), parent 5b5061a
* 5b5061a  Add a feature-specific range wrapper   (c2, feature tip; `feature` still points here)
* 350657b  Make the range check exclusive         <- BIC (c1)
* 6c89af4  Add the range check                    (c0)
```

Every commit has exactly one parent (`git log --format=%p`). The fast-forward is
expressed in the scenario by giving `c4` the feature tip `c2` as its parent;
the generator moves `main` there and commits on top.

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c4`

## Measured blame outcome at BFC^

Blaming the line `c4` deletes returns `c1`; the verifier reports `GI703`. In
SZZG-0043 the same line is only reachable through the merge's second parent
and `--first-parent` hides `c1`; here `c1` is on `main`'s only line.

## What a tool must do

Report `c1` and behave exactly as on SZZG-0043. A tool that behaves differently
between the twins is reacting to the presence of the merge commit, not to the
change that introduced the bug.

## Factors

- `fast-forward`
- `feature-branch`
