# SZZ-0209: Path-traversal check weakened, then rewritten three times before the fix (depth-3 line history)

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `deep-line-history`, `rewrite-depth-3`, `basic-blame-distractor`, `api-misuse` |
| oracle | `exact_set`; required `c1`; known distractors `c2`, `c3`, `c4` · BFC `c5` |
<!-- /szzbench:header -->

## Purpose

A vulnerability-style multi-hop case (issue #24): the fault is a weakened
input check, and the faulty line is rewritten three times before it is
fixed, each time without changing behaviour. [SZZ-0178](../SZZ-0178/README.md)
has two such rewrites; here plain blame is three steps of line history away
from the BIC, and the three steps are of three different kinds — a constant
extracted, a parameter renamed, braces dropped — so no single blame option
(`-w`, `-M`, `-C`) shortcuts the chain.

## Commit structure

- `c0`: `UploadPathPolicy.accepts(path)` rejects any path containing `..` and otherwise requires the
  `uploads/` prefix.
- `c1`: Changes `contains("..")` to `startsWith("..")`: only a *leading* parent reference is rejected, so
  `uploads/../etc/passwd` is accepted. This is the **BIC**.
- `c2`: Extracts the literal into `PARENT_SEGMENT` — the line becomes `startsWith(PARENT_SEGMENT)`.
- `c3`: Renames the parameter `path` to `relativePath` — the line changes again.
- `c4`: Drops the braces around the single-statement guard — the line changes a third time.
- `c5`: Changes `startsWith` back to `contains`. This is the **BFC**.

## Expected behavior

The expected BFC is `c5` and the expected BIC is `c1`. `c2`, `c3` and `c4` are known distractors.

## Behaviour at each commit

`accepts("uploads/report.txt")`, `accepts("../etc/passwd")`,
`accepts("uploads/../etc/passwd")` (`tests/test_deep_line_history.py`):

| commit | result |
|---|---|
| `c0` | true false false |
| `c1` | true false **true** |
| `c2` | true false **true** |
| `c3` | true false **true** |
| `c4` | true false **true** |
| `c5` | true false false |

## Plain blame outcome

`c5` deletes one line, `if (relativePath.startsWith(PARENT_SEGMENT)) return false;`, and `git blame`
at `c5^` attributes it to **`c4`**. Following the line history: the line `c4` replaced was written by
`c3`; the line `c3` replaced was written by `c2`; the line `c2` replaced was written by `c1`. Three hops.
`-w` does not help (none of the rewrites is whitespace-only) and neither does `-M`/`-C` (nothing moved
between files).

## What a tool must do

Report `c1`. A tool has to follow the line history recursively, or recognise each of `c2`, `c3` and
`c4` as behaviour-preserving (a constant extraction, a rename, a brace change) and continue past it,
stopping at the commit where `startsWith` first replaced `contains`.
