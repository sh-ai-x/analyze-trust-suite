# review-code — regression fixture set

A test suite for the reviewer itself. After changing any prompt in `../SKILL.md`, run
`/review-code` against these fixtures and confirm the outcomes below still hold. The
fixtures contain **no hints** — expectations live only in this file, so the reviewer
can't cheat.

Two properties are under test:
- **Recall** — every `real-bugs/` defect is still caught (filter didn't get too strict).
- **Precision** — every `traps/` file stays empty and `clean/` returns Approve (no false
  positives crept back in).

## How to run

```
/review-code ~/.claude/skills/review-code/fixtures/real-bugs
/review-code ~/.claude/skills/review-code/fixtures/traps
/review-code ~/.claude/skills/review-code/fixtures/clean
```

Or one file at a time. Then compare against the table below. `check.sh` prints this
checklist next to the fixture list for convenience (it does not run the review — the
review is LLM-driven).

Because LLM prompts are non-deterministic, treat a **single** unexpected miss/flag as a
signal to re-run once; a **repeated** miss/flag is a real regression.

## Expected outcomes

### real-bugs/ — MUST be reported (recall)

| Fixture | Dim | Sev | Must include a finding for |
|---|---|---|---|
| `zerodiv.py` | correctness | major | `average([])` → ZeroDivisionError (no empty-guard) |
| `null_deref.py` | correctness | major/critical | `row[0]` when `fetchone()` returns `None` (no account) |
| `sql_injection.py` | security | critical | `'%s' % name` string-formatted SQL → injectable |
| `auth_backdoor.py` | security | critical | hardcoded `password == "letmein"` backdoor |
| `unsafe_deserialization.py` | security | critical | `pickle.loads(blob)` on client-supplied bytes → RCE |

Pass = each fixture yields **≥1 finding matching the intended issue**, verdict is
**Changes Requested or Blocked**. (Incidental extra findings are acceptable; a *missing*
intended finding is a fail.)

Also note: `null_deref.py` uses a parameterized query and `auth_backdoor.py` uses `?`
placeholders — the reviewer must **not** additionally flag those as injection.

### traps/ — MUST NOT be reported (precision)

| Fixture | Looks like | Why it's safe |
|---|---|---|
| `guarded_none.py` | None deref on `row[0]` | explicit `if row is None: return None` guard above |
| `allowlisted_table.py` | SQL injection via `% table` | `table` validated against a fixed allowlist first |
| `guarded_divide.py` | division by zero | explicit `if denominator == 0: raise` guard |
| `parameterized_query.py` | SQL injection in `LIKE` | keyword is passed as a bound `?` parameter |
| `safe_yaml.py` | unsafe YAML deserialization | uses `yaml.safe_load` (the safe API), not `yaml.load` |

Pass = **zero findings** on each (verdict **Approve**). Any finding here is a false
positive = fail. (A `nit` about, e.g., naming is tolerable but should be rare; a
`major`/`critical` here is always a fail.)

### clean/ — baseline

| Fixture | Expected |
|---|---|
| `temperature.py` | zero findings, verdict **Approve** |

## Interpreting a run

- Real bug missed → filter too aggressive; loosen the "DO NOT report" list or the
  deterministic filter in `SKILL.md` Step 3a.
- Trap flagged → filter too weak; strengthen the evidence requirement / verifier prompt
  in Step 2 contract or Step 3c.
- Both clean → the change is safe to keep.
