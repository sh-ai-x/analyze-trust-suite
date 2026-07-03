---
name: review-report
description: |
  이미 생성된 docs/reports/*.ipynb 의 자기-일관성을 정적으로 검증.
  MD 셀이 인용한 숫자가 실제 Code 셀 출력에 존재하는지, 동일 수치가 다른 MD 셀에서
  다르게 인용되진 않았는지, 결론이 데이터 trend와 모순되진 않는지 확인한다.
  노트북 재실행 없음 — nbformat + regex 기반 정적 분석.
  Triggers: 리포트 리뷰, 노트북 검증, review-report, report consistency, 자기-일관성
  Prerequisite: docs/reports/YYYYMMDD-<goal>.ipynb 존재
---

# review-report — 노트북 자기-일관성 리뷰 (R1)

## 역할

Post-hoc 정적 검증. 이미 실행된 노트북(`docs/reports/*.ipynb`)을 **재실행 없이** 파싱해서
리포트 내부 일관성을 감사한다. 이 스킬은 `/analyze` 파이프라인의 일부가 아니며,
**완료된 분석의 독립적 감사 도구**다.

기존 `/verify-report` (단일 시드 재실행)와 다르다 — 이 스킬은 노트북 자체의 자기-일관성만 본다.

---

## 입력

- `docs/reports/YYYYMMDD-<goal>.ipynb` (가장 최근 파일 자동 선택)
- 환경 변수: Colab → Drive mount, Local → CWD 기준 상대 경로

## 출력

- `scratch/review-report.md` (YAML 헤더 + finding table + verdict)
- stdout: finding 목록 (severity, id, message, location)

## 산출 스크립트

`scripts/review/report.py` — nbformat + regex 기반 정적 파서. <2초 실행.

---

## 검사 항목

| ID | 검사 | severity=block |
|----|------|----------------|
| N1 | MD 셀이 인용한 숫자가 실제 Code 셀 출력에 존재 | warn |
| N2 | 동일 메트릭이 다른 MD 셀에서 다른 값으로 인용 | block |
| N3 | 결론 MD 셀이 데이터 trend와 모순 | warn |
| N4 | 필수 섹션 누락 (데이터 개요, EDA, 모델링, 검증, 결론) | warn |
| N5 | MD 셀이 stdout 출처 없는 추측 수치 사용 | block |
| N6 | 비어있는 Code 셀 출력 (실행 실패 흔적) | block |
| N7 | 다른 분석 도메인 잔재 (e.g., "타이타닉" 분석인데 "집값" 언급) | warn |
| N8 | 시각화 파일 참조가 실제 파일시스템에 존재 | warn |

---

## 실행 흐름

### Step 1 — 환경 확인 [CLAUDE]

`scratch/env.md` 확인 → execution_env (colab/local), data_path.
없으면: "scratch/env.md 가 없습니다. /analyze 또는 /define-analysis를 먼저 실행해주세요."

가장 최근 `docs/reports/*.ipynb` 자동 선택:
```bash
ls -t docs/reports/*.ipynb 2>/dev/null | head -1
```
없으면: "docs/reports/*.ipynb 가 없습니다."

### Step 2 — 정적 분석 실행 [CLAUDE]

**Colab:**
```python
mcp__colab-mcp__execute_code(code)
```

**Local:**
```bash
Bash("python scripts/review/report.py docs/reports/<file>.ipynb")
```

### Step 3 — stdout 파싱 [CLAUDE]

stdout에서 `FINDING|{id}|{severity}|{message}|{location}` 형식 파싱.
각 finding을 `scratch/review-report.md`에 기록.

### Step 4 — Verdict 산정 [CLAUDE]

```python
block_count = sum(1 for f in findings if f.severity == "block")
warn_count = sum(1 for f in findings if f.severity == "warn")

if block_count >= 1:
    verdict = "FAIL"
elif warn_count >= 3:
    verdict = "WARN"
else:
    verdict = "PASS"
```

### Step 5 — 보고서 작성 [CLAUDE]

`scratch/review-report.md`:
```markdown
---
skill: review-report
notebook: docs/reports/<file>.ipynb
n_block: <count>
n_warn: <count>
verdict: PASS | WARN | FAIL
---

# 리포트 자기-일관성 리뷰

**대상**: docs/reports/<file>.ipynb
**Verdict**: PASS | WARN | FAIL

## Finding Table

| ID | Severity | Message | Location |
|----|----------|---------|----------|
| N1 | warn | MD 셀이 0.85 인용, 실제 출력에 없음 | cell[8] |
| ... |

## 권고 액션

- block ≥ 1: 노트북 재생성 필요 (`/verify-report` 재실행)
- warn ≥ 3: 노트북 수정 권고
- PASS: 자기-일관성 확인됨
```

### Step 6 — 사용자 보고 [CLAUDE → USER]

```
"✅ 리포트 리뷰 완료
  대상: docs/reports/<file>.ipynb
  verdict: PASS | WARN | FAIL
  block: <n>  warn: <n>

  open scratch/review-report.md"
```

---

## Iron Laws

- #3: stdout 없이 verdict 선언 금지 (실제 finding 테이블이 stdout에 있어야 PASS/WARN/FAIL 가능)
- #4: 추측 finding 금지 (모든 N1~N8 finding은 노트북 파싱 결과 기반)

---

## Standalone 사용 예시

```bash
# 노트북 자기-일관성 리뷰
python scripts/review/report.py docs/reports/20260625-titanic-survival.ipynb

# Self-test
python scripts/review/report.py --self-test
```

---

## 역행 (Reference Only)

이 스킬은 standalone 도구이므로 backtrack이 없다. 단, verdict=FAIL이면
사용자가 `/verify-report` 또는 `/analyze`로 노트북을 재생성하도록 안내한다.

---

## 기존 인프라 재사용

- `scratch/<skill-name>.md` YAML 헤더 패턴
- nbformat (`pip install nbformat` — 기존 의존성)
- 한글 폰트 preamble 불필요 (정적 파싱)
