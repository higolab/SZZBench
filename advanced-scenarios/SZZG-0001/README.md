# SZZG-0001: BFC が rename + fix を同時に行う

## Source

- Source scenario: `FUTURE-001`
- Category: BFC の形状に関する未対応シナリオ

## Purpose

ファイル名変更とバグ修正が同一 BFC に含まれる場合に、SZZ が正しい BIC を特定できるかを評価する。

## Expected history

```text
c0: OldRange.java に正しい実装を導入
c1: OldRange.java に boundary bug を混入
c2: OldRange.java を Range.java に rename しつつ bug を修正
```

## Why this needs `scenario.graph.yml`

`replace` だけでも擬似的には表現できるが、Git 履歴上の rename として表現できない。  
rename-aware SZZ の評価には、Git が rename として認識できる履歴を生成する必要がある。

## Required graph-schema features

```yaml
- type: "rename_file"
  from: "src/main/java/example/OldRange.java"
  to: "src/main/java/example/Range.java"
```

さらに BFC 側で rename と replace を同一 commit に入れる必要がある。

## Evaluation points

- `git log --follow` 相当の追跡が必要か
- file path が変わっても BIC に到達できるか
- rename commit 自体を誤って BIC としないか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0001/
├── scenario.graph.yml
└── README.md
```
