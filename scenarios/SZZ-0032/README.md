# SZZ-0032: Null predicate reversed

## Purpose

This scenario introduces a bug by changing `return value != null;` to `return value == null;` and later restores the correct implementation.

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
