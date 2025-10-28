"""
현대해상 전용 파서 (수정 버전)
- pymupdf 원본 텍스트 직접 사용
- 편/장/절/조 구조 정확히 파싱
"""

import re
import pymupdf
from typing import List, Dict
from pathlib import Path


class HyundaiParser:
    """현대해상 PDF 파서"""

    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.company_name = "현대"

    def parse(self) -> Dict:
        """PDF 파싱 메인 함수"""
        # PDF에서 텍스트 추출
        doc = pymupdf.open(self.pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        # 보통약관과 특별약관 분리
        botong_text, special_text = self._split_sections(full_text)

        # 각각 파싱
        botong_data = self._parse_with_structure(botong_text, "보통약관")
        special_data = self._parse_with_structure(special_text, "특별약관")

        return {
            'company': self.company_name,
            'botong_yakgwan': botong_data,
            'special_yakgwan': special_data
        }

    def _split_sections(self, text: str) -> tuple:
        """보통약관과 특별약관 분리"""
        # "보통약관" 찾기
        botong_matches = list(re.finditer(r'^보통약관\s*$', text, re.MULTILINE))
        special_matches = list(re.finditer(r'^특별약관\s*$', text, re.MULTILINE))

        # 보통약관 시작점 (목차가 아닌 본문)
        if len(botong_matches) >= 1:
            # 여러 개 있으면 마지막 것이 본문일 가능성이 높음
            botong_start = botong_matches[-1].start()
        else:
            botong_start = 0

        # 특별약관 시작점
        if len(special_matches) >= 1:
            for match in special_matches:
                if match.start() > botong_start:
                    special_start = match.start()
                    break
            else:
                special_start = len(text)
        else:
            special_start = len(text)

        botong_text = text[botong_start:special_start]
        special_text = text[special_start:] if special_start < len(text) else ""

        return botong_text, special_text

    def _parse_with_structure(self, text: str, category: str) -> List[Dict]:
        """편/장/절/조 구조 파싱"""
        lines = text.split('\n')
        entries = []

        # 계층 구조 스택
        current_pyeon = ""
        current_jang = ""
        current_jeol = ""
        current_jo = ""
        current_content = []

        def flush_jo():
            """현재 조를 entries에 추가"""
            nonlocal current_jo, current_content
            if current_jo and current_content:
                hierarchy_parts = [category]
                if current_pyeon:
                    hierarchy_parts.append(current_pyeon)
                if current_jang:
                    hierarchy_parts.append(current_jang)
                if current_jeol:
                    hierarchy_parts.append(current_jeol)
                hierarchy_parts.append(current_jo)

                hierarchy = ">".join(hierarchy_parts)
                content = "\n".join(current_content).strip()

                if content:
                    entries.append({
                        '약관구분': category,
                        '조항': hierarchy,
                        '내용': content
                    })

            current_jo = ""
            current_content = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                continue

            # 페이지 번호 제거 (다양한 형식)
            #  - 단순 숫자: "56", "57"
            #  - 하이픈 형식: "- 26 -"
            #  - p. 형식: "p.64", "p. 67"
            if re.match(r'^\d+$', stripped):  # 단순 숫자
                continue
            if re.match(r'^-\s*\d+\s*-$', stripped):  # - 26 -
                continue
            if re.match(r'^p\.?\s*\d+$', stripped, re.IGNORECASE):  # p.64 또는 P. 67
                continue

            # 목차/헤더 스킵
            if '목차' in stripped or '.....' in stripped:
                continue

            if re.match(r'^(보통약관|특별약관)\s*$', stripped):
                continue

            # 제X편 패턴
            pyeon_match = re.match(r'^제\s*(\d+)\s*편\s*(.*)$', stripped)
            if pyeon_match:
                flush_jo()
                pyeon_title = pyeon_match.group(2).strip()
                current_pyeon = f"제{pyeon_match.group(1)}편({pyeon_title})" if pyeon_title else f"제{pyeon_match.group(1)}편"
                current_jang = ""
                current_jeol = ""
                continue

            # 제X장 패턴
            jang_match = re.match(r'^제\s*(\d+)\s*장\s*(.*)$', stripped)
            if jang_match:
                flush_jo()
                jang_title = jang_match.group(2).strip()
                current_jang = f"제{jang_match.group(1)}장({jang_title})" if jang_title else f"제{jang_match.group(1)}장"
                current_jeol = ""
                continue

            # 제X절 패턴
            jeol_match = re.match(r'^제\s*(\d+)\s*절\s*(.*)$', stripped)
            if jeol_match:
                flush_jo()
                jeol_title = jeol_match.group(2).strip()
                current_jeol = f"제{jeol_match.group(1)}절({jeol_title})" if jeol_title else f"제{jeol_match.group(1)}절"
                continue

            # 제X조 패턴
            jo_match = re.match(r'^(제\s*\d+\s*조(?:의\s*\d+)?\s*(?:\([^\)]+\))?)', stripped)
            if jo_match:
                flush_jo()
                current_jo = jo_match.group(1).strip()
                rest = stripped[jo_match.end():].strip()
                if rest:
                    current_content.append(rest)
                continue

            # 현재 조의 내용 추가
            if current_jo:
                current_content.append(stripped)

        # 마지막 조 처리
        flush_jo()

        return entries


# 테스트 코드
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = 'dataset/현대/현대_개인용자동차보험.pdf'

    parser = HyundaiParser(pdf_path)
    result = parser.parse()

    print(f"회사: {result['company']}")
    print(f"보통약관: {len(result['botong_yakgwan'])}개")
    print(f"특별약관: {len(result['special_yakgwan'])}개")

    print("\n보통약관 샘플 (처음 5개):")
    for i, item in enumerate(result['botong_yakgwan'][:5], 1):
        print(f"\n{i}. 조항: {item['조항']}")
        print(f"   내용: {item['내용'][:100]}...")

    print("\n특별약관 샘플 (처음 5개):")
    for i, item in enumerate(result['special_yakgwan'][:5], 1):
        print(f"\n{i}. 조항: {item['조항']}")
        print(f"   내용: {item['내용'][:100]}...")
