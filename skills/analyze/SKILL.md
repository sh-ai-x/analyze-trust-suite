---
name: analyze
description: |
  올인원 데이터 분석 스킬. Phase 1(인터뷰 ~5교환)에서 goal·데이터셋·환경 확정,
  Phase 2에서 환경준비→EDA→모델링→검증→ipynb+HTML 리포트까지 자동 완료.
  Triggers: analyze, 분석해줘, 분석 시작, 한번에 분석, 전체 실행, 분석하고 싶어
  Use instead of: define-analysis + kaggle-discover + local-setup + hypothesis-eda + analysis-cycle + verify-report 개별 실행
---

# analyze — 올인원 분석 파이프라인 (오케스트레이터)

## 구조

```
Phase 1 (인터뷰 ~5교환)         Phase 2 (A~E 자동, 입력 없음)
─────────────────────         ──────────────────────────────
P1.1 Goal              →      A. 환경 준비 (local|colab-setup)
P1.2 메타데이터        →      B. EDA (hypothesis-eda)
P1.3 환경 선택         →      C. 모델링 루프 (analysis-cycle, 자동 수렴)
P1.4 데이터셋 선택     →      D. 검증 (verify-report Step 1)
P1.5 승인 → 시작       →      E. 리포트 (verify-report Step 2~5)
```

진행 한 줄 출력: `[A/5] 환경 준비 중...` → `[E/5] 리포트 생성 중...`

---

## PHASE 1 — 인터뷰

### P1.1 — Goal [1교환]
사용자 입력을 즉시 Restate. 목표가 명확하면 Wonder 루프 생략.
```
"타이타닉 승객 데이터로 생존 여부를 예측하는 분류 모델 맞죠?
 다른 방향 (요금 예측, 군집 등)이면 말씀해주세요."
```

### P1.2 — 메타데이터 [1교환]
한 번에 질문:
```
"3가지 확인:
 1. 분석 유형: regression / classification / clustering / descriptive?
 2. 타깃 변수: 예측할 컬럼명? (없으면 '없음')
 3. 성공 기준: AUC-ROC / RMSE / F1 / Silhouette / p-value?"
```

### P1.3 — 환경 선택 [1교환]
```
"실행 환경:
 (1) Local  — Python + ~/.kaggle/kaggle.json 있으면 바로 실행
 (2) Colab  — GPU 필요 / 로컬 Python 없는 경우"
```

### P1.4 — 데이터셋 검색·선정 [1교환]
```python
mcp__kaggle-mcp__search_kaggle_datasets(query="{goal 핵심 키워드}")
```
상위 5개 제시 (ref, 행수, usability, 타깃 컬럼 포함 여부).
선정 기준: `usability ≥ 7.0`, 500+행, CSV, target_variable 컬럼 존재.
결과 불충분 시 쿼리 정제 후 1회 추가 검색.

### P1.5 — 승인 [1교환]
```
"시작 설정:
 goal:    {goal}
 type:    {analysis_type}
 target:  {target_variable}
 metric:  {success_metric}
 dataset: {selected_ref}
 env:     {execution_env}
 '시작' 입력 시 자동으로 분석 완료까지 실행합니다."
```

**승인 직후 파일 저장 (Phase 2 게이트):**

`docs/plans/YYYYMMDD-{goal-kebab}.md`:
```markdown
# {goal}
> Date: {today} | Status: approved
- goal, analysis_type, target_variable, success_metric, execution_env, dataset
```

`scratch/env.md`:
```yaml
---
execution_env: local   # local | colab
data_path: data/raw/   # colab: /content/drive/MyDrive/harness_data_analysis/data/
---
```

`scratch/kaggle-discover.md`:
```markdown
---
selected_ref: {selected_ref}
---
```

---

## PHASE 2 — 자동 실행

> **Iron Law**: 각 단계는 stdout 증거 없이 다음 단계로 진행하지 않는다.

### A — 환경 준비
**`[A/5] 환경 준비 중...`**
→ `/local-setup` 또는 `/colab-setup` Step 1~3을 그대로 실행.
완료 조건: `scratch/{local|colab}-setup.md` status=ready.

### B — EDA
**`[B/5] EDA 실행 중...`**
→ `/hypothesis-eda` Step 2 (Pass 1) + Step 3 (Pass 2) 실행.
stdout 파싱 → 가설 자동 생성 (신호강도 |r| 또는 그룹 평균 차이 내림차순, 최대 3개).
`scratch/hypothesis-eda.md` 저장, `top_hypotheses: [H1, H2, H3]`.

### C — 모델링 루프
**`[C/5] 모델링 루프 중...`**
→ `/analysis-cycle` 전체 루프 실행 (자동 수렴).

모델 후보:
- classification → [LogisticRegression, RandomForest, XGBoost]
- regression → [Ridge, RandomForest, XGBoost]

CV:
- classification (불균형) → StratifiedKFold(n_splits=5)
- regression → KFold(n_splits=5)

진행 출력: `[C | H1 | RF | iter 3] CV=0.8234 | delta=+0.041 | improving`

전체 Outer 완료 후 → global best 선정:
```
"[자동 선정] H1 | RandomForest | [Sex, Pclass, Age, Fare] | CV AUC-ROC=0.8412 ± 0.028"
```
`scratch/analysis-cycle.md` 최종 loop_state 업데이트.

### D — 검증
**`[D/5] 검증 중...`**
→ `/verify-report` Step 1 (재실행).
- OK → E로
- MISMATCH × 1 → 자동 재검증
- MISMATCH × 2 → 중단, 사용자에게 보고

### E — 리포트
**`[E/5] 리포트 생성 중...`**

3단계로 노트북 → HTML 산출물 생성:

**E1. 노트북 빌드** — `/verify-report` Step 2 (`scripts/build_report.py`).
- 각 셀에 Claude 해석 `[MD] 📌` 삽입, 스크립트 코드 셀 + 결과 + 해석 순서.

**E2. 노트북 실행 (executed ipynb)**:
```bash
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=300 \
  docs/reports/{today}-{goal_slug}.ipynb
```

**E3. HTML 변환 (필수)**:
```bash
jupyter nbconvert --to html --no-input \
  docs/reports/{today}-{goal_slug}.ipynb \
  --output docs/reports/{today}-{goal_slug}.html
```

`--no-input`은 코드 셀 숨김 (리포트 가독성). 코드도 표시하려면 제거.

**E4. 검증**:
```bash
ls -lh docs/reports/{today}-{goal_slug}.*
```
기대: `.ipynb` (실행 결과 포함) + `.html` (브라우저용) + `.md` (요약) 3파일.

---

## 최종 보고

```
"✅ 분석 완료
 목표:  {goal}
 결과:  {best_model} | CV {metric} {best_score} ± {std}
        피처: {best_features}
 검증:  {verify_score} (차이 {diff}) ✅
 산출물:
   docs/reports/{today}-{goal_slug}.ipynb
   docs/reports/{today}-{goal_slug}.html
   docs/reports/{today}-{goal_slug}.md
 open docs/reports/{today}-{goal_slug}.html"
```

---

## 역행 (자동, 입력 없음)

| 조건 | 자동 처리 |
|------|---------|
| 패키지 없음 | `pip install -q` 후 계속 |
| kaggle.json 없음 | **멈춤** → 사용자 설정 안내 후 재개 |
| 데이터 다운로드 실패 | fallback: kaggle CLI |
| delta ≤ 0 × 3 | 다음 가설로 자동 전환 |
| 전체 가설 신호 없음 | 수치형 전체 피처로 확장 후 1회 재시도 |
| MISMATCH × 1 | 자동 재검증 |
| MISMATCH × 2 | **멈춤** → 사용자 보고 |
| nbconvert 실패 | ipynb만 저장, HTML 실패 사유 보고 |
| 한글 깨짐 | koreanize-matplotlib 자동 설치 |

---

## Iron Laws (유지)

1. `docs/plans/` 없으면 Phase 2 진입 불가
2. `scratch/env.md` 없으면 Phase 2 진입 불가
3. stdout 없이 완료 선언 불가
4. 추측 수치 금지
5. loop_state 갱신 없이 반복 금지
