# SZZ-0080: Zero-denominator guard deletion introduces a division by zero

## Purpose

The BIC deletes the `denominator == 0` guard, so `divide` throws `ArithmeticException` instead of returning
0, and the BFC restores the guard. No exception handler is involved: the removed code is a plain early-return
branch.

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
- `line-deletion-bic`
- `exception-handling`
