# SZZ-0018: Rounding direction error

## Purpose

This scenario introduces a bug by changing `return (value + 9) / 10;` to `return value / 10;` and later restores the correct implementation.

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
