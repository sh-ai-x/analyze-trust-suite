---
name: kaggle-discover
description: |
  Kaggle MCP로 데이터셋을 검색·선정하는 파이프라인 2단계 스킬.
  Query Refinement Loop(최대 3라운드), 사용자가 최종 데이터셋을 선택한다.
  Triggers: 데이터셋 찾자, kaggle 검색, kaggle-discover, find dataset
  Prerequisite: docs/plans/ approved 파일 존재 (Iron Law #1)
---

# kaggle-discover — 데이터셋 검색·선정

## 역할

파이프라인 2단계. `docs/plans/<goal>.md`에서 `goal`과 `analysis_type`을 읽어 최적 Kaggle 데이터셋을 제시한다. **선택은 사용자가 한다.**

---

## 인터랙션 흐름

### Step 1 — 사전 확인 [CLAUDE]

```
docs/plans/ approved 파일 있음? → 계속
없음 → "Iron Law #1: /define-analysis를 먼저 실행해주세요"
```

`goal`, `analysis_type`, `target_variable` 읽기.

### Step 2 — Round 1 검색 [CLAUDE]

```python
mcp__kaggle-mcp__search_kaggle_datasets(query="<goal 핵심 키워드>")
```

결과 상위 5개를 표로 제시:

```
| # | ref | size | usability | 주요 컬럼 |
|---|-----|------|-----------|---------|
| 1 | ... | ...  | ...       | ...     |
```

→ **[USER]** 선택 또는 "다시 검색해줘"

### Step 3 — Round 2 (필요 시) [CLAUDE]

Round 1 결과가 불충분한 경우 쿼리 정제 후 재검색.
→ **[USER]** 선택 또는 Round 3 요청

### Step 4 — Round 3 (최종) [CLAUDE]

다른 각도의 키워드로 검색 (경쟁명, 도메인 용어).
3라운드 후에도 없으면 → 사용자에게 수동 검색 요청.

### Step 5 — 선정 확정 [CLAUDE]

사용자 선택 후 `scratch/kaggle-discover.md` 기록:

```markdown
---
skill: kaggle-discover
selected_ref: owner/dataset-name
rounds: N
---

## 선정 결과
- ref: owner/dataset-name
- usability: 9.5
- size: 61KB
- 컬럼: [PassengerId, Survived, Pclass, ...]
- 선정 이유: ...
```

→ **[USER]** 확인 후 다음 단계 진행

### Step 6 — 다음 단계 안내 [CLAUDE]

```
"데이터셋 선정 완료: owner/dataset-name
 /colab-setup을 실행해주세요."
```

---

## 선정 기준 (Claude 판단 기준)

- `usability_score >= 7.0`
- 행 수 500개 이상
- CSV/구조화 데이터
- `target_variable` 컬럼 존재 여부

---

## 출력

```yaml
selected_ref: owner/dataset-name
rounds_used: N
```
