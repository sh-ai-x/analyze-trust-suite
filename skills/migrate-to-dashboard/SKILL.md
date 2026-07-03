# migrate-to-dashboard — 기존 분석 결과를 dashboard-state.json으로 일괄 변환

## 역할

`/verify-report`가 호출되기 **전에** 완료된 분석을 대시보드에 등록.
Iron Law: `docs/dashboard-state.json`을 idempotent하게 갱신. 중복 실행 안전.

**사용 시점**:
- analyze-trust 10-step을 거치지 않고 수동으로 분석한 결과가 있을 때
- 여러 goal을 한꺼번에 대시보드에 등록하고 싶을 때
- 다른 프로젝트에서 가져온 분석을 이 대시보드로 통합할 때

---

## Step 0 — 현재 상태 진단 [CLAUDE]

```bash
# 1) 기존 분석 카탈로그
ls docs/plans/*.md 2>/dev/null | wc -l        # plans 개수
ls docs/reports/*-{md,ipynb,html} 2>/dev/null | wc -l  # 발행된 리포트
ls scratch/head-of-data-decision.md 2>/dev/null         # 결정 메타데이터

# 2) 현재 dashboard-state.json
test -f docs/dashboard-state.json && echo "exists" || echo "missing"
```

| 상태 | 진단 |
|------|------|
| `state.json` missing | 신규 생성 |
| `state.json` exists | 기존 goals 보존 + 신규 추가 (idempotent) |
| `head-of-data-decision.md` 없음 | 해당 goal은 decision=UNKNOWN으로 등록 (경고) |

→ **[USER]** "실행해줘" 또는 "goal: <name> 만"

---

## Step 1 — 스캔 전략 [CLAUDE]

`docs/plans/YYYYMMDD-<goal>.md` 파일명을 정렬 → 각 goal에 대해:

```
[goal 수집]
  - docs/plans/<goal>.md          → goal 슬러그, 날짜
  - docs/reports/<date>-<goal>.{md,ipynb,html}  → 리포트 경로
  - scratch/head-of-data-decision.md  → decision, verdicts (있으면)
  - scratch/trust-metrics-{llm,code}.md → LLM/Code verdict fallback
  - scratch/qa-review.md          → QA verdict fallback
```

**fallback 규칙**:
- `head-of-data-decision.md` 없으면 → `scratch/qa-review.md`의 verdict를 qa_verdict로 사용
- 그것도 없으면 → `decision: UNKNOWN`, `*_verdict: UNKNOWN` (대시보드에서 회색 표시)

---

## Step 2 — state.json 생성 [CLAUDE]

**전체 goal 마이그레이션**:

```python
# scripts/migrate_dashboard_state.py
import json, datetime, re
from pathlib import Path

state_path = Path('docs/dashboard-state.json')
if state_path.exists():
    state = json.loads(state_path.read_text())
else:
    state = {"version": 1, "goals": []}

# 기존 goal 슬러그 (idempotent)
existing_goals = {g['goal'] for g in state['goals']}

# plans 파일명에서 goal 추출
new_goals = []
for plan_path in sorted(Path('docs/plans').glob('*.md')):
    # YYYYMMDD-<goal>.md 또는 <goal>.md 모두 지원
    match = re.match(r'^(\d{8})-(.+)\.md$', plan_path.name)
    if match:
        date_str, goal = match.groups()
    else:
        date_str = '00000000'
        goal = plan_path.stem

    if goal in existing_goals:
        print(f"[skip] {goal} (already in state.json)")
        continue

    # 리포트 경로 탐색
    reports = {}
    for ext in ['md', 'ipynb', 'html']:
        candidate = Path(f'docs/reports/{date_str}-{goal}.{ext}')
        if candidate.exists():
            reports[ext] = str(candidate)

    if not reports:
        print(f"[warn] {goal} (no reports found — 건너뜀)")
        continue

    # 결정 메타데이터
    decision_md = Path('scratch/head-of-data-decision.md')
    meta = {}
    if decision_md.exists():
        text = decision_md.read_text()
        # YAML front-matter 파싱
        if text.startswith('---'):
            yaml_part = text.split('---', 2)[1]
            for line in yaml_part.split('\n'):
                if ':' in line and not line.startswith('skill:'):
                    k, v = line.split(':', 1)
                    if k.strip() in ('decision', 'decided_at', 'llm_verdict', 'code_verdict', 'qa_verdict'):
                        meta[k.strip()] = v.strip().strip('"')

    new_goals.append({
        "goal": goal,
        "date": date_str,
        "decision": meta.get('decision', 'UNKNOWN'),
        "llm_verdict": meta.get('llm_verdict', 'UNKNOWN'),
        "code_verdict": meta.get('code_verdict', 'UNKNOWN'),
        "qa_verdict": meta.get('qa_verdict', 'UNKNOWN'),
        "decided_at": meta.get('decided_at', ''),
        "reports": reports,
    })

state['goals'].extend(new_goals)
state['updated_at'] = datetime.datetime.now().isoformat()

state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2))

print(f"[migrate] {len(new_goals)}개 신규 goal 등록 (총 {len(state['goals'])}개)")
for g in new_goals:
    print(f"  - {g['goal']} ({g['date']}, {g['decision']})")
```

**Bash**:
```bash
Bash("python scripts/migrate_dashboard_state.py")
```

---

## Step 3 — 검증 [CLAUDE]

생성된 state.json이 유효한지 검증:

```python
import json, pathlib
state = json.loads(pathlib.Path('docs/dashboard-state.json').read_text())
assert state['version'] == 1
assert isinstance(state['goals'], list)
for g in state['goals']:
    assert 'goal' in g and 'reports' in g
    assert any(Path(p).exists() for p in g['reports'].values()), f"{g['goal']} 리포트 파일 없음"
print(f"[ok] {len(state['goals'])}개 goal 모두 유효")
```

또는 단순 확인:

```bash
cat docs/dashboard-state.json | python -m json.tool > /dev/null && echo "valid JSON"
```

---

## Step 4 — 대시보드 새로고침 [CLAUDE → USER]

```
"마이그레이션 완료.

 docs/dashboard-state.json:
  - N개 goal 등록 (총 M개)

 대시보드 새로고침:
  open http://localhost:8000/

 사이드바에 모든 goal이 표시됩니다.
 첫 번째 goal이 자동 선택되며, 클릭으로 전환 가능."
```

---

## 역행 / 에러 처리

| 에러 | 대응 |
|------|------|
| `docs/plans/` 비어있음 | `"[abort] 마이그레이션할 분석 없음"` |
| `head-of-data-decision.md` 없음 (모든 goal) | `decision: UNKNOWN`로 등록. 대시보드에서 회색 ⚪ 표시 |
| `docs/reports/<goal>.md` 없음 | `plans`만 등록, `[warn]` 출력 |
| `docs/dashboard-state.json` 손상 | `state.json.bak` 백업 후 재생성 |
| 중복 실행 | idempotent — 같은 goal은 한 번만 등록 |

---

## Iron Law 자가 점검

- [ ] `execute_code` 호출 안 함 (로컬 Python만 사용)
- [ ] 기존 분석 데이터 수정 안 함 (read-only scan)
- [ ] `state.json` 손상 시 백업 후 진행
- [ ] 결정 메타데이터 추측 금지 (UNKNOWN으로 fallback)

위반 시: `"[Iron Law 위반] {액션}. read-only 마이그레이션입니다."`
