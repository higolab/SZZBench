# SZZG-0047: issue IDなしの work item 推定

## Source

- Source scenario: `FUTURE-047`
- Category: work item / commit series 系未対応シナリオ

## Purpose

commit message や時間的近接性だけから work item を推定する手法を評価する。

## Expected history

```text
c1, c2, c3 が近い時刻・類似 message だが issue ID はない
c4: fix
```

## Why this needs `scenario.graph.yml`

work item が明示的ではなく、推定対象であることを表現できない。

## Required graph-schema features

```yaml
work_item_ground_truth:
  inference_required: true
  commits:
    - "c1"
    - "c2"
    - "c3"
```

## Evaluation points

- work item 推定の精度
- message/time heuristic の評価
- SZZ 前処理の評価

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0047/
├── scenario.graph.yml
└── README.md
```
