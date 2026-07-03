# Titanic Survival Prediction — Final Report

**Date:** 2026-06-24
**Goal:** Predict the binary `Survived` label for Titanic passengers and demonstrate
measurable lift over naive baselines, evaluated by 5-fold stratified CV accuracy.

## Environment
- **Local** (CPU), code run via `python3 scripts/*.py`.
- Reproducibility: fixed `random_state=42`, 5-fold `StratifiedKFold(shuffle=True)`.

## Data Source & Shape
- Canonical Titanic dataset, **891 rows × 12 columns** (labeled training set).
- Kaggle MCP was **unavailable**, so data was fetched from a public mirror:
  `https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv`.
- Missing values: `Age` 177, `Cabin` 687, `Embarked` 2.

## Key EDA Findings (real numbers from `scripts/eda.py`)
- Overall survival rate: **0.3838** (342/891).
- **Sex** is the dominant signal: female **0.7420** vs male **0.1889** (gap 0.553).
- **Pclass** is monotonic: 1st **0.6296**, 2nd **0.4728**, 3rd **0.2424**.
- **Children** survive more: child(<16) **0.5904** vs adult **0.3819**.
- **Family size** has a sweet spot: solo **0.3035**, families of 2–4 ≈ 0.55–0.72,
  large families (5+) collapse (e.g. size 8 and 11 ⇒ 0.0000); IsAlone 0.3035 vs
  with-family 0.5056.
- Embarked: C **0.5536**, Q **0.3896**, S **0.3370** (weak, likely class-confounded).

## Model Comparison (5-fold StratifiedKFold, real CV from `scripts/run.py`)

| iter | model / rule                              | CV mean | CV std | delta vs prev best |
|------|-------------------------------------------|---------|--------|--------------------|
| 0    | majority-class baseline (all die)         | 0.6162  | 0.0000 | — (baseline)       |
| 1    | sex-only rule (female ⇒ survive)          | 0.7868  | 0.0188 | +0.1706            |
| 2    | LogisticRegression (basic features)       | 0.7969  | 0.0146 | +0.0101            |
| 3    | RandomForest (basic features)             | 0.8170  | 0.0242 | +0.0202            |
| 4    | **HistGradientBoosting (engineered)**     | **0.8316** | **0.0148** | +0.0146      |

## Selected Best Model
**HistGradientBoostingClassifier** on engineered features
(FamilySize, IsAlone, Title, AgeBin, FareBin + raw numeric/categorical).
**CV accuracy = 0.8316 ± 0.0148.**

Verification re-run (Stage 6) reproduced the score exactly: **0.8316 ± 0.0148** (match = True).

## Top Features
RandomForest importances (engineered set): Fare 0.1802, Age 0.1597, Title_Mr 0.1020,
Sex_male 0.0866, Sex_female 0.0830, FamilySize 0.0442, Pclass_3 0.0438, SibSp 0.0296.

LogisticRegression coefficients (direction): Sex_female +1.3778, Sex_male −1.2779,
Pclass_3 −1.0438, Pclass_1 +1.0000, Age −0.4810, SibSp −0.3458.

## Conclusions (data-driven)
1. Sex alone explains most survival variance: the sex-only rule jumps accuracy from 0.6162
   to 0.7868 (+0.1706) over the majority baseline.
2. Adding class, age, fare, and family structure via a linear model adds a further +0.0101,
   and tree ensembles add more (+0.0202 for RandomForest).
3. Feature engineering + gradient boosting yields the best generalization at 0.8316 ± 0.0148,
   a total improvement of **+0.2154** over the majority-class baseline.
4. Feature importances and coefficients agree with EDA: Sex, Pclass, Fare, Age, and the
   derived Title are the strongest drivers.

## Limitations & Reproducibility
- **Fixed seed** (`random_state=42`) and stratified 5-fold CV — the verify re-run matched
  to 4 decimals, so results are reproducible.
- **Single public-mirror dataset** (891 labeled rows); no external/held-out test set.
- **No Kaggle leaderboard submission** — Kaggle MCP was unavailable, so there is no
  held-out Kaggle `test.csv` score; all metrics are cross-validation on the training set.
- Small sample (891 rows) means CV std (~0.015–0.024) is non-trivial; absolute differences
  under ~0.01 between models should be read as roughly comparable.
- `Cabin` (687 missing) was excluded; richer feature engineering on it could add signal.
