---
name: head-of-data
description: |
  최종 승인 게이트. 사용자가 트러스트 결과를 보고 PUBLISH/REVISE-LLM/REVISE-Code/ABORT 결정.
  REVISE 시 LLM 측 / Code 측 분리 지정 가능.
  Triggers: head-of-data, 최종 승인, 발행 결정, go/no-go
  Prerequisite: scratch/qa-review.md verdict 존재
  Depends on: qa-reviewer (same plugin)
---

# head-of-data — 최종 승인 게이트 (PUBLISH 게이트)

## 역할

사람(사용자)이 종합 verdict를 보고 최종 결정. Claude는 결정 요청자이지 결정자가 아니다.

**PUBLISH 게이트**: 본 결정이 `PUBLISH` 일 때만 `/verify-report` 실행 가능. 트러스트 평가·QA verdict 없이 리포트 발행 차단 (Iron Law #7).

**4가지 결정**:
1. `PUBLISH` — 모든 패널 통과. **PUBLISH 게이트 통과** → `/verify-report` 실행 가능.
2. `REVISE-LLM` — LLM 측만 재작성 (`/hypothesis-eda` 또는 `/analysis-cycle` 후 인사이트 재작성)
3. `REVISE-Code` — Code 측만 재실행 (`/analysis-cycle` 또는 `/colab-setup` | `/local-setup`)
4. `ABORT` — 분석 폐기

---

## Step 1 — 종합 패널 표시 [CLAUDE]

`scratch/qa-review.md` + `scratch/trust-metrics-llm.md` + `scratch/trust-metrics-code.md` 를 합쳐서 사용자에게 한 번에 표시:

```
═══════════════════════════════════════════════════
  TRUST PANEL — <goal>
═══════════════════════════════════════════════════

Semantic Trust (LLM 평가)
  Grounded.LLM:           88.5
  Hallucination Risk:     11.5
  Insight Consistency:    CONSISTENT
  LLM Verdict:            PASS

Computation Trust (코드 평가)
  Grounded.Numeric:       95.2
  CV Stability:           OK (std 0.008)
  Model Metrics:          AUC 0.8412 ± 0.0287
  Data Trust:             High
  Confidence:             87.5
  Code Verdict:           PASS

QA Verdict (종합):        PASS

═══════════════════════════════════════════════════
```

---

## Step 2 — 4개 옵션 제시 [CLAUDE → USER]

```
"최종 결정:

 (1) PUBLISH     — 모든 패널 통과. /verify-report로 진행.
 (2) REVISE-LLM  — LLM 측만 재작성. /hypothesis-eda 또는 /analysis-cycle 후 인사이트 재작성.
 (3) REVISE-Code — Code 측만 재실행. /analysis-cycle 또는 /colab-setup | /local-setup.
 (4) ABORT       — 분석 폐기.

선택:"
```

→ **[USER]** 1, 2, 3, 4 중 하나 또는 PUBLISH/REVISE-LLM/REVISE-Code/ABORT 직접 입력.

---

## Step 3 — 결정 기록 [CLAUDE]

`scratch/head-of-data-decision.md` 작성:

```yaml
---
skill: head-of-data
goal: <goal-kebab>
decided_at: YYYY-MM-DDTHH:MM:SS
decision: PUBLISH | REVISE-LLM | REVISE-Code | ABORT
decided_by: <USER_INPUT>
llm_verdict: PASS | WARN | FAIL
code_verdict: PASS | WARN | FAIL
qa_verdict: PASS | WARN | FAIL
---
## 사용자 근거 (인용)
"{user_input_excerpt}"

## 후속 액션
- PUBLISH: /verify-report → docs/reports/<goal>.md에 두 패널 + QA Verdict 섹션 추가 후 발행
- REVISE-LLM: /hypothesis-eda (또는 /analysis-cycle) → 인사이트 재작성 → 트러스트 재실행
- REVISE-Code: /analysis-cycle (또는 /colab-setup | /local-setup) → 모델 재학습 → 트러스트 재실행
- ABORT: 분석 종료. docs/plans/<goal>.md에 cancelled 표시.
```

---

## Step 4 — 후속 안내 [CLAUDE → USER]

| 결정 | Claude 응답 |
|---|---|
| PUBLISH | `"PUBLISH 결정 기록. PUBLISH 게이트 통과. /verify-report를 실행해 리포트에 두 패널 + QA Verdict 섹션을 포함해 발행해주세요. (권장)"` |
| REVISE-LLM | `"REVISE-LLM 결정 기록. /hypothesis-eda를 재실행해 인사이트를 재작성해주세요. 완료 후 /trust-metrics-llm → /qa-reviewer → /head-of-data를 다시 실행합니다."` |
| REVISE-Code | `"REVISE-Code 결정 기록. /analysis-cycle을 재실행해주세요. 완료 후 /trust-metrics-code → /qa-reviewer → /head-of-data를 다시 실행합니다."` |
| ABORT | `"ABORT 결정 기록. 분석을 종료합니다. docs/plans/<goal>.md에 cancelled: true를 추가해주세요."` |

---

## Iron Law #7 (PUBLISH 게이트)

**4종 파일 + PUBLISH 결정 없이 `/verify-report` 실행 금지**:
- `scratch/trust-metrics-llm.md`
- `scratch/trust-metrics-code.md`
- `scratch/qa-review.md`
- `scratch/head-of-data-decision.md` (**decision=PUBLISH 필수**)

4종 중 하나라도 없거나 `decision ≠ PUBLISH` 이면 `/verify-report` 실행 차단:

```
"[Iron Law #7 위반 — PUBLISH 게이트 미통과] 다음을 확인해주세요:
 1. /trust-metrics-llm 완료 → scratch/trust-metrics-llm.md
 2. /trust-metrics-code 완료 → scratch/trust-metrics-code.md
 3. /qa-reviewer 완료 → scratch/qa-review.md
 4. /head-of-data 완료 → scratch/head-of-data-decision.md (decision=PUBLISH)
모두 완료된 후 /verify-report를 실행해주세요."
```

---

## 결정 권한

스킬은 **결정을 사용자에게 요청할 뿐, 스스로 결정하지 않는다**. 다음 모두 금지:

- [ ] PUBLISH 를 사용자 입력 없이 자동 발급
- [ ] REVISE 방향을 임의로 결정 (LLM 측 vs Code 측)
- [ ] ABORT 를 환각/추측으로 발급

사용자 결정 후에도 Iron Law #1~5 (기존 플러그인 참조) 가 동일하게 적용된다.