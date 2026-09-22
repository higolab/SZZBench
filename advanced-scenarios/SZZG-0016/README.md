# SZZG-0016: Original and clone fixed together

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G2` Clone, copy propagation, and origin-vs-direct BIC |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `null-check-omission`, `copy-propagation` |
| oracle | default: `exact_set`; required `c1`; related origins `c0` · `origin-aware`: `relaxed_with_related`; required `c1`; acceptable `c0` (credit 0.5) · BFC `c2` |
| graph features | operation `copy_file`; 2 BICs; 2 fault sites; 1 evaluation variant (`origin-aware`); `clone_relationships` |
<!-- /szzbench:header -->

## Purpose

`TagNormalizer.normalize` trims and lower-cases its argument with no null
guard, so a missing tag throws `NullPointerException`. `c1` copies the file to
`LabelNormalizer.java` and changes only the class declaration, so the faulty
statement enters the second file byte-for-byte. One commit, `c2`, adds the guard
to both. For the fixed `LabelNormalizer` instance the direct BIC is the copy
commit `c1`; `c0` is the origin, which also wrote the `TagNormalizer` instance
repaired by the same fix. A tool that scores the fix as a whole sees both
commits and has to say which one it means.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 3 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* 03f1b6c  2023-10-03  Normalize a missing tag or label to the empty string   <- BFC (c2; both files)
* 2f02e18  2023-09-25  Copy the tag normalizer into a label normalizer        <- direct BIC (c1; copy_file + class rename)
* 57f92ae  2023-09-22  Add the tag normalizer                                 <- origin (c0)
```

## Expected BIC / BFC

- default: `required: [c1]`, `related_origins: [c0]`
- `origin-aware`: `relaxed_with_related`, `c0` at 0.5
- BFC: `c2`

## Measured behaviour and blame

| commit | `TagNormalizer.normalize(null)` | `LabelNormalizer.normalize(null)` | `normalize(" Urgent ")` (both) |
|---|---|---|---|
| `c0` | throws `NullPointerException` | — | `urgent` |
| `c1` | throws `NullPointerException` | **throws `NullPointerException`** | `urgent` |
| `c2` | `""` | `""` | `urgent` |

`c2` deletes one line in each file. The `LabelNormalizer.java` line (line 5)
blames to `c1`; the `TagNormalizer.java` line blames to `c0`, the root commit.
The verifier reports `GW703` for this scenario as it did before the rewrite:
the check blames the first declared fault, which is the origin instance.

## What a tool must do

Report `c1` for the fixed copy. Blame over the whole fix returns `{c0, c1}`;
under the default oracle `c0` is a false positive (an origin), under
`origin-aware` it is tolerated. A copy-aware tool notices that `c1` added the
line to `LabelNormalizer.java` by copying it from `TagNormalizer.java`.
