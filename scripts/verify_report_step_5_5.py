"""verify_report_step_5_5.py — verify-report Step 5.5 helper.

Usage (from analysis target repo CWD):
    python3 /path/to/analyze-trust-suite/scripts/verify_report_step_5_5.py <goal_slug>

환경변수:
    DATA_ANALYSIS_RESULTS_DIR  vault 레포 경로 (기본: /Users/sanghee/dev/data-analysis-results)

현재 goal 의 산출물 (reports / plans / scratch 메타) 을 vault 로 복사하고
INDEX.md 를 재생성한다. vault 가 없으면 skip.
"""
import datetime
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_VAULT = "/Users/sanghee/dev/data-analysis-results"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: verify_report_step_5_5.py <goal_slug>")
        return 1
    goal = sys.argv[1]
    vault = Path(os.environ.get("DATA_ANALYSIS_RESULTS_DIR", DEFAULT_VAULT))
    if not (vault / "scripts" / "update_index.py").exists():
        print(f"[skip] vault 레포 미설정: {vault}")
        return 0
    today = datetime.date.today().strftime("%Y%m%d")
    # 1. reports
    src_reports = Path("docs/reports")
    if src_reports.exists():
        for ext in ("md", "ipynb", "html"):
            for f in src_reports.glob(f"*-{goal}.{ext}"):
                shutil.copy(f, vault / "docs" / "reports" / f.name)
                print(f"  copy: docs/reports/{f.name}")
    # 2. plans
    src_plans = Path("docs/plans")
    if src_plans.exists():
        src_plan = src_plans / f"{goal}.md"
        if src_plan.exists():
            shutil.copy(src_plan, vault / "docs" / "plans" / f"{today}-{goal}.md")
            print(f"  copy: docs/plans/{goal}.md → docs/plans/{today}-{goal}.md")
    # 3. scratch 메타파일
    for name in (
        "analysis-cycle",
        "trust-metrics-llm",
        "trust-metrics-code",
        "qa-review",
        "head-of-data-decision",
    ):
        for f in Path("scratch").glob(f"{name}*-{goal}.md"):
            shutil.copy(f, vault / "scratch" / f.name)
            print(f"  copy: scratch/{f.name}")
    # 4. INDEX 재생성
    subprocess.run(["python3", str(vault / "scripts" / "update_index.py")], cwd=vault, check=False)
    print(f"[vault] {goal} → {vault}")
    return 0


if __name__ == "__main__":
    sys.exit(main())