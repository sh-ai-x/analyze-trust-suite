#!/usr/bin/env python3
"""
review-methodology — 방법론 정적 감사 (R2)

scripts/*.py 와 scratch/*.md 를 AST + 메타데이터 분석해서 방법론적 결함 감사.
재학습/재실행 없음.

검사:
  M1: target leakage (|corr(feature, target)| > 0.95)
  M2: temporal leakage (시계열 데이터에 shuffle=True)
  M3: preprocessing leakage (split 전 fit_transform)
  M4: CV 전략 부적합 (불균형 분류인데 KFold)
  M5: hypothesis selection bias (동일 hypothesis_id > 5회)
  M6: cherry-picking (fold_excluded 흔적)
  M7: NaN impute 누락
  M8: metric direction 오류
  M9: seed 하드코딩 (> 2회)
  M10: 절대 경로 사용
  M11: 한글 폰트 preamble 없음
  M12: EDA→모델링 정합성 (제외 피처 재등장)

stdout: FINDING|<id>|<severity>|<message>|<location>|<evidence>
"""
from __future__ import annotations
import argparse
import ast
import json
import re
import sys
from pathlib import Path
from collections import defaultdict


def parse_plan(path: Path) -> dict:
    """docs/plans/<goal>.md 의 메타데이터 추출."""
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
        # constraints: list 형태
        if line.startswith("- constraints:"):
            info.setdefault("constraints", [])
            info["constraints"].append(line.split(":", 1)[1].strip())
    # 본문에서 "time-series", "시계열" 태그 검사
    info["is_time_series"] = bool(re.search(r"time[\-\s]?series|시계열|timeseries", text, re.I))
    info["is_imbalanced_hint"] = bool(re.search(r"불균형|imbalanced|class\s*imbalance", text, re.I))
    return info


def parse_analysis_cycle(path: Path) -> dict:
    """scratch/analysis-cycle.md 의 loop_state + best_* 추출."""
    if not path or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    info = {}
    # YAML frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            fm = text[3:end]
            for line in fm.splitlines():
                if ":" in line and not line.startswith(" "):
                    k, _, v = line.partition(":")
                    info[k.strip()] = v.strip()
    # 본문에서 hypothesis_id 빈도
    hyp_ids = re.findall(r"hypothesis[_\-]?id[:\s=]+['\"]?([Hh]\d+|HYP\w+)", text)
    info["hypothesis_id_counts"] = dict(defaultdict(int, {h: hyp_ids.count(h) for h in set(hyp_ids)}))
    # fold_excluded 흔적
    info["fold_excluded_present"] = "fold_excluded" in text
    # best_* 추출
    for key in ["best_hypothesis", "best_features", "best_model", "best_score"]:
        m = re.search(rf"{key}:\s*([^\n]+)", text)
        if m:
            info[key] = m.group(1).strip()
    # best_features JSON list
    if "best_features" in info:
        bf = info["best_features"]
        try:
            info["best_features_list"] = json.loads(bf.replace("'", '"'))
        except Exception:
            info["best_features_list"] = [x.strip() for x in re.findall(r"[\w]+", bf)]
    return info


def parse_hypothesis_eda(path: Path) -> dict:
    """scratch/hypothesis-eda.md 의 top_hypotheses + 제외 피처."""
    if not path or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    excluded = []
    m = re.search(r"excluded[_\-]?features[:\s=]+\[([^\]]+)\]", text, re.I)
    if m:
        excluded = [x.strip().strip("'\"") for x in m.group(1).split(",")]
    return {"excluded_features": excluded}


def parse_train_py(path: Path) -> dict:
    """scripts/train.py AST 분석."""
    if not path or not path.exists():
        return {}
    src = path.read_text(encoding="utf-8")
    info = {
        "random_state_count": len(re.findall(r"random_state\s*=\s*42", src)),
        "abs_path_count": len(re.findall(r"^[\"']/(?:Users|tmp|home|content)", src, re.M)) + len(re.findall(r"~/?\w+", src)),
        "has_korean_font": "font.family" in src and ("AppleGothic" in src or "NanumGothic" in src),
        "has_impute": bool(re.search(r"\.fillna\(|SimpleImputer|KNNImputer|IterativeImputer", src)),
        "has_fit_transform_split": False,
        "uses_stratified_kfold": "StratifiedKFold" in src,
        "uses_kfold": bool(re.search(r"\bKFold\b", src)),
        "uses_timeseries_split": "TimeSeriesSplit" in src,
        "uses_train_test_split": "train_test_split" in src,
        "uses_shuffle_true": bool(re.search(r"shuffle\s*=\s*True", src)),
        "metric_score_used": None,
    }
    # metric direction sanity
    m = re.search(r"scoring\s*=\s*['\"]([^'\"]+)['\"]", src)
    if m:
        info["metric_score_used"] = m.group(1)

    # AST: fit_transform 위치 검사
    try:
        tree = ast.parse(src)
        first_split_line = None
        first_fit_transform_line = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
                if "train_test_split" in fn and first_split_line is None:
                    first_split_line = node.lineno
                if "fit_transform" in fn and first_fit_transform_line is None:
                    first_fit_transform_line = node.lineno
        if first_fit_transform_line and (first_split_line is None or first_fit_transform_line < first_split_line):
            info["has_fit_transform_split"] = True
    except SyntaxError:
        pass

    return info


def check_M1_target_leakage(plan: dict, best_features: list[str], data_dir: Path) -> list[dict]:
    """M1: target leakage."""
    findings = []
    if not plan.get("target_variable") or not data_dir.exists():
        return findings
    target = plan["target_variable"]
    try:
        import pandas as pd
        import numpy as np
    except ImportError:
        return findings

    csvs = list(data_dir.rglob("*.csv"))
    if not csvs:
        return findings
    df = pd.read_csv(csvs[0])
    if target not in df.columns:
        return findings

    if df[target].dtype == object or df[target].nunique() < 5:
        # classification — point-biserial via numeric encoding
        y = df[target].astype("category").cat.codes
    else:
        y = df[target]

    for feat in best_features:
        if feat == target or feat not in df.columns:
            continue
        try:
            x = pd.to_numeric(df[feat], errors="coerce")
            if x.isna().all():
                continue
            r = abs(x.corr(y))
            if pd.isna(r):
                continue
            if r > 0.95:
                findings.append({
                    "id": "M1",
                    "severity": "block",
                    "message": f"Target leakage 의심: feature '{feat}' (|r|={r:.4f} with target '{target}')",
                    "location": f"data/raw/{csvs[0].name}",
                    "evidence": f"corr({feat},{target})={r:.4f}",
                })
        except Exception:
            pass
    return findings


def check_M2_temporal(plan: dict, train_info: dict) -> list[dict]:
    """M2: temporal leakage."""
    findings = []
    if plan.get("is_time_series") and train_info.get("uses_shuffle_true"):
        findings.append({
            "id": "M2",
            "severity": "block",
            "message": "시계열 데이터에 shuffle=True 사용 (temporal leakage)",
            "location": "scripts/train.py",
            "evidence": "is_time_series=True, shuffle=True 발견",
        })
    return findings


def check_M3_preprocessing_leakage(train_info: dict) -> list[dict]:
    """M3: preprocessing leakage."""
    findings = []
    if train_info.get("has_fit_transform_split"):
        findings.append({
            "id": "M3",
            "severity": "block",
            "message": "fit_transform 이 split 전에 호출됨 (preprocessing leakage)",
            "location": "scripts/train.py",
            "evidence": "fit_transform 호출 위치 < train_test_split 호출 위치",
        })
    return findings


def check_M4_cv_strategy(plan: dict, train_info: dict, data_dir: Path) -> list[dict]:
    """M4: CV 전략 부적합."""
    findings = []
    if plan.get("analysis_type") == "classification":
        # 클래스 불균형 검사
        try:
            import pandas as pd
            csvs = list(data_dir.rglob("*.csv"))
            target = plan.get("target_variable", "")
            if csvs and target:
                df = pd.read_csv(csvs[0])
                if target in df.columns:
                    vc = df[target].value_counts(normalize=True)
                    if len(vc) > 1 and vc.min() < 0.2:
                        # 불균형 → StratifiedKFold 필요
                        if not train_info.get("uses_stratified_kfold"):
                            findings.append({
                                "id": "M4",
                                "severity": "warn",
                                "message": f"불균형 분류(min class={vc.min():.3f}) 인데 StratifiedKFold 미사용",
                                "location": "scripts/train.py",
                                "evidence": f"target 분포: {dict(vc.round(3))}",
                            })
        except Exception:
            pass
    return findings


def check_M5_selection_bias(cycle_info: dict) -> list[dict]:
    """M5: hypothesis selection bias."""
    findings = []
    counts = cycle_info.get("hypothesis_id_counts", {})
    for hyp_id, n in counts.items():
        if n > 5:
            findings.append({
                "id": "M5",
                "severity": "warn",
                "message": f"가설 '{hyp_id}' 가 {n}회 반복 시도됨 (selection bias 가능성)",
                "location": "scratch/analysis-cycle.md",
                "evidence": f"counts[{hyp_id}]={n}",
            })
    return findings


def check_M6_cherry_picking(cycle_info: dict) -> list[dict]:
    """M6: cherry-picking."""
    findings = []
    if cycle_info.get("fold_excluded_present"):
        findings.append({
            "id": "M6",
            "severity": "warn",
            "message": "fold_excluded 흔적 발견 (특정 fold 제외 가능성)",
            "location": "scratch/analysis-cycle.md",
            "evidence": "fold_excluded 키워드 발견",
        })
    return findings


def check_M7_nan_impute(plan: dict, train_info: dict, data_dir: Path) -> list[dict]:
    """M7: NaN impute 누락."""
    findings = []
    if not data_dir.exists() or train_info.get("has_impute"):
        return findings
    try:
        import pandas as pd
        csvs = list(data_dir.rglob("*.csv"))
        if not csvs:
            return findings
        df = pd.read_csv(csvs[0])
        nan_ratio = df.isnull().mean()
        high_nan = nan_ratio[nan_ratio > 0.05]
        if len(high_nan) > 0 and not train_info.get("has_impute"):
            findings.append({
                "id": "M7",
                "severity": "warn",
                "message": f"결측치 > 5% 컬럼 {len(high_nan)}개 인데 impute 호출 없음",
                "location": "scripts/train.py",
                "evidence": f"고결측 컬럼: {list(high_nan.index)[:5]}",
            })
    except Exception:
        pass
    return findings


def check_M8_metric_direction(plan: dict, train_info: dict) -> list[dict]:
    """M8: metric direction sanity."""
    findings = []
    metric_raw = (plan.get("success_metric") or "")
    used_raw = (train_info.get("metric_score_used") or "")
    if not metric_raw or not used_raw:
        return findings
    # underscore, hyphen, space 모두 제거하고 비교
    def _norm(s: str) -> str:
        return re.sub(r"[\s_\-]", "", s.upper())

    metric = _norm(metric_raw)
    used = _norm(used_raw)

    higher_better = {"AUC", "AUCROC", "F1", "ACCURACY", "RECALL", "PRECISION", "ROCAUC"}
    lower_better = {"RMSE", "MAE", "LOGLOSS", "MSE"}

    if metric in higher_better and used not in higher_better:
        findings.append({
            "id": "M8",
            "severity": "block",
            "message": f"성공 지표 '{metric_raw}' 은 높을수록 좋지만 scoring='{used_raw}' 사용",
            "location": "scripts/train.py",
            "evidence": f"plan.metric={metric_raw}, train.scoring={used_raw}",
        })
    if metric in lower_better and used not in lower_better:
        findings.append({
            "id": "M8",
            "severity": "block",
            "message": f"성공 지표 '{metric_raw}' 은 낮을수록 좋지만 scoring='{used_raw}' 사용",
            "location": "scripts/train.py",
            "evidence": f"plan.metric={metric_raw}, train.scoring={used_raw}",
        })
    return findings


def check_M9_seed_hardcode(train_info: dict) -> list[dict]:
    """M9: seed 하드코딩."""
    findings = []
    if train_info.get("random_state_count", 0) > 2:
        findings.append({
            "id": "M9",
            "severity": "warn",
            "message": f"random_state=42 가 {train_info['random_state_count']}회 등장 (검증 외 하드코딩)",
            "location": "scripts/train.py",
            "evidence": f"random_state=42 count={train_info['random_state_count']}",
        })
    return findings


def check_M10_path_safety(train_info: dict) -> list[dict]:
    """M10: 절대 경로 사용."""
    findings = []
    if train_info.get("abs_path_count", 0) > 0:
        findings.append({
            "id": "M10",
            "severity": "warn",
            "message": f"절대 경로 또는 ~ 사용 {train_info['abs_path_count']}회 (재현성 저하)",
            "location": "scripts/train.py",
            "evidence": "/Users/, /tmp/, ~/ 패턴 발견",
        })
    return findings


def check_M11_reproducibility(train_info: dict) -> list[dict]:
    """M11: 한글 폰트 preamble 없음."""
    findings = []
    if not train_info.get("has_korean_font"):
        findings.append({
            "id": "M11",
            "severity": "warn",
            "message": "한글 폰트 preamble 없음 (matplotlib 한글 깨짐 가능성)",
            "location": "scripts/train.py",
            "evidence": "plt.rcParams['font.family'] 미설정",
        })
    return findings


def check_M12_eda_model_consistency(cycle_info: dict, hyp_eda_info: dict) -> list[dict]:
    """M12: EDA→모델링 정합성 (EDA 제외 피처가 train에 등장)."""
    findings = []
    excluded = set(hyp_eda_info.get("excluded_features", []))
    best = cycle_info.get("best_features_list", [])
    leakage = [f for f in best if f in excluded]
    if leakage:
        findings.append({
            "id": "M12",
            "severity": "block",
            "message": f"EDA에서 제외된 피처가 train에 등장: {leakage}",
            "location": "scripts/train.py",
            "evidence": f"excluded={list(excluded)}, best_features={best}",
        })
    return findings


def run_review(plan_path: Path, scripts_dir: Path, scratch_dir: Path, data_dir: Path) -> list[dict]:
    plan = parse_plan(plan_path)
    cycle_path = scratch_dir / "analysis-cycle.md"
    hyp_eda_path = scratch_dir / "hypothesis-eda.md"
    cycle_info = parse_analysis_cycle(cycle_path)
    hyp_eda_info = parse_hypothesis_eda(hyp_eda_path)

    train_path = scripts_dir / "train.py"
    train_info = parse_train_py(train_path)

    best_features = cycle_info.get("best_features_list", [])

    findings = []
    findings += check_M1_target_leakage(plan, best_features, data_dir)
    findings += check_M2_temporal(plan, train_info)
    findings += check_M3_preprocessing_leakage(train_info)
    findings += check_M4_cv_strategy(plan, train_info, data_dir)
    findings += check_M5_selection_bias(cycle_info)
    findings += check_M6_cherry_picking(cycle_info)
    findings += check_M7_nan_impute(plan, train_info, data_dir)
    findings += check_M8_metric_direction(plan, train_info)
    findings += check_M9_seed_hardcode(train_info)
    findings += check_M10_path_safety(train_info)
    findings += check_M11_reproducibility(train_info)
    findings += check_M12_eda_model_consistency(cycle_info, hyp_eda_info)
    return findings


def self_test() -> int:
    """합성 fixtures 로 self-test."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        # 합성 plan
        (tmp / "plan.md").write_text(
            "# test\n- goal: smoke\n- analysis_type: classification\n- target_variable: target\n- success_metric: AUC-ROC\n",
            encoding="utf-8",
        )
        # 합성 train.py — M3 (fit_transform before split), M9 (seed hardcoded 3x), M11 (no font)
        (tmp / "train.py").write_text(
            "import pandas as pd\n"
            "from sklearn.preprocessing import StandardScaler\n"
            "from sklearn.model_selection import train_test_split, cross_val_score, KFold\n"
            "from sklearn.ensemble import RandomForestClassifier\n"
            "\n"
            "df = pd.read_csv('data.csv')\n"
            "X = df.drop(columns=['target'])\n"
            "y = df['target']\n"
            "X = StandardScaler().fit_transform(X)  # leak!\n"
            "X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42, shuffle=True)\n"
            "model = RandomForestClassifier(random_state=42)\n"
            "cv = KFold(n_splits=5, shuffle=True, random_state=42)\n"
            "scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')\n",
            encoding="utf-8",
        )
        # 합성 data with leaked feature
        import pandas as pd
        import numpy as np
        np.random.seed(0)
        df = pd.DataFrame({
            "feat1": np.random.randn(500),
            "leak_col": np.random.randint(0, 2, 500),
            "target": np.random.randint(0, 2, 500),
        })
        df["leak_col"] = df["target"]  # perfect leak
        df.to_csv(tmp / "data.csv", index=False)
        # 합성 analysis-cycle
        (tmp / "analysis-cycle.md").write_text(
            "---\nbest_score: 0.9\n---\nbest_features: ['feat1']\n",
            encoding="utf-8",
        )
        # 합성 hypothesis-eda
        (tmp / "hypothesis-eda.md").write_text(
            "excluded_features: ['leak_col']\n",
            encoding="utf-8",
        )

        findings = run_review(
            plan_path=tmp / "plan.md",
            scripts_dir=tmp,
            scratch_dir=tmp,
            data_dir=tmp,
        )
        print(f"[selftest] {len(findings)} findings", file=sys.stderr)
        for f in findings:
            print(f"FINDING|{f['id']}|{f['severity']}|{f['message']}|{f['location']}|{f['evidence']}")
        return 0 if findings else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="방법론 정적 감사 (R2)")
    parser.add_argument("--plan", type=Path, help="docs/plans/<goal>.md 경로")
    parser.add_argument("--scripts-dir", type=Path, default=Path("scripts"), help="scripts/ 디렉토리")
    parser.add_argument("--scratch-dir", type=Path, default=Path("scratch"), help="scratch/ 디렉토리")
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"), help="data/raw/ 디렉토리")
    parser.add_argument("--self-test", action="store_true", help="합성 fixture로 self-test")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if not args.plan:
        # 가장 최근 plan 자동 선택
        plans = sorted(Path("docs/plans").glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not plans:
            print("ERROR: docs/plans/*.md 가 없습니다.", file=sys.stderr)
            return 2
        args.plan = plans[0]

    findings = run_review(args.plan, args.scripts_dir, args.scratch_dir, args.data_dir)
    print(f"[review-methodology] {len(findings)} findings", file=sys.stderr)
    for f in findings:
        print(f"FINDING|{f['id']}|{f['severity']}|{f['message']}|{f['location']}|{f['evidence']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
