# SZZG-0015: 1つのBFCが複数BICを修正するが、すべてのBICを返す必要がある

## Source

- Source scenario: `FUTURE-015`
- Category: multiple BIC / multiple BFC に関する未対応シナリオ

## Purpose

複数 BIC の集合を exact set として評価する。

## Expected history

```text
c0: 正常
c1: validation 弱化
c2: caller が不正値を渡すよう変更
c3: 両方を修正
```

## Why this needs `scenario.graph.yml`

複数 BIC の記述はできるが、評価ポリシーとして「全部必要」「一部でもよい」を表現できない。

## Required graph-schema features

```yaml
expected_szz:
  commit_level:
    evaluation_policy: "exact_set"
    required:
      - "c1"
      - "c2"
```

## Evaluation points

- recall を重視するか
- partial credit を認めるか
- top-k での評価方法

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0015/
├── scenario.graph.yml
└── README.md
```
