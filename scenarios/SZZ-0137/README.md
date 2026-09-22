# SZZ-0137: Null handling and empty handling changed separately

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `line-modification` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Purpose

This scenario requires treating two bug-introducing commits as contributing to the same later fix.

`hasText(String value)` is implemented with two named checks. Two independent commits each weaken one of the
checks; a single later commit restores both. Both weakening commits are BICs of the one bug fixed by the BFC.

## Intended contract

`hasText` must accept a string only when it is neither `null` nor empty:

| Input | Expected | `c0` | `c1` | `c2` (before BFC) | `c3` (after BFC) |
|---|---|---|---|---|---|
| `null` | `false` | `false` | `NullPointerException` | `true` | `false` |
| `""` | `false` | `false` | `false` | `true` | `false` |
| `"a"` | `true` | `true` | `true` | `true` | `true` |

(The columns were obtained by compiling every generated commit with `javac` and running a small harness.)

## Commit structure

- `c0`: correct implementation

  ```java
  boolean notNull = value != null;
  boolean notEmpty = notNull && !value.isEmpty();
  return notNull && notEmpty;
  ```

- `c1` (BIC 1): replaces the null check with a constant: `boolean notNull = true;`
  (`hasText(null)` now throws `NullPointerException` in the emptiness check)
- `c2` (BIC 2): collapses the emptiness check into the null check on a different line: `boolean notEmpty = notNull;`
  (`hasText("")` and `hasText(null)` now return `true`)
- `c3` (BFC): restores both lines to their `c0` text in one commit

## Oracle

- Expected BFC: `c3`
- Expected BIC set: `{c1, c2}` (exact set; both are required)
- Faulty statements at `c3^`: `boolean notNull = true;` (from `c1`) and `boolean notEmpty = notNull;` (from `c2`)

## Expected plain-blame behaviour

The BFC modifies exactly two lines of `Scenario0137.java`. `git blame` at `c3^` on those lines (checked on the
generated repository):

| Line at `c3^` | Blamed commit |
|---|---|
| `boolean notNull = true;` | `c1` |
| `boolean notEmpty = notNull;` | `c2` |

Plain line-level blame therefore reaches both BICs. The difficulty of this scenario is not the blame step but
the aggregation: an SZZ implementation must report both commits as the BIC set rather than collapsing to the
most recent one or to a single "primary" BIC.

## History

- 2026-09 (issue 1): rebuilt. The previous version started from `return true;`, added `value != null` in `c1`
  and `&& !value.isEmpty()` in `c2`, and had the BFC restore `return true;`, so the "fix" removed the
  validation and the two "BICs" were improvements. The oracle (`{c1, c2}` -> `c3`) is unchanged.
