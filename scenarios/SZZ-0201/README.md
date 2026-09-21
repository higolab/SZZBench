# SZZ-0201: Floor division mistaken for a typo: `//` becomes `/` in an index expression

## Purpose

A one-character, Python-specific semantic fault. `//` is floor division and
`/` is true division in Python 3; a developer who takes the doubled slash for
a typo turns an integer index into a float and breaks every call. A tool that
normalises operators, or diffs at word level and treats `/` and `//` as one
token, loses the fault entirely.

## Commit structure

- `c0`: `src/search/midpoint.py` with `middle(items)`
  (`return items[len(items) // 2]`) and `bisect_index(items, target)`, which
  also uses `//`.
- `c1`: "Fix the doubled slash in middle()": `len(items) // 2` becomes
  `len(items) / 2`. This is the **BIC**. `bisect_index` is untouched.
- `c2`: Restores `//`. This is the **BFC**.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Behaviour at each commit

`middle([1, 2, 3])` and `bisect_index([1, 3, 5], 4)` at each snapshot:

| commit | `middle([1, 2, 3])` | `bisect_index([1, 3, 5], 4)` |
|---|---|---|
| `c0` | `2` | `2` |
| `c1` | `TypeError: list indices must be integers or slices, not float` | `2` |
| `c2` | `2` | `2` |

The BFC deletes one line, `return items[len(items) / 2]`, and `git blame` at
`c2^` attributes it to `c1`. Every snapshot byte-compiles: the fault is a
runtime error, not a syntax error.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `wrong-operator`
