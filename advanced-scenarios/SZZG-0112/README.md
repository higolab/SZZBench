# SZZG-0112: Non-UTF-8 file

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G8` Non-source, binary, generated, and scalability edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `encoding`, `non-utf8-file`, `binary-file`, `config-bic`, `config-bfc` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
| graph features | operation `write_binary_file` |
<!-- /szzbench:header -->

## Purpose

The fault and the fix both live in `config/range-limits.properties`, a
CP1252-encoded file (its `label=café` line carries the byte `0xE9`, which is not
valid UTF-8 on its own). `ConfigBackedRange` reads `min` and `max` from that
file, so the BIC's narrowing of the limits is a behaviour change the code
shows, not a change to an unread asset. The scenario checks two things: that a
method attributes a fault in a configuration file the code consumes, and that
SZZBench's own tooling handles a non-UTF-8 file without assuming every changed
file is UTF-8 text.

Until 2026-09-22 nothing in the repository read the file, so the declared BIC
could not cause a fault the code showed (issue #23). The effect is now measured
below.

## Expected history

```text
c0: create CP1252-encoded boundary configuration
c1: introduce boundary bug in the non-UTF-8 config
c2: fix the non-UTF-8 config
```

- `c0`: `ConfigBackedRange` loads `config/range-limits.properties` with `Properties.load`
  and answers `contains(value)` from the configured `min=0` / `max=10`.
- `c1` (BIC): rewrites the file with `min=1` / `max=9`; the label line is unchanged.
- `c2` (BFC): rewrites the file with `min=0` / `max=10` again.

## Measured behaviour

`new ConfigBackedRange()` at each commit, run from the snapshot root
(`tests/test_config_scenarios.py`):

| commit | `contains(0)` | `contains(1)` | `contains(9)` | `contains(10)` | `label()` |
|---|---|---|---|---|---|
| `c0` | true | true | true | true | 4 characters, the fourth `U+00E9` |
| `c1` | **false** | true | true | **false** | same |
| `c2` | true | true | true | true | same |

The label is read as `café` at every commit because `Properties.load` decodes
the stream as ISO-8859-1, in which the CP1252 byte `0xE9` is `é`.

## Expected BIC / BFC

- BIC: `c1` (`exact_set`, `required: [c1]`)
- BFC: `c2`

## Why this needs `scenario.graph.yml`

The non-UTF-8 file is modeled with `write_binary_file` so that invalid UTF-8 bytes can be represented safely.
The fault and fix entries therefore carry a `description` and an `encoding` instead of a `statement`, and the
verifier's text-based statement lookup is not used for them.

## What a tool must do

Report `c1`. Git treats the file as text with ordinary line structure:
`git diff --numstat c1 c2` reports `2 2 config/range-limits.properties`, the
zero-context hunk is `-min=1 -max=9 +min=0 +max=10`, and `git blame` on both
deleted lines at `c2^` returns `c1` — the `blame-deleted-lines` baseline solves
the scenario (`tests/test_config_scenarios.py` asserts all three). What the
encoding tests is a tool's *decoding*, not its diffing: a tool that decodes
every changed file as UTF-8 fails on the `0xE9` byte of the `label` line and
loses the file, and a tool that only inspects source files has no candidate at
all.

## Evaluation points

- Whether SZZ identifies c1 as the BIC for the encoded configuration change.
- Whether non-UTF-8 file content does not break parsing, generation, or verification.
- Whether the expected_szz exact-set policy is applied correctly.
