# SZZ-0170: BIC is a test-only commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S8` Non-source, configuration, test-only, and file-level edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `test-only-bic`, `evaluation-variant` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Summary

Evaluates a bug where the bug-introducing commit changes only a test oracle, not production code.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c2

## Notes

- Moved from SZZG-0003 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
