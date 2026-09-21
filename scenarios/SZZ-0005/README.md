# SZZ-0005: Java annotation syntax change

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `language-specific-syntax-change`, `annotation-change` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This scenario checks a language-specific syntax change: the fault is in a Java
annotation argument rather than in an ordinary method-body statement.

## Commit structure

- `c0`: Defines the `@Required` annotation and marks `userId` as required.
- `c1`: Changes the annotation to optional. This is the BIC.
- `c2`: Restores the required annotation. This is the BFC.

## Expected behavior

SZZ should report `c1` as the bug-introducing commit for `B001`.
