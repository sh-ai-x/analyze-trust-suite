---
name: analyze-trust
description: |
  단일 진입점 메타 오케스트레이터. 6단계 분석 + 4단계 트러스트 평가 + PUBLISH 게이트 + verify-report 발행을 차례로 안내하는 가이드 모드.
  각 사용자 결정 게이트(plan 승인, env 선택, 가설 승인, PUBLISH 결정)에서 대기한다.
  가이드 모드: 자동 디스패치 아님. 호출할 때마다 현재 상태를 진단해 다음 단계를 안내.
  Triggers: analyze-trust, 전체 분석, 통합 진입점, 풀 사이클
---

# analyze-trust — 메타 오케스트레이터

## 역할

10단계 분석 사이클의 **단일 진입점**. 사용자 입력에서 goal 을 추출하고, 현재 진행 상태(`scratch/`, `docs/` 검사) 를 진단해 다음 단계를 안내한다.

**가이드 모드**: 본 스킬은 다음 단계를 *자동 실행*하지 않는다. 매 호출마다 진단 → 안내 → 사용자 호출 대기.

## 의존성

이 메타 오케스트레이터는 다음 내부 스킬에 위임한다 (모두 동일 플러그인 `analyze-trust-suite`에 포함):

- **Phase A (분석 6단계)**: `define-analysis`, `kaggle-discover`, `colab-setup` / `local-setup`, `hypothesis-eda`, `analysis-cycle`, `verify-report`
- **Phase B (검증 4단계)**: `trust-metrics-llm`, `trust-metrics-code`, `qa-reviewer`, `head-of-data`

플러그인이 설치되어 있으면 모든 단계를 안내할 수 있다. 실제 단계 실행은 위 스킬에 위임.

---

## Step 0 — 의도 감지 [CLAUDE]

`/analyze-trust <goal>` 호출에서 goal 추출.

| 입력 | 추출 |
|---|---|
| `/analyze-trust 타이타닉 생존 예측` | goal = `타이타닉 생존 예측` |
| `/analyze-trust` (인자 없음) | goal 미정. 사용자에게 질문 |

goal 추출 후 현재 진행 상태 진단:

```
[진단]
 - docs/plans/<goal>.md        → [1] define-analysis 완료 여부
 - scratch/kaggle-discover.md  → [2] 완료 여부
 - scratch/<env>-setup.md      → [3] 완료 여부
 - scratch/hypothesis-eda.md   → [4] 완료 여부
 - scratch/analysis-cycle.md   → [5] 완료 여부 (best_score)
 - docs/reports/<goal>.md      → [6] 발행 여부
 - scratch/trust-metrics-llm.md → [7] 완료 여부
 - scratch/trust-metrics-code.md → [8] 완료 여부
 - scratch/qa-review.md        → [9] 완료 여부
 - scratch/head-of-data-decision.md → [10] 결정 (PUBLISH/REVISE/ABORT)
```

진단 결과를 기반으로 다음 단계를 결정.

---

## Step 1 — 다음 단계 안내 [CLAUDE → USER]

진단 결과에 따라 다음 단계를 안내. 각 안내에는 트리거 키워드 + prerequisite + 산출물을 포함한다.

### Phase A: 분석 (6단계)

| 진단 | 다음 안내 |
|---|---|
| plans 없음 | `[1단계] /define-analysis <goal> 호출` |
| plans 있음 + kaggle-discover 없음 | `[2단계] /kaggle-discover 호출 (목표: <goal>)` |
| kaggle-discover 있음 + setup 없음 | `[3단계] /{colab-setup\|local-setup} 호출 (env=<env>)` |
| setup 있음 + hypothesis-eda 없음 | `[4단계] /hypothesis-eda 호출` |
| hypothesis-eda 있음 + analysis-cycle 없음 | `[5단계] /analysis-cycle 호출 (top_hypotheses 기반)` |
| analysis-cycle 있음 (best_score) + reports 없음 | `[6단계] /verify-report 호출 (재실행 + 보고서 발행)` |
| analysis-cycle + reports 모두 있음 | `(Phase B 검증 단계로 이동. /analyze-trust 재호출 권장)` |

### Phase B: 검증 (4단계)

| 진단 | 다음 안내 |
|---|---|
| analysis-cycle 있음 + trust-metrics-{llm,code} 둘 다 없음 | `[7·8단계 (병렬)] /trust-metrics-llm + /trust-metrics-code 동시 호출` |
| trust-metrics-llm 만 있음 | `[8단계] /trust-metrics-code 호출` |
| trust-metrics-code 만 있음 | `[7단계] /trust-metrics-llm 호출` |
| trust 둘 다 있음 + qa-review 없음 | `[9단계] /qa-reviewer 호출` |
| qa-review 있음 + head-of-data-decision 없음 | `[10단계 — PUBLISH 결정 게이트] /head-of-data 호출` |

### Phase C: PUBLISH 게이트 + 발행

| 진단 | 다음 안내 |
|---|---|
| decision=PUBLISH + reports 없음 | `[발행 단계] /verify-report 호출. PUBLISH 게이트 통과됨.` |
| decision=PUBLISH + reports 있음 | `[완료] 모든 단계 완료. 최종 리포트: docs/reports/<goal>.md` |
| decision=REVISE-LLM | `[역행] /hypothesis-eda 호출 (인사이트 재작성)` |
| decision=REVISE-Code | `[역행] /analysis-cycle 호출 (모델 재학습)` |
| decision=ABORT | `[종료] 분석 폐기. docs/plans/<goal>.md에 cancelled: true 추가 후 종료` |

---

## Step 2 — 출력 형식 [CLAUDE]

매 호출 시 다음 형식으로 응답:

```
═══════════════════════════════════════════════════
  ANALYZE-TRUST — 현재 진단
═══════════════════════════════════════════════════

goal: <goal>
진행률: <N>/10 단계 완료 (예: 5/10)

[완료]
 ✓ [1] define-analysis (plans/<goal>.md)
 ✓ [2] kaggle-discover (selected_ref=...)
 ✓ [3] local-setup (data/raw/)
 ✓ [4] hypothesis-eda (top_hypotheses=3)
 ✓ [5] analysis-cycle (best_score=0.8412)
 ✓ [6] verify-report (docs/reports/<goal>.md)

[진행 중]
   [7] trust-metrics-llm
   [8] trust-metrics-code
   [9] qa-reviewer
   [10] head-of-data (PUBLISH 게이트)

═══════════════════════════════════════════════════
  다음 단계
═══════════════════════════════════════════════════

[7·8 — 병렬] /trust-metrics-llm
            /trust-metrics-code
→ 두 트러스트 모두 완료 후 /analyze-trust 재호출
```

---

## Step 3 — 의존성 확인 [CLAUDE]

Phase A·B의 스킬이 모두 `~/.claude/skills/analyze-trust-suite/skills/` 하위에 있는지 확인한다. 하나라도 없으면 진단만 안내하고 실제 단계 호출은 사용자가 별도 설치 후 진행하도록 한다.

> 참고: 옛 플러그인 (`harness-data-analysis`, `data-team-trust`, `analyze-orchestrator`)은 v1.1.0에서 `analyze-trust-suite`로 통합되었으며 더 이상 지원되지 않는다. 레거시 경로가 보이면 마이그레이션 가이드를 안내한다.

---

## Iron Law 안내

본 가이드가 안내하는 각 단계의 Iron Law:

| 단계 | Iron Law |
|---|---|
| [1] define-analysis | **#1**: plans 승인 없이 코드 실행 금지 |
| [1] define-analysis | **#2**: env 선택 전 setup 불가 |
| [3] setup | 데이터 손상 시 신뢰도 평가 왜곡 |
| [4] hypothesis-eda | 사용자 가설 승인 필수 |
| [5] analysis-cycle | **#5**: loop_state 갱신 필수 |
| [7·8] trust-metrics | LLM 측 / Code 측 분리 평가 |
| [9] qa-reviewer | **#6**: read-only |
| [10] head-of-data | **#7**: PUBLISH 결정 게이트 |
| [발행] verify-report | **#7**: 4종 파일 + decision=PUBLISH 필수 |

---

## 가이드 모드의 한계

본 스킬은 다음을 **하지 않는다**:
- 사용자 결정 없이 다음 단계 자동 실행
- 다른 플러그인의 스킬을 자동 호출
- 결과를 추적해 자동으로 단계 진행

각 호출에서 사용자가 다음 스킬을 직접 호출해야 한다. 이 한계는 의도적이다 (워크숍의 4가지 결정 게이트 보존).

---

## 호출 예시

```
[USER] /analyze-trust 타이타닉 생존 예측
[CLAUDE] (진단: plans 없음)
        → [1단계] /define-analysis 타이타닉 생존 예측 호출

[USER] /define-analysis 타이타닉 생존 예측
[CLAUDE] (Ralph Loop + env 선택)
        → 결정되면 /analyze-trust 재호출

[USER] /analyze-trust
[CLAUDE] (진단: plans 있음, kaggle 없음)
        → [2단계] /kaggle-discover 호출

... (반복)

[USER] /analyze-trust
[CLAUDE] (진단: analysis-cycle 완료, trust 없음)
        → [7·8 병렬] /trust-metrics-llm + trust-metrics-code

[USER] /trust-metrics-llm /trust-metrics-code
[CLAUDE] (각각 산출)
        → /analyze-trust 재호출

[USER] /analyze-trust
[CLAUDE] (진단: trust 완료, qa 없음)
        → [9단계] /qa-reviewer 호출

[USER] /qa-reviewer
[CLAUDE] (verdict 산출)
        → /analyze-trust 재호출

[USER] /analyze-trust
[CLAUDE] (진단: qa 있음, decision 없음)
        → [10단계 — PUBLISH 게이트] /head-of-data 호출

[USER] /head-of-data
[USER] 1 (PUBLISH)
[CLAUDE] (decision=PUBLISH 기록)
        → /analyze-trust 재호출

[USER] /analyze-trust
[CLAUDE] (진단: decision=PUBLISH, reports 없음)
        → [발행 단계] /verify-report 호출

[USER] /verify-report
[CLAUDE] (재실행 + 발행)
        → /analyze-trust 재호출

[USER] /analyze-trust
[CLAUDE] (진단: 모든 단계 완료)
        → [완료] 최종 리포트: docs/reports/<goal>.md
```