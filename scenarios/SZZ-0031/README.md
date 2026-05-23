# SZZ-0031: Wrong threshold constant

## Purpose

This scenario introduces a bug by changing `return score >= 80;` to `return score >= 90;` and later restores the correct implementation.

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
