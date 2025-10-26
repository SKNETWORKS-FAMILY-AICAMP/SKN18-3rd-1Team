"""
롯데손해보험 전용 파서
- 마크다운 헤더(##) 사용
- 제X조(제목) 형식 사용
"""

import re
from .base_parser import BaseParser


class LotteParser(BaseParser):
    """롯데손해보험 PDF 파서"""

    def get_company_name(self):
        return "롯데"

    def split_sections(self, md_text):
        """
        보통약관/특별약관 분리 - 롯데 구조
        - 보통약관: [보통약관] 다음 **제1조 찾기
        - 특별약관: [특별약관] 다음 **제1절 또는 **제1조 찾기
        """
        import re
        
        # 1. 보통약관 본문 시작: [보통약관] 다음의 **제1조
        botong_marker = md_text.find('[보통약관]')
        if botong_marker >= 0:
            # [보통약관] 이후에서 **제1조 찾기
            jo1_pattern = re.compile(r'\*\*제1조')
            jo1_match = jo1_pattern.search(md_text, botong_marker)
            if jo1_match:
                botong_start_idx = jo1_match.start()
            else:
                botong_start_idx = botong_marker
        else:
            # [보통약관] 없으면 보통약관 키워드 찾기
            botong_start_idx = md_text.find('보통약관')
            if botong_start_idx == -1:
                botong_start_idx = 0
        
        # 2. 특별약관 시작: [특별약관] 찾기
        special_marker = md_text.find('[특별약관]', botong_start_idx)
        if special_marker >= 0:
            special_start_idx = special_marker
        else:
            # [특별약관] 없으면 충분히 뒤에 있는 특별약관 찾기
            special_start_idx = md_text.find('특별약관', botong_start_idx + 50000)
        
        if botong_start_idx >= 0 and special_start_idx >= 0:
            return md_text[botong_start_idx:special_start_idx], md_text[special_start_idx:]
        elif botong_start_idx >= 0:
            return md_text[botong_start_idx:], ""
        else:
            return "", md_text

    def parse_botong_yakgwan(self, text):
        """롯데 보통약관 파싱 - 새로운 형식 (조항 = 편>장>절>조)"""
        lines = text.split('\n')
        results = []

        patterns = {
            '편': re.compile(r'^제\s*(\d+)\s*편\s*(?:[\(〔](.+?)[\)〕])?'),
            '장': re.compile(r'^제\s*(\d+)\s*장\s*(?:[\(〔](.+?)[\)〕])?'),
            '절': re.compile(r'^제\s*(\d+)\s*절\s*(?:[\(〔](.+?)[\)〕])?'),
            '조': re.compile(r'^제\s*(\d+)\s*조\s*(?:[\(〔](.+?)[\)〕])?'),
        }

        current_hierarchy = {'편': '', '장': '', '절': ''}
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        # 줄바꿈된 제목 합치기 전처리
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # **로 시작하고 **로 끝나지 않으면 다음 줄과 합치기
            if line.startswith('**') and '조(' in line and not line.endswith('**'):
                merged = line
                j = i + 1
                while j < len(lines) and j < i + 5:
                    next_line = lines[j].strip()
                    merged += ' ' + next_line
                    if next_line.endswith('**'):
                        i = j
                        break
                    j += 1
                merged_lines.append(merged)
            else:
                merged_lines.append(line)
            i += 1

        for line in merged_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # [보통약관] 같은 섹션 마커 건너뛰기
            if stripped.startswith('[') and '보통약관' in stripped:
                continue

            is_hierarchy = False

            # **로 시작하는 경우 볼드 제거, 아니면 그대로 사용
            line_clean = re.sub(r'\*+', '', stripped) if stripped.startswith('**') else stripped

            # 편 체크
            match = patterns['편'].match(line_clean)
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
                pyeon_title = match.group(2) or ''
                pyeon_title = re.sub(r'[·\u2024]+.*$', '', pyeon_title).strip() if pyeon_title else ''
                current_hierarchy['편'] = f"제{pyeon_num}편({pyeon_title})" if pyeon_title else f"제{pyeon_num}편"
                current_hierarchy['장'] = ''
                current_hierarchy['절'] = ''
                is_hierarchy = True

            # 장 체크
            if not is_hierarchy:
                match = patterns['장'].match(line_clean)
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
                    jang_title = match.group(2) or ''
                    jang_title = re.sub(r'[·\u2024]+.*$', '', jang_title).strip() if jang_title else ''
                    current_hierarchy['장'] = f"제{jang_num}장({jang_title})" if jang_title else f"제{jang_num}장"
                    current_hierarchy['절'] = ''
                    is_hierarchy = True

            # 절 체크
            if not is_hierarchy:
                match = patterns['절'].match(line_clean)
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
                    jeol_title = match.group(2) or ''
                    jeol_title = re.sub(r'[·\u2024]+.*$', '', jeol_title).strip() if jeol_title else ''
                    current_hierarchy['절'] = f"제{jeol_num}절({jeol_title})" if jeol_title else f"제{jeol_num}절"
                    is_hierarchy = True

            # 조 체크
            if not is_hierarchy:
                match = patterns['조'].match(line_clean)
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
                    jo_title = match.group(2) or ''
                    jo_title = re.sub(r'[·\u2024]+.*$', '', jo_title).strip() if jo_title else ''
                    current_조 = jo_num
                    current_조_제목 = jo_title
                    current_content = []
                    is_hierarchy = True
                    
                    # 같은 라인에 내용이 있으면 추가
                    remaining_content = line_clean[match.end():].strip()
                    if remaining_content and not remaining_content.startswith('['):
                        current_content.append(remaining_content)
                    continue

            # 내용 추가 (계층구조가 아니고 조가 시작된 경우)
            if not is_hierarchy and current_조:
                # 목차 필터링
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('.')
                if dots_count > 10:
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
        """롯데 특별약관 파싱 - 새로운 형식 (조항 = 특약명>제X조)"""
        lines = text.split('\n')
        results = []

        조_pattern = re.compile(r'^제\s*(\d+)\s*조\s*(?:[\(〔](.+?)[\)〕])?')
        
        # 편/장/절 패턴도 특별약관에 있을 수 있음
        pyeon_pattern = re.compile(r'^제\s*(\d+)\s*편\s*(?:[\(〔](.+?)[\)〕])?')
        jang_pattern = re.compile(r'^제\s*(\d+)\s*장\s*(?:[\(〔](.+?)[\)〕])?')
        jeol_pattern = re.compile(r'^제\s*(\d+)\s*절\s*(?:[\(〔](.+?)[\)〕])?')

        current_특약명 = ''
        current_편 = ''
        current_장 = ''
        current_절 = ''
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        # 줄바꿈된 제목 합치기 전처리
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('**') and '조(' in line and not line.endswith('**'):
                merged = line
                j = i + 1
                while j < len(lines) and j < i + 5:
                    next_line = lines[j].strip()
                    merged += ' ' + next_line
                    if next_line.endswith('**'):
                        i = j
                        break
                    j += 1
                merged_lines.append(merged)
            else:
                merged_lines.append(line)
            i += 1

        for line in merged_lines:
            stripped = line.strip()
            if not stripped:
                continue

            # [특별약관] 같은 섹션 마커 건너뛰기
            if stripped.startswith('[') and '특별약관' in stripped:
                continue

            is_hierarchy = False

            # 특약명 (볼드 처리된 제X절 또는 제X편 등)
            if stripped.startswith('**'):
                line_clean = re.sub(r'\*+', '', stripped)
                
                # 편 체크
                match = pyeon_pattern.match(line_clean)
                if match:
                    if current_조:
                        results.append({
                            '조항': self._build_hierarchy(
                                특약명=current_특약명,
                                편=current_편,
                                장=current_장,
                                절=current_절,
                                조=current_조,
                                조_제목=current_조_제목
                            ),
                            'content': '\n'.join(current_content).strip()
                        })
                        current_content = []
                        current_조 = ''
                        current_조_제목 = ''
                    
                    pyeon_num = match.group(1)
                    pyeon_title = match.group(2) or ''
                    pyeon_title = re.sub(r'[·\u2024]+.*$', '', pyeon_title).strip() if pyeon_title else ''
                    current_편 = f"제{pyeon_num}편({pyeon_title})" if pyeon_title else f"제{pyeon_num}편"
                    current_장 = ''
                    current_절 = ''
                    is_hierarchy = True

                # 장 체크
                if not is_hierarchy:
                    match = jang_pattern.match(line_clean)
                    if match:
                        if current_조:
                            results.append({
                                '조항': self._build_hierarchy(
                                    특약명=current_특약명,
                                    편=current_편,
                                    장=current_장,
                                    절=current_절,
                                    조=current_조,
                                    조_제목=current_조_제목
                                ),
                                'content': '\n'.join(current_content).strip()
                            })
                            current_content = []
                            current_조 = ''
                            current_조_제목 = ''
                        
                        jang_num = match.group(1)
                        jang_title = match.group(2) or ''
                        jang_title = re.sub(r'[·\u2024]+.*$', '', jang_title).strip() if jang_title else ''
                        current_장 = f"제{jang_num}장({jang_title})" if jang_title else f"제{jang_num}장"
                        current_절 = ''
                        is_hierarchy = True

                # 절 체크 (특약명으로도 사용됨)
                if not is_hierarchy:
                    match = jeol_pattern.match(line_clean)
                    if match:
                        if current_조:
                            results.append({
                                '조항': self._build_hierarchy(
                                    특약명=current_특약명,
                                    편=current_편,
                                    장=current_장,
                                    절=current_절,
                                    조=current_조,
                                    조_제목=current_조_제목
                                ),
                                'content': '\n'.join(current_content).strip()
                            })
                            current_content = []
                            current_조 = ''
                            current_조_제목 = ''
                        
                        jeol_num = match.group(1)
                        jeol_title = match.group(2) or ''
                        jeol_title = re.sub(r'[·\u2024]+.*$', '', jeol_title).strip() if jeol_title else ''
                        
                        # 절을 특약명으로 사용
                        current_특약명 = f"제{jeol_num}절 {jeol_title}" if jeol_title else f"제{jeol_num}절"
                        current_절 = ''
                        is_hierarchy = True

                # 조 체크
                if not is_hierarchy:
                    match = 조_pattern.match(line_clean)
                    if match:
                        if current_조:
                            results.append({
                                '조항': self._build_hierarchy(
                                    특약명=current_특약명,
                                    편=current_편,
                                    장=current_장,
                                    절=current_절,
                                    조=current_조,
                                    조_제목=current_조_제목
                                ),
                                'content': '\n'.join(current_content).strip()
                            })
                        
                        jo_num = match.group(1)
                        jo_title = match.group(2) or ''
                        jo_title = re.sub(r'[·\u2024]+.*$', '', jo_title).strip() if jo_title else ''
                        current_조 = jo_num
                        current_조_제목 = jo_title
                        current_content = []
                        is_hierarchy = True
                        
                        # 같은 라인에 내용이 있으면 추가
                        remaining_content = line_clean[match.end():].strip()
                        if remaining_content and not remaining_content.startswith('['):
                            current_content.append(remaining_content)
                        continue

            # 내용 추가
            if not is_hierarchy and current_조:
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('.')
                if dots_count > 10:
                    continue
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조 and current_content:
            results.append({
                '조항': self._build_hierarchy(
                    특약명=current_특약명,
                    편=current_편,
                    장=current_장,
                    절=current_절,
                    조=current_조,
                    조_제목=current_조_제목
                ),
                'content': '\n'.join(current_content).strip()
            })

        return results

    def _build_hierarchy(self, 편='', 장='', 절='', 조='', 조_제목='', 특약명=''):
        """
        계층구조 문자열 생성: 편>장>절>조 형식
        비어있는 계층은 제외
        특약명이 있으면 맨 앞에 추가
        """
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
