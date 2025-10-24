#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 보험 약관 PDF → Markdown 변환기 (쪽번호 자동 제거 버전)
"""

import re
from pathlib import Path
import pymupdf4llm  # pip install pymupdf4llm


# ========================= 📚 규칙 =========================
HEADER_RULES = [
    (r"^\s*제\s*\d+\s*편", 1),
    (r"^\s*제\s*\d+\s*장", 2),
    (r"^\s*제\s*\d+\s*절", 3),
    (r"^\s*제\s*\d+\s*조", 4),
    (r"^\s*제\s*\d+\s*항", 5),
    (r"^\s*<별표\s*\d+>", 4),
    (r"^\s*\(붙임\)", 4),
]


# ========================= 🧹 텍스트 정리 =========================
def clean_text(text: str) -> str:
    """쪽번호 및 잡음 제거 포함 텍스트 정리"""
    text = re.sub(r"\r\n|\r", "\n", text)

    # ✅ 쪽번호 제거 (페이지 하단 숫자, '- 12 -', '페이지 12', '12쪽', 'Page 12' 등)
    text = re.sub(
        r"(?mi)^\s*(?:-?\s*)?(?:page\s*)?\d{1,3}\s*(?:쪽|page)?\s*(?:-?\s*)?$",
        "",
        text,
    )
    # ✅ 문장 중간에 남은 잔여 쪽번호 제거
    text = re.sub(r"(\s|-)?\d{1,3}\s*(?:쪽|page)?(?=\s|$)", "", text, flags=re.IGNORECASE)

    # ✅ 점이나 공백 뒤 숫자 형태 쪽번호 제거
    text = re.sub(r"(\.{2,}|\s)\d{1,3}\s*$", "", text, flags=re.MULTILINE)

    # ✅ 단독 숫자 줄 제거
    text = re.sub(r"(?<=\n)\s*\d+\s*(?=\n)", "", text)

    # 🔽 줄바꿈 이어붙이기 (문장 단위로 자연스럽게)
    text = re.sub(
        r"([가-힣A-Za-z0-9])[ \t]*\n[ \t]*(?=[가-힣A-Za-z0-9])",
        r"\1 ",
        text,
    )

    # ✅ 특수문자·불필요 기호 제거
    text = re.sub(r"[□■※○◇◆▶�]", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ========================= ✂️ 목차 구분 =========================
def enforce_heading_breaks(text: str) -> str:
    """목차(제n장, 제n절 등) 앞에 강제 개행"""
    for _ in range(3):
        text = re.sub(
            r"(?<!^)(?<!\n)(?=\s*(제\s*\d+\s*(?:편|장|절|조|항)\b|<별표|\(붙임\)))",
            "\n",
            text,
        )
    return text


# ========================= 📊 표 감지 =========================
def detect_tables(text: str) -> str:
    """공백·탭·| 형태 표를 Markdown 표로 변환"""
    lines, out = text.split("\n"), []
    for line in lines:
        s = line.strip()
        if not s:
            continue

        # 이미 | 기반 표
        if s.startswith("|") and s.endswith("|"):
            out.append(s)
            continue

        # 공백 3칸 이상 → 열 구분
        if re.search(r"\s{3,}", s) and not any(re.match(p, s) for p, _ in HEADER_RULES):
            cols = [c.strip() for c in re.split(r"\s{3,}", s) if c.strip()]
            if len(cols) >= 2:
                s = "| " + " | ".join(cols) + " |"
        out.append(s)
    return "\n".join(out)


# ========================= 🧾 Markdown 변환 =========================
def to_markdown(text: str) -> str:
    """헤더 규칙에 맞게 # 변환"""
    out = []
    for line in text.split("\n"):
        s = line.strip()
        for p, lvl in HEADER_RULES:
            if re.match(p, s):
                s = "#" * lvl + " " + s
                break
        out.append(s)
    return "\n".join(out)


# ========================= 🚀 실행 =========================
def convert(pdf_path: Path):
    """PDF → Markdown 변환"""
    print(f"📄 변환 중: {pdf_path.name}")
    raw = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=False, write_images=False)
    txt = clean_text(raw)
    txt = enforce_heading_breaks(txt)
    txt = detect_tables(txt)
    md = to_markdown(txt)

    outdir = Path(__file__).resolve().parent / "data" / "extracted_md"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{pdf_path.stem}.md").write_text(md, encoding="utf-8")
    print(f"✅ 저장 완료 → {outdir}/{pdf_path.stem}.md\n")


if __name__ == "__main__":
    target = Path(input("📂 PDF 또는 폴더 경로 입력: ").strip())
    if target.is_file() and target.suffix.lower() == ".pdf":
        convert(target)
    else:
        for pdf in target.glob("*.pdf"):
            convert(pdf)
