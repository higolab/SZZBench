# SZZ-0037: Incorrect clamp lower bound

## Purpose

This scenario introduces a bug by changing `return Math.max(value, lower);` to `return Math.min(value, lower);` and later restores the correct implementation.

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
