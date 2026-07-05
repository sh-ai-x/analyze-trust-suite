---
name: security-scan
description: OWASP Top 10 2025 security scan. Fans out 10 specialist subagents in parallel (one per OWASP A01–A10), each backed by an evidence-required contract; a verification pass refutes false positives before rendering per-finding inline comments plus a PR-style summary with verdict. Bare invocation = whole repo; `--diff` = PR-style changed-files. Use when the user types /security-scan, or asks to "scan for vulnerabilities", "OWASP scan", "security audit", "check for vulns before release".
when_to_use: |
  - User types /security-scan [paths] [--diff] [--diff --staged] [--fast]
  - User asks to "scan for security issues", "run an OWASP scan", "audit before release", "find vulnerabilities", "security review"
  - User wants thorough OWASP Top 10 2025 coverage (more thorough than /review-code's single security dimension)
allowed-tools: Read Grep Glob Bash Agent
disable-model-invocation: false
model: opus
---

## Provider

Defaults to **MiniMax-M3[1m]** via `~/.claude/settings.json`. Same opt-in paths as `/review-code`:

- Session: `source /Users/sanghee/dev/use_minimax/unuseminmax.sh`
- Pre-commit hook: `REVIEW_PROVIDER=anthropic git commit ...`
- GitHub Action: Actions → PR Review → Run workflow → `review_provider: anthropic`

The skill itself does not change behavior between providers — only the model behind the `Agent` tool swaps.

## Flags

| Flag | Scope |
|---|---|
| (none) | whole repo |
| `--diff` | diff vs default branch (`main`) |
| `--diff --staged` | staged + unstaged working-tree changes only |
| `--fast` | skip the verifier subagent (faster, noisier) — combinable with the above |

Examples:
- `/security-scan`                       # whole repo
- `/security-scan src/api/`              # one path
- `/security-scan --diff`                # PR-style diff
- `/security-scan --diff --fast`         # diff, skip verifier

---

## Step 1 — Resolve scope

Same as `/review-code`:
1. **Paths given** → expand globs/dirs with Glob.
2. **No paths** → whole project directory.
3. **No paths + `--diff`** → `git diff --name-only <default-branch>...HEAD`.
4. **`--diff --staged`** → working-tree changes only.
5. **Not a git repo** → whole project directory.

Filter to source files (skip binaries, lockfiles, `node_modules/`, build output, vendored deps). Empty list → tell the user there's nothing to scan and stop. Very large (>~40 files) → scan the most relevant subset or ask the user to narrow.

**On a diff run**, capture the changed hunks (`git diff -U0`) — experts must only flag issues **introduced or triggered by the changed lines**, not pre-existing code.

---

## Step 2 — Fan out to the experts (THE PARALLEL STEP)

> **Issue ALL 10 `Agent` calls inside ONE assistant message** so they run concurrently.
> Separate messages run sequentially and defeat the purpose.

Each call: `subagent_type: "general-purpose"`, `model: "sonnet"`, `run_in_background: false`,
`description: "scan: <category-id>"`. The `prompt` = the **shared contract** below + that
category's **charter** + the resolved file list (+ the changed-hunk list on a diff run).

### Shared contract (prepend to every expert prompt)

```
You are a security expert for ONE OWASP category: <CATEGORY>. Read each file and report
ONLY real, demonstrable issues in your category. Precision matters more than
completeness — a false positive is worse than a missed nit.

Files to scan (read each one):
<file list, absolute paths>
[diff run only] Only report issues in these changed hunks; ignore pre-existing code:
<hunk list>

MANDATORY per finding — a finding without these is invalid, drop it:
- failure_scenario: a CONCRETE trigger — specific inputs/state that lead to the
  vulnerability being exploited (auth bypass, data leak, RCE, etc.). If you cannot
  write one, the issue is speculative → DROP it.
- confidence: high | medium | low — your certainty the issue is real AND reachable.

Before emitting a finding, RE-READ the relevant code and mentally execute your
failure_scenario. If the code actually handles the case (guard elsewhere in the file,
a caller invariant you can see, a framework/type guarantee), DROP the finding.

DO NOT report (these are the usual false positives):
- Style, naming, or formatting preferences with no functional impact.
- Hypothetical issues with no reachable trigger ("this could theoretically…").
- "Missing" validation/null-checks when a visible guard, type, or caller already covers
  it — only report if you can show a reachable path that violates the invariant.
- Defensive-programming / "might be nice" suggestions that aren't a real defect.
- Anything outside your OWASP category, or (on a diff run) outside the changed hunks.
- A weaker restatement of a more fundamental issue you're also reporting.

Severity: critical (exploitable → data loss / breach / RCE / auth bypass) ·
major (real defect or concrete risk) · minor (hardening improvement) · nit (trivial).
Do not inflate severity; map to real impact.

Return ONLY a fenced ```json array. No prose. Each finding:
{
  "file": "<absolute path>",
  "line": <1-indexed anchor int>,
  "owasp": "<CATEGORY-ID>",
  "severity": "critical|major|minor|nit",
  "confidence": "high|medium|low",
  "title": "<short imperative title>",
  "tldr": "<one line: what's wrong and why it matters>",
  "failure_scenario": "<concrete inputs/state → exploit / data leak / etc.>",
  "good": "<what is done well near this code, or null>",
  "fix": "```<lang>\n<corrected code snippet>\n```"
}
Return [] if you find nothing real. Prefer 2 solid findings over 8 speculative ones.
```

### OWASP Top 10 2025 dimension charters (append the matching one)

#### A01:2025 — Broken Access Control
- **IDOR**: handler reads a resource by user-supplied id without an ownership/role check
  (e.g., `db.query("SELECT * FROM orders WHERE id=?", req.params.id)` with no check that
  `order.user_id == current_user.id`).
- **Path traversal**: filesystem paths concatenated from user input without
  canonicalization / `realpath` allowlist (e.g., `open(os.path.join(base, name))`).
- **Force browsing**: admin/debug endpoints left in prod (e.g., `/admin`, `/debug`,
  `/internal/*`).
- **CORS misconfiguration**: `Access-Control-Allow-Origin: *` on authed routes, or
  reflecting `Origin` header without an allowlist.
- **Missing function-level access control**: privileged actions available to all
  authenticated users (e.g., role-check absent on `delete_user`).
- **Privilege escalation**: role/permission change without re-authentication.
- DO NOT report: authorization checks one hop away (e.g., middleware applied globally
  that's visible from imports).

#### A02:2025 — Security Misconfiguration
- **Default credentials**: `admin/admin`, well-known passwords, empty secrets in code.
- **Debug in prod**: `DEBUG=True`, `FLASK_DEBUG=1`, `NODE_ENV=development`,
  `app.debug = True` checked into source.
- **Stack traces exposed to users**: returning `str(e)` or `traceback.format_exc()`
  to an HTTP response.
- **Missing security headers**: CSP, X-Frame-Options, HSTS, X-Content-Type-Options,
  Referrer-Policy absent on a public-facing HTML response.
- **Cloud metadata access**: requests to `169.254.169.254` or
  `http://metadata.google.internal` from app code (SSRF via metadata).
- **Permissive CORS**: `*` with credentials, or origin echoing without validation.
- **Verbose error/info pages**: `app.run()` defaults, `flask --debug`, Django
  `DEBUG=True` in production settings.
- **Default admin panels reachable**: `/admin`, `/phpmyadmin`, `/actuator/*` without
  auth.

#### A03:2025 — Software Supply Chain Failures
- **Vulnerable dependencies**: outdated Django/Flask/requests/lodash/spring versions
  with known CVEs (flag if pinned at a vulnerable version).
- **Unpinned versions**: `requests>=2.0` instead of `==2.31.0` in CI/CD-critical
  paths.
- **Untrusted registries**: `pip install` from `http://` URLs, npm `install` of
  tarballs from arbitrary domains.
- **Build pipeline injection**: PR-triggered CI runs that fetch and execute attacker-
  controlled code without isolation.
- **Postinstall scripts**: `npm` packages with `scripts.postinstall` that run
  arbitrary commands on install.
- **Typosquatting risks**: package names that are look-alikes of popular ones
  (`reqests`, `crossenv`).
- **Auto-update without integrity check**: code that downloads + executes binaries
  without signature or hash verification.

#### A04:2025 — Cryptographic Failures
- **Weak hash for security**: MD5, SHA1, CRC32 used for passwords, signatures, or
  any security purpose.
- **Non-constant-time compare**: `==` between two secret strings (use
  `hmac.compare_digest` / `crypto.timingSafeEqual`).
- **Hardcoded keys/secrets**: `AES_KEY = b"..."`, `JWT_SECRET = "dev"`,
  `HMAC_KEY = "changeme"` in source.
- **Insecure RNG for secrets**: `random.random()`, `Math.random()`, `java.util.Random`
  used for tokens, session IDs, password resets.
- **ECB mode**: AES/3DES in ECB (`AES/ECB/...`, `Cipher.getInstance("AES")`).
- **Small key sizes**: RSA < 2048, AES < 128, DSA / DH with weak groups.
- **TLS verification disabled**: `requests.get(url, verify=False)`,
  `ssl._create_default_https_context = ssl._create_unverified_context`.
- **Roll-your-own crypto**: hand-rolled cipher, hand-rolled MAC, custom PRNG.
- DO NOT report: MD5/SHA1 used purely as cache keys, ETags, or dedup hashes — only
  flag when used for security.

#### A05:2025 — Injection
- **SQL injection**: string concatenation or f-string in queries
  (`f"SELECT * FROM users WHERE id={uid}"`,
  `"SELECT ... WHERE name='" + name + "'"`).
- **Command injection**: `os.system(f"...")`,
  `subprocess.call(f"...{user_input}...", shell=True)`, `child_process.exec(user_input)`.
- **Template injection**: `render_template_string(f"Hello {user_input}")`,
  `Jinja2.Environment(...).from_string(user_input).render()`.
- **XSS**: unescaped user input in HTML output — `{{ user_input | safe }}`,
  `.innerHTML = userInput`, `document.write(userInput)`,
  `dangerouslySetInnerHTML={{__html: userInput}}`.
- **NoSQL injection**: `db.collection.find({"$where": f"this.${field} == '{val}'"})`,
  `{$gt: ""}`-style bypass.
- **Header injection**: `email.message.Message` with newlines in headers,
  `Location: ${user_input}` without validation.
- **XXE**: `xml.etree.ElementTree.parse` / `lxml` without disabling external entities
  on untrusted XML.
- **Format string**: `% user_input % args` outside SQL context, `printf(user_input)`.

#### A06:2025 — Insecure Design
- **No rate limiting**: login / password-reset / OTP endpoints without throttling.
- **Client-side trust only**: business rule enforced only in JS/mobile with no
  server check (negative quantities, discount codes, role checks).
- **Predictable IDs as secrets**: sequential integers used where unguessable IDs
  are required (password reset tokens, share links).
- **Race conditions (TOCTOU)**: read-then-write without locking
  (`balance = read(); if (balance > amount) write(balance - amount)`).
- **Missing CSRF**: state-changing endpoints (POST/PUT/DELETE) without CSRF token
  on a session-cookie authed route.
- **Missing business rules**: e.g., coupon stacking not blocked, transfer amount
  limit absent, withdrawal cap missing.
- DO NOT report: design issues that have a visible guard elsewhere in the file or
  framework defaults that cover the case.

#### A07:2025 — Authentication Failures
- **Weak password policy**: length < 8, no complexity check, accepts `"password"`.
- **Credential stuffing**: no rate limit / no CAPTCHA on `/login`.
- **Session fixation**: session ID not regenerated on login (`session.sid = new_id`
  missing).
- **Plaintext password storage**: passwords in DB without hashing, or with reversible
  encryption.
- **Password in URL**: `GET /reset?password=...` (should be POST + one-time token).
- **JWT `alg: none`** or weak secret (`"secret"`, empty string).
- **Insecure password recovery**: security questions, no expiry on reset token,
  token returned in response body rather than email.
- **Missing MFA** on privileged operations (admin actions, financial ops, key
  rotations).
- **"Remember me" without expiry / revocable check**.

#### A08:2025 — Software or Data Integrity Failures
- **Unsafe deserialization**: `pickle.loads`, `cPickle.load`, `marshal.load`,
  `yaml.load` (not `safe_load`), `shelve.open` on untrusted input.
- **Auto-update without integrity check**: code that downloads + executes a binary
  without signature or hash verification.
- **Insecure plugin loading**: `importlib.import_module(user_path)`, dynamic class
  loading from user-supplied source.
- **Missing checksum on downloaded deps**: no `pip install --require-hashes`,
  no `package-lock.json` integrity, no `--checksum` on `wget`/`curl`.
- **Cookies missing flags**: `Set-Cookie: session=...` without `Secure`,
  `HttpOnly`, `SameSite`.
- **Insecure JWT validation**: `jwt.decode(token, options={"verify_signature":
  False})`, trusting `alg` from header, weak shared secret.
- **Webhook payload trust without signature verification**: handler acts on
  unverified POST bodies claiming to be from a vendor.

#### A09:2025 — Security Logging and Alerting Failures
- **Auth events not logged**: login success/failure, logout, password reset,
  MFA changes — none of them emit log lines.
- **Sensitive data in logs**: passwords, PII, payment info, full session tokens,
  OAuth secrets logged at INFO+.
- **No alerting on suspicious activity**: repeated failed logins, privilege
  escalation, anomalous transfers — no metric/counter/alert wired.
- **Logs mutable / public-readable**: log files in webroot, logs in object
  storage with public ACL.
- **Insufficient log detail for forensics**: exception classes logged but not
  stack traces; user id missing on auth events.
- **Missing audit trail** on sensitive operations (data exports, financial
  transfers, role changes, key rotations).

#### A10:2025 — Mishandling of Exceptional Conditions
- **Bare `except: pass`** / `catch (e) {}` — error swallowed silently, hiding a
  failure path.
- **Fail-open on auth**: error in auth check → allow access (vs fail-closed deny).
- **Fail-open on validation**: error in input validator → proceed with the input.
- **Missing timeout on external calls**: outbound HTTP / DB / Redis call with no
  timeout → resource exhaustion / hang.
- **Unhandled promise rejections** in Node.js — async function throws, no `.catch`,
  no top-level `unhandledRejection` handler.
- **Missing cleanup**: file handles, locks, transactions not released in `finally`
  / `defer` / `using`.
- **Panic in critical path**: `panic("...")` / uncaught `Exception` in middleware
  or service entrypoint that should degrade gracefully.
- DO NOT report: broad `except Exception` that re-raises, logs, or returns a
  well-defined error response.

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
notes. A cross-category pair describing the same root cause collapses to one.

### 3c. Verifier pass (default; skipped with `--fast`)
Spawn **one** verifier subagent (`general-purpose`, `model: "sonnet"`,
`description: "scan: verify"`). Give it the surviving candidates (as JSON) **and** the
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
## Security scan summary

**Verdict:** <Blocked | Changes Requested | Approve>
**Coverage:** A01..A10 (10 categories)
**Severity:** 🔴 <n>  🟠 <n>  🟡 <n>  ⚪ <n>
**Precision:** <M> findings shown · <K> filtered as false positives/low-signal

**By category:**
- A01 Broken Access Control: <n>
- A02 Security Misconfiguration: <n>
- A03 Software Supply Chain Failures: <n>
- A04 Cryptographic Failures: <n>
- A05 Injection: <n>
- A06 Insecure Design: <n>
- A07 Authentication Failures: <n>
- A08 Software or Data Integrity Failures: <n>
- A09 Security Logging and Alerting Failures: <n>
- A10 Mishandling of Exceptional Conditions: <n>

**Walkthrough:** <2–3 lines: what was scanned and its overall shape>

**Strengths:**
- <notable good points>

**Blocking findings (critical + major only):**
- [🔴 critical · CONFIRMED] <title> — path:line (A0X)

**Next actions:**
- [ ] <short, concrete checklist>
```

Verdict rule: **Blocked** if any 🔴 critical; else **Changes Requested** if any 🟠 major;
else **Approve**.

### Layer 1 — inline comments (one per finding, 4 fields)

```
[🔴 critical · CONFIRMED · A05] <title>        @ path/to/file.py:42
TL;DR: <one line — the concrete trigger from failure_scenario>
✓ Good: <redeeming aspect, or "—">
Fix:
```<lang>
<code>
```
```

The verdict badge (`CONFIRMED`/`PLAUSIBLE`) and OWASP category sit in the title line
next to severity. Emit findings in sorted order. Print all output as Markdown.

---

## Relationship to `/review-code`

| | `/review-code` | `/security-scan` |
|---|---|---|
| Dimensions | 3 (correctness + security + architecture) | 10 (A01–A10) |
| Speed | Faster (~1–2 min) | Slower (~3–5 min) |
| Use case | PR-time review | Pre-release audit, quarterly review |
| Output | Verdict + inline findings | Same, plus per-category breakdown |

Both share the same provider plumbing (MiniMax default, Claude Code opt-in).

**When to use which:**
- Every PR → `/review-code` (cheap, catches most stuff at PR-time).
- Release candidate / quarterly / before major refactor → `/security-scan` (thorough).
- After a `/security-scan` flags a category-cluster, run `/review-code --diff` on the fix
  to verify the patch.

---

## Regression testing (after editing any prompt here)

Prompts are brittle — a small wording change can silently reintroduce false positives or
drop real bugs. A regression fixture set lives in `fixtures/`:

- `fixtures/real-bugs/` — genuine defects that MUST be caught (recall).
- `fixtures/traps/` — guarded code that looks buggy and MUST NOT be flagged (precision).
- `fixtures/clean/` — clean code that MUST return Approve.
- `fixtures/expected.md` — per-fixture expected outcomes (the source of truth).

After any change to this file, run `/security-scan fixtures/real-bugs`,
`/security-scan fixtures/traps`, and `/security-scan fixtures/clean`, then compare
against `expected.md`. A repeated (not one-off) miss or false flag is a real
regression. The driver script `fixtures/check.sh` lists the groups + pass criteria.

## Sources

- OWASP Top 10 2025: <https://owasp.org/Top10/2025/>
