# SZZ-0155: Same bug introduced independently

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S6` Multiple BICs, duplicate faults, and composite faults |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `multi-bic`, `single-bfc`, `boundary-condition`, `duplicate-statement` |
| oracle | `exact_set`; required `c1`, `c2` · BFC `c3` |
<!-- /szzbench:header -->

## Summary

Two commits introduce the same exclusive-boundary fault independently in two methods of
`IndependentRanges`: `c1` in one, `c2` in the other, neither copied from the other. `c3` repairs
both, so the oracle is the two-commit set {c1, c2}.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1, c2
- Bug-fixing commit: c3

## Notes

- Moved from SZZG-0084 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
