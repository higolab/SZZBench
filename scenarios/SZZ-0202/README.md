# SZZ-0202: Mutable default argument: the fault is on the def line

## Purpose

Python evaluates a default argument once, when the `def` statement runs, so
`tags=[]` is a single list shared by every call that omits `tags`. The
"simplification" that introduces it looks like a cleanup — three lines
removed, one changed — and the faulty statement is the function header
itself. Tools that skip declaration lines as non-executable (the Java habit
of ignoring method signatures) are left with nothing to blame; the BFC's only
deleted line *is* the def line.

## Commit structure

- `c0`: `src/tagging/tags.py` with `with_tag(tag, tags=None)`, which creates a
  fresh list when `tags` is `None` and appends `tag` to it.
- `c1`: "Simplify with_tag: default to an empty list directly": the header
  becomes `def with_tag(tag, tags=[]):` and the two guard lines are removed.
  This is the **BIC**.
- `c2`: Restores the `None` sentinel and the guard. This is the **BFC**; its
  first-parent diff is `+3 -1`, and the deleted line is
  `def with_tag(tag, tags=[]):`.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.

## Behaviour at each commit

Three calls in one interpreter, `with_tag("a")`, `with_tag("b")`,
`with_tag("c", ["x"])`:

| commit | results |
|---|---|
| `c0` | `['a']`, `['b']`, `['x', 'c']` |
| `c1` | `['a']`, `['a', 'b']`, `['x', 'c']` |
| `c2` | `['a']`, `['b']`, `['x', 'c']` |

At `c1` the second call returns the list the first call filled: the default
is shared. `git blame` at `c2^` attributes the deleted def line to `c1`.

## Factors

- `single-bic`
- `single-bfc`
- `line-modification`
- `mutable-default-argument`
- `signature-line-fault`
