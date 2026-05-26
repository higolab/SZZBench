# SZZ-0172: Root cause not in changed lines

## Summary

Evaluates a fix that changes a caller-side guard while the root-cause bug was introduced earlier in a callee method that the BFC does not edit.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c2

## Notes

- Moved from SZZG-0060 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
