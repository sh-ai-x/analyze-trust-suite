---
name: reflect
description: |
  Wonder가 만든 의미 후보들을 사용자의 의도와 한 쌍씩 비교해 같음/다름을 드러낸다.
  Triggers (KO): reflect, /reflect, 의미 차이 짚어줘, 내가 뜻한 것과 다른 점 봐줘, 의미 비교
  Triggers (EN): reflect, compare meanings, surface meaning gap, check what I meant
  Do NOT use when: 의미 발산 → /wonder. 의미 합치기 → /refine. goal 재진술 → /restate.
  vs wonder: Wonder는 후보를 발산한다. Reflect는 각 후보가 사용자 의도와 어디서 일치하고 어디서 어긋나는지 본다.
---

# Reflect

## 역할

`## Wonder` 후보를 가져와 사용자에게 각 후보가 본인이 뜻한 것과 같은지 한 쌍씩 묻는다.

한 번에 한 비교만. 어떤 의미가 옳은지 결정하지 않는다. 사용자 의도를 임의로 만들지 않는다.

## 출력

비교 리스트:

```markdown
- 의미 A
  - 사용자의 의도된 nuance: ...
  - 모델의 해석 nuance: ...
  - 같음 / 다름: ...
```

## 스크래치 계약

`scratch/define-analysis.md`의 `## Wonder`를 읽는다.

`## Reflect` 섹션에 위 리스트를 기록한다.

모든 의미 후보에 같음/다름 표시가 끝나면 종료하고 `restate`로 넘긴다.
