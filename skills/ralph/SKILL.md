---
name: ralph
description: |
  데이터 분석 목표 인터뷰 스킬. 막연한 분석 아이디어를 받아 Wonder → Reflect → Restate 사이클로 수렴시켜 docs/plans/<goal>.md를 생성한다.
  분석 유형(regression/classification/clustering/descriptive), 타깃 변수, 성공 지표를 확정한다.
  Iron Law #1 게이트: 이 파일 승인 없이 execute_code 실행 불가.
  Triggers (KO): ralph, /ralph, 분석하고 싶어, 뭘 분석할지 모르겠어, 분석 목표 정해줘, 데이터 분석 시작
  Triggers (EN): ralph, define analysis, analysis goal, I want to analyze
  Do NOT use when: 이미 docs/plans/ 파일이 있으면 → /kaggle-discover로 바로 진행
---

# Ralph — 데이터 분석 목표 인터뷰

## 역할

막연한 분석 아이디어를 받아 닫힌 분석 목표를 확정하고 `docs/plans/`에 저장한다.

## 절차

### Step 1 — Wonder
`/wonder` 호출 또는 인라인 실행.
사용자 입력에서 가능한 해석 3가지 발산.
`scratch/define-analysis.md`의 `## Wonder` 섹션에 기록.

### Step 2 — Reflect
`/reflect` 호출 또는 인라인 실행.
각 해석을 사용자 의도와 비교.
같은 파일 `## Reflect` 섹션에 기록.

### Step 3 — Restate
`/restate` 호출 또는 인라인 실행.
수렴된 해석을 goal 한 문장으로 확정.

### Step 4 — 분석 메타데이터 확정
goal 확정 후 한 번에 하나씩 확인:
1. `analysis_type`: `regression` | `classification` | `clustering` | `descriptive`
2. `target_variable`: 예측/분류 대상 컬럼명 또는 `"없음"` (descriptive/clustering)
3. `success_metric`: `RMSE` | `AUC-ROC` | `F1` | `Silhouette` | `p-value` 등
4. `constraints`: 해석 가능성 요구, 특정 모델 금지, 처리 시간 제한 등

### Step 5 — 설계 문서 저장

파일명: `docs/plans/YYYYMMDD-<goal-kebab>.md`

```markdown
# <goal>

> Date: YYYY-MM-DD | Status: pending-approval

## 분석 정의
- goal: ...
- analysis_type: ...
- target_variable: ...
- success_metric: ...
- constraints: [...]

## 승인 체크리스트
- [ ] goal이 Kaggle 데이터셋으로 검증 가능하다
- [ ] analysis_type이 결정되었다
- [ ] success_metric이 측정 가능하다
- [ ] constraints가 Iron Laws와 충돌하지 않는다
```

### Step 6 — 승인 요청
사용자에게 파일 확인 및 "approved" 서명 요청.
승인 전 `/kaggle-discover` 또는 `execute_code` 제안 금지.

## 출력 요약

```yaml
plan_file: docs/plans/YYYYMMDD-<goal-kebab>.md
goal: ...
analysis_type: ...
target_variable: ...
success_metric: ...
next_step: "승인 후 /kaggle-discover 호출"
```
