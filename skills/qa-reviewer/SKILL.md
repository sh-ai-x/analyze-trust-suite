---
name: qa-reviewer
description: |
  Semantic + Code Verdict 종합. Consistency Check + QA Review 4항목 + 최종 verdict 발급.
  신규 분석 생성 금지 (Iron Law #6). LLM Judge / 모델 학습 / 코드 실행 모두 금지 (read-only).
  Triggers: qa-reviewer, QA, 검수, 종합 verdict
  Prerequisite: scratch/trust-metrics-llm.md + scratch/trust-metrics-code.md 모두 존재
  Depends on: trust-metrics-llm + trust-metrics-code (same plugin)
---

# qa-reviewer — 종합 verdict 발급

## 역할

`trust-metrics-llm` (Semantic) 과 `trust-metrics-code` (Computation) 의 결과를 **읽기만** 하고 종합 verdict 를 발급한다. 스킬은 **완전한 read-only** 다.

| 책임 | 대상 |
|---|---|
| Consistency Check | 양 트러스트 파일의 일관성 + iteration 로그의 가설 간 일관성 |
| QA Review | 워크숍 4항목 체크리스트 (양 차원 통합) |
| 종합 verdict | PASS / WARN / FAIL + LLM 측 / Code 측 분리 표시 |

---

## Step 1 — 입력 수집 [CLAUDE]

읽기만:
- `scratch/trust-metrics-llm.md` (필수)
- `scratch/trust-metrics-code.md` (필수)
- `scratch/analysis-cycle.md` (iteration 로그)
- `scratch/hypothesis-eda.md` (원본 가설)

미존재 시:

```
"[prereq fail] 다음 파일이 필요합니다:
 - scratch/trust-metrics-llm.md (필수) → /trust-metrics-llm 먼저 실행
 - scratch/trust-metrics-code.md (필수) → /trust-metrics-code 먼저 실행
먼저 두 트러스트 스킬을 실행해주세요."
```

→ 종료.

---

## Step 2 — Consistency Check [CLAUDE]

| 검사 | 조건 | FLAG |
|---|---|---|
| 동일 가설 best_score 재현성 | `scratch/analysis-cycle.md` 의 best_score 와 `trust-metrics-code.md` 의 CV Stability mean 의 차이 | `|diff| > 0.01` → FLAG |
| 가설 간 구분력 | Outer N개 가설의 best_score 최대 − 최소 | `< 0.02` → "가설 구분 약함" |
| Grounded.Numeric | `trust-metrics-code.md` 의 값 | `< 90` → FLAG |
| Insight Consistency | `trust-metrics-llm.md` 의 값 | `INCONSISTENT` → FLAG |
| LLM/Code verdict 충돌 | (LLM=PASS AND Code=FAIL) OR (LLM=FAIL AND Code=PASS) | 충돌 → FLAG |

산출:
```
consistent: yes | no
flags: [{type, detail}]
```

---

## Step 3 — QA Review 4항목 [CLAUDE]

워크숍 도출 체크리스트 (양 차원 통합):

| # | 항목 | 평가 대상 | 판정 기준 |
|---|---|---|---|
| 1 | 모든 단계 결론 한자리에 비교 | `analysis-cycle.md` 의 모든 iteration + 두 트러스트 파일 | 모두 읽었음 → PASS, 일부 → PARTIAL, 못 읽음 → FAIL |
| 2 | 상충·중복·모순 평가 | LLM 측 verdict vs Code 측 verdict, 가설 간 점수 | 충돌 없음 → PASS, 1건 → PARTIAL, 2건+ → FAIL |
| 3 | **신규 분석 만들지 않았는가** | 스킬의 호출 로그 (자기 점검) | read-only 유지 → PASS |
| 4 | 중복·누락 연결 표시 | 동일 hypothesis의 Outer iteration 결과, 동일 claim 의 trust 평가 | 모두 매핑됨 → PASS, 일부 누락 → PARTIAL |

각 항목 PASS / PARTIAL / FAIL.

---

## Step 4 — 종합 Verdict [CLAUDE]

```
QA Verdict = FAIL  iff
  - Consistency Check == inconsistent  OR
  - 4개 중 FAIL >= 1  OR
  - LLM Verdict == FAIL  OR
  - Code Verdict == FAIL

QA Verdict = WARN  iff
  - 4개 중 PARTIAL >= 2  OR
  - (LLM Verdict == WARN) XOR (Code Verdict == WARN)

QA Verdict = PASS  iff 그 외
```

**양 축 분리 표시 필수**:
- LLM 측: trust-metrics-llm 의 Verdict 그대로
- Code 측: trust-metrics-code 의 Verdict 그대로
- 종합: 위 규칙으로 산출

---

## Step 5 — scratch 저장 [CLAUDE]

`scratch/qa-review.md` 작성:

```yaml
---
skill: qa-reviewer
goal: <goal-kebab>
reviewed_at: YYYY-MM-DDTHH:MM:SS
llm_verdict: PASS | WARN | FAIL
code_verdict: PASS | WARN | FAIL
verdict: PASS | WARN | FAIL
---
## Consistency Check
- consistent: yes
- flags: []

## QA Checklist
1. 모든 단계 결론 비교: PASS
2. 상충·중복 평가: PASS
3. 신규 분석 없음: PASS
4. 중복·누락 연결: PASS

## Verdict 산출
- LLM Verdict: PASS
- Code Verdict: PASS
- 종합: PASS
- 규칙: 양쪽 PASS, 4개 모두 PASS
```

---

## Step 6 — 다음 단계 안내 [CLAUDE → USER]

| 종합 Verdict | 권장 메시지 |
|---|---|
| PASS | `"qa-reviewer 완료. /head-of-data를 실행해 PUBLISH 결정 게이트를 통과해주세요. (게이트 통과 후 /verify-report 실행 가능)"` |
| WARN | 경고 사항 나열 후: `"/head-of-data를 실행해주세요. 발행 결정 시 경고가 함께 표시됩니다. 게이트 통과 후 /verify-report 실행 가능."` |
| FAIL | `"[backtrack] QA Verdict=FAIL. /hypothesis-eda 역행 권장. (또는 /trust-metrics-{llm,code} 재실행 후 /qa-reviewer 재호출)"` |

**핵심**: `/verify-report`는 `/head-of-data`의 decision=PUBLISH 이후에만 실행된다 (PUBLISH 게이트).

---

## Iron Law 자가 점검 (필수)

스킬은 **완전한 read-only**. 다음 모두 금지:

- [ ] `execute_code` 호출 → **위반**
- [ ] `Write(scripts/*.py)` → **위반**
- [ ] `Bash(python ...)` / `Bash(jupyter ...)` → **위반**
- [ ] LLM Judge 호출 → **위반** (trust-metrics-llm 결과만 읽음)
- [ ] 모델 학습 호출 → **위반**
- [ ] `/verify-report` 직접 호출 → **위반**. PUBLISH 게이트는 `/head-of-data` 책임.

위반 시 즉시 중단:
`"[Iron Law #6 위반] {액션}. 스킬은 read-only입니다. {trust-metrics-llm | trust-metrics-code | analysis-cycle | head-of-data | verify-report}로 위임해주세요."`