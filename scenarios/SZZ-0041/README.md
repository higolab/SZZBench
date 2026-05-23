# SZZ-0041: Whitespace-only rewrite after BIC with preserved line

## Purpose

This scenario introduces a bug by changing `return value >= min && value <= max;` to `return value > min && value < max;` and later restores the correct implementation.

## Commit structure

- `c0`: initial correct implementation
- `c1`: introduces the bug
- `c2`: Adjust whitespace without changing semantics
- `c3`: fixes the bug

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `whitespace-preserved-after-bic`
