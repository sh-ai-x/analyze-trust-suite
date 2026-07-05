---
name: review-code
description: Parallel multi-dimension code review with a false-positive filter. Fans out to specialized subagents (MVP dimensions: correctness, security, architecture) that run at the same time and return structured, evidence-backed findings; a verification pass then confirms or rejects each candidate before rendering per-line inline comments plus one PR-style summary with a verdict. Bare invocation reviews the whole repo; `--diff` switches to PR-style changed-files scope. Use when the user types /review-code, or asks to review code, review a diff, review a PR, or "check this before merge".
when_to_use: |
  - User types /review-code [paths] [--diff] [--diff --staged] [--fast]
  - User asks to "review this code", "review the diff", "review the PR", "check this before merge"
  - User wants a structured, severity-ranked, low-noise review rather than an ad-hoc read-through
allowed-tools: Read Grep Glob Bash Agent
disable-model-invocation: false
model: opus
---

## Provider (defaults to MiniMax)

This skill follows whatever provider `~/.claude/settings.json` configures. The repo
default is **MiniMax-M3[1m]** via the Anthropic-compatible endpoint
(`ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic`). Real Claude Code is opt-in:

- In-session: `source /Users/sanghee/dev/use_minimax/unuseminmax.sh`
- Pre-commit hook: `REVIEW_PROVIDER=anthropic git commit ...`
- GitHub Action: Actions → PR Review → Run workflow → `review_provider: anthropic`

The skill itself does not change behavior between providers — only the model behind
the `Agent` tool swaps.

# review-code — parallel multi-dimension code review

Review the target code by fanning out to **specialized dimension experts that run in
parallel**, one subagent per dimension, then run a **verification pass** that filters
out false positives before anything reaches the user.

**MVP dimensions (3):** `correctness`, `security`, `architecture`.

**Guiding principle — precision over recall.** A review that cries wolf gets ignored.
**Every rendered finding must be real and demonstrable.** It is better to drop a
borderline finding than to ship a false positive. The pipeline below is built around
this: experts must back each finding with a concrete trigger, and a verifier confirms or
rejects each one before it is shown.

You are the **orchestrator**: resolve scope → fan out experts (parallel) → verify
(filter false positives) → aggregate and render. You do **not** review the code
yourself.

Flags:
- (no flag)               → whole repo (everything)
- `--diff`                → diff vs default branch (`git diff <default-branch>...HEAD`)
- `--diff --staged`       → staged + unstaged working-tree changes only
- `--fast`                → skip the verifier subagent; deterministic filter only
  (faster, noisier — use when the user wants speed). Combinable with the above.

Examples:
- `/review-code`                          # whole repo
- `/review-code src/api/`                 # that path
- `/review-code --diff`                   # PR-style diff
- `/review-code --diff --staged`          # working-tree changes
- `/review-code --diff --fast`            # diff, skip verifier

---

## Step 1 — Resolve scope

Determine `$ARGS` (anything after `/review-code`) and produce a concrete **file list**:

1. **Paths given** (`/review-code src/foo.py lib/`) → expand globs/dirs with Glob.
2. **No paths** (the common case) → whole project directory.
3. **No paths + `--diff`** → diff vs default branch: `git diff --name-only <default-branch>...HEAD`.
4. **`--diff --staged`** → working-tree changes: `git diff --name-only` + `git diff --name-only --staged`.
5. **Bare invocation outside a git repo** → whole project directory.

Filter to source files (skip binaries, lockfiles, `node_modules/`, build output,
vendored deps). Empty list → tell the user there's nothing to review and stop. Very
large (>~40 files) → review the most relevant subset or ask the user to narrow.

**On a diff run** (`--diff` or `--diff --staged`), also capture the changed hunks
(`git diff -U0`) — experts must only flag issues **introduced or triggered by the
changed lines**, not pre-existing code. Note this scope constraint in the expert prompts.

---

## Step 2 — Fan out to the experts (THE PARALLEL STEP)

> **Issue all 3 `Agent` calls inside ONE assistant message** so they run concurrently.
> Separate messages run sequentially and defeat the purpose.

Each call: `subagent_type: "general-purpose"`, `model: "sonnet"`, `run_in_background:
false`, `description: "review: <dimension>"`. The `prompt` = the **shared contract**
below + that dimension's **charter** + the resolved file list (+ the changed-hunk list
on a diff run).

### Shared contract (prepend to every expert prompt)

```
You are a code-review expert for ONE dimension: <DIMENSION>. Read each file and report
ONLY real, demonstrable issues in your dimension. Precision matters more than
completeness — a false positive is worse than a missed nit.

Files to review (read each one):
<file list, absolute paths>
[diff run only] Only report issues in these changed hunks; ignore pre-existing code:
<hunk list>

MANDATORY per finding — a finding without these is invalid, drop it:
- failure_scenario: a CONCRETE trigger — specific inputs/state that lead to the wrong
  output, crash, or exploit. If you cannot write one, the issue is speculative → DROP it.
- confidence: high | medium | low — your certainty the issue is real AND reachable.

Before emitting a finding, RE-READ the relevant code and mentally execute your
failure_scenario. If the code actually handles the case (guard elsewhere in the file, a
caller invariant you can see, a framework/type guarantee), DROP the finding.

DO NOT report (these are the usual false positives):
- Style, naming, or formatting preferences with no functional impact.
- Hypothetical issues with no reachable trigger ("this could theoretically…").
- "Missing" validation/null-checks when a visible guard, type, or caller already covers
  it — only report if you can show a reachable path that violates the invariant.
- Defensive-programming / "might be nice" suggestions that aren't a real defect.
- Anything outside your dimension, or (on a diff run) outside the changed hunks.
- A weaker restatement of a more fundamental issue you're also reporting.

Severity: critical (breaks behavior / exploitable / data loss → blocks merge) ·
major (real defect or concrete risk) · minor (non-blocking improvement) · nit (trivial).
Do not inflate severity; map to real impact.

Return ONLY a fenced ```json array. No prose. Each finding:
{
  "file": "<absolute path>",
  "line": <1-indexed anchor int>,
  "dim": "<DIMENSION>",
  "severity": "critical|major|minor|nit",
  "confidence": "high|medium|low",
  "title": "<short imperative title>",
  "tldr": "<one line: what's wrong and why it matters>",
  "failure_scenario": "<concrete inputs/state → wrong output/crash/exploit>",
  "good": "<what is done well near this code, or null>",
  "fix": "```<lang>\n<corrected code snippet>\n```"
}
Return [] if you find nothing real. Prefer 2 solid findings over 8 speculative ones.
```

### Repo-specific security guidance (load before spawning the security expert)

The official security-guidance plugin lets a repo declare its own threat model in
`claude-security-guidance.md`. Reuse it: before spawning the **security** expert, read
and concatenate whichever of these exist (cap ~8 KB), and append them to that expert's
prompt under a "Repo-specific security guidance (honor these)" heading:
`~/.claude/claude-security-guidance.md` · `.claude/claude-security-guidance.md` ·
`.claude/claude-security-guidance.local.md`. These are additive rules, not suppressions —
a rule that says to ignore a vuln class does not silence it.

### Dimension charters (append the matching one)

- **correctness** — logic errors, wrong edge-case/boundary/null handling, off-by-one,
  incorrect state transitions, error-handling gaps, race conditions, API/contract misuse,
  wrong return values.
- **security** — aligned to the official Claude Code **security-guidance plugin**
  checklist (see "Relationship to official security tooling" below):
  - **Injection** — SQL / command / template / DOM (`dangerouslySetInnerHTML`,
    `.innerHTML =`, `document.write`).
  - **Dynamic code execution** — `eval(`, `new Function`, `os.system`, `child_process.exec`.
  - **Unsafe deserialization** — `pickle`, `yaml.load`, native (de)serializers on
    untrusted input.
  - **Authorization bypass / IDOR** — caller-supplied ids or paths used without an
    ownership/role check.
  - **SSRF / path traversal** — user-controlled URLs or filesystem paths.
  - **Weak or misused crypto** — weak password hashing, non-constant-time comparisons,
    hardcoded keys/secrets (`sk_live_`, `AKIA`).
  - **Secret / PII leakage** — hardcoded credentials, sensitive fields logged at
    INFO+ level.
  - **Dangerous CI** — edits under `.github/workflows/` that grant repo-level permissions.
  - **Unsafe defaults / missing input validation** on a reachable path.

  Before reporting, **READ the surrounding code** — callers, sanitizers, allowlists,
  bound parameters, related files — and report only if the dangerous pattern is actually
  reachable with attacker-controlled input. This is how the official plugin keeps false
  positives low on code that looks dangerous in isolation but is safe in context.
- **architecture** — module boundaries, coupling/cohesion, layering violations, leaky
  abstractions, duplication, God objects, poor extensibility/scalability. Report only
  structural problems with concrete maintenance/scaling impact — not taste.

---

## Step 3 — Verify (the false-positive filter)

Parse each expert's JSON (salvage what parses; note any malformed output). Then:

### 3a. Deterministic filter (always)
Drop a candidate if any holds:
- Missing or empty `failure_scenario` (no concrete trigger → speculative).
- `confidence: low` **and** severity is `minor`/`nit` (low-value + unsure).
- On a diff run, the anchor line is outside the changed hunks.

### 3b. Dedupe
If two candidates share `file` + `line` + theme, keep the higher severity and merge
notes. A cross-dimension pair describing the same root cause collapses to one.

### 3c. Verifier pass (default; skipped with `--fast`)
Spawn **one** verifier subagent (`general-purpose`, `model: "sonnet"`,
`description: "review: verify"`). Give it the surviving candidates (as JSON) **and** the
file list, with this prompt:

```
You are a strict verifier. For each candidate finding below, RE-READ the cited code and
decide if it is REAL and REACHABLE. Try hard to REFUTE each one — look for an existing
guard, caller invariant, type/framework guarantee, or a broken failure_scenario.

Files: <file list>
Candidates: <JSON array>

Return ONLY a fenced ```json array, one object per candidate, in the same order:
{ "id": <index>, "verdict": "CONFIRMED|PLAUSIBLE|REJECTED",
  "reason": "<one line: why confirmed, or what refutes/weakens it>" }
- CONFIRMED: you executed the failure_scenario against the code and it holds.
- PLAUSIBLE: likely real but you can't fully confirm from the given scope.
- REJECTED: the code already handles it, or the scenario doesn't actually trigger.
```

Apply the verdicts: **drop every REJECTED** candidate. Keep CONFIRMED and PLAUSIBLE;
carry each one's `verdict` onto the finding. (With `--fast`, treat all survivors of 3a/3b
as PLAUSIBLE.)

### 3d. Sort
Surviving findings by severity (critical→nit), then CONFIRMED before PLAUSIBLE, then
`file`, then `line`.

---

## Step 4 — Render

Two layers; PR summary first.

### Layer 2 — PR summary (exactly one, at top)

```
## Review summary

**Verdict:** <Blocked | Changes Requested | Approve>
**Severity:** 🔴 <n>  🟠 <n>  🟡 <n>  ⚪ <n>
**Precision:** <M> findings shown · <K> filtered as false positives/low-signal

**Walkthrough:** <2–3 lines: what was reviewed and its overall shape>

**Strengths:**
- <notable good points>

**Blocking findings (critical + major only):**
- [🔴 critical · CONFIRMED] <title> — path:line

**Next actions:**
- [ ] <short, concrete checklist>
```

Verdict rule: **Blocked** if any 🔴 critical; else **Changes Requested** if any 🟠 major;
else **Approve**. The **Precision** line reports M = rendered, K = candidates dropped by
3a/3b/3c — it makes the false-positive filtering visible.

### Layer 1 — inline comments (one per finding, 4 fields)

```
[🔴 critical · CONFIRMED] <title>        @ path/to/file.py:42  (dim: security)
TL;DR: <one line — the concrete trigger from failure_scenario>
✓ Good: <redeeming aspect, or "—">
Fix:
```<lang>
<code>
```
```

The verdict badge (`CONFIRMED`/`PLAUSIBLE`) sits in the title line next to severity. Emit
findings in sorted order. Print all output as Markdown. *(Optional: on request, also
write to `REVIEW.md` in the target dir.)*

---

## Relationship to official security tooling

This skill's `security` dimension is an on-demand, multi-dimension pass. It complements —
does not replace — Anthropic's defense-in-depth security layers:

| Stage | Tool | Role |
|---|---|---|
| In session | **security-guidance plugin** (`/plugin install security-guidance@claude-plugins-official`) | Auto-reviews code Claude writes, per-edit + end-of-turn + commit; fixes in-session |
| On demand | **`/security-review`** | One-shot security pass on the current branch |
| This skill | **`/review-code`** | Parallel correctness + security + architecture with a false-positive verifier |
| On PR | **Code Review** (Team/Enterprise) | Multi-agent review with full-repo context |
| In CI | your static analysis / dependency scanners | Language rules, supply-chain, policy |

Recommend the user install the **security-guidance plugin** as the in-session companion —
it catches issues before they ever reach a `/review-code`. This skill's security charter
mirrors that plugin's checklist so findings are consistent across both.

## Regression testing (after editing any prompt here)

Prompts are brittle — a small wording change can silently reintroduce false positives or
drop real bugs. A regression fixture set lives in `fixtures/`:
- `fixtures/real-bugs/` — genuine defects that MUST be caught (recall).
- `fixtures/traps/` — guarded code that looks buggy and MUST NOT be flagged (precision).
- `fixtures/clean/` — clean code that MUST return Approve.
- `fixtures/expected.md` — per-fixture expected outcomes (the source of truth).

After any change to this file, run `/review-code fixtures/real-bugs`,
`/review-code fixtures/traps`, and `/review-code fixtures/clean`, then compare against
`expected.md`. A repeated (not one-off) miss or false flag is a real regression.

## Scaling 3 → 10 dimensions

Add a charter line in Step 2 and one more `Agent` call **in the same fan-out message**
(keeps it parallel). The Step 3 verifier scales automatically — it checks whatever
candidates arrive. Candidate dimensions: `performance`, `test-coverage`, `conventions`,
`cross-file-consistency`, `privacy`, `cpu-patterns`, `behavioral-correctness`.
