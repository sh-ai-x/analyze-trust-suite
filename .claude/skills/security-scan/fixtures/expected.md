# Security-scan regression — expected outcomes

Source of truth. After any change to `../SKILL.md`, run each fixture group through
`/security-scan <group>` and compare against the assertions below. A single miss/flag
can be non-determinism; a repeated one is a real regression.

---

## `real-bugs/` — every intended finding MUST appear (recall)

| File | OWASP | Vulnerability | Expected severity |
|---|---|---|---|
| `a01_idor.py` | A01 | Order endpoint reads by id without ownership check | 🟠 major |
| `a02_debug_prod.py` | A02 | `DEBUG=True` + stack-trace returned in HTTP response | 🟠 major |
| `a04_md5_password.py` | A04 | MD5 used to hash passwords; non-constant-time compare | 🔴 critical |
| `a05_sql_injection.py` | A05 | f-string in SQL query | 🔴 critical |
| `a05_cmd_injection.py` | A05 | `subprocess.call(..., shell=True)` with f-string | 🔴 critical |
| `a06_no_rate_limit.py` | A06 | `/login` has no throttling | 🟡 minor |
| `a07_jwt_alg_none.py` | A07 | JWT decoded with `algorithms=["none"]` | 🔴 critical |
| `a08_pickle_loads.py` | A08 | `pickle.loads` on request body | 🔴 critical |
| `a09_pii_in_logs.py` | A09 | Password + full PAN logged at INFO | 🟠 major |
| `a10_bare_except_pass.py` | A10 | Bare `except: pass` in transfer handler — fail-open | 🔴 critical |
| `a10_fail_open_validation.py` | A10 | Validation error → proceeds with input | 🟠 major |

Verdict for the whole `real-bugs/` group: **Blocked** (multiple 🔴 critical present).

---

## `traps/` — ZERO findings (precision)

Each file LOOKS vulnerable but is actually safe. The scanner must NOT flag these.

| File | What looks bad | Why it's actually safe |
|---|---|---|
| `a04_md5_etag.py` | MD5 of file content used as cache key | Cache key, not security context |
| `a05_parameterized_query.py` | Variable interpolation into SQL string at a glance | Actually uses parameterized `?` placeholder |
| `a05_template_literal_static.py` | JS template literal inside HTML | Content is a static, hardcoded value — no user input |
| `a08_yaml_safe_load.py` | `yaml.load` looks risky | Uses `yaml.safe_load` (safe loader) |
| `a08_subprocess_list.py` | `subprocess` call looks risky | Uses list-form args, no `shell=True`, no interpolation |
| `a09_log_truncated_pan.py` | Logs include a card number | Tokenized: logs only last 4 (`**** 1234`) |
| `a10_except_reraise.py` | Broad `except Exception` | Re-raises after logging — not swallowed |
| `a01_owner_check_one_hop.py` | Endpoint reads order by id | One frame up: `require_owner(order)` decorator enforces ownership |

Verdict for the whole `traps/` group: **Approve** (zero findings).

---

## `clean/` — ZERO findings (baseline)

| File | Description |
|---|---|
| `endpoint.py` | Well-formed Flask endpoint: parameterized SQL, ownership check, structured error response, security headers, hashed password, structured logging without PII. |

Verdict for `clean/`: **Approve** (zero findings).

---

## Tolerance

- **Recall (real-bugs/):** ALL listed findings must appear at the expected severity or
  higher. A finding demoted to one severity tier below expected counts as a soft fail
  (still a real signal) — investigate.
- **Precision (traps/, clean/):** ZERO findings. Any confirmed or plausible finding on
  these files is a regression — the prompt let an illusion through.
- A finding on traps/ that is REFUTED by the verifier (drops to REJECTED) is acceptable
  IF the rendered output does not include it. If it appears in the summary or as an
  inline comment, that's a precision regression.