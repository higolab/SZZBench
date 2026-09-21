# SZZ-0116: Multiple-hunk bug-fixing commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `multiple-hunk-bfc`, `same-origin-hunks` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

This is the **same-origin control** for multi-hunk bug-fixing commits: the
BFC has two hunks in one file, and *both* of them blame the bug-introducing
commit, so returning the union of the hunks is exactly right.
**SZZ-0186 is the mixed-origin variant** of the same shape, where the second
hunk blames a later, non-BIC commit and the union is wrong. A tool that
handles hunks per-hunk must pass here and in SZZ-0186; a tool that blindly
unions hunks passes here and fails SZZ-0186.

Both faults of the BFC are now recorded in the oracle (`B001` and `B002`);
before, only the first hunk was, so a tool reporting the second hunk had no
ground truth to be scored against (issue #5).

## Commit structure

- `c0`: Adds `Scenario0116` with the counter helpers `isNonNegative`,
  `clampToZero` and `next`.
- `c1`: Switches the counter convention: `isNonNegative` rejects zero
  (`value > 0`) and `next` advances by two (`value + 2`). This is the BIC
  for both faults. `clampToZero`, which sits between the two methods, is
  untouched.
- `c2`: Restores the zero-based, single-step convention in two hunks. This
  is the BFC.

## Expected behavior

The expected BFC is `c2`; the required BIC set is `{c1}` for both bugs.
There is no intermediate commit and no distractor.

## Plain blame outcome (measured)

`git diff c2^ c2` is `+2 −2` in one file and has **two hunks** with default
context (`-U3`); the two changed lines are 11 lines apart. `git blame` at
`c2^` returns **`c1`** for the deleted line of *each* hunk
(`return value > 0;` at line 5 and `return value + 2;` at line 16), so the
outcome is **exact**: the union over the hunks is `{c1}` with no extra
candidate. `git blame -C -C` returns `c1` for both lines as well.

## What a tool must do

Return `{c1}`. Basic blame over all deleted lines is sufficient here — the
scenario exists to show that a multi-hunk BFC is not by itself a difficulty,
and to be compared with SZZ-0186, where the identical strategy produces a
false positive.

## Behaviour check

The three public methods were probed over
`value ∈ {Integer.MIN_VALUE, MIN_VALUE+1, -100, -2, -1, 0, 1, 2, 3, 100, MAX_VALUE-2, MAX_VALUE-1, MAX_VALUE}`
(including the wrap-around at `Integer.MAX_VALUE`, where `next` overflows
identically in all snapshots): `c1` differs from `c0` on all 13 inputs
(`next` everywhere, `isNonNegative` at `value == 0`), and `c2` agrees with
`c0` on all 13.
