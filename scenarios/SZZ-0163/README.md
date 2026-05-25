# SZZ-0163: Malformed commit message

## Overview

This scenario checks robustness against a malformed-looking bug-fixing commit message.

The history is intentionally simple and linear, so this scenario is represented as a normal `scenario.yml` under `scenarios/` rather than as `scenario.graph.yml` under `advanced-scenarios/`.

## Commit history

```text
c1: Introduce boundary bug
c2: fix boundary bug with malformed-looking commit message
```

## Commit table

| Commit | Role | Message | Description |
|---|---|---|---|
| `c1` | bug_introducing | `Introduce boundary bug` | Creates `Range.java` with a boundary bug. |
| `c2` | bug_fixing | `FIX:::: boundary regression ??? refs=[[[unknown]]] introduced-by=<missing>` | Fixes the bug with an intentionally malformed-looking message. |

## Code states

Buggy code in `c1`:

```java
return value > min && value < max;
```

Fixed code in `c2`:

```java
return value >= min && value <= max;
```

## Oracle

Expected BIC:

```text
c1
```

Bug-fixing commit:

```text
c2
```

## Evaluation purpose

This scenario checks whether SZZ tools and SZZBench tooling remain robust when the BFC message does not follow a normal format.

The message is malformed-looking but safe for YAML and Git tooling. It avoids null bytes and control characters.

## Why this is a normal scenario

This scenario does not require branch, merge, cherry-pick, backport, multiple BFCs, or evaluation variants. Therefore, it is represented as a normal scenario:

```text
scenarios/SZZ-0163/scenario.yml
```
