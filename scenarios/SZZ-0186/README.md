# SZZ-0186: Multi-hunk BFC whose hunks blame different commits

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `mixed-origin-hunks`, `multiple-hunk-bfc`, `tangled-bfc` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

SZZ-0116 is the control in which both hunks of a two-hunk BFC belong to the
BIC. This scenario is the mixed-origin variant: the two hunks of the BFC
blame different commits and only one of them is the BIC. Both hunks contain
semantic code (no comment or whitespace lines), so cosmetic-line filters do
not help.

## Commit structure

- `c0`: Adds `PagingCalculator` with `pageCount`, `offset` and `hasNext`.
- `c1`: Replaces the ceiling division in `pageCount` with
  `itemCount / pageSize + 1`, which is one too high whenever `itemCount` is
  a multiple of `pageSize` (and returns 1 for zero items). This is the BIC.
- `c2`: Clamps negative page numbers in `offset` (`Math.max(0, page - 1)`).
  Correct, unrelated to the fault.
- `c3`: Restores the ceiling division in `pageCount` and, in a second hunk,
  replaces `c2`'s multiplication in `offset` with `Math.multiplyExact`. This
  is the BFC. Its diff is `+2 -2` in one file, two hunks.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes two lines in two hunks. `git blame` at `c3^`
returns **`c1`** for the `pageCount` hunk and **`c2`** for the `offset`
hunk: the BIC is reached, with one extra candidate.

## What a tool must do

To pass, a tool must decide per hunk whether it is part of the fix, e.g. by
relating the commit message ("fix the page count") to the `pageCount`
method, by recognising the `offset` hunk as a behaviour-preserving hardening
for non-overflowing inputs, or by ranking candidates instead of returning
the union.
