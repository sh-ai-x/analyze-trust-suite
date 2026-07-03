---
name: local-setup
description: |
  Local 환경 설정 스킬. Python 환경·패키지를 확인하고 Kaggle 데이터셋을 data/raw/에 다운로드한다.
  Triggers: local-setup, 로컬 환경 설정, local 환경, 로컬 다운로드
  Prerequisite: scratch/env.md execution_env=local, scratch/kaggle-discover.md selected_ref 존재
---

# local-setup — 로컬 환경 설정 및 데이터 다운로드

## 역할

로컬 Python 환경을 확인하고 Kaggle 데이터셋을 `data/raw/`에 다운로드한다.
이후 모든 코드는 `scripts/` 에 저장 후 `Bash("python scripts/...")`로 실행한다.

---

## 인터랙션 흐름

### Step 1 — Python 환경 확인 [CLAUDE]

```bash
Bash("python --version && python -c 'import pandas, sklearn, xgboost, lightgbm, nbformat, jupyter_client; print(\"패키지 OK\")'")
```

패키지 없으면:
```
"다음 명령어로 패키지를 설치해주세요:
 pip install pandas scikit-learn xgboost lightgbm matplotlib seaborn kaggle nbformat nbconvert jupyter
 설치 후 알려주세요."
```

→ **[USER]** 설치 완료 확인

### Step 1-B — 한글 폰트 확인 [CLAUDE]

macOS에서 AppleGothic, Linux에서 NanumGothic 사용 가능 여부를 확인한다.
이후 모든 matplotlib 코드에는 아래 설정을 반드시 포함:

```python
# 모든 scripts/ 파일 상단에 포함
import platform, matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False
```

Linux에서 NanumGothic 없을 경우:
```bash
Bash("pip install koreanize-matplotlib && python -c 'import koreanize_matplotlib; print(\"OK\")'")
```
→ 설치 성공 시 스크립트 상단에 `import koreanize_matplotlib` 사용.

### Step 2 — Kaggle 인증 확인 [CLAUDE]

```bash
Bash("ls ~/.kaggle/kaggle.json 2>/dev/null && echo 'kaggle.json OK' || echo 'kaggle.json 없음'")
```

`kaggle.json 없음` 시:
```
"Kaggle API 키 파일이 없습니다.
 설정 방법:
  1. kaggle.com → Account → Settings → API → 'Create New Token' → kaggle.json 다운로드
  2. mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/
  3. chmod 600 ~/.kaggle/kaggle.json
 완료 후 알려주세요."
```

→ **[USER]** 설정 완료 확인

### Step 3 — 데이터 디렉토리 준비 [CLAUDE]

```bash
Bash("mkdir -p data/raw docs/reports scripts scratch && echo '디렉토리 준비 완료'")
```

### Step 4 — 데이터 다운로드 [CLAUDE]

`selected_ref` = `scratch/kaggle-discover.md`에서 읽기

```python
mcp__kaggle-mcp__download_kaggle_dataset(ref="{selected_ref}", path="data/raw/")
```

또는 fallback:
```bash
Bash("kaggle datasets download -d {selected_ref} --unzip -p data/raw/")
```

### Step 5 — 데이터 검증 [CLAUDE]

`scripts/check_data.py` 작성 후 실행:

```python
# Write("scripts/check_data.py", content below)
import pandas as pd
from pathlib import Path

csv_files = list(Path('data/raw').rglob('*.csv'))
print(f"CSV 파일: {len(csv_files)}개")
for f in csv_files[:3]:
    df = pd.read_csv(f)
    print(f"\n{f.name}: shape={df.shape}")
    print(df.dtypes.to_string())
    print(f"결측치:\n{df.isnull().sum().to_string()}")
```

```bash
Bash("python scripts/check_data.py")
```

stdout 파싱 후 `scratch/local-setup.md` 기록:

```markdown
---
skill: local-setup
dataset_ref: owner/dataset-name
data_path: data/raw/
status: ready
---
shape: (rows, cols)
컬럼: [...]
```

### Step 6 — 다음 단계 안내 [CLAUDE]

```
"로컬 데이터 준비 완료: data/raw/
 shape=(891, 12)
 /hypothesis-eda를 실행해주세요."
```

---

## 역행 조건

| 에러 | 대응 |
|------|------|
| 패키지 없음 | `pip install` 안내 |
| kaggle.json 없음 | Kaggle API 키 설정 안내 |
| 다운로드 실패 | `selected_ref` 확인 |
| CSV 없음 | `data/raw/` 하위 구조 확인 후 경로 조정 |
