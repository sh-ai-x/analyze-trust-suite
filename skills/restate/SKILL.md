---
name: restate
description: |
  Reflect가 수렴한 의미를 다른 사람이 그대로 실행할 수 있는 goal 한 문장으로 재진술한다.
  Triggers (KO): restate, /restate, goal 다시 적어줘, 목표 한 줄로 정리해줘, 실행 가능한 goal
  Triggers (EN): restate, restate goal, one-line goal, turn this into a goal
  Do NOT use when: 의미 발산 → /wonder. 의미 차이 비교 → /reflect. 전체 루프 → /ralph.
  vs reflect: Reflect는 의미 차이를 드러낸다. Restate는 수렴된 의미를 실행 가능한 goal로 옮긴다.
---

# Restate

## 역할

`## Reflect`의 수렴된 의미를 다른 사람이 읽고 그대로 추진할 수 있는 goal 한 문장으로 옮긴다.

사용자에게 goal 후보 하나를 제시하고 확인을 요청한다. goal을 사용자 대신 자유롭게 작성하지 않는다.

## 출력

한 줄:

```markdown
goal: <사용자가 승인한 goal 한 문장>
```

## 스크래치 계약

`scratch/define-analysis.md`의 `## Reflect`를 읽는다.

`## Restate` 섹션에 위 한 줄을 기록한다.

사용자가 goal을 확정하면 종료한다. `ralph`가 이 goal로 분석 메타데이터 확정 단계로 진행한다.
