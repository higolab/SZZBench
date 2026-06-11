# SZZ-0167: Patch context required

## Summary

Evaluates a boundary fix where the caller method provides the context needed to interpret the patched line.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c2

## Notes

- Moved from SZZG-0111 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
