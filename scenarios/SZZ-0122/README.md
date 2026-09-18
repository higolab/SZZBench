# SZZ-0122: BFC touches an extra file besides the fault

## Purpose

This scenario evaluates SZZ behavior when the bug-fixing commit touches the fixed source file and creates an additional file using `write_file`.

## Commit structure

- `c0`: Initial correct implementation
- `c1`: Introduce bug
- `c2`: Fix bug and add an extra source file

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `multi-file-bfc`
