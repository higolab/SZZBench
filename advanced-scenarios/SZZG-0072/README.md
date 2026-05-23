# SZZG-0072: line-level 不可だが entity-level は可能なケース

## Source

- Source scenario: `FUTURE-074`
- Category: schema / evaluation policy が必要な横断シナリオ

## Purpose

omission や semantic relation bug のように line-level oracle はないが、method-level/entity-level oracle はあるケースを評価する。

## Expected history

```text
c1: method-level contract bug
c2: fix
```

## Why this needs `scenario.graph.yml`

`line_level.available: false` は書けるが、entity-level oracle を標準化していない。

## Required graph-schema features

```yaml
expected_szz:
  line_level:
    available: false
  entity_level:
    available: true
    entities:
      - type: "method"
        file: "..."
        signature: "..."
```

## Evaluation points

- entity-level SZZ
- line-level だけでは評価不能な bug
- method-level precision/recall

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0072/
├── scenario.graph.yml
└── README.md
```
