# SZZG-0060: root cause not in changed lines

## Source

- Source scenario: `FUTURE-060`
- Category: context-aware / LLM-based SZZ 向け未対応シナリオ

## Purpose

BFC の変更行そのものではなく、その周辺 context が root cause を示すケースを評価する。

## Expected history

```text
c1: caller contract を壊す
c2: BFC は guard を追加するだけ
```

## Why this needs `scenario.graph.yml`

fault.statement を単一の faulty line として書けない場合がある。  
root cause が changed line ではなく relation である。

## Required graph-schema features

```yaml
root_cause:
  type: "behavioral_relation"
  description: "Caller may pass null while callee assumes non-null."
```

## Evaluation points

- line-based SZZ の限界
- semantic / LLM-based SZZ
- root-cause oracle の表現

---

## K. robustness / 実装品質確認系未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0060/
├── scenario.graph.yml
└── README.md
```
