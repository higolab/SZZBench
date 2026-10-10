# SZZ-0154: One BFC fixes multiple BICs for one composite bug

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `composite-bug`, `multiple-fault-locations` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Summary

A single composite range-check bug is created by two separate BICs. The first BIC breaks the lower-bound helper and the second BIC breaks the upper-bound helper. A single BFC fixes both faults together.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1, c2
- Bug-fixing commit: c3

## Notes

- Moved from SZZG-0035 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
