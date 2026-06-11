# SZZ-0155: Same bug introduced independently

## Summary

Evaluates same bug introduced independently and checks whether SZZ identifies the expected bug-introducing commit set.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1, c2
- Bug-fixing commit: c3

## Notes

- Moved from SZZG-0084 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
