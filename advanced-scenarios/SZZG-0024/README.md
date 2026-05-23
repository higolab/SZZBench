# SZZG-0024: same bug introduced independently

## Source

- Source scenario: `FUTURE-024`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

コピーではないが、同型のバグが別々の commit で独立に混入するケースを評価する。

## Expected history

```text
c0: 正常
c1: A.java に off-by-one bug
c2: B.java に同型 off-by-one bug
c3: 両方を修正
```

## Why this needs `scenario.graph.yml`

複数 fault / fix は表せるが、「copyではない独立導入」を明示できない。  
copy propagation と区別するメタデータが必要。

## Required graph-schema features

```yaml
bug_introduction_relationship:
  type: "independent_same_pattern"
```

## Evaluation points

- clone-origin ではなく複数 direct BIC として扱うべきか
- pattern-aware SZZ との関係
- false origin inference の検出

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0024/
├── scenario.graph.yml
└── README.md
```
