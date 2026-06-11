# SZZ-0013: Logical disjunction error

## Purpose

This scenario introduces a bug by changing `return isAdmin || isOwner;` to `return isAdmin && isOwner;` and later restores the correct implementation.

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
- `logical-operator-error`
