# SZZ-0156: Multiple overloaded methods

## Summary

Evaluates multiple overloaded methods and checks whether SZZ identifies the expected bug-introducing commit set.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c2

## Notes

- Moved from SZZG-0109 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
