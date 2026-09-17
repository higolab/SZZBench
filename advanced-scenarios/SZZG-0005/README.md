# SZZG-0005: Method move between classes

## Purpose

Evaluate whether SZZ can identify the original BIC when the buggy method is moved, unchanged, from one class to
another between the BIC and the BFC. The BIC modifies `Range.java`; the BFC modifies `RangeUtils.java`, a file
that did not exist when the bug was introduced.

## Commit history

```text
c0: create Range with contains and length
c1: introduce boundary bug in Range.contains (BIC)
c2: move contains from Range to a new RangeUtils class (write_file on both files)
c3: fix the boundary bug in RangeUtils.contains (BFC)
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c0` | `main` | none | initial | Creates `Range` with `contains(int, int, int)` (inclusive bounds) and `length(int, int)`. |
| `c1` | `main` | `c0` | bug_introducing | `contains` becomes `return value > min && value < max;` (bounds excluded). |
| `c2` | `main` | `c1` | refactoring | Removes `contains` from `Range.java` (which keeps `length`) and adds it, byte-for-byte identical and still buggy, to the new `RangeUtils.java`. |
| `c3` | `main` | `c2` | bug_fixing | Restores `return value >= min && value <= max;` in `RangeUtils.java`. |

## Code states

Behaviour of `contains(value, min, max)` at each commit (obtained by compiling every generated commit with
`javac` and running a small harness):

| Call | `c0` (`Range`) | `c1` (`Range`, buggy) | `c2` (`RangeUtils`, buggy) | `c3` (`RangeUtils`, fixed) |
|---|---|---|---|---|
| `contains(5, 5, 10)` | `true` | `false` | `false` | `true` |
| `contains(10, 5, 10)` | `true` | `false` | `false` | `true` |
| `contains(7, 5, 10)` | `true` | `true` | `true` | `true` |
| `contains(4, 5, 10)` | `false` | `false` | `false` | `false` |

After `c2`, `Range` no longer has a `contains` method. The `c2` diff is `Range.java | 4 ----` and
`RangeUtils.java | 7 +++++++`, i.e. a genuine move, not a copy.

## Oracle

- Expected BIC: `c1` (exact set)
- Bug-fixing commit: `c3`
- Fault: `return value > min && value < max;` in `Range.java` (`c1`)
- Fix: `return value >= min && value <= max;` in `RangeUtils.java` (`c3`)
- `c2` is listed as `related_but_not_correct`: it is where plain blame stops, but it only moved an already
  faulty line.

## Expected plain-blame behaviour

The BFC modifies one line of `RangeUtils.java`, which was created by `c2`. Checked on the generated repository
at `c3^`:

| Tool | Result for the fixed line |
|---|---|
| `git blame` (plain) | `c2` |
| `git blame -C -C -L 5,5` (copy detection with the default 40-character threshold, line-restricted) | `c2` |
| `git log -L5,5:RangeUtils.java` | `c2` |
| `git blame -C -C -C1` (copy detection across files created in the same commit, low threshold; with or without `-L 5,5`) | `c1`, via `Range.java` |
| `git log -S'return value > min && value < max;'` | `c3`, `c2`, `c1` (oldest hit is `c1`) |

Plain blame therefore returns the move commit `c2`, not the BIC. Reaching `c1` requires refactoring-aware
tracing: recognising that `c2` moved `contains` from `Range.java` to `RangeUtils.java` and continuing the
line history in `Range.java`. That is the intended difficulty of this scenario. The graph verifier reports
`GW701` ("fault.statement not present in final BFC parent") for the same reason: the fault text is no longer in
`Range.java` at `c3^`.

## Difference from SZZG-0006

`SZZG-0006` extracts a new class and splits responsibilities (the source class keeps a delegating call).
`SZZG-0005` moves a single method to another class; the source class keeps its remaining members and has no
reference to the moved method.

## Files

```text
SZZG-0005/
|-- scenario.graph.yml
`-- README.md
```

## History

- 2026-09 (issue 2): the `c2` move was previously expressed with `move_entity`, which the generator realises as
  a whole-file copy (`RangeUtils.java` = header + full copy of `Range.java`, which does not compile) that leaves
  the source untouched, and the BFC fixed `Range.java`. The move is now expressed with explicit `write_file`
  operations, the BFC fixes `RangeUtils.java`, the factor `move_entity` was replaced by `method_move` (plus
  `refactoring`, `post_bic_refactoring`), and commit messages were rewritten to realistic, role-neutral text.
  The oracle (BIC `c1`, BFC `c3`) is unchanged.
