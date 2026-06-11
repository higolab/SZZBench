# SZZ-0173: File creation only as fix

## Summary

Evaluates file creation only as fix and checks whether SZZ identifies the expected bug-introducing commit set.

## Expected SZZ Behavior

- Bug-introducing commit(s): c0
- Bug-fixing commit: c1

## Notes

- Moved from SZZG-0065 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
