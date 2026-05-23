# SZZ-0069: Synchronization guard omission

## Purpose

This scenario represents an omission bug: the method is introduced without a necessary synchronization guard, and the bug-fixing commit adds the missing statement.

## Commit structure

- `c0`: initial class
- `c1`: introduces the method without the synchronization guard
- `c2`: adds the missing synchronization guard

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. Line-level evaluation is unavailable because this is an omission bug.

## Factors

- `single-bic`
- `single-bfc`
- `omission-bug`
- `line-addition-fix`
