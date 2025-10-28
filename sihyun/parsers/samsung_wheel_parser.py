"""
삼성화재 이륜차 전용 파서
- 보통약관: 제 1 편 . (공백과 점 있음)
- 특별약관: 제X절 > 제X조 구조
"""

import re
from .base_parser import BaseParser


class SamsungWheelParser(BaseParser):
    """삼성화재 이륜차 PDF 파서"""

    def get_company_name(self):
        return "삼성화재"

    def split_sections(self, md_text):
        """
        보통약관/특별약관 분리 - 삼성화재 이륜차 구조
        - 보통약관: 본문 "제 1 편 . 용어의 정의" 시작
        - 특별약관: "#### 이륜자동차보험 특별약관" 헤더 이후
        """
        import re
        
        # 1. 보통약관 본문 시작
        pyeon1_pattern = re.compile(r'제\s*1\s*편\s*\.\s*용어의\s*정의')
        pyeon1_matches = list(pyeon1_pattern.finditer(md_text))
        
        if len(pyeon1_matches) >= 2:
            botong_start_idx = pyeon1_matches[1].start()
        elif pyeon1_matches:
            botong_start_idx = pyeon1_matches[0].start()
        else:
            jo1_pattern = re.compile(r'제1조\(용어의\s*정의\)')
            jo1_matches = list(jo1_pattern.finditer(md_text))
            if len(jo1_matches) >= 2:
                botong_start_idx = jo1_matches[1].start()
            elif jo1_matches:
                botong_start_idx = jo1_matches[0].start()
            else:
                botong_start_idx = 0
        
        # 2. 특별약관 본문 시작: "#### 이륜자동차보험 특별약관" 헤더 찾기
        special_header_pattern = re.compile(r'####\s*이륜자동차보험\s*특별약관')
        special_header_matches = list(special_header_pattern.finditer(md_text, botong_start_idx + 50000))
        
        if len(special_header_matches) >= 2:
            # 두 번째가 본문 (첫 번째는 목차)
            special_idx = special_header_matches[1].start()
        elif special_header_matches:
            # 하나만 있으면 그 이후 "제1절" 찾기
            header_pos = special_header_matches[0].end()
            jeol1_pattern = re.compile(r'제\s*1\s*절\.')
            jeol1_matches = list(jeol1_pattern.finditer(md_text, header_pos, header_pos + 5000))
            if jeol1_matches:
                special_idx = jeol1_matches[0].start()
            else:
                special_idx = header_pos
        else:
            # 못 찾으면 "특별약관" 키워드
            special_idx = md_text.find('특별약관', botong_start_idx + 50000)
            if special_idx == -1:
                special_idx = md_text.rfind('특별약관')
        
        if botong_start_idx >= 0 and special_idx > botong_start_idx:
            return md_text[botong_start_idx:special_idx], md_text[special_idx:]
        elif botong_start_idx >= 0:
            return md_text[botong_start_idx:], ""
        else:
            return "", md_text

    def parse_botong_yakgwan(self, text):
        """삼성화재 이륜차 보통약관 파싱 - 볼드 없음"""
        lines = text.split('\n')
        results = []

        patterns = {
            '편': re.compile(r'^제\s*(\d+)\s*편\s*\.\s*(.+)'),
            '장': re.compile(r'^제\s*(\d+)\s*장\s+(.+)'),
            '절': re.compile(r'^제\s*(\d+)\s*절\s+(.+)'),
            '조': re.compile(r'^제\s*(\d+)\s*조\s*[\(〔](.+?)[\)〕]'),
        }

        current_hierarchy = {'편': '', '장': '', '절': ''}
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            is_hierarchy = False

            # 편 체크
            match = patterns['편'].match(stripped)
            if match:
                if current_조:
                    results.append({
                        '약관구분': '보통약관',
                        '조항': self._build_hierarchy(
                            current_hierarchy['편'], 
                            current_hierarchy['장'], 
                            current_hierarchy['절'], 
                            current_조, 
                            current_조_제목
                        ),
                        '내용': '\n'.join(current_content).strip()
                    })
                    current_content = []
                    current_조 = ''
                    current_조_제목 = ''
                
                pyeon_num = match.group(1)
                pyeon_title = match.group(2).strip()
                current_hierarchy['편'] = f"제{pyeon_num}편({pyeon_title})" if pyeon_title else f"제{pyeon_num}편"
                current_hierarchy['장'] = ''
                current_hierarchy['절'] = ''
                is_hierarchy = True

            # 장 체크
            if not is_hierarchy:
                match = patterns['장'].match(stripped)
                if match:
                    if current_조:
                        results.append({
                            '약관구분': '보통약관',
                            '조항': self._build_hierarchy(
                                current_hierarchy['편'], 
                                current_hierarchy['장'], 
                                current_hierarchy['절'], 
                                current_조, 
                                current_조_제목
                            ),
                            '내용': '\n'.join(current_content).strip()
                        })
                        current_content = []
                        current_조 = ''
                        current_조_제목 = ''
                    
                    jang_num = match.group(1)
                    jang_title = match.group(2).strip()
                    current_hierarchy['장'] = f"제{jang_num}장({jang_title})" if jang_title else f"제{jang_num}장"
                    current_hierarchy['절'] = ''
                    is_hierarchy = True

            # 절 체크
            if not is_hierarchy:
                match = patterns['절'].match(stripped)
                if match:
                    if current_조:
                        results.append({
                            '약관구분': '보통약관',
                            '조항': self._build_hierarchy(
                                current_hierarchy['편'], 
                                current_hierarchy['장'], 
                                current_hierarchy['절'], 
                                current_조, 
                                current_조_제목
                            ),
                            '내용': '\n'.join(current_content).strip()
                        })
                        current_content = []
                        current_조 = ''
                        current_조_제목 = ''
                    
                    jeol_num = match.group(1)
                    jeol_title = match.group(2).strip()
                    current_hierarchy['절'] = f"제{jeol_num}절({jeol_title})" if jeol_title else f"제{jeol_num}절"
                    is_hierarchy = True

            # 조 체크
            if not is_hierarchy:
                match = patterns['조'].match(stripped)
                if match:
                    if current_조:
                        results.append({
                            '약관구분': '보통약관',
                            '조항': self._build_hierarchy(
                                current_hierarchy['편'], 
                                current_hierarchy['장'], 
                                current_hierarchy['절'], 
                                current_조, 
                                current_조_제목
                            ),
                            '내용': '\n'.join(current_content).strip()
                        })
                    
                    jo_num = match.group(1)
                    jo_title = match.group(2).strip() if match.group(2) else ''
                    current_조 = jo_num
                    current_조_제목 = jo_title
                    current_content = []
                    is_hierarchy = True
                    continue

            # 내용 추가
            if not is_hierarchy and current_조:
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('.')
                if dots_count > 10:
                    continue
                if re.match(r'^\*\*\d+\*\*$', stripped):
                    continue
                if stripped.startswith('<') and stripped.endswith('>'):
                    continue
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조 and current_content:
            results.append({
                '약관구분': '보통약관',
                '조항': self._build_hierarchy(
                    current_hierarchy['편'], 
                    current_hierarchy['장'], 
                    current_hierarchy['절'], 
                    current_조, 
                    current_조_제목
                ),
                '내용': '\n'.join(current_content).strip()
            })

        return results

    def parse_special_yakgwan(self, text):
        """삼성화재 이륜차 특별약관 파싱 - 제X절>제X조 구조"""
        lines = text.split('\n')
        results = []

        # 패턴
        절_pattern = re.compile(r'^제\s*(\d+)\s*절\.\s*(.+)')
        조_pattern = re.compile(r'^제\s*(\d+)\s*조\s*\.\s*(.+)')

        current_절명 = ''
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            is_hierarchy = False

            # 절 체크
            match = 절_pattern.match(stripped)
            if match:
                if current_조 and current_content:
                    results.append({
                        '약관구분': '특별약관',
                        '조항': f"{current_절명}>제{current_조}조({current_조_제목})",
                        '내용': '\n'.join(current_content).strip()
                    })
                    current_content = []
                    current_조 = ''
                    current_조_제목 = ''
                
                절번호 = match.group(1)
                절제목 = match.group(2).strip()
                current_절명 = f"제{절번호}절({절제목})"
                is_hierarchy = True

            # 조 체크
            if not is_hierarchy:
                match = 조_pattern.match(stripped)
                if match:
                    if current_조 and current_content:
                        results.append({
                            '약관구분': '특별약관',
                            '조항': f"{current_절명}>제{current_조}조({current_조_제목})",
                            '내용': '\n'.join(current_content).strip()
                        })
                    
                    jo_num = match.group(1)
                    jo_title = match.group(2).strip() if match.group(2) else ''
                    current_조 = jo_num
                    current_조_제목 = jo_title
                    current_content = []
                    is_hierarchy = True
                    continue

            # 내용 추가
            if not is_hierarchy and current_조:
                # 목차 필터링
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('…')
                if dots_count > 10:
                    continue
                # 페이지 번호 필터링
                if re.match(r'^\*\*\d+\*\*$', stripped):
                    continue
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조 and current_content:
            results.append({
                '약관구분': '특별약관',
                '조항': f"{current_절명}>제{current_조}조({current_조_제목})",
                '내용': '\n'.join(current_content).strip()
            })

        return results

    def _build_hierarchy(self, 편='', 장='', 절='', 조='', 조_제목=''):
        """계층구조 문자열 생성"""
        parts = []
        if 편:
            parts.append(편)
        if 장:
            parts.append(장)
        if 절:
            parts.append(절)
        if 조:
            if 조_제목:
                parts.append(f"제{조}조({조_제목})")
            else:
                parts.append(f"제{조}조")
        return '>'.join(parts) if parts else ''

