# SZZ-0170: Config and code interaction

## Summary

Evaluates a bug introduced by a configuration unit change that is only visible when read together with the code that interprets the setting.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c3

## Notes

- Moved from SZZG-0056 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
