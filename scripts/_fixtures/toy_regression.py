#!/usr/bin/env python3
"""
toy_regression fixture — 회귀 버전. 누수 피처 + 약한 신호.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def main(out_dir: Path = Path("/tmp")) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(0)

    n = 500
    df = pd.DataFrame({
        "feat1": np.random.randn(n),
        "feat2": np.random.randn(n),
        "noise": np.random.randn(n),
    })
    # 강한 신호 + 약한 노이즈
    df["target"] = 2.0 * df["feat1"] + 0.5 * df["feat2"] + 0.1 * df["noise"]
    # 누수 피처 (target의 함수)
    df["leak_col"] = df["target"] + np.random.randn(n) * 0.001
    csv_path = out_dir / "toy_regression.csv"
    df.to_csv(csv_path, index=False)
    print(f"[fixture] CSV saved: {csv_path} ({df.shape})")
    return 0


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp")
    sys.exit(main(out))
