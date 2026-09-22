# SZZG-0115: Top-k evaluation

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `G9` Evaluation policy variants |
| tier | `control` |
| status | `active` |
| difficulty | `advanced` |
| language | `java` |
| factors | `evaluation-variant` |
| oracle | `top_k`; relevant `c1`; k = 1, 3, 5 · BFC `c4` |
| graph features | policy `top_k` |
<!-- /szzbench:header -->

## Purpose

Evaluate a top-k oracle: whether the bug-introducing commit is ranked above the distractors rather
than returned alone.

## Expected history

```text
c0: create initial state (write_file src/main/java/example/RangeService.java)
c1: introduce bug (replace src/main/java/example/RangeService.java)
c2: add distractor change (replace src/main/java/example/RangeService.java)
c3: add distractor change (write_file docs/range-service-notes.md)
c4: fix bug (replace src/main/java/example/RangeService.java)
```
