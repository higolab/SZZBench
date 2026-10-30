# SZZG-0099: BFC message references the wrong commit

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `message-evidence`, `misleading-message` |
| oracle | `exact_set`; required `c1`; related but not correct `c2` · BFC `c3` |
| defeats | none (a control: every declared naive rule may solve it) |
| graph features | `developer_hints` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether SZZ resists an incorrect BFC-message hint and still identifies the true code-level BIC.

## Expected history

```text
c0: create currency rounding helper
c1: introduce truncating cents normalization
c2: add invoice label helper mentioned by mistake
c3: fix rounding while incorrectly blaming c2 in the message
```

## Why this needs `scenario.graph.yml`

The BFC contains a misleading developer hint that must be represented separately from the code-level fault metadata.

## Evaluation points

- Whether SZZ identifies c1 as the true rounding BIC.
- Whether c2 is treated as an incorrect message reference rather than the expected BIC.
- Whether developer hints are distinguished from trustworthy blame evidence.
