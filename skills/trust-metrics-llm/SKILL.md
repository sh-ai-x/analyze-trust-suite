---
name: trust-metrics-llm
description: |
  Semantic Trust 패널 산출. LLM이 생성한 자연어 주장·인사이트가 데이터/사실과 일치하는가 평가.
  Grounded.LLM, Hallucination Risk, Insight Consistency, LLM Verdict 산출.
  LLM Judge 호출만 허용. 코드 실행 / 모델 학습은 trust-metrics-code 책임.
  Triggers: trust-metrics-llm, 시맨틱 트러스트, LLM 평가, 그라운디드
  Prerequisite: scratch/analysis-cycle.md best_score 존재, docs/reports/<goal>.md 존재
  Depends on: Phase A (define-analysis → analysis-cycle → verify-report)
  Skip when: 동일 goal의 scratch/trust-metrics-llm.md가 1시간 이내라면 → 재사용 제안
---

# trust-metrics-llm — Semantic Trust 패널

## 역할

분석 결과의 **LLM 측 신뢰도** 만 평가한다. 다음 4개 메트릭을 산출해 `scratch/trust-metrics-llm.md` 에 저장한다.

| 메트릭 | 산출 |
|---|---|
| Grounded.LLM | LLM Judge로 claim 3~5개 샘플 평가 (YES=1, PARTIAL=0.5, NO=0) → 평균 × 100 |
| Hallucination Risk | `100 − Grounded.LLM` |
| Insight Consistency | 인사이트 문장 N개 추출 후 LLM Judge로 모순/중복 평가 (CONSISTENT/PARTIAL/INCONSISTENT) |
| LLM Verdict | FAIL / WARN / PASS |

**Iron Law #6**: 스킬은 read-only 평가다. `execute_code` / `Write(scripts/*.py)` / `Bash(python ...)` / `Bash(jupyter ...)` / 모델 학습 호출은 **금지**. LLM Judge 호출은 허용 (스킬의 정의된 동작).

---

## Step 0 — Skip when 확인 [CLAUDE]

`scratch/trust-metrics-llm.md` 의 YAML `computed_at` 이 현재 시각 기준 1시간 이내면:

```
"[skip] 동일 goal의 trust-metrics-llm 결과가 {elapsed} 전입니다. 재사용하시겠습니까?
 (1) 재사용
 (2) 재계산"
```

→ **[USER]** 응답 대기. (2) 또는 silent enter → Step 1 진행.

---

## Step 1 — 입력 수집 [CLAUDE]

읽기만:
- `docs/plans/<goal>.md` — goal, success_metric
- `scratch/env.md` — execution_env, data_path
- `scratch/hypothesis-eda.md` — 원본 데이터 신호
- `scratch/analysis-cycle.md` — 모델 결과, best_score
- `docs/reports/<goal>.md` — **LLM이 생성한 인사이트 문장 (평가 대상)**

claim 샘플 추출:
- 리포트의 핵심 주장 문장 3~5개 (예: "Social 채널의 Engagement Rate가 가장 낮다", "퍼널 단계 이탈률이 61.2%다")
- 각 claim에 인용된 근거(숫자/데이터 출처) 페어링

---

## Step 2 — 메트릭 계산 [CLAUDE — LLM Judge 호출]

### 2.1 Grounded.LLM

각 claim에 대해 LLM Judge 호출:

```
PROMPT:
Claim: "{claim_text}"
Cited evidence: "{evidence_from_scratch_or_data}"
Question: Is this claim fully supported by the cited evidence?

Respond exactly one of: YES | PARTIAL | NO
```

| 응답 | 점수 |
|---|---|
| YES | 1.0 |
| PARTIAL | 0.5 |
| NO | 0.0 |

`Grounded.LLM = (Σ scores / N) × 100` (정수, 소수점 첫째자리 반올림)

### 2.2 Hallucination Risk

```
Hallucination Risk = 100 − Grounded.LLM
```

### 2.3 Insight Consistency

리포트의 인사이트 문장 N개(2~5개)를 추출해 LLM Judge 호출:

```
PROMPT:
Insight A: "{insight_1}"
Insight B: "{insight_2}"
...
Question: Are these insights mutually consistent? (no logical contradiction, no redundant restatement)

Respond exactly one of: CONSISTENT | PARTIAL | INCONSISTENT
```

### 2.4 LLM Verdict

```
LLM Verdict = FAIL  iff (Grounded.LLM < 60) OR (Insight Consistency == INCONSISTENT)
LLM Verdict = WARN  iff (Grounded.LLM < 80) OR (Insight Consistency == PARTIAL)
LLM Verdict = PASS  iff 그 외
```

---

## Step 3 — scratch 저장 [CLAUDE]

`scratch/trust-metrics-llm.md` 작성:

```yaml
---
skill: trust-metrics-llm
goal: <goal-kebab>
computed_at: YYYY-MM-DDTHH:MM:SS
samples_judged: 4
insights_compared: 3
---
## Semantic Trust 패널

| Metric | Value | Note |
|--------|-------|------|
| Grounded.LLM | 88.5 | YES=3, PARTIAL=1, NO=0 (4 samples) |
| Hallucination Risk | 11.5 | 100 - 88.5 |
| Insight Consistency | CONSISTENT | 3/3 인사이트 모순 없음 |
| LLM Verdict | PASS | Grounded.LLM >= 80, Insight OK |

## Claim 평가 상세

| # | Claim | Verdict | Note |
|---|-------|---------|------|
| 1 | Social 채널의 Engagement Rate가 가장 낮다 | YES | marketing_channel_mart: Social 16.7%, Direct 72.3% |
| 2 | 사용자 흐름이 끊기는 지점: 평균 페이지뷰/세션 2.00 | YES | page_view_mart 일치 |
| 3 | 퍼널 단계 이탈률 61.2% | PARTIAL | ±2% 허용 오차 내 (60.8%) |
| 4 | 전체 세션의 44%가 Social | NO | 실측 38% (오류) |

## Insight Consistency 상세

- A vs B: CONSISTENT
- A vs C: CONSISTENT
- B vs C: CONSISTENT
```

---

## Step 4 — 역행 결정 [CLAUDE → USER]

| 조건 | 권장 메시지 |
|---|---|
| LLM Verdict=FAIL | `"[backtrack] LLM Verdict=FAIL. /hypothesis-eda를 재실행해 인사이트를 재작성해주세요."` |
| Hallucination Risk ≥ 40 | `"[backtrack] Hallucination Risk 40+%. /analysis-cycle 재실행 후 리포트 문장을 재작성 권장."` |
| Insight Consistency=INCONSISTENT | `"[backtrack] 인사이트 모순 발견. /hypothesis-eda 역행 권장."` |
| 그 외 | `"trust-metrics-llm 완료. /trust-metrics-code를 실행해주세요 (병렬 가능)."` |

---

## Iron Law 자가 점검

스킬 실행 후 다음을 자가 점검하고 위반 시 명시적으로 거부:

- [ ] `execute_code` 호출했는가? → **위반**. 코드 평가는 trust-metrics-code가 한다.
- [ ] `Write` 로 `scripts/*.py` 생성했는가? → **위반**.
- [ ] `Bash` 로 `python ...` 또는 `jupyter ...` 실행했는가? → **위반**.
- [ ] 모델 학습(fit/train)을 호출했는가? → **위반**.
- [ ] LLM Judge 호출을 했는가? → **허용** (이것이 스킬의 정의된 동작).

위반 발생 시: `"[Iron Law #6 위반] {액션}. 스킬은 read-only입니다. 코드 평가는 /trust-metrics-code를 호출해주세요."`