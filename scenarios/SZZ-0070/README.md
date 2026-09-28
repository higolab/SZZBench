# SZZ-0070: State transition check omission

<!-- szzbench:header (generated from the scenario file: edit the YAML and run `szzbench readme --write`) -->
| | |
|---|---|
| category | `S2` Omission and deletion bugs |
| tier | `control` |
| status | `active` |
| difficulty | `medium` |
| language | `java` |
| factors | `single-bic`, `single-bfc`, `omission-bug`, `line-addition-fix` |
| oracle | `exact_set`; required `c1` · BFC `c2` |
<!-- /szzbench:header -->

## Purpose

An omission bug whose missing check is a property of a **pair** of values.
`canTransition(from, to)` is introduced accepting every transition between two
different states; the fix adds the table the lifecycle actually defines. The
category's other omissions guard one argument — a null check in
[SZZ-0047](../SZZ-0047/README.md), a bounds check in
[SZZ-0053](../SZZ-0053/README.md), a path check in
[SZZ-0076](../SZZ-0076/README.md) — and each of them adds a single early
return, `if (<cond>) { return false; }` in SZZ-0053 and SZZ-0076 and a default
in SZZ-0047. This one is not, which is what
`decisions/consolidation-matrix.md` §2 asked for when it called the earlier
version ("`canStart(ready)`, a minimal guard") a weak example to repair or
delete.

## Commit structure

- `c0`: adds the lifecycle states.
- `c1`: adds `canTransition`, which accepts any two different states. This is
  the expected BIC.
- `c2`: adds the four rules the lifecycle defines. This is the BFC.

## Expected behavior

The expected BFC is `c2` and the expected BIC is `c1`. Line-level evaluation is
unavailable because the fault is an omission: the fix deletes no line, so there
is no faulty line to blame.

`NEW -> RUNNING`, `READY -> DONE` and `RUNNING -> READY` are accepted at `c1`
and refused at `c2`; `NEW -> READY`, `READY -> RUNNING` and `RUNNING -> DONE`
are accepted by both; and `DONE -> any other state` is accepted at `c1` and
refused at `c2`. A transition to the state the order is already in is refused
throughout, by the `from != to` the method had from the start.
