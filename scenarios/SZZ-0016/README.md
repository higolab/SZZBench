# SZZ-0016: Min max swapped

## Purpose

This scenario introduces a bug by changing `return Math.max(left, right);` to `return Math.min(left, right);` and later restores the correct implementation.

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
- `wrong-variable`
