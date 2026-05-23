# SZZG-0011: method move between classes

## Source

- Source scenario: `FUTURE-011`
- Category: 中間履歴に関する未対応シナリオ

## Purpose

faulty method が別クラスに移動された後に修正されるケースを評価する。

## Expected history

```text
c0: Range.contains が Range.java に存在
c1: contains に bug 混入
c2: contains を RangeUtils.java に移動
c3: RangeUtils.contains で bug 修正
```

## Why this needs `scenario.graph.yml`

full-file replace で擬似的に表現できるが、method move としての意味を validator / verifier が理解できない。

## Required graph-schema features

```yaml
- type: "move_entity"
  entity:
    type: "method"
    name: "contains"
  from_file: "src/main/java/example/Range.java"
  to_file: "src/main/java/example/RangeUtils.java"
```

## Evaluation points

- method-level tracking が必要か
- file-level SZZ が失敗するか
- entity-aware SZZ の利点

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0011/
├── scenario.graph.yml
└── README.md
```
