# SZZ-0033: Empty string predicate reversed

## Purpose

This scenario introduces a bug by changing `return !value.isEmpty();` to `return value.isEmpty();` and later restores the correct implementation.

## Commit structure

- `c0`: initial correct implementation
- `c1`: introduces the bug
- `c2`: fixes the bug

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `boolean-negation`
