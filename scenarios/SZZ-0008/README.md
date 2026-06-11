# SZZ-0008: Division denominator error

## Purpose

This scenario introduces a bug by changing `return total / count;` to `return total / (count - 1);` and later restores the correct implementation.

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
