# SZZG-0108: Binary file change

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `binary-file`, `wrong-constant` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | operation `write_binary_file` |
<!-- /szzbench:header -->

## Purpose

The fix's diff contains a file no textual tool can read. `c1` raises the
thumbnail edge from 256 to 512 pixels and writes `51` — a dropped digit. `c2`
sets it to 512 and, in the same commit, refreshes a binary placeholder asset.
The BIC is an ordinary one-line change; the question is whether the binary
entry in the fix's diff derails a tool.

Rewritten 2026-09-21 (issue #13) from the shared `Range.contains` template; the
history shape, oracle and coverage dimensions (`bic_depth` 1, one distractor on
the fault file, 3 commits, 1 ref) are unchanged.

## Commit structure (generated)

```text
* 63e950b  2023-06-22  Use a 512-pixel thumbnail edge and refresh the placeholder asset  <- BFC (c2; assets/placeholder.bin + Thumbnails.java)
* 01569d4  2023-06-19  Raise the thumbnail edge to 512 pixels                            <- BIC (c1; writes 51)
* 2924a0d  2023-06-12  Add the thumbnail settings                                        (c0; 256)
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c2`

## Measured behaviour and blame

`maxEdgePixels()` is 256 at `c0`, **51** at `c1`, 512 at `c2`. The fix's diff
has two entries — `Binary files a/assets/placeholder.bin and
b/assets/placeholder.bin differ` and a one-line change to `Thumbnails.java`
(line 5); blame at `c2^` returns `c1` (verifier `GI703`).

## What a tool must do

Report `c1`. A diff parser must skip the binary entry rather than fail on it;
the source hunk is one deleted line whose blame is direct.
