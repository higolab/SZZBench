# SZZ-0160: Fault in a private helper reached only through its caller

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S1` Basic semantic line changes |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `delegated-call` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

The public method delegates to a private helper, and both the BIC and the BFC edit the helper's boundary
check. Plain line-level blame on the line the fix deletes reaches the BIC exactly, so this is a control for
the delegation shape rather than a case that needs the caller for context.

## Commit structure

- `c0`: initial implementation
- `c1`: introduces the bug
- `c2`: BFC with message: Fix caller-visible boundary failure

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`.
