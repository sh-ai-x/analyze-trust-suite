---
name: review-analysis
description: |
  R1(review-report) + R2(review-methodology) + R3(review-statistical) + R4(review-robustness)
  를 차례로 실행하고 종합 verdict 를 생성하는 오케스트레이터.
  각 리뷰 FAIL 시 즉시 중단하고 사유 보고. 모두 통과 시 scratch/review-analysis.md 작성.
  Triggers: 종합 리뷰, 일괄 검증, review-analysis, review everything
  Prerequisite: docs/reports/*.ipynb 존재 (R1), scratch/analysis-cycle.md best_* (R2-R4)
---

# review-analysis — 4단계 리뷰 오케스트레이터

## 역할

4개의 독립 리뷰 스킬을 차례로 호출하고 종합 verdict 를 만든다.
각 리뷰는 **그 자체로도 호출 가능**하지만, 이 스킬은 한 번에 모두 돌리는 진입점이다.

---

## 파이프라인

```
[R1] /review-report       (정적, 노트북 파싱) — 빠름
        │  PASS/WARN
        ▼
[R2] /review-methodology  (정적 AST + corr) — 빠름
        │  PASS/WARN
        ▼
[R3] /review-statistical  (sklearn + scipy 재실행) — 느림
        │  PASS/WARN
        ▼
[R4] /review-robustness   (5 seeds × 5 folds 재실행) — 가장 느림
        │
        ▼
scratch/review-analysis.md (종합 verdict)
```

**Short-circuit**: R1·R2·R3 중 하나라도 **FAIL**이면 즉시 중단. R4 FAIL은 WARN으로 강등 (성능 이슈는 모델 자체는 유효할 수 있음).

---

## 실행 흐름

### Step 1 — 환경 확인 [CLAUDE]

`scratch/env.md` 확인 → execution_env, data_path.

### Step 2 — 정적 리뷰 [CLAUDE]

```
"[R1/4] 노트북 자기-일관성 (review-report)..."
```

→ `/review-report` 호출. stdout 파싱 → verdict.
- FAIL → `[backtrack] 노트북 자기-일관성 FAIL. /verify-report로 노트북 재생성 필요.` 중단.
- WARN/PASS → 다음 단계.

### Step 3 — 방법론 감사 [CLAUDE]

```
"[R2/4] 방법론 감사 (review-methodology)..."
```

→ `/review-methodology` 호출.
- FAIL → `[backtrack] 방법론 audit FAIL (block finding ≥ 1). scripts/train.py 수정 필요.` 중단.
- WARN/PASS → 다음 단계.

### Step 4 — 통계 검증 [CLAUDE]

```
"[R3/4] 통계 검증 (review-statistical)..."
```

→ `/review-statistical` 호출. 베이스라인 비교, p-value, lift, d.
- FAIL → `[backtrack] 베이스라인 대비 유의미한 차이 없음. 분석 재설계 필요.` 중단.
- WARN/PASS → 다음 단계.

### Step 5 — 강건성 검증 [CLAUDE]

```
"[R4/4] 강건성 검증 (review-robustness)..."
```

→ `/review-robustness` 호출. 5 seeds × 5 folds, LOFO, slice.
- FAIL → WARN으로 강등 (continue).

### Step 6 — 종합 verdict [CLAUDE]

`scratch/review-analysis.md`:

```markdown
---
skill: review-analysis
r1_verdict: PASS
r2_verdict: PASS
r3_verdict: PASS
r4_verdict: WARN
overall: WARN
---

# 종합 리뷰 결과

**대상 분석**: docs/reports/<file>.ipynb
**Overall Verdict**: WARN (R4 강건성 부분 FAIL)

## Per-Layer 결과

| Layer | Skill | Verdict | Findings | 핵심 결과 |
|-------|-------|---------|----------|-----------|
| R1 | review-report | PASS | block=0 warn=0 | 노트북 일관성 OK |
| R2 | review-methodology | PASS | block=0 warn=1 | M11 한글 폰트 누락 (warn) |
| R3 | review-statistical | PASS | gates=4/4 | best vs baseline: +0.236 (p<0.001, d=3.42) |
| R4 | review-robustness | WARN | gates=2/3 | seed_std=0.019 OK, LOFO 단일 피처 critical |

## 핵심 권고

- R4: feat1 단독 의존도 (LOFO 41%). 일반화 위험 → 추가 피처 탐색 권고.
- R2: 한글 폰트 preamble 추가.

## 다음 단계

- `/verify-report` 로 노트북 재생성 (R4 권고 반영)
- 또는 `/analysis-cycle` 로 모델 재학습
```

### Step 7 — 사용자 보고 [CLAUDE → USER]

```
"✅ 종합 리뷰 완료
  Overall: WARN (R4 LOFO 단일 피처 critical)
  
  | Layer | Verdict | Key |
  |-------|---------|-----|
  | R1 report      | PASS | notebook OK |
  | R2 methodology | PASS | M11 warn |
  | R3 statistical | PASS | p<0.001, d=3.42 |
  | R4 robustness  | WARN | seed_std=0.019, LOFO feat1=41% |

  open scratch/review-analysis.md"
```

---

## Iron Laws

- #3: stdout 없이 overall verdict 금지 (각 레이어의 실제 출력이 있어야 종합 가능)
- #4: 추측 finding 종합 금지

---

## 독립 호출

각 레이어는 prereq 만 만족하면 단독 호출 가능:

```
/review-report         (R1, 노트북 파일 필요)
/review-methodology    (R2, scripts/ + scratch/analysis-cycle.md)
/review-statistical    (R3, scratch/analysis-cycle.md + data/raw/)
/review-robustness     (R4, scratch/analysis-cycle.md + data/raw/)
```

---

## 기존 인프라 재사용

- 4개 레이어 스킬의 SKILL.md
- `scratch/<skill-name>.md` YAML 헤더 패턴
- 한글 폰트 preamble (R3·R4 PNG)
