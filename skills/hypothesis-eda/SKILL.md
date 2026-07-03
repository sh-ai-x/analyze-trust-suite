---
name: hypothesis-eda
description: |
  EDA 2-pass를 실행하고 가설 목록을 사용자와 함께 확정하는 파이프라인 4단계 스킬.
  scratch/env.md의 execution_env에 따라 Colab(execute_code) 또는 Local(Bash+script)로 실행한다.
  Triggers: EDA, 탐색 분석, 가설 세우자, hypothesis-eda, 데이터 탐색
  Prerequisite: scratch/colab-setup.md 또는 scratch/local-setup.md status=ready
---

# hypothesis-eda — EDA 및 가설 수립

## 역할

파이프라인 4단계. 2-pass EDA 결과를 제시하고 사용자와 함께 가설 목록을 확정한다.

---

## 한글 폰트 설정 (필수)

**모든 matplotlib 코드 상단에 반드시 포함:**

```python
import platform, matplotlib.pyplot as plt, matplotlib
plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False
```

Linux에서 `NanumGothic` 없을 경우 `import koreanize_matplotlib` 사용 (local-setup Step 1-B 참조).

---

## 실행 환경 확인 [CLAUDE]

`scratch/env.md`에서 읽기:
- `execution_env`: colab | local
- `data_path`: `/content/drive/MyDrive/harness_data_analysis/data/` | `data/raw/`

`docs/plans/<goal>.md`에서 읽기:
- `analysis_type`, `target_variable`

---

## Pass 1 — Wide EDA

```python
# EDA Pass 1 코드 (공통)
import pandas as pd, numpy as np, platform
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

data_path = Path('{data_path}')
df = pd.read_csv(list(data_path.rglob('*.csv'))[0])
print("Shape:", df.shape)
print("\nDtypes:\n", df.dtypes.to_string())
print("\n결측치 비율:\n", df.isnull().mean().round(3).to_string())
print("\n수치형 통계:\n", df.describe().round(3).to_string())

numeric_cols = df.select_dtypes(include='number').columns.tolist()
if len(numeric_cols) > 1:
    corr = df[numeric_cols].corr().round(3)
    print("\n상관행렬:\n", corr.to_string())
    # 상관관계 히트맵
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', ax=ax)
    ax.set_title('수치형 변수 상관관계')
    plt.tight_layout()
    plt.savefig('scratch/eda_corr_heatmap.png', dpi=100, bbox_inches='tight')
    plt.show()
    print("히트맵 저장: scratch/eda_corr_heatmap.png")
```

**Colab 실행:**
```
mcp__colab-mcp__add_text_cell("## Pass 1: Wide EDA")
mcp__colab-mcp__add_code_cell(코드)
mcp__colab-mcp__execute_code(코드)
```

**Local 실행:**
```
Write("scripts/eda_pass1.py", 코드)
Bash("python scripts/eda_pass1.py")
```

→ **[USER]** stdout 결과 자동 수신 (확인 불필요, Claude가 분석)

---

## Pass 2 — Targeted (타깃 관계)

```python
# EDA Pass 2 코드 (공통)
import pandas as pd, numpy as np, platform
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

data_path = Path('{data_path}')
df = pd.read_csv(list(data_path.rglob('*.csv'))[0])
target = '{target_variable}'
numeric_cols = df.select_dtypes(include='number').columns.tolist()

# classification
if df[target].dtype == 'object' or df[target].nunique() < 10:
    print("클래스 분포:\n", df[target].value_counts(normalize=True).round(3).to_string())
    cat_cols = df.select_dtypes(include='object').columns.difference([target])
    for col in list(cat_cols)[:5]:
        print(f"\n{col} vs {target}:\n", df.groupby(col)[target].mean().round(3).to_string())

    # 범주형 vs 타깃 시각화
    top_cats = list(cat_cols)[:3]
    if top_cats:
        fig, axes = plt.subplots(1, len(top_cats), figsize=(5 * len(top_cats), 4))
        axes = [axes] if len(top_cats) == 1 else axes
        for ax, col in zip(axes, top_cats):
            df.groupby(col)[target].mean().plot(kind='bar', ax=ax, color='steelblue')
            ax.set_title(f'{col}별 {target} 비율')
            ax.set_ylabel('평균')
            ax.set_xlabel(col)
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig('scratch/eda_cat_target.png', dpi=100, bbox_inches='tight')
        plt.show()
        print("범주형 시각화 저장: scratch/eda_cat_target.png")

# regression
else:
    corrs = df[numeric_cols].corr()[target].abs().drop(target, errors='ignore')
    print("타깃 상관관계 (|r|):\n", corrs.sort_values(ascending=False).round(3).to_string())

    # 상위 피처 산점도
    top_feats = corrs.sort_values(ascending=False).head(4).index.tolist()
    fig, axes = plt.subplots(1, len(top_feats), figsize=(4 * len(top_feats), 4))
    axes = [axes] if len(top_feats) == 1 else axes
    for ax, feat in zip(axes, top_feats):
        ax.scatter(df[feat], df[target], alpha=0.3, s=10)
        ax.set_xlabel(feat)
        ax.set_ylabel(target)
        ax.set_title(f'{feat} vs {target}')
    plt.tight_layout()
    plt.savefig('scratch/eda_scatter.png', dpi=100, bbox_inches='tight')
    plt.show()
    print("산점도 저장: scratch/eda_scatter.png")
```

**Colab:** `add_code_cell` + `execute_code`
**Local:** `Write("scripts/eda_pass2.py")` + `Bash("python scripts/eda_pass2.py")`

---

## 가설 목록 제시 [CLAUDE → USER]

Pass 1 + Pass 2 stdout 분석 후:

```
"EDA 결과 기반 가설 초안:

H1: sex → survival (|r|=0.54) — high
H2: pclass → survival (|r|=0.34) — high
H3: age → survival (|r|=0.24) — medium

추가·제외할 가설이 있나요?"
```

→ **[USER]** "H3 빼고" 또는 "그대로"

---

## scratch 기록 [CLAUDE]

`scratch/hypothesis-eda.md` 저장:

```markdown
---
skill: hypothesis-eda
---

## 가설 목록 (신호강도 순)
| # | 가설 | 신호강도 | 관련 피처 | 우선순위 |
|---|------|---------|---------|---------|
| H1 | sex → survival | 0.54 | [sex, survived] | high |

## top_hypotheses: [H1, H2]
```

다음 단계: `"/analysis-cycle을 실행해주세요."`

---

## 역행 조건

전체 가설 신호 없음 → `"[backtrack] 신호 없음. /kaggle-discover를 재실행해주세요."`
