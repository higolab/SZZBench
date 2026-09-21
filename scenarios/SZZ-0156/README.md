# SZZ-0156: Multiple overloaded methods

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `boundary-condition`, `duplicate-statement` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Summary

`Range.contains` has several overloads and only the `int` overload is faulty: `c1` makes its
boundary check exclusive and `c2` restores it, while the other overloads stay correct throughout. A
tool must attribute the fix to the overload it repairs, not to the method name.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c2

## Notes

- Moved from SZZG-0109 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
