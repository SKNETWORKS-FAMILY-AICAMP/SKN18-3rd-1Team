"""
롯데 이륜차 전용 파서
- 볼드 처리 없음
- ● 패턴 대량 포함
- 특별약관이 제1절로 시작
"""

import re
from .base_parser import BaseParser


class LotteWheelParser(BaseParser):
    """롯데 이륜차 PDF 파서"""

    def get_company_name(self):
        return "롯데"

    def split_sections(self, md_text):
        """
        보통약관/특별약관 분리 - 롯데 이륜차 구조
        - 보통약관: 목차 다음 "제1편 용어의 정의" 시작
        - 특별약관: "제1절 보험료 분할납입" 시작
        """
        import re
        
        # 1. 보통약관 본문 시작: 목차 이후 "제1편 용어의 정의" 찾기
        mok_cha = md_text.find('목  차')
        if mok_cha > 0:
            # 목차 이후에서 "제1편" 찾기
            pyeon1_pattern = re.compile(r'제1편\s+용어의\s+정의')
            pyeon1_match = pyeon1_pattern.search(md_text, mok_cha)
            if pyeon1_match:
                botong_start_idx = pyeon1_match.start()
            else:
                # 못 찾으면 "제1조(용어의 정의)" 찾기
                jo1_pattern = re.compile(r'제1조\(용어의\s*정의\)')
                jo1_match = jo1_pattern.search(md_text, mok_cha)
                if jo1_match:
                    botong_start_idx = jo1_match.start()
                else:
                    botong_start_idx = 0
        else:
            botong_start_idx = 0
        
        # 2. 특별약관 시작: "제1절 보험료 분할납입" 찾기
        special_pattern = re.compile(r'제1절\s+보험료\s+분할납입')
        special_match = special_pattern.search(md_text, botong_start_idx + 10000)
        
        if special_match:
            special_start_idx = special_match.start()
        else:
            # 못 찾으면 충분히 뒤에 있는 "특별약관" 찾기
            special_start_idx = md_text.find('특별약관', botong_start_idx + 50000)
        
        if botong_start_idx >= 0 and special_start_idx >= 0:
            return md_text[botong_start_idx:special_start_idx], md_text[special_start_idx:]
        elif botong_start_idx >= 0:
            return md_text[botong_start_idx:], ""
        else:
            return "", md_text

    def parse_botong_yakgwan(self, text):
        """롯데 이륜차 보통약관 파싱 - 볼드 없음"""
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

            # ● 패턴 필터링
            if stripped.startswith('-') and '●' in stripped:
                continue
            if stripped.count('●') > 10:
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
        """롯데 이륜차 특별약관 파싱 - 제X절로 시작"""
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

            # ● 패턴 필터링
            if stripped.startswith('-') and '●' in stripped:
                continue
            if stripped.count('●') > 10:
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


