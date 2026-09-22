# SZZ-0207: Code BIC fixed by a configuration change

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S8` Non-source, configuration, test-only, and file-level edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `config-bfc`, `cross-artifact-fix`, `string-comparison`, `blame-unreachable-bic` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

The mirror image of [SZZ-0172](../SZZ-0172/README.md). There the fault is a
configuration value and the fix is in Java; here the fault is in Java and the
fix is a configuration value. `RetryPolicy` reads `retry.delay.unit` from
`config/retry.properties` and multiplies the configured delay by 1000 when the
unit means seconds. The BIC changes which *spelling* of the unit the code
recognises; the BFC changes the configuration to that spelling. Nothing the fix touches was
written by the BIC, so a tool has to cross from the configuration file back to
the code that interprets it (issue #23).

## Commit structure

- `c0`: `config/retry.properties` (`retry.delay.value=2`, `retry.delay.unit=seconds`) and
  `RetryPolicy`, whose `delayMillis()` returns `configuredDelay * 1000` when the unit equals
  `"seconds"` and `configuredDelay` otherwise.
- `c1`: Compares the unit against `TimeUnit.SECONDS.name()`, which is `SECONDS`. The configuration
  still says `seconds`, so the comparison fails and the delay is read as 2 milliseconds. This is the
  **BIC**; it touches only Java.
- `c2`: Adds `docs/retry-units.md`, which says the unit is a `TimeUnit` constant name. A distractor that
  touches neither the fault nor the fix.
- `c3`: Changes the configuration to `retry.delay.unit=SECONDS`. This is the **BFC**; it touches only
  the properties file.

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

The BFC's first-parent diff deletes one line, `retry.delay.unit=seconds` in
`config/retry.properties`, and `git blame` at `c3^` attributes it to **`c0`**,
the commit that wrote the configuration. `c1` changed only `RetryPolicy.java`,
which the fix does not open, so blame on the fix's deleted line cannot reach
the BIC under any variant; the `blame-deleted-lines` baseline answers `c0`.
`szzbench verify` still reports `I700`, because its check blames the declared
fault line in `RetryPolicy.java` at `c3^`, which `c1` wrote and nothing
rewrote — the fault line is reachable, the fix's deleted line is not.

## What a tool must do

Report `c1`. Blame answers `c0`; the file the fix touches has one previous
author, and it is not the BIC. Reaching `c1` means asking which code reads the
key the fix changed and which commit last changed what that code accepts — the
case of the value, here.
