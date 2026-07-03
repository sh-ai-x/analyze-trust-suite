---
name: review-robustness
description: |
  단일 seed=42 점수가 아닌 5 seeds × 5 folds = 25 scores 로 모델 안정성 측정.
  추가로 leave-one-feature-out (LOFO) 감도 분석, 슬라이스별 성능, permutation importance 안정성.
  Triggers: 강건성, 다중 시드, review-robustness, robustness, sensitivity, LOFO
  Prerequisite: scratch/analysis-cycle.md best_model 확정, docs/plans/<goal>.md
---

# review-robustness — 강건성 검증 (R4)

## 역할

기존 분석의 `best_score`가 **seed에 의존하지 않고 안정적인지** 검증.
단일 시드 점수만 보고하면 overfit-to-validation 가능성을 놓칠 수 있다.
5 seeds × 5 folds = 25 scores 로 안정성 측정 + 추가 감도 분석.

---

## 입력

- `scratch/analysis-cycle.md` (best_hypothesis, best_features, best_model, best_score)
- `docs/plans/<goal>.md` (analysis_type, target_variable, success_metric)
- `data/raw/*.csv`

## 출력

- `scratch/review-robustness.md`
- `scratch/robustness_results.json`
- `scratch/seed_boxplot.png`
- `scratch/lofo_drop.png`
- `scratch/slice_perf.png`
- stdout: numeric results

## 산출 스크립트

`scripts/review/robustness.py` — sklearn + matplotlib.

---

## 단계

### B1. Multi-seed CV

```
seeds = [0, 1, 7, 42, 123]
n_folds = 5
→ 25 scores
metrics: mean, std, min, max, median, IQR
```

### B2. Bootstrap CI on best_score

```
B = 2000 resamples of the 25 scores
CI = percentile 2.5/97.5
```

베이스라인 평균과 비교 → CI excludes baseline_mean? 검증.

### B3. Leave-One-Feature-Out (LOFO)

각 피처 `f_i` 제거 후 5-seed × 5-fold CV 재실행 → `delta_drop = best_full_score - score_without_fi`.

`scratch/lofo_drop.png` 시각화. 임계치(기본 15%) 초과 피처 → load-bearing으로 flag.

### B4. Per-slice performance

자동으로 slice 차원 탐색 (최대 3개):
- (a) 가장 높은 |r| numeric 컬럼의 low/mid/high 분위
- (b) 가장 중요한 피처의 head/tail 50%
- (c) classification: rare-vs-common class

각 slice 별 5-seed CV 점수.

### B5. Permutation importance stability

`permutation_importance(n_repeats=20)` for each seed.  
top-3 features ≥4/5 seeds 일치? mismatch → warn.

---

## 게이트

| Gate | pass 조건 |
|------|----------|
| G1 (stability) | seed_std ≤ 0.03 |
| G2 (CI > baseline) | bootstrap CI_low > baseline_mean |
| G3 (LOFO) | no feature drop > 25% |

Verdict: G1+G2+G3 → PASS / 일부 → WARN / 0 → FAIL

---

## 실행 흐름

### Step 1 — 환경 확인 [CLAUDE]

`scratch/env.md` 확인.

### Step 2 — 메타데이터 파싱 [CLAUDE]

`docs/plans/<goal>.md` + `scratch/analysis-cycle.md` 파싱.

### Step 3 — 스크립트 실행 [CLAUDE]

**Colab:** `mcp__colab-mcp__execute_code(code)`
**Local:** `Bash("python scripts/review/robustness.py --plan ... --scratch-dir scratch/ --data-dir data/raw/")`

### Step 4 — stdout 파싱 [CLAUDE]

```text
[robustness] task=classification metric=AUC-ROC features=5 seeds=5 folds=5
[multi-seed] mean=0.8523 std=0.0187 min=0.8234 max=0.8789 median=0.8545 IQR=[0.8398, 0.8654]
[bootstrap] CI=[0.8156, 0.8890]
[gate-G1] PASS (seed_std=0.0187 <= 0.03)
[lofo] feat1 dropped: 0.8234 (drop=0.0289, 3.4%)
       feat2 dropped: 0.7891 (drop=0.0632, 7.4%) [load-bearing]
       ...
[gate-G3] WARN (feat2 drop=7.4% in [5%, 15%])
[slice] rare_class: 0.8123 (5-seed mean)
[slice] head_50%: 0.8912
[slice] tail_50%: 0.8234
[perm-importance] top3=feat1,feat2,feat3 (5/5 seeds 일치)
[gate-G2] PASS (CI_low=0.8156 > baseline=0.6167)
[verdict] PASS
```

### Step 5 — 보고서 작성 [CLAUDE]

`scratch/review-robustness.md`:
```markdown
---
skill: review-robustness
n_seeds: 5
n_folds: 5
n_features: 5
verdict: PASS | WARN | FAIL
---

# 강건성 검증 결과

**Best 모델**: <best_model>
**Multi-seed 통계**: mean=... std=... CI=[lo, hi]

## 시각화

![seeds](scratch/seed_boxplot.png)
![lofo](scratch/lofo_drop.png)
![slice](scratch/slice_perf.png)

## LOFO 감도

| 피처 | 점수 (제거 후) | Drop | Status |
|------|---------------|------|--------|
| feat1 | 0.8234 | -0.029 (3.4%) | OK |
| feat2 | 0.7891 | -0.063 (7.4%) | LOAD-BEARING (warn) |

## 슬라이스별 성능

| Slice | Score | Notes |
|-------|-------|-------|
| rare_class | 0.8123 | baseline=0.6167 |
| head_50% | 0.8912 | |
| tail_50% | 0.8234 | |

## 결론
...
```

### Step 6 — 사용자 보고

```
"✅ 강건성 검증 완료
  seeds × folds: 5 × 5 = 25 scores
  std: 0.0187, CI: [0.8156, 0.8890]
  verdict: PASS

  open scratch/review-robustness.md"
```

---

## Iron Laws

- #3: stdout 없이 verdict 금지
- #4: 추측 점수 금지 (실제 25 scores 기반)

---

## Standalone 사용 예시

```bash
python scripts/review/robustness.py \
  --plan docs/plans/20260625-titanic-survival.md \
  --scratch-dir scratch/ \
  --data-dir data/raw/

python scripts/review/robustness.py --self-test
```

---

## 기존 인프라 재사용

- `scratch/<skill-name>.md` YAML 헤더
- 한글 폰트 preamble (3 PNG)
- 동일 CV 전략 (`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`)
- 동일 `cross_val_score` 기반
