# SZZG-0022: clone が少し変更されてから修正

## Source

- Source scenario: `FUTURE-022`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

コピーされたコードが変形された後に修正されるケースを評価する。

## Expected history

```text
c0: A.java に bug
c1: B.java にコピー
c2: B.java の変数名や構造を少し変更
c3: B.java の bug を修正
```

## Why this needs `scenario.graph.yml`

copy とその後の clone divergence を表すメタデータがない。

## Required graph-schema features

```yaml
clone_relationships:
  - origin_file: "A.java"
    copied_file: "B.java"
    copy_commit: "c1"
    divergence_commits:
      - "c2"
```

## Evaluation points

- 類似性が低下しても origin を追えるか
- direct BIC は c1 か c2 か
- clone-aware / semantic SZZ の比較

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0022/
├── scenario.graph.yml
└── README.md
```
