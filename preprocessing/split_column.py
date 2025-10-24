#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
📘 CSV 칼럼 분리기 (최종 완성형)
- title + content → 조항 / 내용 / 보험사명 / 상품명
- 보험사명은 항상 'DB손해보험'으로 고정
- 상품명은 파일명에서 자동 추출
- 원본 내용(content) 손실 없이 유지
"""

import pandas as pd
from pathlib import Path
import re


def split_csv_columns(csv_path: Path):
    """기존 CSV를 읽어 조항 / 내용 / 보험사명 / 상품명으로 분리"""

    # CSV 읽기
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # ✅ 보험사명 고정
    insurer = "DB손해보험"

    # ✅ 파일명에서 상품명 추출
    # 예시: 2025-09-01_개인용자동차보험약관(공동)_filtered.csv
    filename = csv_path.stem
    match = re.search(r"(\d{4}-\d{2}-\d{2})?[_\-]?(.*?)(약관|보험|상품|filtered)?$", filename)
    if match:
        product_name = match.group(2).strip()
    else:
        product_name = "자동차보험"

    # ✅ title에서 조항명(편·장·절·조) 추출
    def extract_article(title):
        if pd.isna(title):
            return ""
        m = re.search(r"(제\s*\d+\s*(편|장|절|조)[^\s]*)", str(title))
        return m.group(1).strip() if m else title.strip()

    df["조항"] = df["title"].apply(extract_article)
    df["내용"] = df["content"]
    df["보험사명"] = insurer
    df["상품명"] = product_name

    # ✅ 새로운 컬럼 순서로 정리
    new_df = df[["조항", "내용", "보험사명", "상품명"]]

    # ✅ 결과 저장 폴더 자동 생성
    output_dir = csv_path.parent / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{csv_path.stem}_split.csv"

    new_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"✅ 변환 완료 → {output_path}")


# ========================= 💬 실행부 =========================
if __name__ == "__main__":
    input_path = input("📂 분리할 CSV 파일 경로를 입력하세요: ").strip()
    csv_path = Path(input_path)

    if csv_path.exists() and csv_path.suffix.lower() == ".csv":
        split_csv_columns(csv_path)
    else:
        print("❌ 유효한 CSV 파일 경로를 입력해주세요 (.csv 파일이어야 합니다).")
