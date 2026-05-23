# SZZ-0012: Basic multiple bug-introducing commits

## Purpose

This scenario represents a basic multi-BIC case. The bug is caused by a
callee-side change and a later caller-side change.

## Commit structure

- `c0`: Introduces safe division.
- `c1`: Adds an unsafe divide mode. This is a contributing BIC.
- `c2`: Calls the unsafe mode. This is the directly observable BIC.
- `c3`: Switches the caller back to safe mode. This is the BFC.

## Expected behavior

The oracle lists both `c1` and `c2` as bug-introducing commits. A line-based SZZ
may naturally identify `c2`, while a multi-cause analysis should also consider
`c1`.
