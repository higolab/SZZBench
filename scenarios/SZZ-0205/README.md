# SZZ-0205: f-string conversion rewrites the faulty format line after the BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `python` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `wrong-variable`, `deep-line-history`, `basic-blame-distractor`, `string-format-rewrite` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

A modernisation rewrite that no normalisation undoes. The faulty line is a
`%`-formatted string whose two arguments are in the wrong order; the noise
commit converts it to an f-string and faithfully keeps the wrong order. The
old and new spellings share no token sequence (`"%d of %d items shipped" %
(total, shipped)` versus `f"{total} of {shipped} items shipped"`), so neither
whitespace-insensitive blame nor token-level diffing connects them. The fix
swaps the two names inside the f-string.

## Commit structure

- `c0`: `src/shipping/summary.py` with `progress_line(shipped)` returning
  `"%d items shipped" % shipped`.
- `c1`: "Show the order total in the progress line": the signature becomes
  `progress_line(shipped, total)` and the body
  `return "%d of %d items shipped" % (total, shipped)` — the tuple lists
  `total` first while the template reads shipped-of-total. This is the
  **BIC**.
- `c2`: "Convert the progress line to an f-string":
  `return f"{total} of {shipped} items shipped"`. Same output for every
  input. This is the planted distractor.
- `c3`: `return f"{shipped} of {total} items shipped"`. This is the **BFC**.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known
distractor; the rewrite is declared by the factor `string-format-rewrite`.

## Behaviour at each commit

`progress_line(3, 12)`:

| commit | output |
|---|---|
| `c0` | `TypeError` (one-argument signature) |
| `c1` | `12 of 3 items shipped` |
| `c2` | `12 of 3 items shipped` |
| `c3` | `3 of 12 items shipped` |

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes one line, line 5,
`    return f"{total} of {shipped} items shipped"`.

- `git blame` at `c3^` attributes it to `c2`.
- `git blame -w` at `c3^` attributes it to `c2`.

Blame class of plain blame: **miss** — B-SZZ returns `{c2}`.

## What a tool must do

Continue past a rewrite that changes every token of the line: follow the
line's history through `c2` (`git log -L`, or blame the line again at `c2^`),
or judge `c2` behaviour-preserving by evaluating both spellings. Text-level
tricks that rescue whitespace, line-ending and BOM rewrites (SZZ-0083,
SZZ-0108, SZZ-0206) do not apply here.
