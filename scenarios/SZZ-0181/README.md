# SZZ-0181: Omission fix with an adjacent unrelated line edit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `line-addition-fix`, `tangled-bfc`, `adjacent-edit-noise` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario asks what a tool should return when the bug is an omission and
the only line the bug-fixing commit deletes is noise. The BFC inserts the
missing guard and, in the same hunk, edits the adjacent line. That adjacent
line was last touched by a rename commit, not by the BIC, so deleted-line
blame returns a wrong commit with full confidence.

## Commit structure

- `c0`: Adds `SessionTokenParser` with `tokenFrom(...)` and
  `issuedByUs(...)`.
- `c1`: Adds `expiresAt(String token)`, which splits the token on `.` and
  reads `parts[1]` without checking that a second segment exists. This is
  the BIC.
- `c2`: Renames the local `payload` to `expirySegment` (two lines). This is
  a refactoring, not a BIC.
- `c3`: Inserts `if (parts.length < 2) { throw ... }` after the split and
  changes `String expirySegment = parts[1];` to
  `String expirySegment = parts[1].trim();`. This is the BFC. Its diff is
  `+4 -1`; the deleted line is `c2`'s.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line, `String expirySegment = parts[1];`.
`git blame` at `c3^` on that line returns **`c2`**: plain blame misses the
BIC and reports a false positive.

## What a tool must do

To pass, a tool must recognise that the deleted line is not the fault
(the `.trim()` change is unrelated to the added guard) and attribute the fix
to the omitted check instead, e.g. by blaming the context of the added lines
(`String[] parts = token.split("\\.");` belongs to `c1`) or by tracing the
enclosing method `expiresAt` to the commit that added it. Simply returning
the blame of every deleted line yields `{c2}` and fails.
