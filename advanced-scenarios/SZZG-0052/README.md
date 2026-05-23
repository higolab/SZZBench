# SZZG-0052: multiple overloaded methods

## Source

- Source scenario: `FUTURE-052`
- Category: ambiguous blame / duplicate 系未対応シナリオ

## Purpose

同名メソッドが複数あり、fault.statement だけでは entity を特定できないケースを評価する。

## Expected history

```text
Range.contains(int)
Range.contains(double)
の両方に類似 statement が存在
片方のみが bug
```

## Why this needs `scenario.graph.yml`

`entity.signature` はあるが、validator / verifier が entity anchor を使って statement 範囲を限定できない。

## Required graph-schema features

```yaml
fault:
  entity:
    type: "method"
    name: "contains"
    signature: "boolean contains(int value, int min, int max)"
  anchor_policy: "entity_scope"
```

## Evaluation points

- statement matching の曖昧性
- method-level SZZ の必要性
- overload の扱い

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0052/
├── scenario.graph.yml
└── README.md
```
