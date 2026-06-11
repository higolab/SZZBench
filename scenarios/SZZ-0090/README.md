# SZZ-0090: Guard clause addition after BIC

## Purpose

This scenario introduces a bug by changing `return value >= min && value <= max;` to `return value > min && value < max;` and later restores the correct implementation.

## Commit structure

- `c0`: initial correct implementation
- `c1`: introduces the bug
- `c2`: Add guard clause after bug introduction
- `c3`: fixes the bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `guard-clause-after-bic`
