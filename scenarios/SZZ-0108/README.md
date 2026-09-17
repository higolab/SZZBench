# SZZ-0108: CRLF-like full file rewrite

## Purpose

This scenario checks whether an SZZ implementation survives a line-ending
conversion between the BIC and the BFC. The intermediate commit stores the
Java source with CRLF endings, which rewrites **every** line of the file,
including the faulty one, without changing a single character of code.

Unlike the other S3 scenarios in this range this is not a control: plain
`git blame` at the BFC parent returns the line-ending commit and misses the
BIC.

## Commit structure

- `c0`: Adds `com.example.io.LineBudget` (LF, 20 lines) with `fits(int)`
  (`return lineCount <= maxLines;`) and `overflow(int)`.
- `c1`: Changes the bound to `return lineCount < maxLines;`. This is the
  **BIC**: a page of exactly `maxLines` lines is reported as not fitting
  although `overflow()` computes `0` for it. The file is still LF.
- `c2`: Adds `.editorconfig` (`end_of_line = crlf` for `*.java`) and rewrites
  `LineBudget.java` with CRLF endings. `git diff --numstat c1 c2` reports
  `20 20` for the Java file and `git diff --ignore-cr-at-eol` reports no
  change for it at all, so the carriage returns are the only difference.
- `c3`: Restores `lineCount <= maxLines`. This is the **BFC**; the file is
  CRLF before and after, so its first-parent diff is `+1 -1` on the faulty
  line only.

Byte-level evidence (`git show <commit>:src/main/java/com/example/io/LineBudget.java | xxd`):
`c0` and `c1` contain 0 CR bytes and 20 LF bytes; `c2` and `c3` contain 20 CR
and 20 LF bytes. At `c2` the first line reads
`7061 636b ... 696f 3b0d 0a` (`package com.example.io;\r\n`), where the same
line at `c1` ends `3b0a`.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line,
`        return lineCount < maxLines;` (line 11).

- `git blame` at `c3^` attributes that line — in fact all 20 lines of the
  file — to `c2`, the line-ending commit.
- `git blame -w` at `c3^` attributes it to `c1`. Measured with
  git 2.50.1: `-w` treats the trailing carriage return as whitespace and does
  see through the conversion, so whitespace-insensitive blame is enough here.

Blame class of plain blame: **miss** — B-SZZ returns `{c2}` and the expected
`c1` is absent.

## What a tool must do

Look through the line-ending conversion. Any of the following is sufficient:
blame with `-w` (measured above), pre-normalize line endings before diffing,
skip commits whose diff is empty under `--ignore-cr-at-eol` when walking back,
or follow the line history (`git log -L`) instead of a single blame step.
A tool that reports `{c2}` has reported a pure formatting commit as the cause
of a boundary fault.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `robustness`
- `line-ending-noise`
- `full-file-rewrite`
