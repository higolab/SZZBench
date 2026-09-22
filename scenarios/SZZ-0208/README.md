# SZZ-0208: Configuration key rename as the BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S8` Non-source, configuration, test-only, and file-level edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `config-bic`, `config-key-rename`, `cross-artifact-fix`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

The BIC changes no value: it renames the key `retry.delay.unit` to
`retry.delayUnit` in `config/retry.properties`. `RetryPolicy` keeps reading the
old key, gets nothing, and falls back to its default of `milliseconds`, so the
configured two-second delay becomes two milliseconds. The fix teaches the code
the new key. It is the configuration-side counterpart of the `.gitattributes`
BIC of [SZZG-0134](../../advanced-scenarios/SZZG-0134/README.md) and the
key-rename case issue #23 asked for: the fault is a rename in a non-source
file, and the fix is in code that never mentions the old name again.

## Commit structure

- `c0`: `config/retry.properties` (`retry.delay.value=2`, `retry.delay.unit=seconds`) and
  `RetryPolicy`, which reads the unit with `getProperty("retry.delay.unit", "milliseconds")`.
- `c1`: Renames the key to `retry.delayUnit`; the value `seconds` is unchanged. This is the **BIC**; it
  touches only the properties file.
- `c2`: Adds a `describe()` method to `RetryPolicy`. A distractor that touches the file the fix will
  touch, but not the line.
- `c3`: Reads `retry.delayUnit` instead of `retry.delay.unit`. This is the **BFC**; it touches only Java.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`. `c2` is a known distractor.

## Behaviour at each commit

`new RetryPolicy().delayMillis()`, run from the root of each snapshot
(`tests/test_config_scenarios.py`):

| commit | result |
|---|---|
| `c0` | `2000` |
| `c1` | **`2`** |
| `c2` | **`2`** |
| `c3` | `2000` |

## Plain blame outcome

The BFC's first-parent diff deletes one line of `RetryPolicy.java`, the
`getProperty("retry.delay.unit", …)` call, and `git blame` at `c3^` attributes
it to **`c0`**. The BIC changed only the properties file, which the fix does not
open, so blame on the fix's deleted line cannot reach it; the `blame-deleted-lines`
baseline answers `c0`, and the file's last toucher before the fix, `c2`, is the
distractor. `szzbench verify` still reports `I700`, because its check blames the
declared fault line — `retry.delayUnit=seconds` in the properties file at `c3^`,
which `c1` wrote — and that line is reachable even though the fix never opens
the file.

## What a tool must do

Report `c1`. Blame answers `c0` and the last-toucher heuristic answers `c2`;
neither opens `config/retry.properties`. Reaching `c1` means noticing that the
fix changed which key is read and asking which commit last changed that key in
the configuration.
