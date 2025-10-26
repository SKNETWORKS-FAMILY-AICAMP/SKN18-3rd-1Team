"""
롯데 업무용/영업용/이륜차 전용 파서
- 볼드 처리 없음
- 일반 텍스트로 된 제X조(제목) 형식
"""

import re
from .base_parser import BaseParser


class LotteBusinessParser(BaseParser):
    """롯데 업무용/영업용/이륜차 PDF 파서"""

    def get_company_name(self):
        return "롯데"

    def split_sections(self, md_text):
        """
        보통약관/특별약관 분리 - 롯데 업무용 구조
        - 볼드 없음, 일반 텍스트
        - 보통약관: "제1편 용어의 정의" 시작
        - 특별약관: "제1편 긴급출동" 또는 "◦ 특별약관" 이후
        """
        import re
        
        # 1. 보통약관 본문 시작: "제1편 용어의 정의" 찾기
        pyeon1_botong = md_text.find('제1편 용어의 정의')
        if pyeon1_botong == -1:
            pyeon1_botong = md_text.find('제1조(용어의 정의)')
        
        if pyeon1_botong == -1:
            # 못 찾으면 "◦ 보통약관" 이후 찾기
            botong_marker = md_text.find('◦ 보통약관')
            if botong_marker >= 0:
                pyeon1_botong = md_text.find('제1조', botong_marker)
        
        if pyeon1_botong == -1:
            pyeon1_botong = 0
        
        # 2. 특별약관 시작: "제1편 긴급출동" 찾기
        special_start = md_text.find('제1편 긴급출동', pyeon1_botong + 1000)
        
        if special_start == -1:
            # 못 찾으면 "◦ 특별약관" 이후 찾기
            special_marker = md_text.find('◦ 특별약관', pyeon1_botong + 1000)
            if special_marker >= 0:
                special_start = md_text.find('제1절', special_marker)
                if special_start == -1:
                    special_start = md_text.find('제1조', special_marker)
        
        if pyeon1_botong >= 0 and special_start >= 0:
            return md_text[pyeon1_botong:special_start], md_text[special_start:]
        elif pyeon1_botong >= 0:
            return md_text[pyeon1_botong:], ""
        else:
            return "", md_text

    def parse_botong_yakgwan(self, text):
        """롯데 업무용 보통약관 파싱 - 볼드 없음"""
        lines = text.split('\n')
        results = []

        patterns = {
            '편': re.compile(r'^제\s*(\d+)\s*편\s+(.+)'),
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
                        '조항': self._build_hierarchy(
                            current_hierarchy['편'], 
                            current_hierarchy['장'], 
                            current_hierarchy['절'], 
                            current_조, 
                            current_조_제목
                        ),
                        'content': '\n'.join(current_content).strip()
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
                            '조항': self._build_hierarchy(
                                current_hierarchy['편'], 
                                current_hierarchy['장'], 
                                current_hierarchy['절'], 
                                current_조, 
                                current_조_제목
                            ),
                            'content': '\n'.join(current_content).strip()
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
                            '조항': self._build_hierarchy(
                                current_hierarchy['편'], 
                                current_hierarchy['장'], 
                                current_hierarchy['절'], 
                                current_조, 
                                current_조_제목
                            ),
                            'content': '\n'.join(current_content).strip()
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
                            '조항': self._build_hierarchy(
                                current_hierarchy['편'], 
                                current_hierarchy['장'], 
                                current_hierarchy['절'], 
                                current_조, 
                                current_조_제목
                            ),
                            'content': '\n'.join(current_content).strip()
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
                # 목차 필터링 (점이 많은 라인)
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('.')
                if dots_count > 10:
                    continue
                # 페이지 번호 필터링
                if re.match(r'^\*\*\d+\*\*$', stripped):
                    continue
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조 and current_content:
            results.append({
                '조항': self._build_hierarchy(
                    current_hierarchy['편'], 
                    current_hierarchy['장'], 
                    current_hierarchy['절'], 
                    current_조, 
                    current_조_제목
                ),
                'content': '\n'.join(current_content).strip()
            })

        return results

    def parse_special_yakgwan(self, text):
        """롯데 업무용 특별약관 파싱 - 볼드 없음"""
        lines = text.split('\n')
        results = []

        조_pattern = re.compile(r'^제\s*(\d+)\s*조\s*[\(〔](.+?)[\)〕]')
        jeol_pattern = re.compile(r'^제\s*(\d+)\s*절\s+(.+)')

        current_특약명 = ''
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            is_hierarchy = False

            # 절 체크 (특약명으로 사용)
            match = jeol_pattern.match(stripped)
            if match:
                if current_조:
                    results.append({
                        '조항': self._build_hierarchy(
                            특약명=current_특약명,
                            조=current_조,
                            조_제목=current_조_제목
                        ),
                        'content': '\n'.join(current_content).strip()
                    })
                    current_content = []
                    current_조 = ''
                    current_조_제목 = ''
                
                jeol_num = match.group(1)
                jeol_title = match.group(2).strip()
                current_특약명 = f"제{jeol_num}절 {jeol_title}"
                is_hierarchy = True

            # 조 체크
            if not is_hierarchy:
                match = 조_pattern.match(stripped)
                if match:
                    if current_조:
                        results.append({
                            '조항': self._build_hierarchy(
                                특약명=current_특약명,
                                조=current_조,
                                조_제목=current_조_제목
                            ),
                            'content': '\n'.join(current_content).strip()
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
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조 and current_content:
            results.append({
                '조항': self._build_hierarchy(
                    특약명=current_특약명,
                    조=current_조,
                    조_제목=current_조_제목
                ),
                'content': '\n'.join(current_content).strip()
            })

        return results

    def _build_hierarchy(self, 편='', 장='', 절='', 조='', 조_제목='', 특약명=''):
        """계층구조 문자열 생성"""
        parts = []
        if 특약명:
            parts.append(특약명)
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

