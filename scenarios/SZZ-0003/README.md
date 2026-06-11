# SZZ-0003: Constant value change

## Purpose

This scenario checks whether SZZ can identify a bug introduced by changing a
constant-like return value.

## Commit structure

- `c0`: Returns the correct retry attempt count.
- `c1`: Changes the count from `3` to `2`. This is the BIC.
- `c2`: Restores the count to `3`. This is the BFC.

## Expected behavior

SZZ should report `c1` as the bug-introducing commit for bug `B001`.
