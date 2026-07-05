# analyze-trust-suite

End-to-end data analysis + trust evaluation + meta-orchestrator. **Single plugin, 24 skills, one repo.**

## Why this exists

The data-analysis pipeline used to live across 3 separate git repos (`analyze-orchestrator`, `harness-data-analysis`, `data-team-trust`). Coordinating releases across three repos with cross-repo `plugin.json` `dependencies` was painful. **This plugin is the consolidation** — one repo, one `plugin.json`, one CLAUDE.md, one version.

## Install

```bash
git clone git@github.com:sh-ai-x/analyze-trust-suite.git ~/.claude/skills/analyze-trust-suite
```

No build step. Claude Code auto-discovers via `~/.claude/skills/` directory scanning.

## Usage

**Single command** (recommended for new analysis):
```
/analyze <goal>
```

**Guided 10-step flow** (for inspection, debugging, or partial re-runs):
```
/analyze-trust <goal>
```

**Individual stages** (when you know exactly which step you need):
```
/define-analysis <goal>
/kaggle-discover
/colab-setup | /local-setup
/hypothesis-eda
/analysis-cycle
/verify-report
/trust-metrics-llm | /trust-metrics-code
/qa-reviewer
/head-of-data
```

## What's in this plugin

### 6-stage Analysis Pipeline

| Skill | Purpose |
|---|---|
| `define-analysis` | Goal interview + environment selection |
| `kaggle-discover` | Search and pick a Kaggle dataset |
| `colab-setup` | Mount Google Drive, download data to Colab |
| `local-setup` | Download data to local `data/raw/` |
| `hypothesis-eda` | EDA passes + hypothesis generation |
| `analysis-cycle` | 2-level modeling loop (hypothesis × model) |
| `verify-report` | Re-execute + emit ipynb + HTML + md report |

### Ralph Loop (goal clarification)

| Skill | Purpose |
|---|---|
| `wonder` | Diverge — surface hidden meanings of an idea |
| `reflect` | Compare each candidate to your intent |
| `restate` | Converge — turn the meaning into an executable goal |

### All-in-one convenience

| Skill | Purpose |
|---|---|
| `analyze` | Phase 1 interview + Phase 2 auto-execute (A→E) |
| `analyze-trust` | Meta-orchestrator: diagnose state, guide to next step |

### Verification and quality

| Skill | Purpose |
|---|---|
| `verification-before-completion` | Force evidence before claiming done |
| `review` (5 subs) | Post-hoc review (analysis, methodology, statistical, robustness, report) |

### Trust evaluation (4 stages)

| Skill | Purpose |
|---|---|
| `trust-metrics-llm` | Semantic Trust panel (LLM Judge) |
| `trust-metrics-code` | Computation Trust panel (re-execute + CV) |
| `qa-reviewer` | Consolidate LLM + Code verdicts (read-only) |
| `head-of-data` | User decision gate: PUBLISH / REVISE / ABORT |

### Dashboard integration

| Skill | Purpose |
|---|---|
| `migrate-to-dashboard` | Generate `docs/dashboard-state.json` from scratch/ + docs/ |

---

## Iron Laws (7)

1. No code execution without plan approval
2. No execution without env selection
3. No "done" claim without evidence
4. Conclusions from data only
5. No iteration without loop_state update
6. QA Reviewer + trust-metrics-llm are read-only
7. verify-report requires all 4 trust files + decision=PUBLISH

See [CLAUDE.md](./CLAUDE.md) for details.

---

## File layout

```
~/dev/analyze-trust-suite/
├── .claude-plugin/plugin.json   # manifest
├── skills/                      # 24 SKILL.md (this is the plugin entry point)
├── scripts/                     # eda.py, run.py, review/, _fixtures/
├── .claude/settings.json        # permissions allowlist
├── docs/plans/, docs/reports/   # sample artifacts
├── install-harness.sh           # copies this plugin into target repos
├── CLAUDE.md                    # full guidance (Claude reads this)
├── README.md                    # this file
└── LICENSE                      # MIT
```

## Installing in a target repo

```bash
/Users/sanghee/dev/analyze-trust-suite/install-harness.sh /path/to/target-repo
```

This copies all 24 skills into `<target>/.claude/skills/` and creates `scratch/`, `docs/plans/`, `docs/reports/`, `scripts/`, `data/raw/` directories. The target repo can then run any of the 24 skills via Claude Code.

## PR review (MiniMax-M3[1m])

Every PR runs `/review-code` automatically — a parallel correctness + security + architecture pass with a verifier, gated on severity and auto-approved on the lowest tier.

| Layer | Where | Provider |
|---|---|---|
| Pre-commit (local) | `.githooks/pre-commit` | MiniMax (default), Anthropic opt-in |
| PR review (CI) | `.github/workflows/review.yml` | MiniMax (default), Anthropic opt-in |
| Legacy Anthropic-native review | `.github/workflows/claude-code-review.yml` | Anthropic — opt-in via `claude-code-review` label |

### CI setup (one-time per repo)

1. Install the [Claude GitHub App](https://github.com/apps/claude) on the repo (Contents/Issues/PRs read+write).
2. Set the secrets:
   ```bash
   gh secret set MINMAX_API_KEY        # default reviewer (MiniMax-M3[1m])
   gh secret set ANTHROPIC_API_KEY     # opt-in reviewer
   ```
3. Open a PR — the `PR Review (MiniMax)` workflow fans out 3 reviewer agents, posts a
   verdict (`Approve` / `Changes Requested` / `Blocked`), and auto-approves on `Approve`.

### Manual override

Re-run on demand with a different provider:

```
Actions → PR Review (MiniMax) → Run workflow
  review_provider: anthropic
  pr_number: 42
```

### Local pre-commit (optional)

```bash
git config core.hooksPath .githooks
cp .env.example .env   # then fill in MINMAX_API_KEY
```

Bypass per-commit: `git commit --no-verify`. Opt out of MiniMax for one commit:
`REVIEW_PROVIDER=anthropic git commit ...`.

---

## Migration from 3-plugin setup

If you previously had `~/.claude/skills/{analyze-orchestrator,harness-data-analysis,data-team-trust}/`, remove them after this plugin is verified:

```bash
rm -rf ~/.claude/skills/analyze-orchestrator
rm -rf ~/.claude/skills/harness-data-analysis
rm -rf ~/.claude/skills/data-team-trust
```

Update skill references in your docs:
- `/harness-data-analysis:define-analysis` → `/define-analysis`
- `/data-team-trust:head-of-data` → `/head-of-data`
- `/analyze-orchestrator:analyze-trust` → `/analyze-trust`

## License

MIT — see [LICENSE](./LICENSE).