# SZZ-0142: Authentication and token checks introduced separately

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

`authorized(boolean authenticated, boolean tokenValid)` combines two named checks. Two independent commits each
bypass one of the checks ("temporary" bypasses that were never reverted); a single later commit restores both.
Both bypass commits are BICs of the one bug fixed by the BFC.

## Intended contract

`authorized` must be `true` only when the caller is authenticated **and** the token is valid:

| `(authenticated, tokenValid)` | Expected | `c0` | `c1` | `c2` (before BFC) | `c3` (after BFC) |
|---|---|---|---|---|---|
| `(true, true)` | `true` | `true` | `true` | `true` | `true` |
| `(false, true)` | `false` | `false` | `true` | `true` | `false` |
| `(true, false)` | `false` | `false` | `false` | `true` | `false` |
| `(false, false)` | `false` | `false` | `false` | `true` | `false` |

(The columns were obtained by compiling every generated commit with `javac` and running a small harness.)

## Commit structure

- `c0`: correct implementation

  ```java
  boolean authOk = authenticated;
  boolean tokenOk = tokenValid;
  return authOk && tokenOk;
  ```

- `c1` (BIC 1): hard-codes the authentication check: `boolean authOk = true;`
  (unauthenticated callers with a valid token are accepted)
- `c2` (BIC 2): hard-codes the token check on a different line: `boolean tokenOk = true;`
  (every call is now accepted)
- `c3` (BFC): restores both lines to their `c0` text in one commit

## Oracle

- Expected BFC: `c3`
- Expected BIC set: `{c1, c2}` (exact set; both are required)
- Faulty statements at `c3^`: `boolean authOk = true;` (from `c1`) and `boolean tokenOk = true;` (from `c2`)

## Expected plain-blame behaviour

The BFC modifies exactly two lines of `Scenario0142.java`. `git blame` at `c3^` on those lines (checked on the
generated repository):

| Line at `c3^` | Blamed commit |
|---|---|
| `boolean authOk = true;` | `c1` |
| `boolean tokenOk = true;` | `c2` |

Plain line-level blame therefore reaches both BICs. The difficulty of this scenario is the aggregation: an SZZ
implementation must report both commits as the BIC set rather than collapsing to the most recent one or to a
single "primary" BIC.

## History

- 2026-09 (issue 1): rebuilt. The previous version started from `return true;`, added `authenticated` in `c1`
  and `&& tokenValid` in `c2`, and had the BFC restore `return true;`, so the "fix" removed authorization and
  the two "BICs" were improvements. The oracle (`{c1, c2}` -> `c3`) is unchanged.
