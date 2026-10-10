# SZZ-0159: Bug reason only in commit message

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S7` Context, message, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `message-evidence` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

S7 asks what a commit message is worth. Here the message is **right**: the fix
names "the previous change" as the cause, and that is `c1`. Nothing in the code
says which earlier commit made the boundary exclusive, so a tool that reads only
the diff has blame and nothing else, while a tool that reads the message gets a
second witness that agrees with it.

[SZZ-0158](../SZZ-0158/README.md) is the counterpart, and the two are not a
controlled pair: they are separate three-commit boundary histories, with
different faults (`value > min` here, `value < max` there), authors and dates.
What they contrast is what the fix's message does with the evidence, which is
what their factors now say — `message-evidence` here, `misleading-message`
there.

## Commit structure

- `c0`: initial implementation
- `c1`: requires a value above the lower bound. This is the expected BIC.
- `c2`: the BFC, whose message names the previous change as the cause

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`, which both blame and the
message agree on.
