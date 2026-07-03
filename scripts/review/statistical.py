#!/usr/bin/env python3
"""
review-statistical — 베이스라인 대비 통계 검증 (R3)

analysis-cycle.md 의 best_score 가 DummyClassifier/Regressor 대비 통계적으로
유의미한지 paired t-test + bootstrap CI + Cohen's d 로 검증.

stdout 출력:
  [statistical] analysis_type=classification metric=AUC-ROC
  [baseline] <name>: mean=... ± ...
  [best] CV <metric>: mean=... ± ...
  [paired-t vs <baseline>] t=..., p=...
  [bootstrap] lift=..., CI=[..., ...]
  [effect] cohen_d=...
  [gate] G1: PASS|FAIL (p=0.0001)
  [gate] G2: PASS|FAIL (lift=+15.3%)
  [gate] G3: PASS|FAIL (d=2.1)
  [gate] G4: PASS|FAIL (CI_low=0.05 > 0)
  [verdict] PASS|WARN|FAIL (gates: G1+G2+G3+G4)
"""
from __future__ import annotations
import argparse
import json
import platform
import re
import sys
import warnings
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# 한글 폰트
plt.rcParams["font.family"] = "AppleGothic" if platform.system() == "Darwin" else "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

from sklearn.model_selection import StratifiedKFold, KFold, cross_val_score  # noqa: E402
from sklearn.dummy import DummyClassifier, DummyRegressor  # noqa: E402
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor  # noqa: E402
from sklearn.linear_model import LogisticRegression, Ridge  # noqa: E402
from sklearn.preprocessing import LabelEncoder  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from scipy import stats  # noqa: E402


# ─── 파서 ─────────────────────────────────────────────────────
def parse_plan(path: Path) -> dict:
    if not path or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    info = {}
    for line in text.splitlines():
        line = line.strip()
        for key in ["goal:", "analysis_type:", "target_variable:", "success_metric:", "execution_env:"]:
            if line.startswith(f"- {key}") or line.startswith(key):
                value = line.split(":", 1)[1].strip()
                info[key.rstrip(":").strip()] = value
    info["is_time_series"] = bool(re.search(r"time[\-\s]?series|시계열", text, re.I))
    return info


def parse_analysis_cycle(path: Path) -> dict:
    if not path or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    info = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            for line in text[3:end].splitlines():
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    info[k.strip()] = v.strip()
    for key in ["best_hypothesis", "best_features", "best_model", "best_score"]:
        m = re.search(rf"{key}:\s*([^\n]+)", text)
        if m:
            info[key] = m.group(1).strip()
    if "best_features" in info:
        bf = info["best_features"]
        try:
            info["best_features_list"] = json.loads(bf.replace("'", '"'))
        except Exception:
            info["best_features_list"] = [x.strip() for x in re.findall(r"[\w]+", bf)]
    return info


def get_model(name: str, task: str):
    """best_model 이름 → sklearn 인스턴스."""
    name_upper = (name or "").upper()
    if task == "classification":
        if "RANDOMFOREST" in name_upper or "RF" in name_upper:
            return RandomForestClassifier(n_estimators=100, random_state=42)
        if "XGBOOST" in name_upper or "XGB" in name_upper:
            try:
                from xgboost import XGBClassifier
                return XGBClassifier(n_estimators=100, random_state=42, verbosity=0)
            except ImportError:
                return RandomForestClassifier(n_estimators=100, random_state=42)
        if "LIGHTGBM" in name_upper or "LGBM" in name_upper:
            try:
                from lightgbm import LGBMClassifier
                return LGBMClassifier(n_estimators=100, random_state=42, verbosity=-1)
            except ImportError:
                return RandomForestClassifier(n_estimators=100, random_state=42)
        if "LOGISTIC" in name_upper or "LR" in name_upper:
            return LogisticRegression(max_iter=1000, random_state=42)
        return RandomForestClassifier(n_estimators=100, random_state=42)
    else:
        if "RIDGE" in name_upper:
            return Ridge(random_state=42)
        if "XGBOOST" in name_upper or "XGB" in name_upper:
            try:
                from xgboost import XGBRegressor
                return XGBRegressor(n_estimators=100, random_state=42, verbosity=0)
            except ImportError:
                return RandomForestRegressor(n_estimators=100, random_state=42)
        return RandomForestRegressor(n_estimators=100, random_state=42)


def get_baselines(task: str) -> list:
    if task == "classification":
        return [
            ("DummyClassifier(most_frequent)", DummyClassifier(strategy="most_frequent")),
            ("DummyClassifier(stratified)", DummyClassifier(strategy="stratified")),
        ]
    elif task == "regression":
        return [
            ("DummyRegressor(mean)", DummyRegressor(strategy="mean")),
            ("DummyRegressor(median)", DummyRegressor(strategy="median")),
        ]
    return []


def make_cv(task: str, is_ts: bool):
    if is_ts:
        from sklearn.model_selection import TimeSeriesSplit
        return TimeSeriesSplit(n_splits=5)
    if task == "classification":
        return StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    return KFold(n_splits=5, shuffle=True, random_state=42)


def scoring_for(metric: str, task: str) -> str:
    metric_norm = re.sub(r"[\s_\-]", "", (metric or "").upper())
    if "AUC" in metric_norm or "ROC" in metric_norm:
        return "roc_auc"
    if metric_norm in ("F1",):
        return "f1"
    if metric_norm == "ACCURACY":
        return "accuracy"
    if metric_norm == "RMSE":
        return "neg_root_mean_squared_error"
    if metric_norm == "MAE":
        return "neg_mean_absolute_error"
    if "LOGLOSS" in metric_norm:
        return "neg_log_loss"
    if metric_norm in ("R2", "RSQUARED"):
        return "r2"
    return "roc_auc" if task == "classification" else "r2"


def load_xy(plan: dict, data_dir: Path, feature_list: list):
    csvs = list(data_dir.rglob("*.csv"))
    if not csvs:
        return None, None, None
    import pandas as pd
    df = pd.read_csv(csvs[0])
    target = plan.get("target_variable", "")
    if target not in df.columns:
        return None, None, None
    features = [f for f in feature_list if f in df.columns] or [c for c in df.columns if c != target]
    X = df[features].copy()
    y = df[target]
    # impute numeric
    num_cols = X.select_dtypes(include="number").columns
    if len(num_cols) > 0 and X[num_cols].isnull().any().any():
        X[num_cols] = SimpleImputer(strategy="median").fit_transform(X[num_cols])
    # encode object
    for col in X.select_dtypes(include="object").columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    if y.dtype == object or y.dtype.name == "category":
        y = LabelEncoder().fit_transform(y.astype(str))
    return X, y, features


def fold_aligned_scores(model, X, y, cv, scoring):
    """Fold-aligned 점수 (best와 baseline 모두 같은 fold)."""
    scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=1)
    return np.asarray(scores, dtype=float)


def cohen_d_paired(a: np.ndarray, b: np.ndarray) -> float:
    diff = a - b
    sd = diff.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(diff.mean() / sd)


def bootstrap_lift_ci(best: np.ndarray, baseline: np.ndarray, B: int = 2000, alpha: float = 0.05, seed: int = 42):
    rng = np.random.default_rng(seed)
    n = len(best)
    diffs = best - baseline
    idx = rng.integers(0, n, size=(B, n))
    lifts = diffs[idx].mean(axis=1)
    lo = float(np.percentile(lifts, 100 * alpha / 2))
    hi = float(np.percentile(lifts, 100 * (1 - alpha / 2)))
    return float(diffs.mean()), lo, hi


def paired_test(best: np.ndarray, baseline: np.ndarray):
    """정규성 검사 → t-test / Wilcoxon / permutation."""
    diff = best - baseline
    if len(diff) < 3:
        return ("insufficient", np.nan, np.nan)
    # Shapiro normality
    try:
        _, p_norm = stats.shapiro(diff)
    except Exception:
        p_norm = 1.0
    if p_norm >= 0.05:
        # paired t-test
        t, p = stats.ttest_rel(best, baseline, alternative="greater")
        return ("paired_t", float(t), float(p))
    elif len(diff) >= 6:
        # Wilcoxon (need ≥6)
        try:
            w, p = stats.wilcoxon(best, baseline, alternative="greater")
            return ("wilcoxon", float(w), float(p))
        except Exception:
            pass
    # Permutation fallback
    rng = np.random.default_rng(42)
    obs = (best - baseline).mean()
    combined = np.concatenate([best, baseline])
    count = 0
    n_perm = 10000
    for _ in range(n_perm):
        rng.shuffle(combined)
        a = combined[: len(best)]
        b = combined[len(best):]
        if (a.mean() - b.mean()) >= obs:
            count += 1
    p_perm = count / n_perm
    return ("permutation", float(obs), float(p_perm))


def forest_plot(best_label: str, best_mean: float, baseline_results: list, out_path: Path):
    """Forest plot: best vs 각 baseline with CI bars."""
    fig, ax = plt.subplots(figsize=(8, max(3, len(baseline_results) * 0.8)))
    y_positions = list(range(len(baseline_results) + 1))
    labels = [best_label] + [r["name"] for r in baseline_results]
    means = [best_mean] + [r["lift"] + r["baseline_mean"] for r in baseline_results]
    ci_lows = [best_mean] + [r["baseline_mean"] + r["ci_low"] for r in baseline_results]
    ci_highs = [best_mean] + [r["baseline_mean"] + r["ci_high"] for r in baseline_results]

    ax.errorbar(
        means, y_positions,
        xerr=[np.array(means) - np.array(ci_lows), np.array(ci_highs) - np.array(means)],
        fmt="o", capsize=5, color="steelblue", ecolor="gray", markersize=8,
    )
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.axvline(best_mean, color="green", linestyle="--", alpha=0.5, label=f"best={best_mean:.4f}")
    ax.set_xlabel("점수 (success_metric)")
    ax.set_title("베이스라인 대비 Best 모델 Forest Plot")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


# ─── 메인 검증 ──────────────────────────────────────────────
def run_review(plan_path: Path, scratch_dir: Path, data_dir: Path, out_dir: Path) -> dict:
    plan = parse_plan(plan_path)
    cycle = parse_analysis_cycle(scratch_dir / "analysis-cycle.md")
    task = plan.get("analysis_type", "")
    target = plan.get("target_variable", "")
    metric = plan.get("success_metric", "")
    best_features = cycle.get("best_features_list", [])
    best_model_name = cycle.get("best_model", "RandomForest")

    if task == "clustering" or task not in {"classification", "regression"}:
        print(f"[statistical] task={task}: 베이스라인 비교 미지원 (not_applicable)")
        return {"verdict": "N/A", "task": task, "reason": "unsupported task"}

    X, y, features = load_xy(plan, data_dir, best_features)
    if X is None:
        print(f"[statistical] 데이터 또는 피처 없음 (X=None)")
        return {"verdict": "FAIL", "reason": "no_data"}

    print(f"[statistical] task={task} target={target} metric={metric} features={len(features)}")

    cv = make_cv(task, plan.get("is_time_series", False))
    scoring = scoring_for(metric, task)
    print(f"[cv] {type(cv).__name__}(n_splits={cv.n_splits if hasattr(cv, 'n_splits') else '?'}) scoring={scoring}")

    # Best model
    best_model = get_model(best_model_name, task)
    best_scores = fold_aligned_scores(best_model, X, y, cv, scoring)
    best_mean = float(best_scores.mean())
    print(f"[best] {best_model_name} CV {metric}: {best_mean:.4f} ± {best_scores.std():.4f}")

    # Baselines
    baselines = get_baselines(task)
    baseline_results = []
    gates = {"G1": False, "G2": False, "G3": False, "G4": False}

    for name, baseline in baselines:
        try:
            b_scores = fold_aligned_scores(baseline, X, y, cv, scoring)
        except Exception as e:
            print(f"[baseline] {name}: SKIP ({e})")
            continue
        b_mean = float(b_scores.mean())
        print(f"[baseline] {name}: {b_mean:.4f} ± {b_scores.std():.4f}")

        test_name, stat_val, p_val = paired_test(best_scores, b_scores)
        lift_mean, ci_low, ci_high = bootstrap_lift_ci(best_scores, b_scores)
        d = cohen_d_paired(best_scores, b_scores)
        # baseline 이 음수 (e.g., neg_root_mean_squared_error) 면 abs 로 부호 무시.
        # G2 게이트 (lift_pct ≥ 2%) 는 |baseline| 대비 상대적 개선폭으로 평가.
        denom = abs(b_mean) if abs(b_mean) > 1e-9 else 1.0
        lift_pct = (lift_mean / denom) * 100

        print(f"[{test_name} vs {name}] stat={stat_val:.4f} p={p_val:.6f}")
        print(f"[bootstrap] lift={lift_mean:.4f} CI=[{ci_low:.4f}, {ci_high:.4f}]")
        print(f"[effect] cohen_d={d:.4f} lift_pct={lift_pct:.2f}%")

        # gate update (any baseline pass = gate pass)
        if p_val < 0.05:
            gates["G1"] = True
        if lift_pct >= 2.0:
            gates["G2"] = True
        if abs(d) >= 0.2:
            gates["G3"] = True
        if ci_low > 0:
            gates["G4"] = True

        baseline_results.append({
            "name": name,
            "baseline_mean": b_mean,
            "baseline_std": float(b_scores.std()),
            "test": test_name,
            "stat": stat_val,
            "p_value": p_val,
            "lift": lift_mean,
            "lift_pct": lift_pct,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "cohen_d": d,
        })

    # Verdict
    n_pass = sum(gates.values())
    if n_pass == 4:
        verdict = "PASS"
    elif n_pass >= 2:
        verdict = "WARN"
    else:
        verdict = "FAIL"
    print(f"[gate] G1: {'PASS' if gates['G1'] else 'FAIL'}")
    print(f"[gate] G2: {'PASS' if gates['G2'] else 'FAIL'}")
    print(f"[gate] G3: {'PASS' if gates['G3'] else 'FAIL'}")
    print(f"[gate] G4: {'PASS' if gates['G4'] else 'FAIL'}")
    print(f"[verdict] {verdict} (gates passed: {n_pass}/4)")

    # Forest plot
    out_dir.mkdir(parents=True, exist_ok=True)
    forest_plot(best_model_name, best_mean, baseline_results, out_dir / "stat_lift.png")
    print(f"[plot] saved: {out_dir / 'stat_lift.png'}")

    # JSON output
    result = {
        "verdict": verdict,
        "task": task,
        "metric": metric,
        "best_model": best_model_name,
        "best_mean": best_mean,
        "best_std": float(best_scores.std()),
        "gates": gates,
        "n_pass": n_pass,
        "baselines": baseline_results,
    }
    (out_dir / "stat_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[json] saved: {out_dir / 'stat_results.json'}")
    return result


def self_test() -> int:
    import tempfile
    import pandas as pd

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "plan.md").write_text(
            "# selftest\n- goal: smoke\n- analysis_type: classification\n- target_variable: target\n- success_metric: AUC-ROC\n",
            encoding="utf-8",
        )
        (tmp / "analysis-cycle.md").write_text(
            "---\nbest_score: 0.85\n---\nbest_features: ['feat1', 'feat2']\nbest_model: RandomForest\n",
            encoding="utf-8",
        )
        np.random.seed(0)
        n = 500
        df = pd.DataFrame({
            "feat1": np.random.randn(n),
            "feat2": np.random.randn(n),
            "target": np.random.randint(0, 2, n),
        })
        df["target"] = (df["feat1"] + 0.3 * df["feat2"] > 0).astype(int)
        df.to_csv(tmp / "data.csv", index=False)
        result = run_review(
            plan_path=tmp / "plan.md",
            scratch_dir=tmp,
            data_dir=tmp,
            out_dir=tmp,
        )
        return 0 if result.get("verdict") in {"PASS", "WARN"} else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="베이스라인 대비 통계 검증 (R3)")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--scratch-dir", type=Path, default=Path("scratch"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("scratch"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if not args.plan:
        plans = sorted(Path("docs/plans").glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not plans:
            print("ERROR: docs/plans/*.md 가 없습니다.", file=sys.stderr)
            return 2
        args.plan = plans[0]

    run_review(args.plan, args.scratch_dir, args.data_dir, args.out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
