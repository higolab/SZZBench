# SZZG-0054: Fixed on main but unfixed on release

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G4` Branch, merge, cherry-pick, backport, and release branches |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `release-branch`, `partial-fix-propagation`, `unfixed-release`, `wrong-variable` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
| defeats | none (a control: every declared cheap rule may solve it) |
| graph features | 2 branches |
<!-- /szzbench:header -->

## Purpose

`c1` spells out the grand total "component by component" and types `tax`
twice — the total counts tax twice and shipping never. The `release` branch is
cut from that state. `main` fixes the line; `release` continues with follow-up
notes and never receives the fix. One BIC, one BFC, and a branch on which the
bug is still live at its tip.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 5 commits, 2 refs) are unchanged.

## Commit structure (generated)

```text
* 45a0094  2023-09-21  Add the release follow-up note                          (c4, release; still buggy)
* 5503c00  2023-09-05  Cut the release branch                                  (c2, release; docs/release-note.md)
| * cc0e52f  2023-09-14  Add shipping, not tax twice, to the grand total on main  <- BFC (c3, main)
|/
* 55264e7  2023-09-04  Spell out the grand total component by component        <- BIC (c1)
* f7bcb54  2023-08-28  Add the invoice totals                                  (c0)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c3` (main only); `bug_instances` records `release` as `unfixed` at `c4`

## Measured behaviour and blame

`grand(100, 20, 15)`: **135** at `c0`; **140** at `c1`, `c2` and `c4` — the
release tip is still wrong; 135 at `c3`. `c3` deletes one line (`return net +
tax + tax;`, line 6); blame at `c3^` returns `c1` (verifier `GI703`).

## What a tool must do

Report `c1` for the fix `c3`. The scenario also asks a branch-aware tool to
notice that `release` contains the BIC and no fix: the bug instance there is
open, which SZZ alone does not say.
