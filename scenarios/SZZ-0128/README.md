# SZZ-0128: Extract helper after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S5` Refactoring, move, and rename after BIC |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `extract-method-after-bic`, `basic-blame-distractor` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

An extract-method refactoring moves the faulty line out of an `if` block
into a new private helper. The statement text is unchanged, but the move
costs it one level of indentation, so for `git blame` the line belongs to
the extracting commit and the BIC is missed. The bug-fixing commit repairs
the comparison **inside the helper** and does not inline the extraction
again.

Two defects of the previous version are repaired: the code did not compile
(the identifier `min` was never declared, so javac failed at c0, c1 and c3 —
issue #10), and the BFC restored the initial file text, which deleted the
whole extracted helper and made a textbook SZZ return `{c1, c2}` (issue #6).

## Commit structure

- `c0`: Adds `ShipmentGate.readyToShip(...)`, which computes the available
  units inside the `if (paymentCleared)` block and compares them with
  `minimumUnits`.
- `c1`: Makes that comparison strict (`availableUnits > minimumUnits`), so an
  order holding exactly the minimum is held back. This is the BIC.
- `c2`: Extracts the two statements of the `if` block into the private helper
  `hasEnoughUnits(pickedUnits, reservedUnits)`. Behaviour-preserving; the
  faulty statement text is unchanged but sits four spaces further left.
- `c3`: Restores the inclusive comparison inside the helper. This is the
  BFC; its diff is `+1 −1` in one hunk.

## Expected behavior

The expected BFC is `c3` and the required BIC set is exactly `{c1}`. `c2` is
a known distractor: it is what basic blame returns, but it did not introduce
the fault.

## Plain blame outcome (measured)

`git diff -U0 c3^ c3` deletes exactly one line,
`return availableUnits > minimumUnits;` — none of the lines `c2` added (the
helper signature, the delegating call) is deleted. `git blame` at `c3^` on
the deleted line returns **`c2`**, so the outcome is **miss**. Measured
variants on the same line at `c3^`:

| command | result |
|---|---|
| `git blame` | `c2` |
| `git blame -M`, `-M20`, `-M10` | `c2` |
| `git blame -C`, `-C -C`, `-C -C -C`, `-C1 -C -C` | `c2` |
| `git blame -w -M` | **`c1`** |
| `git blame -w -C -C` | **`c1`** |
| `git log -L 24,24:<file>` (first step) | `c2` |

Copy/move detection alone is not enough here: the moved chunk is short, and
its indentation changed, so git only follows it when whitespace is ignored
as well. `szzbench generate` reports the informational finding
`W703: basic git blame reaches <c2>, not expected BIC(s) ['c1']`, which is
the designed property of the scenario (as in SZZ-0081 and SZZ-0178).

## What a tool must do

To pass, a tool has to follow the extracted statement across `c2` — through
whitespace-insensitive move detection (`-w -M` / `-w -C -C`), through a
recursive line history, or through a refactoring detector that reports the
extract-method and maps the new helper body back to the original block.
Returning `{c1, c2}` counts as a false positive
(`false_positives_allowed: []`).

## Behaviour check

`readyToShip` keeps its signature (the extracted helper is private), so all
four snapshots were probed with the same driver over 720 input combinations:
`minimumUnits ∈ {Integer.MIN_VALUE, 0, 1, 5, 20, Integer.MAX_VALUE}`
(constructor), `pickedUnits ∈ {Integer.MIN_VALUE, -1, 0, 1, 4, 5, 6, 20, 21, Integer.MAX_VALUE}`,
`reservedUnits ∈ {Integer.MIN_VALUE, -1, 0, 1, 5, Integer.MAX_VALUE}` and
`paymentCleared ∈ {false, true}`, including the combinations in which
`pickedUnits - reservedUnits` overflows. `c1` differs from `c0` in 22 of
them, `c2` reproduces `c1` exactly (the extraction is behaviour-preserving),
and `c3` agrees with `c0` in all 720.
