# SZZG-0019: buggy code copied to new file

## Source

- Source scenario: `FUTURE-019`
- Category: copy / clone / propagation 系未対応シナリオ

## Purpose

バグを含むコードが別ファイルへコピーされ、コピー先で後に修正されるケースを評価する。

## Expected history

```text
c0: A.java に bug を含む実装
c1: A.java の処理を B.java にコピー
c2: B.java の bug を修正
```

## Why this needs `scenario.graph.yml`

`copy_file` がないため、copy commit として表現できない。  
また、direct BIC と origin BIC の区別が必要。

## Required graph-schema features

```yaml
- type: "copy_file"
  from: "src/main/java/example/A.java"
  to: "src/main/java/example/B.java"

bug_introducing_commits:
  - commit: "c1"
    role: "direct"
  - commit: "c0"
    role: "origin"
```

## Evaluation points

- direct BIC を正解とするか origin BIC を正解とするか
- clone-aware SZZ の評価
- conventional SZZ が copy commit を返すか

---

## Draft status

This scenario is a draft for the proposed `scenario.graph.yml` schema.  It is intended to guide the implementation of a future graph-aware validator/generator and should not be treated as executable by the current simple `scenario.yml` generator.

## Files

```text
SZZG-0019/
├── scenario.graph.yml
└── README.md
```
