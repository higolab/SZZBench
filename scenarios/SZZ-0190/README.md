# SZZ-0190: Unit change and a later consumer that assumes the old unit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `discriminating` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `line-modification`, `value-flow`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`, `c3` · BFC `c4` |
| defeats | `blame`, `shape`, `position` |
<!-- /szzbench:header -->

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

`c1` converts the constant and its only consumer together, so a caller that
passes milliseconds gets the same answer as before and nothing else reads `TTL`
yet. (It is not behaviour-preserving in the narrow sense: `expired(int)` keeps
its signature while its parameter changes unit, so the same numeric argument
means something different — 6 of the 24 probes below change at `c1`. Nothing in
the repository passes the old unit.) `c3` adds a second consumer that divides
as if the constant were still seconds, and only then does
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
