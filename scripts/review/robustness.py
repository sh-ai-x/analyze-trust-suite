#!/usr/bin/env python3
"""
review-robustness — 강건성 검증 (R4)

5 seeds × 5 folds = 25 scores + bootstrap CI + LOFO + per-slice + permutation importance.

stdout 출력:
  [robustness] task=... metric=... n_features=... seeds=5 folds=5
  [multi-seed] mean=... std=... min=... max=... median=... IQR=[..., ...]
  [bootstrap] CI=[..., ...]
  [gate-G1] PASS|FAIL (seed_std=...)
  [lofo] <feat> dropped: <score> (drop=<delta>, <pct>%) [load-bearing?]
  [gate-G3] PASS|WARN|FAIL
  [slice] <name>: <score>
  [perm-importance] top3=<f1>,<f2>,<f3> (<n>/5 seeds 일치)
  [gate-G2] PASS|FAIL (CI_low=... vs baseline=...)
  [verdict] PASS|WARN|FAIL
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

plt.rcParams["font.family"] = "AppleGothic" if platform.system() == "Darwin" else "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

from sklearn.model_selection import StratifiedKFold, KFold, cross_val_score  # noqa: E402
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor  # noqa: E402
from sklearn.linear_model import LogisticRegression, Ridge  # noqa: E402
from sklearn.preprocessing import LabelEncoder  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402


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
    name_upper = (name or "").upper()
    if task == "classification":
        if "RANDOMFOREST" in name_upper or "RF" in name_upper:
            return RandomForestClassifier(n_estimators=100)
        if "XGBOOST" in name_upper or "XGB" in name_upper:
            try:
                from xgboost import XGBClassifier
                return XGBClassifier(n_estimators=100, verbosity=0)
            except ImportError:
                return RandomForestClassifier(n_estimators=100)
        if "LOGISTIC" in name_upper:
            return LogisticRegression(max_iter=1000)
        return RandomForestClassifier(n_estimators=100)
    else:
        if "RIDGE" in name_upper:
            return Ridge()
        return RandomForestRegressor(n_estimators=100)


def make_cv(task: str, is_ts: bool):
    if is_ts:
        from sklearn.model_selection import TimeSeriesSplit
        return TimeSeriesSplit(n_splits=5)
    if task == "classification":
        return StratifiedKFold(n_splits=5, shuffle=True)
    return KFold(n_splits=5, shuffle=True)


def scoring_for(metric: str, task: str) -> str:
    metric_norm = re.sub(r"[\s_\-]", "", (metric or "").upper())
    if "AUC" in metric_norm or "ROC" in metric_norm:
        return "roc_auc"
    if metric_norm == "F1":
        return "f1"
    if metric_norm == "ACCURACY":
        return "accuracy"
    if metric_norm == "RMSE":
        return "neg_root_mean_squared_error"
    if metric_norm == "MAE":
        return "neg_mean_absolute_error"
    return "roc_auc" if task == "classification" else "r2"


def load_xy(plan: dict, data_dir: Path, feature_list: list):
    csvs = list(data_dir.rglob("*.csv"))
    if not csvs:
        return None, None, None, None
    import pandas as pd
    df = pd.read_csv(csvs[0])
    target = plan.get("target_variable", "")
    if target not in df.columns:
        return None, None, None, None
    features = [f for f in feature_list if f in df.columns] or [c for c in df.columns if c != target]
    X = df[features].copy()
    y = df[target]
    num_cols = X.select_dtypes(include="number").columns
    if len(num_cols) > 0 and X[num_cols].isnull().any().any():
        X[num_cols] = SimpleImputer(strategy="median").fit_transform(X[num_cols])
    for col in X.select_dtypes(include="object").columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    if y.dtype == object or y.dtype.name == "category":
        y = LabelEncoder().fit_transform(y.astype(str))
    return X, y, features, df


def multi_seed_cv(model_cls, X, y, cv_template, scoring: str, seeds=(0, 1, 7, 42, 123)):
    """5 seeds × 5 folds → 25 scores."""
    all_scores = []
    per_seed = {}
    for seed in seeds:
        if hasattr(cv_template, "set_params"):
            cv = cv_template.__class__(**{**cv_template.get_params(), "random_state": seed})
        else:
            cv = cv_template
        m = model_cls.__class__(**{**model_cls.get_params(), "random_state": seed}) if hasattr(model_cls, "get_params") else model_cls
        try:
            scores = cross_val_score(m, X, y, cv=cv, scoring=scoring, n_jobs=1)
            per_seed[seed] = scores.tolist()
            all_scores.extend(scores.tolist())
        except Exception as e:
            print(f"[multi-seed] seed={seed}: SKIP ({e})", file=sys.stderr)
    return np.asarray(all_scores, dtype=float), per_seed


def bootstrap_ci(scores: np.ndarray, B: int = 2000, alpha: float = 0.05, seed: int = 42):
    rng = np.random.default_rng(seed)
    n = len(scores)
    idx = rng.integers(0, n, size=(B, n))
    means = scores[idx].mean(axis=1)
    return float(np.percentile(means, 100 * alpha / 2)), float(np.percentile(means, 100 * (1 - alpha / 2)))


def lofo_scores(model_cls, X, y, cv_template, scoring: str, seeds=(0, 1, 7, 42, 123)):
    """각 피처 제거 후 multi-seed CV 평균."""
    results = {}
    cols = list(X.columns)
    full_scores, _ = multi_seed_cv(model_cls, X, y, cv_template, scoring, seeds)
    full_mean = float(full_scores.mean())
    for col in cols:
        X_drop = X.drop(columns=[col])
        scores, _ = multi_seed_cv(model_cls, X_drop, y, cv_template, scoring, seeds)
        drop_mean = float(scores.mean())
        delta = full_mean - drop_mean
        results[col] = {"score": drop_mean, "drop": delta, "drop_pct": (delta / abs(full_mean)) * 100 if full_mean else 0}
    return full_mean, results


def per_slice_perf(model_cls, X, y, df, target: str, task: str, cv_template, scoring: str, seeds=(0, 1, 7, 42, 123)):
    """자동 slice 탐색 (3개)."""
    import pandas as pd
    slices = {}
    # (a) 가장 높은 |r| numeric 컬럼의 low/mid/high 분위
    try:
        num_cols = [c for c in X.columns if X[c].dtype != object]
        if num_cols and target in df.columns:
            target_num = df[target]
            if target_num.dtype == object:
                target_num = LabelEncoder().fit_transform(target_num.astype(str))
            best_col, best_r = None, 0
            for c in num_cols:
                r = abs(df[c].corr(pd.Series(target_num)))
                if pd.notna(r) and r > best_r:
                    best_r, best_col = r, c
            if best_col:
                q33, q67 = df[best_col].quantile([0.33, 0.67])
                for label, mask in [
                    ("low_33%", df[best_col] <= q33),
                    ("mid_33%", (df[best_col] > q33) & (df[best_col] <= q67)),
                    ("high_33%", df[best_col] > q67),
                ]:
                    if mask.sum() < 30:
                        continue
                    Xs, ys = X.loc[mask], y[mask.values]
                    if len(np.unique(ys)) < 2 and task == "classification":
                        continue
                    scores, _ = multi_seed_cv(model_cls, Xs, ys, cv_template, scoring, seeds)
                    slices[f"by_{best_col}_{label}"] = float(scores.mean())
    except Exception as e:
        print(f"[slice] (a) skip: {e}", file=sys.stderr)

    # (b) 가장 중요한 피처의 head/tail 50%
    try:
        if len(X.columns) > 0:
            best_col = X.columns[0]  # 단순 휴리스틱: 첫 컬럼
            sorted_idx = df[best_col].sort_values().index
            n = len(sorted_idx)
            head_idx = sorted_idx[n // 2:]
            tail_idx = sorted_idx[: n // 2]
            for label, idx in [("head_50%", head_idx), ("tail_50%", tail_idx)]:
                Xs, ys = X.loc[idx], y[idx.values]
                if len(np.unique(ys)) < 2 and task == "classification":
                    continue
                scores, _ = multi_seed_cv(model_cls, Xs, ys, cv_template, scoring, seeds)
                slices[f"by_{best_col}_{label}"] = float(scores.mean())
    except Exception as e:
        print(f"[slice] (b) skip: {e}", file=sys.stderr)

    # (c) classification: rare vs common
    if task == "classification":
        try:
            unique, counts = np.unique(y, return_counts=True)
            if len(unique) >= 2:
                rare_class = unique[np.argmin(counts)]
                common_class = unique[np.argmax(counts)]
                for label, cls in [("rare_class", rare_class), ("common_class", common_class)]:
                    mask = (y == cls)
                    if mask.sum() < 30:
                        continue
                    Xs, ys = X.loc[mask], y[mask]
                    if len(np.unique(ys)) < 2:
                        continue
                    scores, _ = multi_seed_cv(model_cls, Xs, ys, cv_template, scoring, seeds)
                    slices[label] = float(scores.mean())
        except Exception as e:
            print(f"[slice] (c) skip: {e}", file=sys.stderr)

    return slices


def perm_importance_stability(model_cls, X, y, scoring: str, seeds=(0, 1, 7, 42, 123)):
    """5 seeds 별 permutation importance 의 top-3 안정성."""
    import pandas as pd
    from collections import Counter
    top3_per_seed = []
    for seed in seeds:
        m = model_cls.__class__(**{**model_cls.get_params(), "random_state": seed}) if hasattr(model_cls, "get_params") else model_cls
        m.fit(X, y)
        try:
            r = permutation_importance(m, X, y, n_repeats=10, random_state=seed, scoring=scoring)
            imp = pd.Series(r.importances_mean, index=X.columns).sort_values(ascending=False)
            top3_per_seed.append(tuple(imp.head(3).index.tolist()))
        except Exception as e:
            print(f"[perm-importance] seed={seed}: SKIP ({e})", file=sys.stderr)
    if not top3_per_seed:
        return {}, 0, []
    cnt = Counter(top3_per_seed)
    most_common = cnt.most_common(1)[0][0]
    n_match = cnt[most_common]
    return dict(zip(X.columns, [0] * len(X.columns))), n_match, list(most_common)


def seed_boxplot(scores_per_seed: dict, out_path: Path):
    fig, ax = plt.subplots(figsize=(8, 4))
    seeds = sorted(scores_per_seed.keys())
    data = [scores_per_seed[s] for s in seeds]
    ax.boxplot(data, tick_labels=[str(s) for s in seeds])
    ax.set_xlabel("seed")
    ax.set_ylabel("CV score")
    ax.set_title("Multi-seed CV 분포")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def lofo_bar(lofo_results: dict, full_mean: float, out_path: Path):
    cols = list(lofo_results.keys())
    drops = [lofo_results[c]["drop_pct"] for c in cols]
    fig, ax = plt.subplots(figsize=(max(6, len(cols) * 0.5), 4))
    colors = ["red" if d > 15 else "steelblue" for d in drops]
    ax.barh(cols, drops, color=colors)
    ax.axvline(15, color="orange", linestyle="--", alpha=0.5, label="warn threshold (15%)")
    ax.axvline(25, color="red", linestyle="--", alpha=0.5, label="critical threshold (25%)")
    ax.set_xlabel("점수 drop (%)")
    ax.set_title(f"LOFO 감도 분석 (full mean = {full_mean:.4f})")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def slice_bar(slices: dict, baseline: float, out_path: Path):
    if not slices:
        return
    labels = list(slices.keys())
    values = list(slices.values())
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.5), 4))
    ax.barh(labels, values, color="steelblue")
    ax.axvline(baseline, color="red", linestyle="--", alpha=0.5, label=f"baseline={baseline:.4f}")
    ax.set_xlabel("Slice score")
    ax.set_title("슬라이스별 성능")
    ax.legend(loc="lower right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


# ─── 메인 검증 ──────────────────────────────────────────────
def run_review(plan_path: Path, scratch_dir: Path, data_dir: Path, out_dir: Path, seeds=None, n_folds: int = 5) -> dict:
    import pandas as pd

    plan = parse_plan(plan_path)
    cycle = parse_analysis_cycle(scratch_dir / "analysis-cycle.md")
    task = plan.get("analysis_type", "")
    target = plan.get("target_variable", "")
    metric = plan.get("success_metric", "")
    best_features = cycle.get("best_features_list", [])
    best_model_name = cycle.get("best_model", "RandomForest")

    if task not in {"classification", "regression"}:
        print(f"[robustness] task={task}: 미지원")
        return {"verdict": "N/A"}

    X, y, features, df = load_xy(plan, data_dir, best_features)
    if X is None:
        print(f"[robustness] 데이터 또는 피처 없음")
        return {"verdict": "FAIL", "reason": "no_data"}

    n_features = len(features)
    if seeds is None:
        seeds = (0, 1, 7, 42, 123)
    print(f"[robustness] task={task} metric={metric} n_features={n_features} seeds={len(seeds)} folds={n_folds}")

    # n_folds 적용하여 CV 재생성
    if plan.get("is_time_series"):
        from sklearn.model_selection import TimeSeriesSplit
        cv = TimeSeriesSplit(n_splits=n_folds)
    elif task == "classification":
        cv = StratifiedKFold(n_splits=n_folds, shuffle=True)
    else:
        cv = KFold(n_splits=n_folds, shuffle=True)
    scoring = scoring_for(metric, task)
    model_cls = get_model(best_model_name, task)

    # B1: multi-seed
    scores, per_seed = multi_seed_cv(model_cls, X, y, cv, scoring, seeds)
    mean = float(scores.mean())
    std = float(scores.std())
    iqr = np.percentile(scores, [25, 75])
    print(f"[multi-seed] mean={mean:.4f} std={std:.4f} min={scores.min():.4f} max={scores.max():.4f} median={np.median(scores):.4f} IQR=[{iqr[0]:.4f}, {iqr[1]:.4f}]")

    # B2: bootstrap CI
    ci_low, ci_high = bootstrap_ci(scores)
    print(f"[bootstrap] CI=[{ci_low:.4f}, {ci_high:.4f}]")

    # 베이스라인 (R3 와 동일 로직 — DummyClassifier)
    from sklearn.dummy import DummyClassifier, DummyRegressor
    if task == "classification":
        baseline_model = DummyClassifier(strategy="most_frequent")
    else:
        baseline_model = DummyRegressor(strategy="mean")
    cv_b = make_cv(task, plan.get("is_time_series", False))
    if hasattr(cv_b, "set_params"):
        cv_b = cv_b.__class__(**{**cv_b.get_params(), "random_state": 42})
    baseline_scores = cross_val_score(baseline_model, X, y, cv=cv_b, scoring=scoring, n_jobs=1)
    baseline_mean = float(baseline_scores.mean())
    print(f"[baseline] {type(baseline_model).__name__}: {baseline_mean:.4f}")

    # G1 (stability)
    gate_G1 = std <= 0.03
    print(f"[gate-G1] {'PASS' if gate_G1 else 'FAIL'} (seed_std={std:.4f} <= 0.03)")
    # G2 (CI > baseline)
    gate_G2 = ci_low > baseline_mean
    print(f"[gate-G2] {'PASS' if gate_G2 else 'FAIL'} (CI_low={ci_low:.4f} > baseline={baseline_mean:.4f})")

    # B3: LOFO
    full_mean, lofo_results = lofo_scores(model_cls, X, y, cv, scoring, seeds)
    lofo_critical = []
    for feat, r in lofo_results.items():
        status = ""
        if r["drop_pct"] > 25:
            status = "[CRITICAL]"
            lofo_critical.append(feat)
        elif r["drop_pct"] > 15:
            status = "[load-bearing]"
        print(f"[lofo] {feat}: score={r['score']:.4f} drop={r['drop']:.4f} ({r['drop_pct']:.2f}%) {status}")
    gate_G3 = len(lofo_critical) == 0
    print(f"[gate-G3] {'PASS' if gate_G3 else 'FAIL'} (critical drops: {len(lofo_critical)})")

    # B4: per-slice
    slices = per_slice_perf(model_cls, X, y, df, target, task, cv, scoring, seeds)
    for name, s in slices.items():
        print(f"[slice] {name}: {s:.4f}")

    # B5: perm importance
    _, n_match, top3 = perm_importance_stability(model_cls, X, y, scoring, seeds)
    print(f"[perm-importance] top3={top3} ({n_match}/{len(seeds)} seeds 일치)")

    # Verdict
    n_pass = sum([gate_G1, gate_G2, gate_G3])
    if n_pass == 3:
        verdict = "PASS"
    elif n_pass >= 1:
        verdict = "WARN"
    else:
        verdict = "FAIL"
    print(f"[verdict] {verdict} (gates passed: {n_pass}/3)")

    # 시각화
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_boxplot(per_seed, out_dir / "seed_boxplot.png")
    lofo_bar(lofo_results, full_mean, out_dir / "lofo_drop.png")
    slice_bar(slices, baseline_mean, out_dir / "slice_perf.png")
    print(f"[plot] saved: seed_boxplot.png, lofo_drop.png, slice_perf.png")

    # JSON
    result = {
        "verdict": verdict,
        "task": task,
        "metric": metric,
        "best_model": best_model_name,
        "multi_seed": {
            "n_seeds": len(seeds),
            "n_folds": 5,
            "mean": mean,
            "std": std,
            "min": float(scores.min()),
            "max": float(scores.max()),
            "median": float(np.median(scores)),
            "iqr": [float(iqr[0]), float(iqr[1])],
        },
        "bootstrap_ci": {"low": ci_low, "high": ci_high},
        "baseline_mean": baseline_mean,
        "gates": {"G1_stability": gate_G1, "G2_ci_above_baseline": gate_G2, "G3_lofo": gate_G3},
        "lofo": {f: {"score": r["score"], "drop_pct": r["drop_pct"]} for f, r in lofo_results.items()},
        "lofo_critical": lofo_critical,
        "slices": slices,
        "perm_importance_top3": list(top3),
        "perm_importance_n_match": n_match,
    }
    (out_dir / "robustness_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[json] saved: {out_dir / 'robustness_results.json'}")
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
            "---\nbest_score: 0.85\n---\nbest_features: ['feat1', 'feat2', 'feat3']\nbest_model: RandomForest\n",
            encoding="utf-8",
        )
        np.random.seed(0)
        n = 500
        df = pd.DataFrame({
            "feat1": np.random.randn(n),
            "feat2": np.random.randn(n),
            "feat3": np.random.randn(n),
            "target": np.random.randint(0, 2, n),
        })
        df["target"] = (df["feat1"] + 0.5 * df["feat2"] > 0).astype(int)
        df.to_csv(tmp / "data.csv", index=False)
        # CLI 옵션이 있으면 그 값으로 self-test
        import sys as _sys
        n_seeds = 5
        n_folds = 5
        for i, arg in enumerate(_sys.argv):
            if arg == "--n-seeds" and i + 1 < len(_sys.argv):
                n_seeds = int(_sys.argv[i + 1])
            elif arg.startswith("--n-seeds="):
                n_seeds = int(arg.split("=", 1)[1])
            if arg == "--n-folds" and i + 1 < len(_sys.argv):
                n_folds = int(_sys.argv[i + 1])
            elif arg.startswith("--n-folds="):
                n_folds = int(arg.split("=", 1)[1])
        seeds = tuple(range(n_seeds))
        result = run_review(
            plan_path=tmp / "plan.md",
            scratch_dir=tmp,
            data_dir=tmp,
            out_dir=tmp,
            seeds=seeds,
            n_folds=n_folds,
        )
        return 0 if result.get("verdict") in {"PASS", "WARN"} else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="강건성 검증 (R4)")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--scratch-dir", type=Path, default=Path("scratch"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("scratch"))
    parser.add_argument("--n-seeds", type=int, default=5, help="multi-seed CV seeds count (default 5)")
    parser.add_argument("--n-folds", type=int, default=5, help="CV folds count (default 5)")
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

    seeds = tuple(range(args.n_seeds))
    run_review(args.plan, args.scratch_dir, args.data_dir, args.out_dir, seeds=seeds, n_folds=args.n_folds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
