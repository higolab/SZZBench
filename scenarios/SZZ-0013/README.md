# SZZ-0013: Duplicate fault statement

## Purpose

This scenario checks ambiguity when the same faulty statement appears in multiple
locations at the BIC.

## Commit structure

- `c0`: Introduces two validators with identical correct return statements.
- `c1`: Changes both statements to the same faulty text. This is the BIC.
- `c2`: Fixes only the `acceptsAge` occurrence. This is the BFC.

## Expected behavior

Commit-level SZZ should report `c1`. Line/entity-level analysis needs context to
distinguish the fixed occurrence from the duplicate occurrence.
