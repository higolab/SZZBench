# SZZG-0018: 同一BICが複数bugの原因になる

## Source

- Source scenario: `FUTURE-018`
- Category: multiple BIC / multiple BFC に関する未対応シナリオ

## Purpose

共通処理の bug が複数の症状として後に現れるケースを評価する。

## Expected history

```text
c0: 正常な共通処理
c1: 共通処理に bug 混入
c2: 症状 A を修正
c3: 症状 B を修正
```

## Why this needs `scenario.graph.yml`

複数 bug から同一 BIC を参照することは可能だが、bug 間の関係を表現できない。

## Required graph-schema features

```yaml
bug_groups:
  - id: "BG001"
    root_cause: "c1"
    bugs:
      - "B001"
      - "B002"
```

## Evaluation points

- 症状別 BFC から同じ BIC に到達するか
- root cause と symptom fix の関係
- 実プロジェクトでの multi-symptom bug 評価

---

## E. copy / clone / propagation 系未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0018/
├── scenario.graph.yml
└── README.md
```
