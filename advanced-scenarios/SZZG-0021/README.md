# SZZG-0021: original と clone を同時修正

## Source

- Source scenario: `FUTURE-021`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

コピー元とコピー先の同型バグを同じ BFC で修正する場合を評価する。

## Expected history

```text
c0: A.java に bug
c1: A.java を B.java にコピー
c2: A.java と B.java を同時修正
```

## Why this needs `scenario.graph.yml`

複数 fault location / fix location が必要。  
direct/origin の評価方針も必要。

## Required graph-schema features

```yaml
faults:
  - id: "F001"
    file: "A.java"
  - id: "F002"
    file: "B.java"
```

## Evaluation points

- SZZ が両方の BIC を返すか
- origin と direct の扱い
- clone-aware analysis の必要性

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0021/
├── scenario.graph.yml
└── README.md
```
