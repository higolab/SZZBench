# SZZG-0007: Line moved and duplicated

## Purpose

Evaluate a bug whose faulty line is introduced in `Range.java`, then moved into a new `RangeUtils.java` and, in
the same commit, duplicated into a second helper `Bounds.java`, before both copies are fixed by one BFC.

The required BIC remains `c1`. Commit `c2` is propagation history only: it moves and duplicates an already
buggy line and must not replace the original BIC.

## Commit history

```text
c1: create Range with a buggy contains check (BIC)
c2: move contains from Range to a new RangeUtils class and duplicate the same check into a new Bounds.within
c3: fix both copies in RangeUtils.java and Bounds.java (BFC)
```

## Commit table

| Commit | Branch | Parents | Role | Description |
|---|---|---|---|---|
| `c1` | `main` | none | bug_introducing | Creates `Range` with `contains` returning `value > min && value < max` (bounds excluded) and `length`. |
| `c2` | `main` | `c1` | refactoring | Removes `contains` from `Range.java` (which keeps `length`); adds `RangeUtils.contains` with the identical faulty line (move); adds `Bounds.within` with the identical faulty line (copy). |
| `c3` | `main` | `c2` | bug_fixing | Changes both copies to `value >= min && value <= max`. |

## Code states

Behaviour at each commit (obtained by compiling every generated commit with `javac` and running a small
harness); `(5, 5, 10)` and `(10, 5, 10)` are the boundary cases:

| Method | `c1` | `c2` | `c3` |
|---|---|---|---|
| `Range.contains(5, 5, 10)` / `(10, 5, 10)` | `false` / `false` (buggy) | method absent | method absent |
| `RangeUtils.contains(5, 5, 10)` / `(10, 5, 10)` | class absent | `false` / `false` (buggy) | `true` / `true` |
| `Bounds.within(5, 5, 10)` / `(10, 5, 10)` | class absent | `false` / `false` (buggy) | `true` / `true` |

The `c2` diff removes 4 lines from `Range.java` and creates `RangeUtils.java` and `Bounds.java`; the `c3` diff
is `Bounds.java | 2 +-` and `RangeUtils.java | 2 +-`. No faulty copy remains at HEAD.

## Oracle

- Expected BIC: `c1` (exact set)
- Bug-fixing commit: `c3` (`complete_fix`; it fixes both copies)
- Fault `F001`: `return value > min && value < max;` in `Range.java` (`c1`)
- Fix `X001`: `return value >= min && value <= max;` in `RangeUtils.java` (moved copy)
- Fix `X002`: `return value >= min && value <= max;` in `Bounds.java` (duplicated copy)
- `c2` is listed as `related_but_not_correct`: it is where plain blame stops for both fixed lines.

Bug instances (`bug_instances` in the YAML):

| Instance | File | State |
|---|---|---|
| `B001-origin` | `Range.java` | introduced by `c1`, removed by `c2` (moved out) |
| `B001-moved` | `RangeUtils.java` | created by `c2` from the origin line, fixed by `c3` |
| `B001-duplicate` | `Bounds.java` | created by `c2` from the origin line, fixed by `c3` |

## Expected plain-blame behaviour

Both lines modified by the BFC live in files created by `c2`. Checked on the generated repository at `c3^`:

| Tool | `RangeUtils.java` line 5 | `Bounds.java` line 5 |
|---|---|---|
| `git blame` (plain) | `c2` | `c2` |
| `git blame -C -C -C1` (copy detection across files created in the same commit, low threshold) | `c1`, via `Range.java` | `c1`, via `Range.java` |
| `git log -S'return value > min && value < max;'` | `c3`, `c2`, `c1` (oldest hit is `c1`) | same |

Plain blame therefore returns the move/copy commit `c2` for both fixed lines, not the BIC. Reaching `c1`
requires refactoring- or clone-aware tracing: recognising that `c2` moved the line from `Range.java` into
`RangeUtils.java` and copied it into `Bounds.java`, then continuing the line history in `Range.java`. That is
the intended difficulty. The graph verifier reports `GW701` ("fault.statement not present in final BFC
parent") for the same reason: the fault text is no longer in `Range.java` at `c3^`.

## Files

```text
SZZG-0007/
|-- scenario.graph.yml
`-- README.md
```

## History

- 2026-09 (issue 2): `c2` was previously expressed with `move_entity` and `copy_entity`, which the generator
  realises as whole-file copies with a header line that leave the source untouched; `Range.java` still held
  the buggy line at HEAD and `RangeUtils.java` did not compile. The move and the copy are now expressed with
  explicit `write_file` operations, the duplicate lives in `Bounds.java`, the BFC fixes both copies (`X001`,
  `X002`), the factors `move_entity`/`copy_entity` were replaced by `method_move`/`copy_propagation`, and
  commit messages were rewritten to realistic, role-neutral text. The oracle (BIC `c1`, BFC `c3`) is unchanged.
