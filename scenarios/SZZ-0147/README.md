# SZZ-0147: Duplicate normalization statements

## Purpose

This scenario contains duplicate or similar statements so that line-level oracle interpretation is intentionally harder.

## Commit structure

- `c0`: initial implementation with duplicate-looking statement
- `c1`: introduces the fault
- `c2`: fixes the fault

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`; duplicate statements may trigger warning-level ambiguity.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `ambiguous-blame`
- `duplicate-statement`
