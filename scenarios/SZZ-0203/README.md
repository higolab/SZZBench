# SZZ-0203: Dictionary lookup added without a key check (Python omission twin of SZZ-0047)

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `python` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `line-addition-fix`, `missing-key-check` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

The Python counterpart of SZZ-0047. A function is added that indexes a
dictionary directly; an unknown key raises `KeyError`. The fix adds a
two-line guard and deletes nothing, so the BFC is addition-only and blame has
no deleted line to follow. In Java the same omission returns `null` from
`Map.get`; in Python it raises, which is why the fix is a guard rather than a
default.

## Commit structure

- `c0`: `src/carriers/names.py` with the `CARRIERS` table.
- `c1`: Adds `carrier_name(code)` returning `CARRIERS[code]`. This is the
  **BIC**: the guard for unknown codes is missing.
- `c2`: Inserts `if code not in CARRIERS: return "unknown carrier"` before the
  lookup. This is the **BFC**; its first-parent diff is `+2 -0`.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. `line_level.available`
is `false`: the fault is an omission.

## Behaviour at each commit

`carrier_name("UPS")` and `carrier_name("XYZ")`:

| commit | `"UPS"` | `"XYZ"` |
|---|---|---|
| `c0` | function does not exist | — |
| `c1` | `United Parcel Service` | `KeyError: 'XYZ'` |
| `c2` | `United Parcel Service` | `unknown carrier` |

The BFC deletes no line, so B-SZZ returns the empty set; a tool must
attribute an added guard to the commit that added the unguarded statement
(`c1`), for example by blaming the surrounding lines or the enclosing
function.

## Difficulty

`medium` by the floor rule of `decisions/vocabulary.md` §4 (decided 2026-09-22): plain
first-parent blame on the lines the fix deletes is `addition-only` for this scenario, and a scenario may not
declare less than that class sets. The author's grade was `easy`.
