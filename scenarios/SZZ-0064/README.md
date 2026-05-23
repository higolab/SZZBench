# SZZ-0064: Permission check omission

## Purpose

This scenario represents an omission bug: the method is introduced without a necessary permission check, and the bug-fixing commit adds the missing statement.

## Commit structure

- `c0`: initial class
- `c1`: introduces the method without the permission check
- `c2`: adds the missing permission check

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. Line-level evaluation is unavailable because this is an omission bug.

## Factors

- `single-bic`
- `single-bfc`
- `omission-bug`
- `line-addition-fix`
- `security`
