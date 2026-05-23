# SZZ-0075: Empty string check omission

## Purpose

This scenario represents an omission bug: the method is introduced without a necessary empty string check, and the bug-fixing commit adds the missing statement.

## Commit structure

- `c0`: initial class
- `c1`: introduces the method without the empty string check
- `c2`: adds the missing empty string check

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. Line-level evaluation is unavailable because this is an omission bug.

## Factors

- `single-bic`
- `single-bfc`
- `omission-bug`
- `line-addition-fix`
