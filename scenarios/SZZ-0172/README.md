# SZZ-0172: Config and code interaction

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S8` Non-source, configuration, test-only, and file-level edge cases |
| tier | `control` |
| status | `active` |
| difficulty | `hard` |
| language | `java` |
| factors | `config`, `code-interaction`, `context`, `config-value` |
| oracle | `exact_set`; required `c1` · BFC `c3` |
<!-- /szzbench:header -->

## Summary

Evaluates a bug introduced by a configuration unit change that is only visible when read together with the code that interprets the setting.

## Expected SZZ Behavior

- Bug-introducing commit(s): c1
- Bug-fixing commit: c3

## Notes

- Moved from SZZG-0113 after applying the scenario.yml / scenario.graph.yml boundary policy.
- This scenario uses a linear main-branch history and a commit-level exact-set oracle.
