# SZZ-0168: Cause can be inferred from test failure

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S7` Context, message, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `test-context`, `message-evidence` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
<!-- /szzbench:header -->

## Summary

Evaluates a case where the BFC is a small parser change and the specific cause is clarified by a failing test message.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c3

## Notes

- Moved from SZZG-0114 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario declares `repository.build_system: none`, so the regression test at `c2` is textual
  evidence a tool reads rather than a suite anyone runs. It therefore asserts with a plain
  `AssertionError` carrying the expected and actual dates, instead of importing JUnit, which would
  only make the snapshot uncompilable.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
