"""삼성화재 원데이 자동차보험 파서"""
from .base_parser import BaseParser
import re


class SamsungOnedayParser(BaseParser):
    """삼성화재 원데이 자동차보험 파서
    
    구조:
    - 보통약관: # 원데이 애니카 자동차보험 보통약관 → ### 제X 편 → 제X조(
    - 특별약관: #### Ⅰ. 타인차량 특별약관, #### Ⅰ-1. 대인배상Ⅰ 지원금 추가특별약관 등 → 제X조(
    """
    
    def get_company_name(self):
        return "삼성화재"
    
    def split_sections(self, md_text):
        """보통약관과 특별약관 분리"""
        botong_text = ''
        special_text = ''
        
        # 보통약관 헤더: # 원데이 애니카 자동차보험 보통약관
        botong_header = re.search(r'#\s*`?원데이\s+애니카\s+자동차보험\s+보통약관', md_text)
        
        # 특별약관 헤더: # 원데이 애니카 자동차보험 특별약관
        special_header = re.search(r'#\s*`?원데이\s+애니카\s+자동차보험\s+특별약관', md_text)
        
        if botong_header and special_header:
            botong_text = md_text[botong_header.start():special_header.start()]
            special_text = md_text[special_header.start():]
        elif botong_header:
            botong_text = md_text[botong_header.start():]
        
        return botong_text, special_text
    
    def parse_botong_yakgwan(self, text):
        """보통약관 파싱
        
        구조: ### 제X 편 ... → 제X조(...)
        """
        results = []
        product_name = self.pdf_path.stem  # 파일명에서 보험명 추출
        
        # 멀티라인 제목 처리: 제X조(...\n...)를 하나로 합침
        text = self._merge_multiline_titles(text, r'제\d+\s*조\s*\(')
        
        # 현재 계층 추적
        current_편 = ""
        current_편_제목 = ""
        current_장 = ""
        current_장_제목 = ""
        current_절 = ""
        current_절_제목 = ""
        current_조 = ""
        current_조_제목 = ""
        
        lines = text.split('\n')
        current_content = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # 편 패턴 (### 제X 편 ...)
            pyeon_match = re.match(r'###\s*`?제\s*(\d+)\s*편\s+([^`\n]+)', line_stripped)
            if pyeon_match:
                # 이전 조 저장
                if current_조 and current_조_제목:
                    results.append({
                        '회사명': self.get_company_name(),
                        '보험명': product_name,
                        '약관구분': '보통약관',
                        '조항': self._build_hierarchy(current_편, current_편_제목, 
                                                      current_장, current_장_제목,
                                                      current_절, current_절_제목,
                                                      current_조, current_조_제목),
                        '내용': '\n'.join(current_content).strip()
                    })
                
                current_편 = pyeon_match.group(1)
                current_편_제목 = pyeon_match.group(2).strip().strip('`').strip()
                current_장 = ""
                current_장_제목 = ""
                current_절 = ""
                current_절_제목 = ""
                current_조 = ""
                current_조_제목 = ""
                current_content = []
                continue
            
            # 조 패턴: 제X조(...)
            jo_match = re.match(r'제\s*(\d+)\s*조\s*\(([^)]+)\)', line_stripped)
            if jo_match:
                # 이전 조 저장
                if current_조 and current_조_제목:
                    results.append({
                        '회사명': self.get_company_name(),
                        '보험명': product_name,
                        '약관구분': '보통약관',
                        '조항': self._build_hierarchy(current_편, current_편_제목, 
                                                      current_장, current_장_제목,
                                                      current_절, current_절_제목,
                                                      current_조, current_조_제목),
                        '내용': '\n'.join(current_content).strip()
                    })
                
                current_조 = jo_match.group(1)
                current_조_제목 = jo_match.group(2).strip()
                current_content = []
                continue
            
            # 내용 수집
            if current_조:
                # 빈 줄이 아니면 추가
                if line_stripped:
                    current_content.append(line)
        
        # 마지막 조 저장
        if current_조 and current_조_제목:
            results.append({
                '회사명': self.get_company_name(),
                '보험명': product_name,
                '약관구분': '보통약관',
                '조항': self._build_hierarchy(current_편, current_편_제목, 
                                              current_장, current_장_제목,
                                              current_절, current_절_제목,
                                              current_조, current_조_제목),
                '내용': '\n'.join(current_content).strip()
            })
        
        return results
    
    def parse_special_yakgwan(self, text):
        """특별약관 파싱
        
        구조: #### Ⅰ. 타인차량 특별약관 → 제X조(...)
        """
        results = []
        product_name = self.pdf_path.stem  # 파일명에서 보험명 추출
        
        # 멀티라인 제목 처리
        text = self._merge_multiline_titles(text, r'제\d+\s*조\s*\(')
        
        # 특별약관 헤더 패턴: #### Ⅰ. 타인차량 특별약관, #### Ⅰ-1. 대인배상Ⅰ 지원금 추가특별약관
        special_pattern = re.compile(r'####\s*`?([IⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ\d\-\.]+)\.\s*([^`\n]+)(?:`)?')
        special_matches = list(special_pattern.finditer(text))
        
        for i, match in enumerate(special_matches):
            start_pos = match.start()
            end_pos = special_matches[i+1].start() if i+1 < len(special_matches) else len(text)
            
            special_name = f"{match.group(1)}. {match.group(2)}".strip().strip('`').strip()
            special_text = text[start_pos:end_pos]
            
            # 현재 특별약관 내 조 파싱
            current_조 = ""
            current_조_제목 = ""
            current_content = []
            
            lines = special_text.split('\n')
            
            for line in lines:
                line_stripped = line.strip()
                
                # 조 패턴
                jo_match = re.match(r'제\s*(\d+)\s*조\s*\(([^)]+)\)', line_stripped)
                if jo_match:
                    # 이전 조 저장
                    if current_조 and current_조_제목:
                        results.append({
                            '회사명': self.get_company_name(),
                            '보험명': product_name,
                            '약관구분': '특별약관',
                            '조항': f"{special_name} > 제{current_조}조({current_조_제목})",
                            '내용': '\n'.join(current_content).strip()
                        })
                    
                    current_조 = jo_match.group(1)
                    current_조_제목 = jo_match.group(2).strip()
                    current_content = []
                    continue
                
                # 내용 수집
                if current_조:
                    if line_stripped and not line_stripped.startswith('####'):
                        current_content.append(line)
            
            # 마지막 조 저장
            if current_조 and current_조_제목:
                results.append({
                    '회사명': self.get_company_name(),
                    '보험명': product_name,
                    '약관구분': '특별약관',
                    '조항': f"{special_name} > 제{current_조}조({current_조_제목})",
                    '내용': '\n'.join(current_content).strip()
                })
        
        return results
    
    def _build_hierarchy(self, pyeon, pyeon_title, jang, jang_title, jeol, jeol_title, jo, jo_title):
        """계층 구조 문자열 생성"""
        parts = []
        
        if pyeon:
            parts.append(f"제{pyeon}편({pyeon_title})")
        if jang:
            parts.append(f"제{jang}장({jang_title})")
        if jeol:
            parts.append(f"제{jeol}절({jeol_title})")
        if jo:
            parts.append(f"제{jo}조({jo_title})")
        
        return " > ".join(parts) if parts else ""
    
    def _merge_multiline_titles(self, text, pattern_start):
        """멀티라인 제목을 하나로 합침
        
        예: 제1조(적용\n대상) → 제1조(적용 대상)
        """
        lines = text.split('\n')
        merged_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 패턴 시작인지 확인
            if re.match(pattern_start, line.strip()):
                # 괄호가 닫히지 않았으면 다음 줄과 병합
                if '(' in line and ')' not in line:
                    merged = line
                    i += 1
                    while i < len(lines) and ')' not in merged:
                        merged += ' ' + lines[i].strip()
                        i += 1
                    merged_lines.append(merged)
                else:
                    merged_lines.append(line)
                    i += 1
            else:
                merged_lines.append(line)
                i += 1
        
        return '\n'.join(merged_lines)

