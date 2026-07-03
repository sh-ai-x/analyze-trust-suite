#!/usr/bin/env python3
"""
toy_classification fixture — review-report N1/N5 트리거용 합성 노트북 + CSV.

생성:
  /tmp/toy_classification.csv (500행, 누수 피처 포함)
  /tmp/toy_classification.ipynb (의도적 N5 위반 MD 포함)
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main(out_dir: Path = Path("/tmp")) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(0)

    # CSV with leaked feature
    n = 500
    df = pd.DataFrame({
        "feat1": np.random.randn(n),
        "feat2": np.random.randn(n),
        "feat3": np.random.randn(n),
        "leak_col": np.random.randint(0, 2, n),
    })
    df["target"] = (df["feat1"] + 0.4 * df["feat2"] > 0).astype(int)
    df["leak_col"] = df["target"]  # perfect leak
    csv_path = out_dir / "toy_classification.csv"
    df.to_csv(csv_path, index=False)
    print(f"[fixture] CSV saved: {csv_path} ({df.shape})")

    # 의도적 N5 위반 MD 포함 노트북
    nb = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": [
                    "# 합성 분류 분석\n",
                    "## 데이터 개요\n",
                    "500행, 4 피처 + 1 타깃.\n",
                    "## EDA Pass 1\n",
                    "결측치 없음.\n",
                    "## 모델링\n",
                    "RandomForestClassifier 사용.\n",
                    "## 검증\n",
                    "검증 결과 점수는 약 0.999 였음 (의도적 추측 — stdout 출처 없음)\n",
                    "## 결론\n",
                    "AUC-ROC 가 0.99 로 매우 높게 향상됨. 본 분석은 합성 데이터로 약 0.999 의 AUC 를 달성했다.\n",
                ],
                "metadata": {},
            },
            {
                "cell_type": "code",
                "source": ["import pandas as pd\n", "df = pd.read_csv('toy_classification.csv')\n", "print('Shape:', df.shape)\n"],
                "metadata": {},
                "outputs": [{"output_type": "stream", "text": ["Shape: (500, 5)\n"]}],
                "execution_count": 1,
            },
            {
                "cell_type": "code",
                "source": ["print('AUC-ROC: 0.9823')\n"],
                "metadata": {},
                "outputs": [{"output_type": "stream", "text": ["AUC-ROC: 0.9823\n"]}],
                "execution_count": 2,
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    nb_path = out_dir / "toy_classification.ipynb"
    nb_path.write_text(json.dumps(nb), encoding="utf-8")
    print(f"[fixture] notebook saved: {nb_path}")

    # scratch 파일 (R2/R3/R4 prereq)
    scratch_dir = out_dir / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    (scratch_dir / "env.md").write_text(
        "---\nexecution_env: local\ndata_path: /tmp/\n---\n",
        encoding="utf-8",
    )
    (scratch_dir / "analysis-cycle.md").write_text(
        "---\nbest_hypothesis: H1\nbest_score: 0.98\n---\nbest_features: ['feat1', 'feat2']\nbest_model: RandomForest\n",
        encoding="utf-8",
    )
    (scratch_dir / "hypothesis-eda.md").write_text(
        "top_hypotheses: [H1]\nexcluded_features: ['leak_col']\n",
        encoding="utf-8",
    )
    print(f"[fixture] scratch saved: {scratch_dir}")

    # docs/plans
    plans_dir = out_dir / "docs" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    (plans_dir / "toy.md").write_text(
        "# toy\n> Status: approved\n- goal: smoke\n- analysis_type: classification\n- target_variable: target\n- success_metric: AUC-ROC\n",
        encoding="utf-8",
    )
    print(f"[fixture] plan saved: {plans_dir / 'toy.md'}")

    # scripts/train.py (R2 prereq)
    scripts_dir = out_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "train.py").write_text(
        "import pandas as pd\n"
        "from sklearn.model_selection import cross_val_score, StratifiedKFold\n"
        "from sklearn.ensemble import RandomForestClassifier\n"
        "import platform, matplotlib.pyplot as plt\n"
        "plt.rcParams['font.family'] = 'AppleGothic' if platform.system() == 'Darwin' else 'NanumGothic'\n"
        "plt.rcParams['axes.unicode_minus'] = False\n"
        "\n"
        "df = pd.read_csv('toy_classification.csv')\n"
        "X = df.drop(columns=['target'])\n"
        "y = df['target']\n"
        "model = RandomForestClassifier(random_state=42, n_estimators=100)\n"
        "cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)\n"
        "scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')\n"
        "print('AUC-ROC:', scores.mean())\n",
        encoding="utf-8",
    )
    print(f"[fixture] train.py saved: {scripts_dir / 'train.py'}")

    print("\n[usage]")
    print(f"  python3 scripts/review/report.py --self-test")
    print(f"  python3 scripts/review/methodology.py --plan {plans_dir}/toy.md --scripts-dir {scripts_dir} --scratch-dir {scratch_dir} --data-dir {out_dir}")
    print(f"  python3 scripts/review/statistical.py --plan {plans_dir}/toy.md --scratch-dir {scratch_dir} --data-dir {out_dir}")
    print(f"  python3 scripts/review/robustness.py --plan {plans_dir}/toy.md --scratch-dir {scratch_dir} --data-dir {out_dir}")
    return 0


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp")
    sys.exit(main(out))
