# SZZ-0166: Signature-only cleanup between BIC and BFC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S7` Context, message, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `message-evidence`, `intermediate-cleanup` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

Between the BIC and the BFC, an unrelated tidy-up commit touches the same file
and the same method, but not the faulty line. The commit is genuine and its
message says exactly what it does. The scenario checks that a tool which reads
commit messages or patch context does not attribute the fix to that neighbour.

## Commit structure

- `c0`: `check(int attempts, int limit)` returns `attempts < limit`.
- `c1`: Changes the comparison to `attempts <= limit`, so one attempt beyond the
  limit is accepted. This is the BIC.
- `c2`: Makes `check` static; it reads no instance state. Only the signature
  line changes. Message: *Make check static; it reads no instance state*.
- `c3`: Restores `attempts < limit`. This is the BFC. Message: *Stop accepting
  one attempt beyond the configured limit*.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (`return attempts <= limit;`). `git blame`
at `c3^` on that line returns **`c1`**: plain blame reaches the BIC. `c2` never
touched that line, so it is not a blame distractor; it is a distractor only for
tools that weigh commit messages or nearby edits.
