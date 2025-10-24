#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 스마트 PDF 추출기 - 파일별 맞춤 정규식 적용
──────────────────────────────────────────────
- 파일명 기반 자동 패턴 선택 
- 각 보험사/상품별 최적화된 정규식 적용 
- PyMuPDF4LLM으로 PDF → 텍스트 추출
- 맞춤 패턴으로 구조화된 CSV 생성 (Markdown 계층 포함)
"""

import re
import logging
import pandas as pd
from pathlib import Path
from file_patterns import get_patterns_by_filename, detect_content_start, should_skip_line

# ==========================================================
# 0️⃣ PyMuPDF4LLM import
# ==========================================================
try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False
    print("⚠️ PyMuPDF4LLM 설치 필요: pip install pymupdf4llm")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================================================
# 1️⃣ PDF 텍스트 추출
# ==========================================================
def extract_pdf(pdf_path: Path):
    """PDF → 텍스트 추출"""
    if not PYMUPDF4LLM_AVAILABLE:
        raise ImportError("PyMuPDF4LLM이 설치되지 않았습니다.")

    try:
        content = pymupdf4llm.to_markdown(
            str(pdf_path),
            page_chunks=False,
            write_images=False,
            embed_images=False
        )
    except Exception as e:
        print(f"⚠️ PyMuPDF4LLM 실패: {e} → 기본 PyMuPDF로 재시도")
        import fitz
        doc = fitz.open(pdf_path)
        content = "\n".join([page.get_text("text") for page in doc])

    if content:
        content = re.sub(r"[�\x01]", " ", content)
        content = re.sub(r"<br\s*/?>", "", content)
        # 🔥 추가: BEL 및 도형 문자 제거
        content = re.sub(r"\bBEL\b", " ", content, flags=re.IGNORECASE)
        content = re.sub(r"[\u25A0-\u25FF\u2190-\u21FF]+", " ", content)

    return content.strip() if content else None


# ==========================================================
# 2️⃣ 전처리
# ==========================================================
def smart_preprocess_text(text: str, patterns: dict) -> str:
    """패턴 기반 전처리"""
    lines = text.splitlines()
    cleaned = []
    start_idx = detect_content_start(text, patterns)

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if i < start_idx:
            continue
        if should_skip_line(line, patterns):
            continue
        if re.match(r"^\s*-?\s*\d+\s*-?\s*$", line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

# ==========================================================
# 3️⃣ 구조 파싱 (Markdown 계층 포함)
# ==========================================================
def smart_parse_structure(text: str, patterns: dict):
    data = []
    part = chapter = section = article = None
    content_lines = []

    is_carrot = "캐롯" in patterns.get("name", "")
    start_saving = not is_carrot  # 캐롯은 제1편 제2조부터

    def save_block():
        nonlocal content_lines
        if start_saving and content_lines:
            content = "\n".join(content_lines).strip()
            if content and len(content) > 5:
                # ✅ 계층 제목은 content에 넣지 않고, 별도 컬럼으로만 관리
                data.append({
                    "part": part or "",
                    "chapter": chapter or "",
                    "section": section or "",
                    "article": article or "",
                    "content": content    # ← Markdown 제목 없이 본문만 저장
                })
        content_lines = []

    def clean_title(s):
        s = re.sub(r"\s*-\s*·*$", "", s)
        s = re.sub(r"·+$", "", s)
        return s.strip()

    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # === 별표 구역 ===
        if re.match(patterns["appendix_title"], line):
            save_block()
            part = clean_title(line)
            chapter = section = article = None
            continue
        elif re.match(patterns["appendix_item"], line):
            save_block()
            m = re.match(r"\[별표\s*(\d+)\]\s*(.+)?", line)
            if m:
                num, title = m.groups()
                part = f"별표{num}. {title.strip() if title else ''}"
            else:
                part = clean_title(line)
            chapter = section = article = None
            continue

        # === 편/장/절/조 인식 ===
        if re.match(patterns["part"], line):
            save_block()
            part = clean_title(line)
            chapter = section = article = None
            print(f"🔍 Part 인식: {part}")
            if is_carrot and re.search(r"제\s*1\s*편", part):
                start_saving = False
            continue

        if re.match(patterns["chapter"], line):
            save_block()
            chapter = clean_title(line)
            section = article = None
            print(f"🔍 Chapter 인식: {chapter}")
            continue

        if re.match(patterns["section"], line):
            save_block()
            section = clean_title(line)
            article = None
            print(f"🔍 Section 인식: {section}")
            continue

        if re.match(patterns["article"], line):
            save_block()
            article = clean_title(line)
            print(f"🔍 Article 인식: {article}")

            # 🔧 캐롯 전용 저장 시작 조건
            if is_carrot and not start_saving:
                if re.search(r"제\s*1\s*편", part or "") and re.search(r"제\s*2\s*조", article or ""):
                    print("🚀 [캐롯] 제1편 제2조부터 저장 시작")
                    start_saving = True
            continue

        # === 내용 누적 ===
        if start_saving:
            if not re.match(r"^\s*\d+\s*$", line) and not re.search(r"·{5,}", line):
                content_lines.append(line)

    save_block()
    return data


# ==========================================================
# 4️⃣ 필터링 및 CSV 저장
# ==========================================================
def filter_and_save(parsed, output_path: Path, apply_filter=True, pdf_path: Path = None):
    if apply_filter:
        filtered = []
        exclude_keywords = [
            "확인필", "인가", "승인", "신고", "금융감독원",
            "보험소비자", "권익 보호", "금융소비자 보호에 관한 법률",
            "내부통제 절차", "작성한 자료",
            "고객센터", "홈페이지", "www.", "http",
            "가이드북", "안내서", "설명서"
        ]
        for item in parsed:
            c = item["content"]
            if any(k in c for k in exclude_keywords):
                continue
            if len(c.strip()) < 10:
                continue
            if c.strip().isdigit():
                continue
            filtered.append(item)
        print(f"📊 필터링 결과: {len(parsed)} → {len(filtered)} 항목")
        parsed = filtered

    if not parsed:
        pd.DataFrame(columns=["조항(편 장 절 조)", "내용", "보험사명", "상품명"]).to_csv(
            output_path, index=False, encoding="utf-8-sig", quoting=1
        )
        print("⚠️ 추출된 데이터가 없어 빈 CSV 파일을 생성했습니다.")
        return 0

    # ✅ 정렬 키 생성
    def extract_num(s, pattern):
        m = re.search(pattern, s or "")
        return int(m.group(1)) if m else 999

    def sort_key(item):
        return (
            extract_num(item.get("part"), r"제\s*(\d+)\s*편"),
            extract_num(item.get("chapter"), r"제\s*(\d+)\s*장"),
            extract_num(item.get("section"), r"제\s*(\d+)\s*절"),
            extract_num(item.get("article"), r"제\s*(\d+)\s*조"),
        )

    parsed.sort(key=sort_key)

    # ✅ 보험사명 / 상품명 자동 추출
    if pdf_path:
        company_name = pdf_path.parent.name        # 바로 위 폴더명
        product_name = pdf_path.stem               # 파일명 (확장자 제외)
    else:
        company_name = ""
        product_name = ""

    # ✅ 조항 통합 및 새로운 구조 생성
    rows = []
    for item in parsed:
        parts = [item.get("part"), item.get("chapter"), item.get("section"), item.get("article")]
        clause = " ".join([p for p in parts if p]).strip()

        rows.append({
            "조항(편 장 절 조)": clause,
            "내용": item.get("content", "").strip(),
            "보험사명": company_name,
            "상품명": product_name
        })

    # ✅ CSV 저장
    df = pd.DataFrame(rows, columns=["조항(편 장 절 조)", "내용", "보험사명", "상품명"])
    df.to_csv(output_path, index=False, encoding="utf-8-sig", quoting=1)
    print(f"💾 CSV 저장 완료: {output_path.name} ({len(df)}행)")
    return len(df)


# ==========================================================
# 5️⃣ 단일 PDF 처리
# ==========================================================
def smart_process_pdf(pdf_path: Path, apply_filter=True):
    logger.info(f"📄 스마트 PDF 처리 시작: {pdf_path.name}")
    patterns = get_patterns_by_filename(pdf_path.name)
    print(f"🎯 선택된 패턴: {patterns['name']}")

    # 1️⃣ PDF → 텍스트 추출
    text = extract_pdf(pdf_path)
    if not text:
        logger.warning(f"⚠️ 텍스트 추출 실패: {pdf_path.name}")
        return None

    # 2️⃣ 🔥 원본 텍스트 저장 (.txt)
    txt_path = pdf_path.parent / f"{pdf_path.stem}_raw.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"💾 원문 텍스트 저장 완료: {txt_path.name}")

    # 3️⃣ 전처리 → 파싱 → CSV 저장
    cleaned = smart_preprocess_text(text, patterns)
    parsed = smart_parse_structure(cleaned, patterns)
    original_count = len(parsed)
    out_path = pdf_path.parent / f"{pdf_path.stem}_smart.csv"

    # ✅ 여기 수정 포인트
    filtered_count = filter_and_save(parsed, out_path, apply_filter, pdf_path)

    logger.info(f"✅ 완료: {pdf_path.name}")
    return {
        "filename": pdf_path.name,
        "pattern_type": patterns["name"],
        "original_count": original_count,
        "filtered_count": filtered_count,
        "status": "성공"
    }



# ==========================================================
# 6️⃣ 폴더 전체 처리
# ==========================================================
def smart_process_folder(folder_path: str, apply_filter=True):
    folder = Path(folder_path)
    pdfs = list(folder.glob("*.pdf"))
    if not pdfs:
        print("⚠️ PDF 파일이 없습니다.")
        return

    print(f"📂 총 {len(pdfs)}개 PDF 처리 시작...")
    results = []

    for i, pdf in enumerate(pdfs, 1):
        print(f"\n({i}/{len(pdfs)}) ▶ {pdf.name}")
        try:
            r = smart_process_pdf(pdf, apply_filter)
            if r:
                results.append(r)
            else:
                results.append({
                    "filename": pdf.name,
                    "status": "실패",
                    "original_count": 0,
                    "filtered_count": 0
                })
        except Exception as e:
            logger.error(f"❌ {pdf.name} 처리 실패: {e}")
            results.append({
                "filename": pdf.name,
                "status": f"오류: {str(e)}",
                "original_count": 0,
                "filtered_count": 0
            })

    print_smart_summary(results, apply_filter)


# ==========================================================
# 7️⃣ 결과 요약
# ==========================================================
def print_smart_summary(results, apply_filter):
    print("\n" + "="*90)
    print("📊 스마트 PDF 처리 결과 요약")
    print("="*90)
    ok = [r for r in results if r["status"] == "성공"]
    print(f"📁 총 처리 파일: {len(results)}개")
    print(f"✅ 성공: {len(ok)}개")
    print(f"❌ 실패: {len(results)-len(ok)}개")
    total_orig = sum(r["original_count"] for r in ok)
    total_filt = sum(r["filtered_count"] for r in ok)
    print(f"📄 총 추출 항목: {total_orig}")
    if apply_filter:
        print(f"🔍 필터링 후: {total_filt}")
        print(f"🗑️ 제거된 항목: {total_orig-total_filt}")
    print("="*90)

# ==========================================================
# 8️⃣ 실행부
# ==========================================================
if __name__ == "__main__":
    print("📘 스마트 PDF 추출기 - 파일별 맞춤 정규식 적용")
    print("=" * 70)
    mode = input("1️⃣ 단일 PDF / 2️⃣ 폴더 전체 변환 (1/2): ").strip()
    use_filter = input("약관 외 내용 필터링 적용? (Y/n): ").strip().lower() != "n"

    if mode == "1":
        path = Path(input("PDF 경로를 입력하세요: ").strip())
        res = smart_process_pdf(path, use_filter)
        if res:
            print_smart_summary([res], use_filter)
    elif mode == "2":
        folder = input("PDF 폴더 경로를 입력하세요: ").strip()
        smart_process_folder(folder, use_filter)
    else:
        print("종료합니다.")
