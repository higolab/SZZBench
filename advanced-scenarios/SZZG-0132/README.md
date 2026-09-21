# SZZG-0132: The fix message names the rewrite commit that blame also returns

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `misleading-fix-message`, `rewrite-after-bic`, `basic-blame-distractor`, `semantics-required` |
| oracle | `exact_set`; required `c1`; related but not correct `c2` · BFC `c3` |
| graph features | none: a linear history with one bug and an exact-set oracle, kept in the graph suite for its category |
<!-- /szzbench:header -->

## Purpose

SZZ-0158 and SZZ-0159 have misleading fix messages whose references are vague
or unresolvable, and SZZ-0192 has blame landing on an equivalence-preserving
rewrite. Here both happen at once and agree: the fix's subject quotes the
rewrite's subject verbatim, and blame on the fixed line returns the rewrite. A
tool that trusts either signal — or both, because they corroborate each other —
is wrong; only comparing behaviour across the snapshots finds the cause.

## Commit structure (generated)

```text
* 50b6888  Fix the zero delay before the first retry left by "Name the backoff step"   <- BFC (c3)
* edafd22  Name the backoff step                                                       (c2, behaviour-preserving)
* e9e4002  Count retry attempts from one                                               <- BIC (c1)
* 4eb1658  Add the retry backoff                                                       (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- `related_but_not_correct`: `c2` — named by the fix, returned by blame, changed no behaviour
- BFC: `c3`

## Measured behaviour and blame

`delayMillis(1)`: 100 at `c0`, **0** at `c1`, 0 at `c2`, 100 at `c3`. `c2`
moved `attempt - 1` into a named variable; the declared fault statement is
therefore absent at `c3^` and the verifier reports `GW701` (basic blame
unavailable). Blaming the line `c3` deletes (`int step = attempt - 1;`) returns
`c2`. The fix subject contains `"Name the backoff step"`, which resolves to `c2`
and nothing else.

## What a tool must do

Report `c1`. Resolving the quoted subject gives `c2`; blaming the fixed line
gives `c2`; the two agree and are both wrong. The zero delay first appears at
`c1`, and `c2`'s snapshot behaves exactly like `c1`'s.
