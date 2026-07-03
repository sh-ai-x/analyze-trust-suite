---
name: colab-setup
description: |
  Colab 환경 설정 스킬. Colab 세션 연결 후 Google Drive에 데이터를 저장한다.
  Drive 저장으로 Colab 세션 재시작 후에도 데이터가 유지된다.
  Triggers: colab-setup, colab 연결, Colab 환경 설정
  Prerequisite: scratch/env.md execution_env=colab, scratch/kaggle-discover.md selected_ref 존재
---

# colab-setup — Colab 연결 및 Google Drive 데이터 저장

## 역할

Colab 세션을 열고 데이터를 **Google Drive**에 다운로드한다.
`/content/data/`(ephemeral) 대신 Drive를 사용해 세션 재시작 후에도 데이터가 유지된다.

---

## 인터랙션 흐름

### Step 1 — Colab Secrets 확인 [CLAUDE → USER]

```
"시작 전 확인:
  Colab 좌측 패널 → 🔑 → Add new secret:
  - KAGGLE_USERNAME : Kaggle 계정명
  - KAGGLE_KEY     : Kaggle API 키 (kaggle.com → Settings → API)

  등록 완료됐나요?"
```

→ **[USER]** "응"

### Step 2 — Colab 세션 연결 [CLAUDE]

```python
mcp__colab-mcp__open_colab_browser_connection()
```

→ **[USER]** 브라우저에서 반환된 URL 열기 → "연결됐어"

### Step 3 — Google Drive 마운트 [CLAUDE]

```python
mcp__colab-mcp__execute_code("""
from google.colab import drive
drive.mount('/content/drive')
import os
os.makedirs('/content/drive/MyDrive/harness_data_analysis/data', exist_ok=True)
print("Drive 마운트 완료")
print("저장 경로:", '/content/drive/MyDrive/harness_data_analysis/data')
""")
```

### Step 4 — 패키지 설치 [CLAUDE]

```python
mcp__colab-mcp__execute_code("""
!pip install -q kaggle pandas scikit-learn xgboost lightgbm matplotlib seaborn
print("패키지 설치 완료")
""")
```

### Step 5 — Kaggle 인증 [CLAUDE]

```python
mcp__colab-mcp__execute_code("""
from google.colab import userdata
import os
os.environ['KAGGLE_USERNAME'] = userdata.get('KAGGLE_USERNAME')
os.environ['KAGGLE_KEY'] = userdata.get('KAGGLE_KEY')
print(f"Kaggle 인증: {os.environ['KAGGLE_USERNAME']}")
""")
```

에러 시: "Colab Secrets 등록을 확인해주세요."

### Step 6 — 데이터를 Drive에 다운로드 [CLAUDE]

`selected_ref` = `scratch/kaggle-discover.md`에서 읽기

```python
mcp__colab-mcp__execute_code(f"""
data_path = '/content/drive/MyDrive/harness_data_analysis/data'
!kaggle datasets download -d {selected_ref} --unzip -p {{data_path}}
print("다운로드 완료")
""")
```

### Step 7 — 데이터 검증 [CLAUDE]

```python
mcp__colab-mcp__execute_code("""
import pandas as pd
from pathlib import Path

data_path = Path('/content/drive/MyDrive/harness_data_analysis/data')
csv_files = list(data_path.rglob('*.csv'))
print(f"CSV 파일: {len(csv_files)}개")
for f in csv_files[:3]:
    df = pd.read_csv(f)
    print(f"\\n{f.name}: shape={df.shape}")
    print(df.dtypes.to_string())
""")
```

stdout 파싱 후 `scratch/colab-setup.md` 기록:

```markdown
---
skill: colab-setup
dataset_ref: owner/dataset-name
data_path: /content/drive/MyDrive/harness_data_analysis/data/
status: ready
---
shape: (rows, cols)
컬럼: [...]
```

### Step 8 — 다음 단계 안내 [CLAUDE]

```
"Drive 저장 완료: MyDrive/harness_data_analysis/data/
 shape=(891, 12)
 /hypothesis-eda를 실행해주세요."
```

---

## 역행 조건

| 에러 | 대응 |
|------|------|
| Drive 마운트 실패 | Google 계정 로그인 확인 |
| Kaggle 인증 실패 | Colab Secrets 재등록 |
| 다운로드 실패 | `selected_ref` 확인 후 재시도 |
