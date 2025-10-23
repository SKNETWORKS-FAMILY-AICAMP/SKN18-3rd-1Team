#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import re
import csv


# ✅ Markdown 구조 분석 함수
def parse_markdown_structure(md_text: str):
    """Markdown 문서의 헤더(#) 구조를 분석해 level, title, content 리스트 반환"""
    sections = []
    current = {"level": None, "title": None, "content": ""}
    for line in md_text.splitlines():
        header_match = re.match(r"^(#{1,6})\s*(.+)", line)
        if header_match:
            if current["title"]:
                sections.append(current)
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current = {"level": level, "title": title, "content": ""}
        else:
            current["content"] += line + "\n"
    if current["title"]:
        sections.append(current)
    return sections


# ✅ 필터링 함수
def filter_and_save(md_path: Path, output_dir: Path):
    """단일 파일 필터링 및 CSV 저장"""
    md_text = md_path.read_text(encoding="utf-8")

    # 헤더 누락 공백 보정
    md_text = re.sub(r"^(#{1,6})([^#\s])", r"\1 \2", md_text, flags=re.MULTILINE)

    # 마크다운 구조 파싱
    sections = parse_markdown_structure(md_text)

    # ✅ '제2조'와 '자동차보험의 구성' 모두 포함된 행 찾기
    match_indices = [
        i for i, s in enumerate(sections)
        if s["level"] == 4 and "제2조" in s["title"] and "자동차보험의 구성" in s["title"]
    ]

    if not match_indices:
        print(f"⚠️ {md_path.name}: '제2조 자동차보험의 구성' 행을 찾지 못했습니다.")
        filtered_sections = sections
    else:
        cutoff_index = match_indices[0]
        filtered_sections = sections[cutoff_index:]
        print(f"✂️ {md_path.name}: 기준 인덱스 {cutoff_index} ('제2조 자동차보험의 구성') 이후 데이터만 저장")

    # CSV 자동 저장 (data/preprocessing 폴더)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{md_path.stem}_filtered.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["level", "title", "content"])
        for s in filtered_sections:
            writer.writerow([s.get("level", ""), s.get("title", ""), s.get("content", "")])

    print(f"✅ {md_path.name} → 필터링 완료 ({csv_path})")


# ✅ 실행부
if __name__ == "__main__":
    # 🧭 입력 경로 입력받기
    input_path = input("📂 필터링할 마크다운(.md) 파일 또는 폴더 경로를 입력하세요: ").strip()
    input_dir = Path(input_path)

    # 💾 CSV 결과 자동 저장 폴더 (data/preprocessing)
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "data" / "preprocessing"

    print(f"💾 결과는 자동으로 {output_dir} 에 저장됩니다.\n")

    # 파일 또는 폴더 처리
    if input_dir.is_file() and input_dir.suffix.lower() == ".md":
        print(f"🚀 단일 파일 처리 중: {input_dir.name}")
        filter_and_save(input_dir, output_dir)

    elif input_dir.is_dir():
        md_files = list(input_dir.glob("*.md"))
        if not md_files:
            print("❌ 폴더 내에 마크다운(.md) 파일이 없습니다.")
        else:
            for md_path in md_files:
                print(f"🚀 {md_path.name} 처리 중 ...")
                filter_and_save(md_path, output_dir)
            print(f"✅ 모든 파일 필터링 완료! 결과는 {output_dir} 폴더에 저장되었습니다.")

    else:
        print("❌ 올바른 파일 또는 폴더 경로를 입력해주세요.")
