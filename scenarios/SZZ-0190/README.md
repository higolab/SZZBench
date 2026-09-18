# SZZ-0190: Unit change and a later consumer that assumes the old unit

## Purpose

The first scenario of the **discriminating tier** built on the measured axis:
the answer is two commits, and only one of them is reachable by blaming what
the fix deletes. Here the unreachable commit changed the *unit* of a constant,
and reaching it means following the value the fixed expression reads.

## Commit structure

```text
c0  Add the session cache expiry check          TTL = 60 (seconds)
c1  Express the session TTL in milliseconds     TTL = 60000, expired() updated   <- BIC
c2  Document the session cache fields           class comment only (distractor)
c3  Report when the session should be refreshed adds refreshAfterSeconds() = TTL / 2   <- BIC
c4  Convert the refresh interval back to seconds TTL / 2000                       <- BFC
```

`c1` is behaviour-preserving on its own: it converts the constant and its only
consumer together, so nothing is wrong yet. `c3` adds a second consumer that
divides as if the constant were still seconds, and only then does
`refreshAfterSeconds()` return 30000 instead of 30.

## Expected BIC / BFC

- BICs: `c1` and `c3` (`true_positives`, `exact_set`, no allowed false positives)
- BFC: `c4`

Both are necessary. Without `c3` there is no second consumer and no bug;
without `c1` the constant is still 60 and `TTL / 2` is correct.

## Measured blame outcome at BFC^ (from the generated repository)

The fix deletes exactly one line:

```text
"return TTL / 2;"    plain -> c3    -w -> c3    -w -C -C -> c3
```

So blame returns `{c3}` — half the answer — and `c1` is not reachable from the
deleted line by any blame variant.

## What a tool must do to pass

Report exactly `{c1, c3}`. Returning `{c3}` alone is a false negative on `c1`;
reaching `c1` means following `TTL` from the expression the fix repairs to the
commit that changed what the constant means.

## Baseline outcome (measured)

No baseline of any declared family solves this scenario — metadata, position,
shape or blame. It is declared `tier: discriminating` and `szzbench baselines`
confirms the declaration.
