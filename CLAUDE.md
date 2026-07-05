# analyze-trust-suite

End-to-end data analysis + trust evaluation + meta-orchestrator in one plugin. Replaces the legacy 3-plugin setup (`analyze-orchestrator`, `harness-data-analysis`, `data-team-trust`). PR review is wired to MiniMax-M3[1m] via `.github/workflows/review.yml`.

---

## 1. Overview

`/analyze-trust <goal>` — single entry point. The orchestrator diagnoses the current state of `scratch/` and `docs/` and guides the user through the 10-step pipeline. Each user decision gate (plan approval, env selection, hypothesis approval, PUBLISH decision) waits for explicit input.

The suite bundles three formerly separate plugins:

| Legacy plugin | Skills inherited | Role |
|---|---|---|
| `harness-data-analysis` | define-analysis, kaggle-discover, colab-setup, local-setup, hypothesis-eda, analysis-cycle, verify-report, analyze, ralph, wonder, reflect, restate, verification-before-completion, migrate-to-dashboard, review/5 | 6-stage analysis pipeline |
| `data-team-trust` | trust-metrics-llm, trust-metrics-code, qa-reviewer, head-of-data | 4-stage trust evaluation + PUBLISH gate |
| `analyze-orchestrator` | analyze-trust | Meta-orchestrator (the entry point) |

---

## 2. 6-stage Analysis Pipeline

Kaggle MCP + Colab/Local data analysis. Choose environment in `/define-analysis`; `scratch/env.md` records the choice.

| Stage | Skill | Output |
|---|---|---|
| 1 | `define-analysis` | `docs/plans/<goal>.md` + `scratch/env.md` |
| 2 | `kaggle-discover` | `scratch/kaggle-discover.md` (data ref) |
| 3 | `colab-setup` or `local-setup` | `data/` populated |
| 4 | `hypothesis-eda` | `scratch/hypothesis-eda.md` (top hypotheses) |
| 5 | `analysis-cycle` | `scratch/analysis-cycle.md` (best_score, best_model) |
| 6 | `verify-report` | `docs/reports/<date>-<goal>.{md,ipynb,html}` |

**All-in-one entry**: `/analyze <goal>` runs Phase 1 (5-exchange interview) → Phase 2 (auto-execute A→E) without further input.

**Environment selection**:

| Env | When to pick | Code exec | Data |
|---|---|---|---|
| **Colab** | GPU, large data | `mcp__colab-mcp__execute_code` | Google Drive |
| **Local** | CPU, small data | `Bash("python scripts/...")` | `data/raw/` |

---

## 3. 4-stage Trust Pipeline

Evaluates analysis output along two independent dimensions.

| Stage | Skill | Reads | Writes | Cost |
|---|---|---|---|---|
| 7 | `trust-metrics-llm` ∥ `trust-metrics-code` | `scratch/analysis-cycle.md`, `docs/reports/<goal>.md` | `scratch/trust-metrics-{llm,code}.md` | LLM Judge (7), Re-run (8) |
| 9 | `qa-reviewer` | both trust files | `scratch/qa-review.md` | read-only |
| 10 | `head-of-data` | all 3 above | `scratch/head-of-data-decision.md` | user decision |

**Semantic Trust vs Computation Trust — Responsibility separation**:

- `trust-metrics-llm`: LLM Judge only. No code execution, no model training.
- `trust-metrics-code`: re-execution only. No LLM Judge.
- `qa-reviewer`: read-only synthesis of both. No new computation.

---

## 4. Meta-orchestrator (`/analyze-trust`)

Diagnostic-and-guide mode. Each invocation:

1. Inspects `scratch/` + `docs/` for current state.
2. Determines the next stage from the table below.
3. Tells the user which skill to invoke.

| State | Next action |
|---|---|
| No `docs/plans/<goal>.md` | `/define-analysis <goal>` |
| Plan exists, no `scratch/kaggle-discover.md` | `/kaggle-discover` |
| Discover exists, no `scratch/{colab,local}-setup.md` | `/{colab,local}-setup` |
| Setup exists, no `scratch/hypothesis-eda.md` | `/hypothesis-eda` |
| EDA exists, no `scratch/analysis-cycle.md` | `/analysis-cycle` |
| Cycle exists (best_score), no `scratch/trust-metrics-*.md` | `/trust-metrics-llm` + `/trust-metrics-code` (parallel) |
| Both trust metrics, no `scratch/qa-review.md` | `/qa-reviewer` |
| QA review, no `scratch/head-of-data-decision.md` | `/head-of-data` |
| Decision=PUBLISH, no `docs/reports/<goal>.md` | `/verify-report` |
| Report exists | Pipeline complete |

---

## 5. Iron Laws (7 — unified)

**From harness-data-analysis** (5):

1. **No code execution without plan approval** — `docs/plans/` file required.
2. **No execution without env selection** — `scratch/env.md` required.
3. **No "done" claim without evidence** — stdout required.
4. **Conclusions from data only** — no speculative numbers.
5. **No iteration without loop_state update** — record delta + convergence per iteration.

**From data-team-trust** (2 — added by this suite):

6. **QA Reviewer and trust-metrics-llm are read-only** — no `execute_code`, no `Write(scripts/*.py)`, no `Bash(python ...)`, no model training. LLM Judge only via `trust-metrics-llm`.
7. **PUBLISH gate — verify-report requires all 4 files + decision=PUBLISH**:
   - `scratch/trust-metrics-llm.md`
   - `scratch/trust-metrics-code.md`
   - `scratch/qa-review.md`
   - `scratch/head-of-data-decision.md` (decision=PUBLISH)

   Trust evaluation + QA verdict + user PUBLISH decision all required before report publication.

---

## 6. Cross-references

All skills in this plugin are same-plugin. References in SKILL.md bodies use unqualified skill names:

| Old syntax (legacy) | New syntax (this suite) |
|---|---|
| `/harness-data-analysis:define-analysis` | `/define-analysis` |
| `/data-team-trust:head-of-data` | `/head-of-data` |
| `/analyze-orchestrator:analyze-trust` | `/analyze-trust` |

---

## 7. Installing in a target repo

```bash
/Users/sanghee/dev/analyze-trust-suite/install-harness.sh /path/to/target-repo
```

Installs 24 skills, creates `scratch/`, `docs/plans/`, `docs/reports/`, `scripts/`, `data/raw/`, and writes `.gitignore` entries.

---

## 8. scratch/ files

```
scratch/
├── env.md                       # execution_env, data_path
├── define-analysis.md           # Ralph Loop interview log
├── kaggle-discover.md           # search results + selected ref
├── colab-setup.md / local-setup.md  # data load result
├── hypothesis-eda.md            # hypotheses ranked by signal
├── analysis-cycle.md            # loop_state + iteration log
├── trust-metrics-llm.md         # Semantic Trust panel
├── trust-metrics-code.md        # Computation Trust panel
├── qa-review.md                 # consolidated verdict
└── head-of-data-decision.md     # PUBLISH | REVISE-LLM | REVISE-Code | ABORT
```

---

## 9. Install (this plugin)

```bash
git clone git@github.com:sh-ai-x/analyze-trust-suite.git ~/.claude/skills/analyze-trust-suite
```

No build step. Claude Code auto-discovers via `~/.claude/skills/` directory scanning.

---

## 10. Migration from 3-plugin setup

Old plugins at `~/.claude/skills/{analyze-orchestrator,harness-data-analysis,data-team-trust}/` are obsolete. Remove after this plugin is verified:

```bash
rm -rf ~/.claude/skills/analyze-orchestrator
rm -rf ~/.claude/skills/harness-data-analysis
rm -rf ~/.claude/skills/data-team-trust
```

Skill name references in your existing docs (CLAUDE.md, PRD.md, README.md) must drop the `plugin:` prefix. See §6 above.