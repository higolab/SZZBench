# SZZ-0005: Java annotation syntax change

## Purpose

This scenario checks a language-specific syntax change: the fault is in a Java
annotation argument rather than in an ordinary method-body statement.

## Commit structure

- `c0`: Marks `userId` as required.
- `c1`: Changes the annotation to optional. This is the BIC.
- `c2`: Restores the required annotation. This is the BFC.

## Expected behavior

SZZ should report `c1` as the bug-introducing commit for `B001`.
