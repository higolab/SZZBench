# SZZ-0200: Wrong threshold constant in a Python module

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `python` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `wrong-constant` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

The Python twin of SZZ-0021. The history is the same three commits with the
same authors, dates and messages; only the language differs. Running a tool
on both twins separates a language dependency (the tool handles `.java` but
not `.py`: file filters, comment stripping, tokenisation) from an algorithmic
one. This is the first scenario whose `repository.language` is not `java`.

## Commit structure

- `c0`: `src/grading/scores.py` with `passes(score)` returning `score >= 80`
  (plus an empty `src/grading/__init__.py`).
- `c1`: Changes the threshold to `score >= 90`. This is the **BIC**.
- `c2`: Restores `score >= 80`. This is the **BFC**.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Behaviour at each commit

`[passes(s) for s in (79, 80, 85, 89, 90)]`, run against the snapshot of each
commit:

| commit | result |
|---|---|
| `c0` | `[False, True, True, True, True]` |
| `c1` | `[False, False, False, False, True]` |
| `c2` | `[False, True, True, True, True]` |

The BFC's first-parent diff deletes one line, `return score >= 90`, and
`git blame` at `c2^` attributes it to `c1`. Every snapshot byte-compiles
(`tests/test_python_scenarios.py`, which also checks that the twins' authors,
dates and messages agree commit by commit).
