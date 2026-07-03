---
name: analysis-cycle
description: |
  2-level 모델링 루프를 실행하는 파이프라인 5단계 스킬.
  scratch/env.md의 execution_env에 따라 Colab(execute_code) 또는 Local(Bash+script)로 실행한다.
  매 iteration 결과를 사용자에게 보고하고 방향 피드백을 받는다.
  Triggers: 모델링, 분석 사이클, analysis-cycle, 모델 돌리자
  Prerequisite: scratch/hypothesis-eda.md top_hypotheses 존재
---

# analysis-cycle — 모델링 루프

## 역할

파이프라인 5단계. Outer(가설) + Inner(피처+모델+CV) 2-level 루프.
매 Outer 전환 시 사용자 확인을 받는다.

---

## 한글 폰트 설정 (필수)

**train.py 상단에 반드시 포함:**

```python
import platform, matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False
```

---

## 실행 환경 확인 [CLAUDE]

`scratch/env.md`에서 읽기: `execution_env`, `data_path`
`docs/plans/<goal>.md`에서 읽기: `analysis_type`, `target_variable`, `success_metric`
`scratch/hypothesis-eda.md`에서 읽기: `top_hypotheses`, 각 가설의 관련 피처

---

## 모델 후보 (analysis_type 기반)

```
regression     → Ridge, RandomForest, XGBoost, LightGBM
classification → LogisticRegression, RandomForest, XGBoost, LightGBM
clustering     → KMeans(k=3~8), DBSCAN
descriptive    → t-test, ANOVA, chi2
```

## CV 전략

```
시계열 데이터   → TimeSeriesSplit(n_splits=5)
불균형 클래스   → StratifiedKFold(n_splits=5)
일반           → KFold(n_splits=5)
```

---

## 초기화 [CLAUDE]

`scratch/analysis-cycle.md` 없으면 생성:

```yaml
---
skill: analysis-cycle
stage: outer
outer_iter: 0
inner_iter: 0
hypothesis: ""
feature_set: []
model: ""
prev_score: 0.0
curr_score: 0.0
delta: 0.0
convergence: improving
max_outer: 5
max_inner: 10
---
```

---

## Outer Loop 시작 [CLAUDE → USER]

```
"H1부터 시작합니다: '{H1 설명}'
 관련 피처: [sex, pclass, age]
 진행할까요?"
```

→ **[USER]** "응" 또는 순서 변경

---

## Inner Loop 실행 [CLAUDE]

### 학습 코드 (공통)

```python
# scripts/train.py (iteration마다 덮어씀)
import pandas as pd, numpy as np, warnings, platform
from pathlib import Path
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

data_path = Path('{data_path}')
df = pd.read_csv(list(data_path.rglob('*.csv'))[0])
features = {feature_set}
target = '{target_variable}'

X = df[features].copy()
y = df[target]
X = X.fillna(X.median(numeric_only=True))
for col in X.select_dtypes(include='object').columns:
    X[col] = LabelEncoder().fit_transform(X[col].astype(str))

model = {model_instance}
cv = {cv_strategy}
scores = cross_val_score(model, X, y, cv=cv, scoring='{metric}')
print(f"CV: {scores.round(4)}")
print(f"평균: {scores.mean():.4f} ± {scores.std():.4f}")

# 피처 중요도 (트리 모델)
model.fit(X, y)
if hasattr(model, 'feature_importances_'):
    fi = pd.Series(model.feature_importances_, index=features).sort_values(ascending=True)
    fig, ax = plt.subplots(figsize=(6, max(3, len(features) * 0.4)))
    fi.plot(kind='barh', ax=ax, color='steelblue')
    ax.set_title('피처 중요도')
    ax.set_xlabel('중요도')
    plt.tight_layout()
    plt.savefig('scratch/feature_importance.png', dpi=100, bbox_inches='tight')
    plt.show()
    print(f"피처 중요도 저장: scratch/feature_importance.png")
    print(f"상위 피처: {fi.sort_values(ascending=False).head(3).to_dict()}")
```

**Colab 실행:**
```
mcp__colab-mcp__execute_code(코드)
```

**Local 실행:**
```
Write("scripts/train.py", 코드)
Bash("python scripts/train.py")
```

---

## 결과 보고 [CLAUDE → USER]

stdout에서 `평균: X.XXXX` 파싱 → loop_state 갱신:

```
"[Outer 1 / Inner 3] H1 | RandomForest | [sex, pclass, age]
 CV: 0.8234 ± 0.0312 | delta: +0.0187 | convergence: improving"
```

`scratch/analysis-cycle.md` loop_state 헤더 + iteration 로그 갱신.

수렴 판단:
```
delta > 0.005               → improving (계속)
0 < delta ≤ 0.005 × 2회   → plateaued → 모델 교체
delta ≤ 0 × 3회            → backtrack
curr_score ≥ 목표 threshold → converged
```

→ **[USER]** 언제든 방향 수정 가능: "다른 모델", "피처 추가", "여기서 끝내"

---

## Outer 전환 [CLAUDE → USER]

```
"H1 최고: 0.8412 (RandomForest). H2로 이동할까요?"
```

→ **[USER]** 결정

---

## 역행 [CLAUDE → USER]

```
"[backtrack] delta=0 × 3회. /hypothesis-eda를 재실행해주세요."
```

---

## 종료 [CLAUDE]

```
"분석 완료:
 최우선: H1 | RandomForest | 0.8412
 /verify-report를 실행해주세요."
```
