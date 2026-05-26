# SZZ-0164: BIC is a test-only commit

## Summary

Evaluates a bug where the bug-introducing commit changes only a test oracle, not production code.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c2

## Notes

- Moved from SZZG-0007 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
