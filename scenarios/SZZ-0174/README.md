# SZZ-0174: Addition-only fix for a missing null check

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `addition-only-fix`, `missing-null-check` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario checks how SZZ implementations behave when the bug is an
omitted null guard and the bug-fixing commit is *addition-only*: its
first-parent diff contains only `+` lines (no deleted and no re-indented
line). Such fixes are "ghost" BFCs for line-based SZZ, which has no deleted
line to blame.

## Commit structure

- `c0`: Adds `ContactFormatter` with `formatName` and `formatPhones`.
- `c1`: Adds `displayLabel(Map<String, String> labels, String key)`, which
  dereferences the result of `labels.get(key)` without checking for null.
  This is the BIC.
- `c2`: Unrelated addition in `formatPhones` (skips empty phone entries).
- `c3`: Inserts `if (label == null) { return key; }` before the dereference.
  This is the BFC. The diff is `+3 -0`.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes no line, so `git blame` at `c3^` has nothing to
trace: **none** (ghost). A deleted-line-based SZZ returns an empty candidate
set for this scenario.

## What a tool must do

To pass, a tool has to map the *added* guard to the code it protects, for
example by blaming the surrounding context lines (`String label =
labels.get(key);`, `return label.toUpperCase();`), or by identifying the
commit that added the enclosing method `displayLabel`. Both lead to `c1`.
