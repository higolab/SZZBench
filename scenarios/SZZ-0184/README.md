# SZZ-0184: BFC also modifies existing test lines owned by another commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S4` BFC-side noise and tangled commits |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `test-line-noise`, `multi-file-bfc` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

SZZ-0117 covers a BFC that *adds* a test file. This scenario covers a BFC
that *modifies existing test lines*: the fix to the production code is
accompanied by a change to an assertion that a test-only commit wrote. A
tool that blames every deleted line reports the test-only commit as a second
BIC; a tool that filters test files (or test-only commits) obtains the exact
answer.

## Commit structure

- `c0`: Adds `WordCounter.count(...)` (splits on `\s+`) and a plain-Java
  test class `WordCounterTest` under `src/test/java`.
- `c1`: Changes the split pattern to a single space, so consecutive spaces
  and tabs produce empty tokens that are counted as words. This is the BIC.
- `c2`: Adds the test method `blankInputHasNoWords` (test-only commit).
- `c3`: Restores `split("\\s+")` and changes the assertion in
  `blankInputHasNoWords` from `count("")` to `count(" \t ")`. This is the
  BFC. Its diff is `+2 -2` across `src/main/java` and `src/test/java`.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes two lines. `git blame` at `c3^` returns
**`c1`** for the production line and **`c2`** for the test line: the BIC is
reached, with one extra candidate.

## What a tool must do

To pass, a tool must exclude the test-file hunk from candidate generation
(path filter on `src/test/java`, or a filter on test-only commits) or
otherwise rank the production hunk above the test hunk.
