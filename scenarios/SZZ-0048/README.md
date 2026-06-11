# SZZ-0048: Bounds check omission bug

## Purpose

This scenario checks an omission bug where a bounds check is missing from an
array access method.

## Commit structure

- `c0`: Introduces an empty class.
- `c1`: Adds an array access method without a bounds check. This is the BIC.
- `c2`: Adds the missing bounds check. This is the BFC.

## Expected behavior

The expected BIC is `c1`, but line-level deleted-line SZZ is not directly
applicable because the fix is primarily an added guard.
