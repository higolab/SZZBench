# SZZ-0175: Addition-only fix for a missing break in a switch

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `addition-only-fix`, `missing-break` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks how SZZ implementations behave when the fault is a
missing `break;` in a `switch` and the bug-fixing commit is *addition-only*:
it inserts exactly one line and deletes nothing. The BIC is the commit that
added the incomplete `case`.

## Commit structure

- `c0`: Adds `EscalationLevels.levelFor(String priority)` with a complete
  `switch` (`low`, `normal`, `high`, `default`), each case ending in `break;`.
- `c1`: Adds the `URGENT` level and a `case "urgent":` without `break;`, so
  urgent tickets fall through into `case "high":` and receive level 3 instead
  of 4. This is the BIC. Its diff is `+3 -0`.
- `c2`: Unrelated addition at the top of `levelFor` (blank priorities return
  the default level).
- `c3`: Inserts `break;` after `level = URGENT;`. This is the BFC. Its diff
  is `+1 -0`.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes no line, so `git blame` at `c3^` has nothing to
trace: **none** (ghost). A deleted-line-based SZZ returns an empty candidate
set.

## What a tool must do

To pass, a tool has to relate the inserted `break;` to its context, for
example by blaming the neighbouring lines `level = URGENT;` and
`case "high":` at `c3^`. The first belongs to `c1`; the second belongs to
`c0` and must be rejected, e.g. because `c0` did not create the fall-through.
