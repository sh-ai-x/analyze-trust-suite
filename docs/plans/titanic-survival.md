# Analysis Plan — Titanic Survival Prediction

## Goal
Build and evaluate a classification model that predicts whether a Titanic passenger
survived (`Survived` ∈ {0,1}) from passenger attributes, and quantify how much each
modeling step improves over naive baselines.

## Ralph Loop (Wonder → Reflect → Restate)

**Wonder** — What does "predict survival" actually mean here? Candidate readings:
(a) rank passengers by survival probability, (b) produce a hard 0/1 label, (c) explain
*which* attributes drove survival. The classic Titanic task is (b) hard-label accuracy,
with (c) as supporting interpretation.

**Reflect** — The user wants a reproducible, evidence-backed pipeline, not just a single
score. So the target is a clean classification model **plus** a comparison against
baselines (majority-class, sex-only rule) to show genuine lift. Pure accuracy without
baselines would hide that "women survive" alone is already strong.

**Restate (goal sentence)** — *Predict the binary `Survived` label for Titanic passengers
using demographic/ticket features, evaluated by 5-fold stratified cross-validation
accuracy, and demonstrate improvement over majority-class and sex-only baselines.*

## Framing Questions
1. How much signal comes from `Sex` and `Pclass` alone vs. engineered features?
2. Does feature engineering (Title, FamilySize, IsAlone, bins) beat raw features?
3. Which model family (linear vs. tree ensemble) generalizes best under CV?
4. Are the gains real (positive delta vs. previous best) or noise?

## Prediction Target
`Survived` (binary classification: 1 = survived, 0 = died).

## Success Metric
- Primary: **5-fold StratifiedKFold accuracy** (mean ± std), fixed `random_state=42`.
- Comparative: each iteration's CV accuracy and delta vs. the previous best.
- Baselines to beat: majority-class (all-die) and sex-only rule (female ⇒ survive).

## Environment
**Local** (CPU, small dataset). Code executed via `python3 scripts/*.py`; data in `data/raw/`.

## Data Source Note
Kaggle MCP was **unavailable** in this environment, so the canonical Titanic dataset was
sourced from a public mirror:
`https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv`
(891 rows × 12 columns — equivalent to the Kaggle `train.csv`).
