# SZZG-0096: Multiple candidate BICs inside a work item

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G7` Issue, message, context, and non-local evidence |
| tier | `control` |
| status | `active` |
| difficulty | `easy` |
| language | `java` |
| factors | `work-item`, `evaluation-variant` |
| oracle | `top_k`; relevant `c2` · BFC `c4` |
| defeats | `shape` |
| graph features | policy `top_k`; `work_items` |
<!-- /szzbench:header -->

## Purpose

Evaluate whether a method picks the one commit of a work item that introduced the fault, rather than
the work item.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/RangeService.java)
c1: add candidate change (replace src/main/java/example/RangeService.java)
c2: introduce bug (replace src/main/java/example/RangeService.java)
c3: add candidate change (replace src/main/java/example/RangeService.java)
c4: fix bug (replace src/main/java/example/RangeService.java)
```
