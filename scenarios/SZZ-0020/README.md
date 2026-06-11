# SZZ-0020: Wrong fallback number

## Purpose

This scenario introduces a bug by changing `return value < 0 ? 0 : value;` to `return value < 0 ? -1 : value;` and later restores the correct implementation.

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
- `wrong-constant`
