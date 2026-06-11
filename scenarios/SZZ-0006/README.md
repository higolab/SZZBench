# SZZ-0006: Arithmetic sign error

## Purpose

This scenario introduces a bug by changing `return value + 1;` to `return value - 1;` and later restores the correct implementation.

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
- `arithmetic-error`
