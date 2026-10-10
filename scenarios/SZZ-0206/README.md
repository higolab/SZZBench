# SZZ-0206: BOM-only rewrite of the faulty line

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `python` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `wrong-constant`, `robustness`, `bom-only-rewrite`, `basic-blame-distractor` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

The third member of the "the bytes of the faulty line changed but the code
did not" family, after whitespace (SZZ-0083) and line endings (SZZ-0108). A
UTF-8 byte order mark can only sit at the start of a file, so the faulty
statement is the first line of a Python module — a constant, which Python
allows where Java would demand a `package` line. The noise commit re-saves
the file with a BOM: three bytes prepended to line 1, nothing else. Unlike
the CRLF case, `git blame -w` does **not** see through it, because a BOM is
not whitespace.

## Commit structure

- `c0`: `src/limits/upload.py`, whose first line is `MAX_UPLOAD_KB = 20480`,
  and `accepts(size_kb, name)`, which compares against the constant.
- `c1`: "Raise the upload ceiling to 60 MB" writes `MAX_UPLOAD_KB = 6144`: 60
  MB is 61440 KB, and a digit was dropped. This is the **BIC**; the ceiling
  falls from 20 MB to 6 MB.
- `c2`: "Save upload.py with the editor's default encoding (UTF-8 with BOM)":
  `write_file` with `encoding: utf-8-sig` and identical content. This is the
  planted distractor.
- `c3`: `MAX_UPLOAD_KB = 61440`. This is the **BFC**; the file keeps its BOM.

## Byte-level evidence

`git show <commit>:src/limits/upload.py | head -1 | xxd`:

| commit | first bytes of line 1 | blob size |
|---|---|---|
| `c0` | `4d41 585f …` (`MAX_UPLOAD_KB = 20480`) | 258 |
| `c1` | `4d41 585f …` (`MAX_UPLOAD_KB = 6144`) | 257 |
| `c2` | `efbb bf4d 4158 5f…` (BOM + `MAX_UPLOAD_KB = 6144`) | 260 |
| `c3` | `efbb bf4d 4158 5f…` (BOM + `MAX_UPLOAD_KB = 61440`) | 261 |

`git diff --numstat c1 c2` reports `1 1` for the file, and the hunk is
`-MAX_UPLOAD_KB = 6144` / `+<EF BB BF>MAX_UPLOAD_KB = 6144`: the only
difference between `c1` and `c2` is the three-byte BOM. `git diff -w c1 c2`
still shows the hunk. Every snapshot byte-compiles; CPython accepts a UTF-8
BOM at the start of a source file.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is declared as a
known distractor.

## Behaviour at each commit

`MAX_UPLOAD_KB` and `[accepts(k, "a.pdf") for k in (6144, 6145, 20480, 61440, 61441)]`:

| commit | result |
|---|---|
| `c0` | `20480 [True, True, True, False, False]` |
| `c1` | `6144 [True, False, False, False, False]` |
| `c2` | `6144 [True, False, False, False, False]` |
| `c3` | `61440 [True, True, True, True, False]` |

## Measured plain-blame outcome at BFC^

`git diff -U0 c3^ c3` deletes exactly one line, line 1.

- `git blame` at `c3^` attributes it to `c2`, the re-save.
- `git blame -w` at `c3^` attributes it to `c2` as well (measured with
  git 2.50.1; the same holds for `-M` and `-C`).

Blame class of plain blame: **miss** — B-SZZ returns `{c2}`. The verifier
reports this as W703 ("basic git blame reaches c2, not the expected BIC"),
as it does for SZZ-0108: the finding *is* the scenario.

## What a tool must do

Compare decoded text rather than bytes, or skip a commit whose diff is empty
once both sides are decoded (`git diff --textconv` with a BOM-stripping
filter, or a pre-pass that strips U+FEFF), or follow the line one step
further (`git log -L1,1:src/limits/upload.py` lists `c3`, `c2`, `c1`, `c0`).
A tool that reports `{c2}` has blamed an encoding re-save for a wrong
constant.

## Difficulty

`hard` by the floor rule of `decisions/vocabulary.md` §4 (decided 2026-09-22): plain
first-parent blame on the lines the fix deletes is `miss` for this scenario, and a scenario may not
declare less than that class sets. The author's grade was `medium`.
