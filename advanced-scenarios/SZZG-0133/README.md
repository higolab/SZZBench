# SZZG-0133: A binary asset is changed by both the BIC and the BFC

## Purpose

[SZZG-0108](../SZZG-0108/README.md) changes a binary in the fix only, next to a
Java change. Here the fault and the fix are both replacements of the same binary
asset, the code demonstrably depends on the asset's bytes, and no text line
changes anywhere after `c0`. A tool has to attribute a binary change with no
line-level evidence at all.

## Commit structure (generated)

```text
* 7e096f1  Re-export the palette with its PAL header      <- BFC (c2)   src/main/resources/palette.bin
* 6aa5cba  Re-export the palette from the design tool     <- BIC (c1)   src/main/resources/palette.bin
* 4b10764  Add the palette loader and the default palette (c0)          Palette.java + palette.bin
```

`git show --stat` reports `Bin 13 -> 13 bytes` for the asset in both `c1` and
`c2`; neither commit touches a text file.

## The bytes

The asset is a four-byte header — `PAL` and a version — followed by three RGB
triples. `c1`'s export zeroes the header; `c2` restores it (version 2).

```text
c0  50 41 4C 01 | FF 00 00 | 00 FF 00 | 00 00 FF
c1  00 00 00 00 | FF 00 00 | 00 FF 00 | 00 00 FF
c2  50 41 4C 02 | FF 00 00 | 00 FF 00 | 00 00 FF
```

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c2`
- `line_level.available: false` — there is no line.

## Measured behaviour and blame

`Palette.isValid()` / `colours()`: `true 3` at `c0`, **`false 0`** at `c1`,
`true 3` at `c2` (`tests/test_twins_and_transitions.py` loads the resource from
the classpath at every commit). The fault and fix entries carry no `statement`,
so the verifier has no line to blame and performs no blame check.

## What a tool must do

Report `c1`. Line-level SZZ has nothing to work with; commit-level reasoning over
which commits touched the file the fix touched finds `c1` and `c0`, and only `c1`
changed the bytes the loader validates.

## Factors

- `binary-file`
- `binary-bic`
- `binary-bfc`
- `no-line-level-evidence`
