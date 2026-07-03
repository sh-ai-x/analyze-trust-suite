#!/usr/bin/env python3
"""
review-report — 노트북 자기-일관성 정적 분석 (R1)

docs/reports/*.ipynb 를 재실행 없이 파싱해서:
  N1: MD 셀이 인용한 숫자가 실제 Code 셀 출력에 존재
  N2: 동일 메트릭이 다른 MD 셀에서 다른 값으로 인용
  N3: 결론 MD 셀이 데이터 trend와 모순
  N4: 필수 섹션 누락
  N5: MD 셀이 stdout 출처 없는 추측 수치 사용
  N6: 비어있는 Code 셀 출력
  N7: 다른 분석 도메인 잔재 (간단 휴리스틱)
  N8: 시각화 파일 참조가 실제 파일시스템에 존재

stdout 출력 형식 (한 줄 = 한 finding):
  FINDING|<id>|<severity>|<message>|<location>
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def parse_notebook(path: Path) -> list[dict]:
    """nbformat 없이 .ipynb JSON 직접 파싱 (의존성 최소화)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    cells = []
    for i, c in enumerate(raw.get("cells", [])):
        cells.append({
            "index": i,
            "type": c.get("cell_type", ""),
            "source": "".join(c.get("source", [])) if isinstance(c.get("source"), list) else str(c.get("source", "")),
            "outputs": c.get("outputs", []) if c.get("cell_type") == "code" else [],
        })
    return cells


def extract_numbers(text: str) -> list[tuple[str, str]]:
    """텍스트에서 (맥락, 숫자문자열) 쌍 추출. AUC-ROC 같은 메트릭과 짝지을 수 있게."""
    pattern = r"([A-Za-z가-힣\-\s_]*?)(0\.\d{2,4}|1\.000|0\.0000?)"
    matches = re.findall(pattern, text)
    return [(ctx.strip(), num) for ctx, num in matches]


def cell_outputs_text(outputs: list[dict]) -> str:
    """code cell outputs 를 하나의 텍스트로 결합."""
    parts = []
    for o in outputs:
        if "text" in o:
            parts.append("".join(o["text"]) if isinstance(o["text"], list) else str(o["text"]))
        elif "data" in o:
            data = o["data"]
            if "text/plain" in data:
                parts.append("".join(data["text/plain"]) if isinstance(data["text/plain"], list) else str(data["text/plain"]))
        if "printout" in o:
            parts.append(str(o["printout"]))
    return "\n".join(parts)


def check_N1_md_numbers_in_outputs(cells: list[dict]) -> list[dict]:
    """N1: MD 셀이 인용한 숫자가 실제 Code 셀 출력에 존재하는지."""
    findings = []
    # 모든 code cell 출력 텍스트를 하나로 결합
    code_outputs_combined = "\n".join(cell_outputs_text(c["outputs"]) for c in cells if c["type"] == "code")

    for c in cells:
        if c["type"] != "markdown":
            continue
        for ctx, num in extract_numbers(c["source"]):
            # 너무 일반적인 숫자 (0.000, 1.000) 는 스킵
            if num in ("0.000", "1.000") and not ctx:
                continue
            # metric-like 컨텍스트가 있을 때만 검사 (e.g., "AUC-ROC 0.85")
            if not ctx:
                continue
            # code 출력에 해당 숫자가 있는지
            if num not in code_outputs_combined:
                findings.append({
                    "id": "N1",
                    "severity": "warn",
                    "message": f"MD 셀 인용 수치 '{num}' (맥락: '{ctx[:30]}') 가 code 출력에 없음",
                    "location": f"cell[{c['index']}] (markdown)",
                    "evidence": f"ctx={ctx!r}, num={num}",
                })
    return findings


def check_N2_metric_inconsistency(cells: list[dict]) -> list[dict]:
    """N2: 동일 메트릭 (e.g., 'AUC-ROC') 이 다른 MD 셀에서 다른 값으로 인용."""
    findings = []
    # 메트릭별 인용값 수집
    metric_values: dict[str, list[tuple[str, float, int]]] = defaultdict(list)
    metric_pattern = r"(AUC[\-\s]?ROC|F1|RMSE|MAE|Accuracy|AUC|R²|R2)[^\d]{0,5}(0\.\d{2,4}|1\.000)"

    for c in cells:
        if c["type"] != "markdown":
            continue
        for metric, value in re.findall(metric_pattern, c["source"]):
            metric_key = metric.upper().replace(" ", "").replace("-", "")
            try:
                v = float(value)
                metric_values[metric_key].append((c["source"][:60].strip(), v, c["index"]))
            except ValueError:
                pass

    # 동일 메트릭이 다른 값으로 2회 이상 인용되면 block
    for metric, occurrences in metric_values.items():
        unique_vals = set(v for _, v, _ in occurrences)
        if len(unique_vals) > 1:
            occurrences_str = ", ".join(f"cell[{i}]={v}" for _, v, i in occurrences)
            findings.append({
                "id": "N2",
                "severity": "block",
                "message": f"메트릭 '{metric}' 이(가) {len(unique_vals)} 개의 다른 값으로 인용됨: {sorted(unique_vals)}",
                "location": occurrences_str,
                "evidence": occurrences_str,
            })
    return findings


def check_N3_contradiction(cells: list[dict]) -> list[dict]:
    """N3: 결론 MD 셀이 데이터 trend와 모순."""
    findings = []
    positive_keywords = ["향상", "개선", "높", "좋", "증가", "상향", "improved", "increased", "better", "higher"]
    negative_keywords = ["하향", "감소", "낮", "악화", "떨", "worse", "lower", "decreased", "worsen"]

    for c in cells:
        if c["type"] != "markdown":
            continue
        text = c["source"]
        # 결론성 문단 (마지막 markdown 셀, 200자 이상)
        if len(text) < 100:
            continue
        if "결론" not in text and "Conclusion" not in text and "conclusion" not in text:
            continue
        has_pos = any(kw in text for kw in positive_keywords)
        has_neg = any(kw in text for kw in negative_keywords)
        if has_pos and has_neg:
            findings.append({
                "id": "N3",
                "severity": "warn",
                "message": "결론 셀에 긍정/부정 키워드가 혼재 (모순 가능성)",
                "location": f"cell[{c['index']}] (markdown)",
                "evidence": text[:80] + "...",
            })
    return findings


def check_N4_missing_sections(cells: list[dict]) -> list[dict]:
    """N4: 필수 섹션 누락."""
    findings = []
    required = {
        "데이터": ["데이터 개요", "Data Overview", "Dataset", "데이터셋"],
        "EDA": ["EDA", "탐색", "Pass 1", "Pass 2", "Pass1", "Pass2"],
        "모델": ["모델", "Modeling", "Model", "Training", "학습"],
        "검증": ["검증", "Verification", "Verify", "Validation"],
        "결론": ["결론", "Conclusion", "Summary"],
    }
    all_md = "\n".join(c["source"] for c in cells if c["type"] == "markdown")
    found = set()
    for category, kws in required.items():
        if any(kw in all_md for kw in kws):
            found.add(category)
    missing = set(required.keys()) - found
    if missing:
        findings.append({
            "id": "N4",
            "severity": "warn",
            "message": f"필수 섹션 누락: {sorted(missing)}",
            "location": "notebook 전체",
            "evidence": f"missing={sorted(missing)}",
        })
    return findings


def check_N5_unsupported_numbers(cells: list[dict]) -> list[dict]:
    """N5: MD 셀이 stdout 출처 없는 추측 수치를 사용하는지 (마커 패턴)."""
    findings = []
    unsupported_markers = ["약", "大概", "roughly", "大概", "정도", "쯤", "대략", "≈", "approximately", "估计"]
    code_outputs_combined = "\n".join(cell_outputs_text(c["outputs"]) for c in cells if c["type"] == "code")

    for c in cells:
        if c["type"] != "markdown":
            continue
        text = c["source"]
        for marker in unsupported_markers:
            if marker not in text:
                continue
            # 마커 주변에 숫자가 있고, 그 숫자가 code 출력에 없으면 의심
            idx = text.find(marker)
            nearby = text[max(0, idx - 30):idx + 50]
            nums = re.findall(r"0\.\d{2,4}", nearby)
            for n in nums:
                if n not in code_outputs_combined:
                    findings.append({
                        "id": "N5",
                        "severity": "block",
                        "message": f"추측 마커 '{marker}' 주변에 stdout 출처 없는 수치 '{n}'",
                        "location": f"cell[{c['index']}] (markdown)",
                        "evidence": f"marker={marker}, num={n}, context={nearby!r}",
                    })
    return findings


def check_N6_empty_outputs(cells: list[dict]) -> list[dict]:
    """N6: 비어있는 Code 셀 출력 (실행 실패 흔적)."""
    findings = []
    for c in cells:
        if c["type"] != "code":
            continue
        if not c["outputs"]:
            continue
        out_text = cell_outputs_text(c["outputs"]).strip()
        if not out_text:
            findings.append({
                "id": "N6",
                "severity": "block",
                "message": "Code cell 출력이 비어있음 (실행 실패 또는 silent error 가능성)",
                "location": f"cell[{c['index']}] (code)",
                "evidence": "outputs.length=0 또는 빈 텍스트",
            })
    return findings


def check_N7_domain_residue(cells: list[dict]) -> list[dict]:
    """N7: 다른 분석 도메인 잔재 (간단 휴리스틱 - 키워드 중복)."""
    findings = []
    # 흔한 도메인 키워드들
    domain_keywords = {
        "titanic": ["titanic", "타이타닉"],
        "house_price": ["house", "집값", "주택", "real estate"],
        "iris": ["iris", "붓꽃"],
        "mnist": ["mnist", "손글씨"],
        "imdb": ["imdb", "영화리뷰"],
    }
    counts = defaultdict(int)
    for c in cells:
        if c["type"] != "markdown":
            continue
        text_lower = c["source"].lower()
        for domain, kws in domain_keywords.items():
            if any(kw.lower() in text_lower for kw in kws):
                counts[domain] += 1

    # 가장 많이 등장한 도메인이 1개면 정상. 2개 이상 등장 시 잔재 가능성
    active = {d: n for d, n in counts.items() if n > 0}
    if len(active) >= 2:
        findings.append({
            "id": "N7",
            "severity": "warn",
            "message": f"여러 도메인 키워드가 혼재: {active}",
            "location": "notebook 전체",
            "evidence": json.dumps(active),
        })
    return findings


def check_N8_image_references(cells: list[dict]) -> list[dict]:
    """N8: MD 셀에서 참조하는 이미지 파일이 실제 파일시스템에 존재하는지."""
    findings = []
    img_pattern = r"!\[.*?\]\(([^)]+\.(?:png|jpg|jpeg|gif|svg))\)"
    cwd = Path.cwd()

    for c in cells:
        if c["type"] != "markdown":
            continue
        for img_path in re.findall(img_pattern, c["source"]):
            resolved = cwd / img_path
            if not resolved.exists():
                findings.append({
                    "id": "N8",
                    "severity": "warn",
                    "message": f"이미지 참조 '{img_path}' 가 파일시스템에 없음",
                    "location": f"cell[{c['index']}] (markdown)",
                    "evidence": f"checked={resolved}",
                })
    return findings


def run_review(notebook_path: Path) -> list[dict]:
    """전체 리뷰 실행."""
    cells = parse_notebook(notebook_path)
    findings = []
    findings += check_N1_md_numbers_in_outputs(cells)
    findings += check_N2_metric_inconsistency(cells)
    findings += check_N3_contradiction(cells)
    findings += check_N4_missing_sections(cells)
    findings += check_N5_unsupported_numbers(cells)
    findings += check_N6_empty_outputs(cells)
    findings += check_N7_domain_residue(cells)
    findings += check_N8_image_references(cells)
    return findings


def self_test() -> int:
    """합성 노트북으로 self-test."""
    tmp = Path("/tmp/_review_report_selftest.ipynb")
    nb = {
        "cells": [
            {
                "cell_type": "markdown",
                "source": ["# 테스트 노트북\n", "## 데이터 개요\n", "## EDA Pass 1\n"],
                "metadata": {},
            },
            {
                "cell_type": "code",
                "source": ["print('AUC-ROC: 0.8523')"],
                "metadata": {},
                "outputs": [{"output_type": "stream", "text": ["AUC-ROC: 0.8523\n"]}],
                "execution_count": 1,
            },
            {
                "cell_type": "markdown",
                "source": ["## 결론\n", "AUC-ROC 가 0.85 로 향상됨"],
                "metadata": {},
            },
            # N1 트리거: stdout에 없는 숫자 인용
            {
                "cell_type": "markdown",
                "source": ["## 검증\n", "검증 결과 점수는 약 0.999 였음"],
                "metadata": {},
            },
            # N6 트리거: 빈 output
            {
                "cell_type": "code",
                "source": ["x = 1"],
                "metadata": {},
                "outputs": [],
                "execution_count": 2,
            },
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    tmp.write_text(json.dumps(nb), encoding="utf-8")
    findings = run_review(tmp)
    print(f"[selftest] {len(findings)} findings", file=sys.stderr)
    for f in findings:
        print(f"FINDING|{f['id']}|{f['severity']}|{f['message']}|{f['location']}")
    tmp.unlink()
    return 0 if findings else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="노트북 자기-일관성 정적 분석 (R1)")
    parser.add_argument("notebook", nargs="?", help="검토할 .ipynb 경로")
    parser.add_argument("--self-test", action="store_true", help="합성 노트북으로 self-test")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if not args.notebook:
        # 기본: 가장 최근 docs/reports/*.ipynb
        candidates = sorted(Path("docs/reports").glob("*.ipynb"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            print("ERROR: docs/reports/*.ipynb 가 없습니다.", file=sys.stderr)
            return 2
        args.notebook = str(candidates[0])

    nb_path = Path(args.notebook)
    if not nb_path.exists():
        print(f"ERROR: 노트북 파일 없음: {nb_path}", file=sys.stderr)
        return 2

    findings = run_review(nb_path)
    print(f"[review-report] {nb_path}: {len(findings)} findings", file=sys.stderr)
    for f in findings:
        print(f"FINDING|{f['id']}|{f['severity']}|{f['message']}|{f['location']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
