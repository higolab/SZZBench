# SZZ-0158: BFC message has misleading reference

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S7` Context, message, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `line-modification`, `context-aware`, `misleading-message` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

S7 asks what a commit message is worth. Here the message is **wrong**: the fix
says it suspected "the first version of the comparison", which is `c0`, and the
commit that made the check exclusive is `c1`. A tool that reads the message and
follows it reports `c0`; blame on the line the fix deletes reports `c1` and is
right.

[SZZ-0159](../SZZ-0159/README.md) is the counterpart, and the two are not a
controlled pair: they are separate three-commit boundary histories, with
different faults (`value < max` here, `value > min` there), authors and dates.
What they contrast is what the fix's message does with the evidence, which is
what their factors now say — `misleading-message` here, `message-evidence`
there.

## Commit structure

- `c0`: initial implementation
- `c1`: makes the check exclusive. This is the expected BIC.
- `c2`: the BFC, whose message blames the first version of the comparison

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. Reporting `c0` is the
failure this scenario is built to catch: the message names it, and the code does
not support it.
