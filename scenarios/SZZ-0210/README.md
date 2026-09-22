# SZZ-0210: Size check that overflows, moved into a helper and rewritten twice more before the fix (depth-3 line history across a method extraction)

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S5` Refactoring, move, and rename after BIC |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `deep-line-history`, `rewrite-depth-3`, `method-extract`, `basic-blame-distractor`, `integer-overflow` |
| oracle | `exact_set`; required `c1`; known distractors `c2`, `c3`, `c4` · BFC `c5` |
<!-- /szzbench:header -->

## Purpose

A vulnerability-style multi-hop case (issue #24) in which one of the hops is
a **method extraction**: the faulty expression does not stay on "its" line but
moves into a new private method, so following the line history means
following an expression, not a line number. The fault itself is an integer
overflow in a size check — the kind of arithmetic mistake that turns a limit
into a bypass.

## Commit structure

- `c0`: `UploadLimit.accepts(declaredBlocks, blockSize)` computes the declared size in `long`
  (`(long) declaredBlocks * blockSize`) and compares it with `MAX_BYTES`.
- `c1`: Drops the cast: `declaredBlocks * blockSize` is now an `int` product that wraps for large
  declarations, and a negative product is `<= MAX_BYTES`. This is the **BIC**.
- `c2`: Renames the local `bytes` to `declaredBytes` (two lines, including the faulty one).
- `c3`: Extracts the product into `private long declaredBytes(int, int)`; `accepts` calls it. The faulty
  expression is now on a different line in a different method.
- `c4`: Rewrites the helper to compute a local `product` and return it — the expression's line changes
  a third time.
- `c5`: Restores the `(long)` cast on the product. This is the **BFC**.

## Expected behavior

The expected BFC is `c5` and the expected BIC is `c1`. `c2`, `c3` and `c4` are known distractors.

## Behaviour at each commit

`accepts(1000, 4096)` (about 4 MB) and `accepts(3_000_000, 1024)` (about 3 GB, over the 2 GB limit;
the `int` product is `-1_221_967_872`) — `tests/test_deep_line_history.py`:

| commit | 4 MB | 3 GB |
|---|---|---|
| `c0` | true | false |
| `c1` | true | **true** |
| `c2` | true | **true** |
| `c3` | true | **true** |
| `c4` | true | **true** |
| `c5` | true | false |

## Plain blame outcome

`c5` deletes one line, `long product = declaredBlocks * blockSize;`, and `git blame` at `c5^`
attributes it to **`c4`**. The line `c4` replaced (`return declaredBlocks * blockSize;`) was written
by `c3` — in the helper `c3` created; the product `c3` moved there came from the `accepts` line that
`c2` had rewritten, and that line's product was written by `c1`. Three hops, the middle one across a
method boundary: a line-number-based history stops at `c3`, because before `c3` the helper did not
exist.

## What a tool must do

Report `c1`. A tool has to follow the *expression* `declaredBlocks * blockSize` back through the
extraction — recognising `c3` as a move rather than an origin — and then through the rename to the
commit that dropped the cast.
