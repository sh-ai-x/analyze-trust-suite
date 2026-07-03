---
name: verify-report
description: |
  분석 결과를 재실행으로 검증하고 executed ipynb + HTML 리포트를 생성하는 파이프라인 6단계 스킬.
  각 셀 결과에 Claude 해석 마크다운을 추가하고, nbconvert로 실행 후 HTML 변환한다.
  Triggers: 검증, 리포트, 완료, verify-report, 결과 정리
  Prerequisite: scratch/analysis-cycle.md best_score 존재
---

# verify-report — 검증 및 리포트 생성

## 역할

파이프라인 마지막 단계. 재실행으로 검증하고 **executed ipynb + HTML** 리포트를 생성한다.
출력물: `docs/reports/YYYYMMDD-<goal>.ipynb` (실행 결과 포함) + `.html`
Iron Law #3: stdout 없이 완료 선언 불가.

---

## 실행 환경 확인 [CLAUDE]

`scratch/env.md`: `execution_env`, `data_path`
`scratch/analysis-cycle.md`: `best_hypothesis`, `best_features`, `best_model`, `best_score`
`docs/plans/<goal>.md`: `goal`, `success_metric`

---

## Step 1 — 스폿체크 재실행 [CLAUDE]

```python
# scripts/verify.py
import pandas as pd, numpy as np, warnings, platform
from pathlib import Path
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False

data_path = Path('{data_path}')
df = pd.read_csv(list(data_path.rglob('*.csv'))[0])
features = {best_features}
target = '{target_variable}'
best_score = {best_score}

X = df[features].copy()
y = df[target]
X = X.fillna(X.median(numeric_only=True))
for col in X.select_dtypes(include='object').columns:
    X[col] = LabelEncoder().fit_transform(X[col].astype(str))

model = {best_model_instance}
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=cv, scoring='{metric}')
mean_score = scores.mean()
diff = abs(mean_score - best_score)

print(f"[재실행] CV: {scores.round(4)}")
print(f"[재실행] 평균: {mean_score:.4f}")
print(f"[기록값] {best_score:.4f}")
print(f"[검증] {'OK' if diff < 0.01 else 'MISMATCH'} (차이: {diff:.4f})")
```

**Colab:** `mcp__colab-mcp__execute_code(코드)`
**Local:** `Write("scripts/verify.py", 코드)` → `Bash("python scripts/verify.py")`

`MISMATCH` 시: `"[backtrack] 수치 불일치. /analysis-cycle을 재실행해주세요."`

---

## Step 2 — 리포트 노트북 빌드 [CLAUDE]

검증 OK 후 Claude가 `scratch/` + 대화 컨텍스트를 바탕으로  
각 단계 해석(description)을 작성하고 `scripts/build_report.py`에 하드코딩한다.

### 노트북 구조

```
[MD] 제목 + 분석 개요
[Code] 공통 설정 (한글 폰트, 라이브러리)
[MD] 📌 데이터 개요 — Claude 해석
[Code] eda_pass1.py 내용
[MD] 📌 EDA Pass 1 해석 — Claude가 실제 수치 기반으로 작성
[Code] eda_pass2.py 내용
[MD] 📌 EDA Pass 2 해석 — 타깃 관계, 핵심 신호 요약
[MD] 🔬 가설 검증 — 선정 가설 및 근거
[Code] train.py 내용 (최종 best iteration)
[MD] 📌 모델링 결과 해석 — CV 점수, 피처 중요도 해석
[Code] verify.py 내용
[MD] 📌 검증 결과 — 재현성 확인 및 결론
```

### 해석 마크다운 작성 규칙 [CLAUDE]

- 각 `[MD] 📌` 셀은 Claude가 **실제 stdout 수치**를 인용하여 작성한다
- 추측 수치 금지 (Iron Law #4)
- 형식: `**핵심 발견**: ...`, `**의미**: ...`, `**다음 단계에서 활용**: ...`

### `scripts/build_report.py` 생성 [CLAUDE]

```python
# Claude가 실제 분석 결과를 바탕으로 아래 descriptions 딕셔너리를 채워 넣는다
import nbformat, datetime, platform
from pathlib import Path

today = datetime.date.today().strftime('%Y%m%d')
goal_slug = '{goal_slug}'

nb = nbformat.v4.new_notebook()
cells = []

# 제목
cells.append(nbformat.v4.new_markdown_cell(
    f"# {goal_slug} 분석 리포트\n\n"
    f"> Date: {today} | env: local | "
    f"Best Score: {'{best_score}'} ({'{metric}'})"
))

# 공통 설정 셀
cells.append(nbformat.v4.new_code_cell(
    "import platform, warnings\n"
    "import matplotlib.pyplot as plt\n"
    "import pandas as pd, numpy as np\n"
    "warnings.filterwarnings('ignore')\n"
    "plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'\n"
    "plt.rcParams['axes.unicode_minus'] = False\n"
    "print('환경 설정 완료')"
))

# 각 스크립트 + 해석 셀 쌍
script_configs = [
    ('eda_pass1.py', '📌 EDA Pass 1 — 데이터 구조 개요',
     # Claude가 실제 결과를 기반으로 이 문자열을 채운다:
     '{desc_eda_pass1}'),
    ('eda_pass2.py', '📌 EDA Pass 2 — 타깃 변수 관계 분석',
     '{desc_eda_pass2}'),
    ('train.py',    '📌 모델링 결과',
     '{desc_train}'),
    ('verify.py',   '📌 재현성 검증',
     '{desc_verify}'),
]

for script_name, section_title, description in script_configs:
    p = Path('scripts') / script_name
    if not p.exists():
        continue
    cells.append(nbformat.v4.new_markdown_cell(f"## {section_title}"))
    cells.append(nbformat.v4.new_code_cell(p.read_text()))
    cells.append(nbformat.v4.new_markdown_cell(description))

nb.cells = cells
out_dir = Path('docs/reports')
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / f"{today}-{goal_slug}.ipynb"
with open(out_path, 'w') as f:
    nbformat.write(nb, f)
print(f"노트북 생성: {out_path}")
```

`{desc_*}` 자리에 Claude가 실제 수치 기반 해석을 작성한다. 예시:

```
desc_eda_pass1 = """
**데이터 규모**: 891행 × 12컬럼  
**주요 결측치**: Age 19.9%, Cabin 77.1% — Cabin은 피처에서 제외  
**수치형 분포**: Fare 우측 꼬리 분포 (max=512, mean=32) — 로그 변환 고려
"""
```

---

## Step 3 — 노트북 실행 (nbconvert --execute) [CLAUDE]

```bash
Bash("python scripts/build_report.py")
```

노트북 파일 생성 확인 후 실행:

```bash
Bash("jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=300 \
  docs/reports/YYYYMMDD-{goal_slug}.ipynb 2>&1")
```

실패 시 확인:
- `jupyter` 미설치: `pip install jupyter nbconvert`
- 커널 없음: `python -m ipykernel install --user`
- 개별 셀 오류: stdout에서 `[Error]` 찾아 해당 스크립트 수정 후 재실행

성공 확인: stdout에 `Writing YYYYMMDD-{goal_slug}.ipynb` 출력 확인.

---

## Step 4 — HTML 변환 [CLAUDE]

```bash
Bash("jupyter nbconvert --to html \
  --no-input \
  docs/reports/YYYYMMDD-{goal_slug}.ipynb \
  --output docs/reports/YYYYMMDD-{goal_slug}.html 2>&1")
```

`--no-input` 플래그: 코드 셀 숨김, 출력·마크다운만 표시 (리포트 가독성 향상).  
코드도 보고 싶은 경우 `--no-input` 제거.

성공 확인:
```bash
Bash("ls -lh docs/reports/YYYYMMDD-{goal_slug}.*")
```

기대 출력:
```
docs/reports/YYYYMMDD-goal.ipynb   (실행 결과 포함 노트북)
docs/reports/YYYYMMDD-goal.html    (브라우저용)
```

---

## Step 5 — 요약 리포트 작성 [CLAUDE]

`docs/reports/YYYYMMDD-<goal-kebab>.md` 생성:

```markdown
# <goal> 분석 리포트

> Date: YYYY-MM-DD | env: local

## 분석 요약
- goal: ...
- analysis_type: ...
- 데이터셋: owner/dataset-name

## 최종 결과
| 항목 | 값 |
|------|-----|
| 가설 | H1: ... |
| 피처 | [...] |
| 모델 | RandomForest |
| CV 점수 | 0.8412 ± 0.0287 |
| 성공 기준 | AUC-ROC >= 0.80 ✅ |

## 검증
- 재실행 결과: 0.8401 (차이 0.0011) ✅

## 산출물
- 실행 노트북: docs/reports/YYYYMMDD-<goal>.ipynb
- HTML 리포트: docs/reports/YYYYMMDD-<goal>.html
```

---

## Step 5.5 — Results vault 동기화 [CLAUDE]

분석 결과를 `data-analysis-results` vault 레포에 자동 등록. `scratch/head-of-data-decision.md` 의 메타데이터를 모아 `docs/INDEX.md` 를 갱신한다.

**Vault 레포 경로** (env 또는 `DATA_ANALYSIS_RESULTS_DIR` 환경변수로 override 가능):
- 기본: `/Users/sanghee/dev/data-analysis-results/`
- vault 없으면 → `[skip] vault 레포 미설정. 수동 복사 필요.`

**갱신 로직**:

```python
# vault 레포의 scripts/update_index.py 가 docs/INDEX.md 를 재생성한다.
# verify-report 는 vault 가 있으면 실행, 없으면 skip.
import subprocess
from pathlib import Path

vault = Path(os.environ.get("DATA_ANALYSIS_RESULTS_DIR", "/Users/sanghee/dev/data-analysis-results"))
if not (vault / "scripts" / "update_index.py").exists():
    print("[skip] vault 레포 미설정. 수동 복사 필요.")
else:
    # 1. 이번 goal 의 산출물 복사
    today = datetime.date.today().strftime('%Y%m%d')
    src_reports = Path('docs/reports')
    if src_reports.exists():
        for ext in ('md', 'ipynb', 'html'):
            for f in src_reports.glob(f'*-{goal_slug}.{ext}'):
                shutil.copy(f, vault / 'docs' / 'reports' / f.name)
    src_plans = Path('docs/plans')
    if (src_plans / f'{goal_slug}.md').exists():
        shutil.copy(src_plans / f'{goal_slug}.md', vault / 'docs' / 'plans' / f'{today}-{goal_slug}.md')
    # 2. scratch 메타파일 복사
    for name in ('analysis-cycle', 'trust-metrics-llm', 'trust-metrics-code', 'qa-review', 'head-of-data-decision'):
        for f in Path('scratch').glob(f'{name}*-{goal_slug}.md'):
            shutil.copy(f, vault / 'scratch' / f.name)
    # 3. INDEX.md 재생성
    subprocess.run(['python3', str(vault / 'scripts' / 'update_index.py')], cwd=vault, check=False)
    print(f"[vault] {goal_slug} → {vault}")
```

**Bash**:
```bash
Bash("python scripts/verify_report_step_5_5.py <goal_slug>")
# 또는 환경변수로 vault 경로 override:
Bash("DATA_ANALYSIS_RESULTS_DIR=/path/to/vault python scripts/verify_report_step_5_5.py <goal_slug>")
```

**예외 처리**:
- vault 레포 없음 → `[skip] vault 레포 미설정. 수동 복사 필요.`
- `head-of-data-decision-<goal>.md` 없음 → `[warn] decision 메타데이터 없음. /head-of-data 먼저 실행.`

---

## Step 6 — 완료 보고 [CLAUDE → USER]

```
"분석 완료.

 산출물:
  - docs/reports/YYYYMMDD-<goal>.ipynb  (executed notebook)
  - docs/reports/YYYYMMDD-<goal>.html   (브라우저 리포트)
  - docs/reports/YYYYMMDD-<goal>.md     (요약)
  - data-analysis-results/             (vault 자동 동기화)

 Vault 확인:
  - INDEX: cat data-analysis-results/docs/INDEX.md
  - GitHub: https://github.com/sh-ai-x/data-analysis-results"
```

→ **[USER]** 최종 확인

---

## Colab 환경 저장 경로

Colab인 경우 Step 2~4를 Colab에서 실행:

```python
# execute_code로 실행
import shutil, datetime, glob, os
from google.colab import drive
drive.mount('/content/drive', force_remount=False)
today = datetime.date.today().strftime('%Y%m%d')
dst_dir = '/content/drive/MyDrive/harness_data_analysis/reports/'
os.makedirs(dst_dir, exist_ok=True)
nb_files = glob.glob('/content/*.ipynb')
if nb_files:
    dst_nb = f"{dst_dir}{today}-{goal_slug}.ipynb"
    shutil.copy(nb_files[0], dst_nb)
    # HTML 변환
    os.system(f"jupyter nbconvert --to html --no-input {dst_nb}")
    print(f"Drive 저장: {dst_nb}")
    print(f"HTML: {dst_nb.replace('.ipynb', '.html')}")
else:
    print("노트북 파일 없음")
```

---

## 역행 조건

| 에러 | 대응 |
|------|------|
| MISMATCH (diff ≥ 0.01) | `[backtrack] /analysis-cycle 재실행` |
| nbconvert 실행 실패 | 커널 설치 후 재시도 |
| HTML 빈 파일 | `--no-input` 제거 후 재시도 |
| 한글 깨짐 | 공통 설정 셀 폰트 확인 (AppleGothic/NanumGothic) |
