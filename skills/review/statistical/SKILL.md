---
name: review-statistical
description: |
  scratch/analysis-cycle.md 의 best_score 가 베이스라인 대비 통계적으로 유의미한지
  독립 재실행으로 검증. DummyClassifier / DummyRegressor 대비 paired t-test,
  95% bootstrap CI on lift, Cohen's d 효과 크기 측정.
  Triggers: 통계 검증, 베이스라인, review-statistical, baseline comparison, p-value
  Prerequisite: scratch/analysis-cycle.md best_* 확정, data/raw/, docs/plans/<goal>.md
---

# review-statistical — 통계 주장 재검증 (R3)

## 역할

기존 분석의 `best_score`가 베이스라인 대비 **통계적으로 유의미한지** 독립 재실행으로 검증.
재학습은 best_model만 재사용하고, 베이스라인은 DummyClassifier / DummyRegressor로 새로 적합한다.

---

## 입력

- `scratch/analysis-cycle.md` (best_hypothesis, best_features, best_model, best_score)
- `docs/plans/<goal>.md` (analysis_type, target_variable, success_metric)
- `data/raw/*.csv`

## 출력

- `scratch/review-statistical.md`
- `scratch/stat_results.json` (machine-readable)
- `scratch/stat_lift.png` (forest plot: best vs baselines with CI)
- stdout: numeric results (mean, p-value, lift, CI, d)

## 산출 스크립트

`scripts/review/statistical.py` — sklearn + scipy + matplotlib.

---

## 단계

### S1. Baseline fit

`analysis_type`별:

| type | baselines |
|------|-----------|
| classification | `DummyClassifier(strategy='most_frequent')`, `DummyClassifier(strategy='stratified')` |
| regression | `DummyRegressor(strategy='mean')`, `DummyRegressor(strategy='median')` |
| clustering | skip (not_applicable) |

### S2. Fold-aligned paired evaluation

`scripts/train.py` 와 동일한 CV 전략 사용:
- classification: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`
- regression: `KFold(n_splits=5, shuffle=True, random_state=42)`
- time-series: `TimeSeriesSplit(n_splits=5)`

각 fold에서 best_model과 모든 baseline 학습/평가 → aligned scores length=5.

### S3. Paired t-test

```python
scipy.stats.ttest_rel(best_scores, baseline_scores, alternative='greater')
```

Shapiro p<0.05 → Wilcoxon (n≥6) 또는 permutation test (n_perm=10000) fallback.

### S4. Bootstrap CI on lift

```python
lift = best_score - baseline_score
B = 2000 resamples with replacement
CI = percentile 2.5/97.5
```

### S5. Cohen's d (effect size)

```python
d = mean(best - baseline) / std(best - baseline)
```

### S6. Verdict

각 gate 통과 여부 + 종합 verdict:

| Gate | pass 조건 |
|------|----------|
| G1 | p_value < 0.05 |
| G2 | lift_pct ≥ 2% |
| G3 | |Cohen's d| ≥ 0.2 |
| G4 | CI_low > 0 |

Verdict: G1&G2&G3&G4 → PASS / 일부만 → WARN / 0 → FAIL

---

## 실행 흐름

### Step 1 — 환경 확인 [CLAUDE]

`scratch/env.md` 확인. 없으면 안내.

### Step 2 — 메타데이터 파싱 [CLAUDE]

`docs/plans/<goal>.md`: analysis_type, target_variable, success_metric
`scratch/analysis-cycle.md`: best_features, best_model, best_score

### Step 3 — 스크립트 실행 [CLAUDE]

**Colab:**
```python
mcp__colab-mcp__execute_code(code)
```

**Local:**
```bash
Bash("python scripts/review/statistical.py --plan <plan.md> --scratch-dir scratch/ --data-dir data/raw/")
```

### Step 4 — stdout 파싱 [CLAUDE]

```text
[statistical] analysis_type=classification
[baseline] most_frequent: mean=0.6167 ± 0.0054
[baseline] stratified: mean=0.6234 ± 0.0142
[best] CV AUC-ROC: 0.8523 ± 0.0287
[paired-t vs most_frequent] t=18.4, p=0.0000032
[bootstrap] lift=0.2356, CI=[0.2100, 0.2589]
[effect] cohen_d=3.42
[verdict] PASS (G1+G2+G3+G4)
```

각 수치를 `scratch/review-statistical.md` 본문에 인용.

### Step 5 — 보고서 작성 [CLAUDE]

```markdown
---
skill: review-statistical
plan: docs/plans/<file>.md
n_baselines: 2
verdict: PASS | WARN | FAIL
---

# 통계 검증 결과

**Best 모델**: <best_model>  
**Best 점수**: <best_score> ± <std>  
**베이스라인 수**: 2  
**Verdict**: PASS

## 베이스라인 비교

| 모델 | 평균 ± std | p-value | lift | 95% CI | Cohen's d |
|------|-----------|---------|------|--------|-----------|
| RandomForest (best) | 0.8523 ± 0.029 | — | — | — | — |
| DummyClassifier(most_frequent) | 0.6167 ± 0.005 | 0.0000032 | +0.236 | [0.210, 0.259] | 3.42 |
| DummyClassifier(stratified) | 0.6234 ± 0.014 | 0.0000041 | +0.229 | [0.198, 0.258] | 3.10 |

## Forest Plot

![lift](scratch/stat_lift.png)

## 결론

베이스라인 대비 통계적으로 유의미한 성능 우위 확인 (p<0.001, d>3). 모형이 단순 추측을 넘어서는 실제 신호를 학습했음.
```

### Step 6 — 사용자 보고

```
"✅ 통계 검증 완료
  베이스라인 수: 2
  verdict: PASS
  best vs baseline: +0.236 (p<0.001, d=3.42)

  open scratch/review-statistical.md"
```

---

## Iron Laws

- #3: stdout 없이 verdict 선언 금지
- #4: 추측 p-value 금지 (scipy 실측값만 인용)

---

## Standalone 사용 예시

```bash
python scripts/review/statistical.py \
  --plan docs/plans/20260625-titanic-survival.md \
  --scratch-dir scratch/ \
  --data-dir data/raw/

python scripts/review/statistical.py --self-test
```

---

## 기존 인프라 재사용

- `scratch/<skill-name>.md` YAML 헤더
- 한글 폰트 preamble (forest plot PNG)
- 동일 CV 전략 (`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`)
