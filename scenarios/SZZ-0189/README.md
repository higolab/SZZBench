# SZZ-0189: Missing close() fixed by an addition whose only deleted line is a distractor's comment

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `line-addition-fix`, `missing-close`, `cosmetic-line-noise` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

SZZ-0185 tests the cosmetic-line filter when the BFC deletes comment and
blank lines *together with* the faulty statement. This scenario is the
inverse: the BFC deletes *only* such a line. The fault is an omitted
`writer.close()`; the fix adds it and, in the same commit, removes a stale
comment that a distractor commit placed above the method. After a
MA-/RA-SZZ-style filter for comment-only lines nothing remains to blame
(ghost); without the filter, plain blame returns exactly one wrong commit.

## Commit structure

- `c0`: Adds `Report` and `ReportExporter.exportRows(...)`, which writes
  with try-with-resources.
- `c1`: Adds `ReportExporter.exportSummary(...)`, which opens a
  `BufferedWriter` outside try-with-resources and never closes it, so the
  buffered content is never flushed and the handle leaks. This is the BIC
  (`+8 -0`).
- `c2`: Inserts the comment `// Consumed by the nightly archive job.` above
  `exportSummary`. Comment only.
- `c3`: Adds `writer.close();` at the end of `exportSummary` and removes
  `c2`'s comment line. This is the BFC. Its diff is `+1 -1` in two hunks;
  the deleted line is the comment.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line, the comment. `git blame` at `c3^` on
that line returns **`c2`**: plain blame misses the BIC and reports a false
positive. With a comment-line filter the deleted-line set is empty:
**none** (ghost).

## What a tool must do

To pass, a tool must first discard the comment-only deleted line (otherwise
`c2` is reported) and then treat the remaining addition-only fix like a
ghost BFC: relate the added `writer.close();` to the surrounding code (the
context lines `writer.newLine();` and the closing `}` of `exportSummary`
belong to `c1`), or trace the enclosing method to the commit that added it.
Both lead to `c1`.
