# SZZ-0098: Enum case addition after BIC

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S3` Intermediate noise and history noise |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `enum-change-after-bic`, `plain-blame-control` |
| oracle | `exact_set`; required `c1`; known distractors `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario is an honest **control** for language-specific noise: between the
BIC and the BFC a commit adds one constant to an enum and changes nothing else.
The addition is *relevant* to the fault — it is the reason the fix returns to the
negative form of the check — but it does not touch the faulty line.

## Commit structure

- `c0`: Adds `ThermostatController` with the nested enum `Mode { OFF, HEAT, COOL }`,
  `setMode`, `mode()` and `drawsPower()`, which returns `mode != Mode.OFF`.
- `c1`: Replaces the check with `mode == Mode.HEAT`, dropping `COOL`. This is the
  BIC: a cooling thermostat is reported as drawing no power.
- `c2`: Adds the constant `AUTO` to `Mode` (the `COOL` line gains a comma and one
  line is inserted). No method is touched.
- `c3`: Restores `return mode != Mode.OFF;`. This is the BFC. Its first-parent
  diff is `+1 -1` on a single line; the new enum constant stays.

## Expected behavior

The expected BFC is `c3` and the expected BIC is `c1`.

## Plain blame outcome

`git diff -U0 c3^ c3` deletes one line (`return mode == Mode.HEAT;`).
`git blame` at `c3^` on that line returns **`c1`**: **exact**. The generator's
verification reports `I700` (basic blame reaches the expected BIC).

## What a tool must do

To pass, a tool only has to blame the deleted line. It must not add `c2` to the
candidate set although `c2` is the most recent change to the file and its new
constant is what makes the explicit enumeration untenable; the fault was already
there for `COOL` before `AUTO` existed.

## Verification

- `javac` (JDK 25) compiles the snapshots of `c0`, `c1`, `c2` and `c3`; the enum
  is declared in the same compilation unit and no snapshot switches over it.
- Behaviour probe over the domain that `c0` and `c3` share: each of `OFF`, `HEAT`
  and `COOL` set on a fresh controller (plus the default state before each call)
  and all nine two-step mode sequences over those constants — 16 outputs. The
  `c1` snapshot differs from `c0` whenever the current mode is `COOL` (4 of the
  16 outputs); the `c3` snapshot agrees with `c0` on all 16.
- Contract beyond that domain: `AUTO` exists only from `c2` on, so it cannot be
  compared with `c0`. `c3` reports `drawsPower() == true` for `AUTO`, which is
  the intended contract ("every mode except off draws power") and the reason the
  fix does not enumerate the powered modes.
