---
name: trust-metrics-code
description: |
  Computation Trust 패널 산출. 생성된 ML/분석 코드가 정확한 결과를 내는가, 재현 가능한가 평가.
  Grounded.Numeric, CV Stability, Model Metrics, Data Trust, Confidence, Code Verdict 산출.
  재실행 필수. LLM Judge 호출은 하지 않음 (read-only 평가 금지).
  Triggers: trust-metrics-code, 컴퓨테이션 트러스트, 코드 평가, 그라운디드.넘버릭
  Prerequisite: scratch/analysis-cycle.md best_score + best_model/best_features 존재
  Depends on: harness-data-analysis (분석 6단계)
  Skip when: 동일 goal의 scratch/trust-metrics-code.md가 1시간 이내라면 → 재사용 제안
---

# trust-metrics-code — Computation Trust 패널

## 역할

분석 결과의 **코드 측 신뢰도** 만 평가한다. 다음 6개 메트릭을 산출해 `scratch/trust-metrics-code.md` 에 저장한다.

| 메트릭 | 산출 |
|---|---|
| Grounded.Numeric | 리포트 인용 숫자(N1개) vs scratch stdout → 일치 / N1 × 100 (±2% 허용) |
| CV Stability | best_model을 5-fold CV로 3회 재실행 → std ≤ 0.01 OK |
| Model Metrics | success_metric 기준 best_score |
| Data Trust | Freshness / Completeness / Consistency / Missing Rate → High/Medium/Low |
| Confidence | QA Checklist 4항목 + Outer/Inner verdict → (PASS + PARTIAL×0.5)/N × 100 |
| Code Verdict | FAIL / WARN / PASS |

**책임 경계**:
- 스킬만 **코드 재실행** 허용.
- LLM Judge 호출 **금지** (`trust-metrics-llm` 책임).
- 모델 학습(fit)은 `best_model`을 재실행하는 경우에만 허용. 신규 학습은 사용자 결정 + `/analysis-cycle` 위임.

---

## Step 0 — Skip when 확인 [CLAUDE]

`scratch/trust-metrics-code.md` 의 YAML `computed_at` 이 현재 시각 기준 1시간 이내면:

```
"[skip] 동일 goal의 trust-metrics-code 결과가 {elapsed} 전입니다. 재사용하시겠습니까?
 (1) 재사용
 (2) 재계산"
```

→ **[USER]** 응답 대기.

---

## Step 1 — 입력 수집 [CLAUDE]

읽기:
- `docs/plans/<goal>.md` — goal, success_metric
- `scratch/env.md` — execution_env, data_path, dataset_loaded_at
- `scratch/hypothesis-eda.md` — 데이터 품질 baseline
- `scratch/analysis-cycle.md` — **best_score, best_model, best_features, iteration 로그 (필수)**
- `docs/reports/<goal>.md` — 인용된 숫자 목록 (Grounded.Numeric 평가 대상)

---

## Step 2 — 메트릭 계산 [CLAUDE — 코드 실행]

### 2.1 Grounded.Numeric

리포트 `<goal>.md` 의 모든 숫자 토큰 추출 (버즈워드/단위/날짜 제외). 각 숫자에 대해 scratch/ 의 원본 stdout 또는 데이터 mart와 비교.

```
Grounded.Numeric = (일치 / 전체) × 100

일치 조건: |cited − actual| / |actual| ≤ 0.02  (허용 오차 ±2%)
```

산출 절차:
1. `docs/reports/<goal>.md` 파싱 → 숫자 + 인용 컨텍스트 추출
2. 각 숫자의 출처(`scratch/hypothesis-eda.md`, `scratch/analysis-cycle.md`, 데이터 mart) 추적
3. 실제 값과 비교 → 일치 / 부분일치 / 불일치 카운트

### 2.2 CV Stability

**Colab**: `mcp__colab-mcp__execute_code(code)`
**Local**: `Write("scripts/trust_verify.py", code)` → `Bash("python scripts/trust_verify.py")`

```python
# scripts/trust_verify.py (공통 골격, env별 실행)
import warnings
from pathlib import Path
import pandas as pd
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.preprocessing import LabelEncoder
warnings.filterwarnings('ignore')

data_path = Path('{data_path}')
df = pd.read_csv(list(data_path.rglob('*.csv'))[0])
features = {best_features}
target = '{target}'
success_metric = '{success_metric}'

X = df[features].copy()
y = df[target]
X = X.fillna(X.median(numeric_only=True))
for col in X.select_dtypes(include='object').columns:
    X[col] = LabelEncoder().fit_transform(X[col].astype(str))

model = {best_model_instance}
cv = {cv_strategy}

scores_list = []
for seed in range(3):
    if cv.__class__.__name__ == 'StratifiedKFold':
        cv_run = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    else:
        cv_run = KFold(n_splits=5, shuffle=True, random_state=seed)
    scores = cross_val_score(model, X, y, cv=cv_run, scoring=success_metric)
    scores_list.append(scores.mean())

import statistics
mean = statistics.mean(scores_list)
std = statistics.stdev(scores_list)
print(f"[CV Stability] runs=3, mean={mean:.4f}, std={std:.4f}")
print(f"[Verdict] {'OK' if std <= 0.01 else 'WARN' if std <= 0.02 else 'FAIL'}")
```

### 2.3 Model Metrics

`scratch/analysis-cycle.md` 의 `best_score` 와 `success_metric` 을 그대로 인용.

```
Model Metrics = {success_metric} {best_score} ± {best_std}
```

### 2.4 Data Trust

4개 신호 종합:

| 신호 | High 조건 |
|---|---|
| Freshness | `dataset_loaded_at` 기준 30일 이내 |
| Completeness | 전체 결측률 < 5% |
| Consistency | numeric range / dtype 모두 EDA와 일치 |
| Missing Rate | 핵심 컬럼 결측률 < 2% |

```
Data Trust = High   iff 4개 모두 High
Data Trust = Medium iff 3개 High
Data Trust = Low    iff 그 외
```

판단은 `scratch/hypothesis-eda.md` 의 EDA 결과 + `scratch/env.md` 의 `dataset_loaded_at` 기반.

### 2.5 Confidence

워크숍 QA Checklist 4항목 (qa-reviewer 책임이지만 스킬에서 사전 집계):

| 항목 | 평가 대상 |
|---|---|
| 모든 단계 결론 비교 | iteration 로그의 hypothesis ↔ score 일관성 |
| 상충·중복 평가 | 동일 hypothesis의 Outer iteration 간 score 변동 |
| 신규 분석 없음 | (qa-reviewer가 검증) |
| 중복·누락 연결 | Outer 가설 간 비교 |

각 항목 PASS / PARTIAL / FAIL 판정 후:

```
Confidence = (PASS + PARTIAL×0.5) / 4 × 100
```

### 2.6 Code Verdict

```
Code Verdict = FAIL  iff (CV Stability == FAIL) OR (Confidence < 60) OR (Data Trust == Low)
Code Verdict = WARN  iff (CV Stability == WARN) OR (Confidence < 80) OR (Data Trust == Medium)
Code Verdict = PASS  iff 그 외
```

---

## Step 3 — scratch 저장 [CLAUDE]

`scratch/trust-metrics-code.md` 작성:

```yaml
---
skill: trust-metrics-code
goal: <goal-kebab>
computed_at: YYYY-MM-DDTHH:MM:SS
env: colab | local
---
## Computation Trust 패널

| Metric | Value | Note |
|--------|-------|------|
| Grounded.Numeric | 95.2 | 39/41 일치 (±2%) |
| CV Stability | OK | std 0.008 (3회 재실행) |
| Model Metrics | AUC 0.8412 ± 0.0287 | success_metric 기준 |
| Data Trust | High | Freshness ✓, Completeness ✓, Consistency ✓, Missing ✓ |
| Confidence | 87.5 | 4 PASS / 0 PARTIAL / 0 FAIL |
| Code Verdict | PASS | CV OK, Confidence >= 80, Data Trust=High |

## 숫자 대조 상세 (상위 5개)

| Cited | Actual | Δ% | Verdict |
|-------|--------|----|---------|
| 0.8412 | 0.8408 | 0.05% | OK |
| 16.7% | 16.5% | 1.20% | OK |
| 72.3% | 72.1% | 0.28% | OK |
| ... | ... | ... | ... |

## CV Stability Runs
- seed=0: 0.8412
- seed=1: 0.8398
- seed=2: 0.8405
- mean=0.8405, std=0.0007
```

---

## Step 4 — 역행 결정 [CLAUDE → USER]

| 조건 | 권장 메시지 |
|---|---|
| Code Verdict=FAIL | `"[backtrack] Code Verdict=FAIL. /analysis-cycle을 재실행해주세요."` |
| Data Trust=Low | `"[backtrack] Data Trust=Low. /colab-setup 또는 /local-setup으로 데이터 재로드 권장."` |
| CV Stability=FAIL | `"[backtrack] CV Stability FAIL (std {std}). /analysis-cycle에서 모델 변경 권장."` |
| Grounded.Numeric < 70 | `"[backtrack] Grounded.Numeric {val}% < 70%. 리포트 숫자 재검토 권장."` |
| 그 외 | `"trust-metrics-code 완료. /qa-reviewer를 실행해주세요."` |

---

## Iron Law 자가 점검

스킬은 **코드 실행 허용**. 다음만 금지:
- LLM Judge 호출 (trust-metrics-llm 책임)
- 신규 분석 스킬 호출 (`/analysis-cycle` 등) — 사용자 결정 후 별도 호출

위반 시: `"[Iron Law 위반] {액션}. LLM 평가는 /trust-metrics-llm 책임, 분석 재실행은 /analysis-cycle 책임입니다."`