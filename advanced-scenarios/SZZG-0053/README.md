# SZZG-0053: line moved and duplicated

## Source

- Source scenario: `FUTURE-053`
- Category: ambiguous blame / duplicate 系未対応シナリオ

## Purpose

faulty line が移動され、さらに複製されることで、blame と oracle が曖昧になるケースを評価する。

## Expected history

```text
c1: faulty line 導入
c2: faulty line を別メソッドへ移動し、元にも残す
c3: 片方のみ修正
```

## Why this needs `scenario.graph.yml`

line move / duplication の関係を表現できない。  
direct / origin / instance の区別が必要。

## Required graph-schema features

- `move_entity`
- `copy_entity`
- bug instance

## Evaluation points

- どの instance を修正したか
- moved line の origin
- duplicate line の blame

---

## J. context-aware / LLM-based SZZ 向け未対応シナリオ

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0053/
├── scenario.graph.yml
└── README.md
```
