---
name: define-analysis
description: |
  데이터 분석 목표를 인터뷰로 확정하고 실행 환경(colab/local)을 선택하는 파이프라인 1단계 스킬.
  Ralph Loop(Wonder→Reflect→Restate)로 goal을 수렴하고, analysis_type·success_metric 확정 후 환경을 선택한다.
  Triggers: 분석 시작, 분석하고 싶어, 뭘 분석할지, define analysis, 분석 목표 잡자
  Skip when: docs/plans/ + scratch/env.md 모두 존재 → /kaggle-discover로 바로 진행
---

# define-analysis — 분석 목표 확정 + 환경 선택

## 역할

파이프라인 시작점. 두 가지 결과물을 생성:
- `docs/plans/<goal>.md` → Iron Law #1 게이트
- `scratch/env.md` → Iron Law #2 게이트 (환경 미선택 시 이후 스킬 실행 불가)

---

## 인터랙션 흐름

### Step 1 — Wonder [CLAUDE]

사용자 입력에서 해석 후보 3가지 발산.
`scratch/define-analysis.md`의 `## Wonder` 섹션에 기록.

→ **[USER]** "몇 번 의미가 맞아?" 또는 직접 수정

### Step 2 — Reflect [CLAUDE]

각 해석을 사용자 의도와 비교. `## Reflect` 섹션에 기록.
→ **[USER]** 차이 확인 및 수정

### Step 3 — Restate [CLAUDE]

수렴된 해석을 goal 한 문장으로 제시.
→ **[USER]** goal 승인 또는 수정

### Step 4 — 분석 메타데이터 확정 [CLAUDE + USER]

goal 확정 후 한 번에 하나씩:

```
Q1: "analysis_type이 다음 중 무엇인가요?"
    → regression / classification / clustering / descriptive

Q2: "target_variable이 무엇인가요?"
    → 컬럼명 (clustering/descriptive는 "없음")

Q3: "성공 기준(success_metric)은 무엇인가요?"
    → RMSE / AUC-ROC / F1 / Silhouette / p-value

Q4: "제약 조건이 있나요?"
    → 해석 가능성 요구, 특정 모델 금지 등 (없으면 "없음")
```

→ **[USER]** 각 질문에 답변

### Step 5 — 환경 선택 [CLAUDE → USER]

```
"마지막으로 분석 환경을 선택해주세요:

(1) Colab  — GPU 필요 / 대용량 데이터 / 로컬 Python 없는 경우
             데이터를 Google Drive에 저장, 세션 재시작해도 유지됨
             사전 조건: Colab Secrets에 KAGGLE_USERNAME / KAGGLE_KEY 등록

(2) Local  — CPU 일반 ML / 소규모 데이터 / 로컬 환경 있는 경우
             데이터를 data/raw/에 저장
             사전 조건: Python + kaggle CLI, ~/.kaggle/kaggle.json"
```

→ **[USER]** "1" / "colab" / "2" / "local"

### Step 6 — 파일 저장 [CLAUDE]

`docs/plans/YYYYMMDD-<goal-kebab>.md` 저장:

```markdown
# <goal>

> Date: YYYY-MM-DD | Status: pending-approval

## 분석 정의
- goal: ...
- analysis_type: ...
- target_variable: ...
- success_metric: ...
- constraints: [...]
- execution_env: colab | local

## 승인 체크리스트
- [ ] goal이 Kaggle 데이터셋으로 검증 가능하다
- [ ] analysis_type이 결정되었다
- [ ] success_metric이 측정 가능하다
- [ ] 실행 환경이 선택되었다
```

`scratch/env.md` 저장:

```yaml
---
execution_env: colab        # colab | local
data_path: /content/drive/MyDrive/harness_data_analysis/data/
# local인 경우:
# execution_env: local
# data_path: data/raw/
---
```

→ **[USER]** "approved" 입력

### Step 7 — 다음 단계 안내 [CLAUDE]

```
"설정 완료.
 /kaggle-discover를 실행해주세요."
```
