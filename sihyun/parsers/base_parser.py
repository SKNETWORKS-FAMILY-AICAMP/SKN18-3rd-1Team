"""
기본 파서 추상 클래스
모든 보험사 파서가 상속받아 구현
"""

from abc import ABC, abstractmethod
import pymupdf4llm
import pymupdf  # PyMuPDF 직접 사용 (일부 PDF는 pymupdf4llm이 페이지 누락)
import re
from pathlib import Path

# 마크다운 전처리 함수 (inline으로 정의)
def _preprocess_markdown(md_text: str) -> str:
    """
    마크다운 텍스트 전처리
    1. 표 형식 제거 (내용은 유지)
    2. 세로 목차(┃ 구분) 제거
    3. 세로 출력(한 줄에 한 글자) 제거
    """
    lines = md_text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # 세로 목차 라인 제거 (┃ 포함)
        if '┃' in line:
            continue
        
        # 한 줄에 한 글자만 있는 경우 제거 (세로 출력)
        stripped = line.strip()
        if len(stripped) == 1 and stripped.isalpha():
            continue
        
        # 표 구분선 제거 (|---|---|--- 형태)
        if re.match(r'^\s*\|[\s\-:]+\|\s*$', line):
            continue
        
        # 표 형식 라인 처리
        if '|' in line and not line.strip().startswith('#'):
            # 표 형식 제거하고 내용만 추출
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]

            if cells:
                # 의미있는 내용만 필터링 (Col1, Col2 등 제외)
                meaningful_cells = [
                    cell for cell in cells
                    if cell and not re.match(r'^Col\d+$', cell)
                ]

                if meaningful_cells:
                    # 각 셀을 개별 라인으로 추가 (중복돼도 OK, 다른 내용일 수 있음)
                    for cell in meaningful_cells:
                        if cell:
                            cleaned_lines.append(cell)
            continue
        
        # 일반 라인은 그대로 추가
        cleaned_lines.append(line)
    
    # 연속된 빈 줄을 하나로 압축
    result = '\n'.join(cleaned_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # p.XX 형태 제거 (목차 마커)
    result = re.sub(r'p\.\s*\d+', '', result)

    # HTML 태그 제거 (<br>, <br/>, <br />, 기타 태그)
    result = re.sub(r'<br\s*/?\s*>', ' ', result)  # <br> 태그를 공백으로
    result = re.sub(r'<[^>]+>', '', result)  # 기타 HTML 태그 제거

    return result


class BaseParser(ABC):
    """보험사 PDF 파서 기본 클래스"""

    def __init__(self, pdf_path):
        """
        Args:
            pdf_path: PDF 파일 경로
        """
        self.pdf_path = Path(pdf_path)
        self.md_text = None
        self.lines = []
        self.company_name = self.get_company_name()

    @abstractmethod
    def get_company_name(self):
        """회사명 반환"""
        pass

    @abstractmethod
    def split_sections(self, md_text):
        """
        보통약관과 특별약관 분리

        Returns:
            tuple: (보통약관_텍스트, 특별약관_텍스트)
        """
        pass

    @abstractmethod
    def parse_botong_yakgwan(self, text):
        """
        보통약관 파싱

        Returns:
            list: [{'편': ..., '장': ..., '절': ..., '조': ..., 'content': ...}, ...]
        """
        pass

    @abstractmethod
    def parse_special_yakgwan(self, text):
        """
        특별약관 파싱

        Returns:
            list: [{'조': ..., 'content': ...}, ...]
        """
        pass

    def load_pdf(self):
        """PDF를 마크다운으로 변환하고 전처리"""
        if self.md_text is None:
            # PDF를 마크다운으로 변환
            raw_md = pymupdf4llm.to_markdown(self.pdf_path)
            # 마크다운 전처리 (표 형식 제거, 세로 목차 제거)
            self.md_text = _preprocess_markdown(raw_md)
            self.lines = self.md_text.split('\n')
        return self.md_text

    def parse(self):
        """
        전체 파싱 프로세스 실행

        Returns:
            dict: {
                'company': 회사명,
                'pdf_name': PDF파일명,
                'botong_yakgwan': [...],
                'special_yakgwan': [...]
            }
        """
        # PDF 로드
        md_text = self.load_pdf()

        # 보통약관/특별약관 분리
        botong_text, special_text = self.split_sections(md_text)

        # 각각 파싱
        botong_results = self.parse_botong_yakgwan(botong_text)
        special_results = self.parse_special_yakgwan(special_text)

        return {
            'company': self.company_name,
            'pdf_name': self.pdf_path.name,
            'botong_yakgwan': botong_results,
            'special_yakgwan': special_results
        }

    # 공통 유틸리티 메서드들
    def find_line_positions(self):
        """각 라인의 문자 위치 계산"""
        line_char_positions = []
        char_pos = 0
        for line in self.lines:
            line_char_positions.append(char_pos)
            char_pos += len(line) + 1
        return line_char_positions

    def clean_line(self, line):
        """라인 정리 (마크다운 기호 제거 등)"""
        cleaned = line.strip()
        # 마크다운 볼드 제거
        cleaned = re.sub(r'\*+', '', cleaned)
        # 앞뒤 공백 제거
        cleaned = cleaned.strip()
        return cleaned
