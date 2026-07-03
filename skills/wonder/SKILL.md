---
name: wonder
description: |
  사용자의 막연한 한 단어나 요청 안에 숨어 있는 의미 후보들을 발산한다. Socrates 루프 안에서는 현재 사이클의 ### Wonder 섹션만 채운다.
  Triggers (KO): wonder, /wonder, 의미 더 캐줘, 숨어 있는 뜻 찾아줘, 의미 발산
  Triggers (EN): wonder, expand meaning, explore hidden meanings, what else could this mean
  Do NOT use when: 의미 차이 비교 → /reflect. 의미 합치기 → /refine. goal 재진술 → /restate. 전체 Seed 루프 → /ralph.
  vs reflect: Wonder는 의미 후보를 발산한다. Reflect는 그 후보를 사용자 의도와 비교한다.
---

# Wonder

## 역할

사용자의 막연한 요청 안에 숨어 있는 의미를 적어도 세 후보까지 드러낸다.

질문은 한 번에 하나씩 한다. 의미를 임의로 만들어 칸을 채우지 않는다.

## 출력

마크다운 리스트로 최소 세 후보:

```markdown
- 의미 A — 한 줄 설명
- 의미 B — 한 줄 설명
- 의미 C — 한 줄 설명
```

## 스크래치 계약

`scratch/define-analysis.md`의 `## Wonder` 섹션에 위 리스트를 기록한다.

섹션이 없으면 만든다:

```markdown
## User Input
<원문 그대로>

## Wonder
- 의미 A — ...
- 의미 B — ...
- 의미 C — ...
```

세 후보 이상이 모이면 종료하고 `reflect`로 넘긴다.
