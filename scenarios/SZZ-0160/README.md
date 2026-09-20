# SZZ-0160: Fault in a private helper reached only through its caller

## Purpose

The public method delegates to a private helper, and both the BIC and the BFC edit the helper's boundary
check. Plain line-level blame on the line the fix deletes reaches the BIC exactly, so this is a control for
the delegation shape rather than a case that needs the caller for context.

## Commit structure

- `c0`: initial implementation
- `c1`: introduces the bug
- `c2`: BFC with message: Fix caller-visible boundary failure

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `context-aware`
