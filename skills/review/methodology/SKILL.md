---
name: review-methodology
description: |
  scripts/*.py 와 scratch/*.md 를 AST + 메타데이터 정적 분석해서 방법론적 결함을 감사.
  데이터 누수 (target / temporal / preprocessing), CV 전략 부적합, 가설 selection bias,
  metric direction 오류, seed 하드코딩, 경로 안전성, EDA→모델링 정합성 등을 탐지.
  재학습/재실행 없음.
  Triggers: 방법론 감사, 누수 검사, methodology review, audit, AST review
  Prerequisite: scripts/{train,eda_pass1,eda_pass2}.py, scratch/analysis-cycle.md
---

# review-methodology — 방법론 정적 감사 (R2)

## 역할

Post-hoc 정적 감사. 기존 분석의 스크립트와 메타데이터를 AST + 메타데이터 파싱해서
방법론적 결함을 탐지한다. **재학습/재실행 없음** — 빠르고 결정적인 감사 도구다.

`/verify-report` (단일 시드 재실행)나 `/review-report` (노트북 자기-일관성)와 다르다.
이 스킬은 **작성된 코드가 방법론적으로 올바른가**를 본다.

---

## 입력

- `scripts/train.py`, `scripts/eda_pass1.py`, `scripts/eda_pass2.py`
- `scratch/analysis-cycle.md` (best_*, loop_state)
- `scratch/hypothesis-eda.md` (top_hypotheses)
- `data/raw/*.csv` (target 누수 계산용)
- `docs/plans/<goal>.md` (analysis_type, target_variable, constraints)

## 출력

- `scratch/review-methodology.md` (YAML + finding table + verdict)
- stdout: finding 목록

## 산출 스크립트

`scripts/review/methodology.py` — AST walker + metadata parser + corr 계산.

---

## 검사 항목

| ID | 검사 | severity |
|----|------|----------|
| M1 | Target leakage — 피처가 타깃의 직접 사본/함수 (|r|>0.95) | block |
| M2 | Temporal leakage — 시계열 데이터에 shuffle=True | block |
| M3 | Preprocessing leakage — split 전 fit_transform | block |
| M4 | CV 전략 부적합 — 불균형 분류인데 KFold 사용 | warn |
| M5 | Hypothesis selection bias — 동일 hypothesis_id 반복 > 5회 | warn |
| M6 | Cherry-picking 흔적 — fold_excluded 플래그 | warn |
| M7 | 데이터 위생 — NaN 비율 > 0 인데 impute 호출 없음 | warn |
| M8 | Metric direction 오류 | block |
| M9 | Seed 하드코딩 — random_state=42 등장 > 2회 (검증 외) | warn |
| M10 | Path 안전성 — 절대 경로 또는 ~ 사용 | warn |
| M11 | Reproducibility — 한글 폰트 preamble 없음 | warn |
| M12 | EDA → 모델링 정합성 — EDA 제외 피처가 train에 등장 | block |

---

## 실행 흐름

### Step 1 — 환경 확인 [CLAUDE]

`scratch/env.md` 확인 → execution_env, data_path.
없으면: "scratch/env.md 가 없습니다. /analyze 또는 /define-analysis를 먼저 실행해주세요."

입력 파일 확인:
- `scripts/train.py` 없으면: "scripts/train.py 가 없습니다."
- `scratch/analysis-cycle.md` 없으면: "scratch/analysis-cycle.md 가 없습니다."

### Step 2 — 메타데이터 파싱 [CLAUDE]

`docs/plans/<goal>.md` frontmatter + body 파싱:
- analysis_type, target_variable, success_metric, constraints

`scratch/analysis-cycle.md` frontmatter + body 파싱:
- best_hypothesis, best_features, best_model, best_score
- loop_state: outer_iter, inner_iter, hypothesis_id 빈도

`scratch/hypothesis-eda.md` 파싱:
- top_hypotheses, 각 가설의 관련 피처

### Step 3 — 정적 분석 실행 [CLAUDE]

**Colab:**
```python
mcp__colab-mcp__execute_code(code)
```

**Local:**
```bash
Bash("python scripts/review/methodology.py --plan <plan.md> --scripts-dir scripts/ --scratch-dir scratch/ --data-dir data/raw/")
```

스크립트는 다음을 수행:
1. `scripts/train.py` AST 파싱 → fit_transform 위치, random_state, 절대 경로, 한글 폰트 preamble 검사
2. `docs/plans/<goal>.md` 분석 → metric direction, CV 전략 추론
3. `data/raw/*.csv` 로드 → 타깃 컬럼 기준 |corr(feature, target)| 계산 (M1, M7)
4. `scratch/analysis-cycle.md` 가설 빈도 카운트 (M5, M6)

### Step 4 — stdout 파싱 + Verdict [CLAUDE]

`FINDING|{id}|{severity}|{message}|{location}|{evidence}` 파싱.

Verdict:
- block ≥ 1 → FAIL
- warn ≥ 3 → WARN
- else → PASS

### Step 5 — 보고서 작성 [CLAUDE]

`scratch/review-methodology.md`:
```markdown
---
skill: review-methodology
plan: docs/plans/<file>.md
scripts: scripts/train.py
n_block: <count>
n_warn: <count>
verdict: PASS | WARN | FAIL
---

# 방법론 감사 결과

**대상**: docs/plans/<plan>, scripts/train.py, scratch/analysis-cycle.md
**Verdict**: PASS | WARN | FAIL

## 요약

- Best 가설: <best_hypothesis>
- Best 모델: <best_model>
- Best 점수: <best_score>
- 데이터 shape: (n, p)

## Finding Table

| ID | Severity | Message | Location | Evidence |
|----|----------|---------|----------|----------|
| M1 | block | target leak feature 'leak_col' (r=1.00) | scripts/train.py | corr=1.0 |
| ... |

## 권고 액션

- block ≥ 1: scripts/train.py 재작성 필요
- warn ≥ 3: 방법론 보강 권고
```

### Step 6 — 사용자 보고 [CLAUDE → USER]

```
"✅ 방법론 감사 완료
  대상: scripts/train.py + scratch/analysis-cycle.md
  verdict: PASS | WARN | FAIL
  block: <n>  warn: <n>

  open scratch/review-methodology.md"
```

---

## Iron Laws

- #3: stdout 없이 verdict 선언 금지
- #4: 추측 finding 금지 — 모든 finding은 AST/corr/count 계산 결과 기반

---

## Standalone 사용 예시

```bash
python scripts/review/methodology.py \
  --plan docs/plans/20260625-titanic-survival.md \
  --scripts-dir scripts/ \
  --scratch-dir scratch/ \
  --data-dir data/raw/

python scripts/review/methodology.py --self-test
```

---

## 기존 인프라 재사용

- `scratch/<skill-name>.md` YAML 헤더
- `python -c "import ast"` (stdlib) — 추가 의존성 없음
- pandas, sklearn (M1, M7 corr 계산용) — 기존 의존성
