"""
KB 업무용/영업용/이륜 자동차보험 전용 파서
- 마크다운 헤더 없음
- 목차: 제X조 용어의 정의 ┃ 3 (┃ 기호로 목차 구분)
- 본문: **제X조(용어의 정의)** (볼드로 감싼 괄호 형식)
"""

import re
from .base_parser import BaseParser


class KBBusinessParser(BaseParser):
    """KB 업무용/영업용/이륜 자동차보험 PDF 파서"""

    def get_company_name(self):
        return "KB"

    def split_sections(self, md_text):
        """
        보통약관/특별약관 분리 - PDF 구조 기반
        - KB 업무용/영업용/이륜: 목차 건너뛰고 **제1편부터 시작 (본문)
        - 특별약관: **KB업무용자동차보험 특별약관** 패턴
        """
        import re
        
        # 1. 보통약관 본문 시작: **제1편 찾기 (두 번째 등장 = 본문)
        first_pyeon_pattern = re.compile(r'\*\*제1편')
        pyeon_matches = list(first_pyeon_pattern.finditer(md_text))
        
        if len(pyeon_matches) >= 2:
            # 두 번째 **제1편이 본문 시작
            botong_start_idx = pyeon_matches[1].start()
        elif len(pyeon_matches) == 1:
            # 하나만 있으면 그게 본문 시작
            botong_start_idx = pyeon_matches[0].start()
        else:
            # **제1편이 없으면 **제1조 찾기
            first_jo_pattern = re.compile(r'\*\*제1조')
            first_jo_match = first_jo_pattern.search(md_text)
            if first_jo_match:
                botong_start_idx = first_jo_match.start()
            else:
                botong_start_idx = md_text.find('보통약관')
                if botong_start_idx == -1:
                    botong_start_idx = 0
        
        # 2. 특별약관 시작: **KB...자동차보험 특별약관** 찾기
        special_pattern = re.compile(r'\*\*KB\w+자동차보험\s+특별약관\*\*')
        special_match = special_pattern.search(md_text, botong_start_idx)
        
        if special_match:
            special_start_idx = special_match.start()
        else:
            # KB 패턴이 없으면 충분히 뒤에 있는 특별약관 찾기
            special_start_idx = md_text.find('특별약관', botong_start_idx + 50000)
        
        if botong_start_idx >= 0 and special_start_idx >= 0:
            return md_text[botong_start_idx:special_start_idx], md_text[special_start_idx:]
        elif botong_start_idx >= 0:
            return md_text[botong_start_idx:], ""
        else:
            return "", md_text

    def parse_botong_yakgwan(self, text):
        """
        KB 업무용/영업용/이륜 보통약관 파싱 (preprocess.py 로직 적용)
        - **제X조(제목)** 형식
        """
        # 정규표현식 패턴
        patterns = {
            '편': re.compile(r'^제\s*(\d+)\s*편\s+(.+?)(?:\s*[·\u2024]+.*)?$'),
            '장': re.compile(r'^제\s*(\d+)\s*장\s+(.+?)(?:\s*[·\u2024]+.*)?$'),
            '절': re.compile(r'^제\s*(\d+)\s*절\s+(.+?)(?:\s*[·\u2024]+.*)?$'),
            '조': re.compile(r'^제\s*(\d+)\s*조\s*(?:[\(〔](.+?)[\)〕])?'),  # 조 다음에 내용이 올 수 있음
        }

        results = []
        current_hierarchy = {
            '편': '',
            '장': '',
            '절': ''
        }
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        lines = text.split('\n')
        
        # 줄바꿈된 제목 합치기 전처리
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # **로 시작하고 **로 끝나지 않으면 다음 줄과 합치기
            if line.startswith('**') and '조(' in line and not line.endswith('**'):
                # 다음 줄들을 합침
                merged = line
                j = i + 1
                while j < len(lines) and j < i + 5:  # 최대 5줄까지만 합침
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

            # 마크다운 헤더는 건너뛰기
            if stripped.startswith('#'):
                continue

            is_hierarchy = False
            
            # 편/장/절/조는 **로 볼드 처리된 것만 인식
            if not stripped.startswith('**'):
                # 볼드가 아니면 내용으로 추가
                if current_조:
                    current_content.append(stripped)
                continue
            
            line_clean = re.sub(r'\*+', '', stripped)

            # 편 체크
            match = patterns['편'].match(line_clean)
            if match:
                # 이전 조 저장
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy(
                            current_hierarchy['편'], current_hierarchy['장'],
                            current_hierarchy['절'], current_조, current_조_제목
                        )
                        results.append({
                            '조항': hierarchy,
                            'content': cleaned_content
                        })
                    current_content = []
                    current_조 = ''
                    current_조_제목 = ''

                title = match.group(2).strip()
                title = re.sub(r'[·\u2024]+.*$', '', title).strip()
                title = re.sub(r'[｛｝\[\]].*$', '', title).strip()
                if len(title) > 30:
                    title = title[:30]
                current_hierarchy['편'] = f"제{match.group(1)}편({title})" if title else f"제{match.group(1)}편"
                current_hierarchy['장'] = ''
                current_hierarchy['절'] = ''
                is_hierarchy = True

            # 장 체크
            if not is_hierarchy:
                match = patterns['장'].match(line_clean)
                if match:
                    if current_조:
                        cleaned_content = '\n'.join(current_content).strip()
                        if cleaned_content:
                            hierarchy = self._build_hierarchy(
                                current_hierarchy['편'], current_hierarchy['장'],
                                current_hierarchy['절'], current_조, current_조_제목
                            )
                            results.append({
                                '조항': hierarchy,
                                'content': cleaned_content
                            })
                        current_content = []
                        current_조 = ''
                        current_조_제목 = ''

                    title = match.group(2).strip()
                    title = re.sub(r'[·\u2024]+.*$', '', title).strip()
                    title = re.sub(r'[｛｝\[\]].*$', '', title).strip()
                    if len(title) > 30:
                        title = title[:30]
                    current_hierarchy['장'] = f"제{match.group(1)}장({title})" if title else f"제{match.group(1)}장"
                    current_hierarchy['절'] = ''
                    is_hierarchy = True

            # 절 체크
            if not is_hierarchy:
                match = patterns['절'].match(line_clean)
                if match:
                    if current_조:
                        cleaned_content = '\n'.join(current_content).strip()
                        if cleaned_content:
                            hierarchy = self._build_hierarchy(
                                current_hierarchy['편'], current_hierarchy['장'],
                                current_hierarchy['절'], current_조, current_조_제목
                            )
                            results.append({
                                '조항': hierarchy,
                                'content': cleaned_content
                            })
                        current_content = []
                        current_조 = ''
                        current_조_제목 = ''

                    title = match.group(2).strip()
                    title = re.sub(r'[·\u2024]+.*$', '', title).strip()
                    title = re.sub(r'[｛｝\[\]].*$', '', title).strip()
                    if len(title) > 30:
                        title = title[:30]
                    current_hierarchy['절'] = f"제{match.group(1)}절({title})" if title else f"제{match.group(1)}절"
                    is_hierarchy = True

            # 조 체크
            if not is_hierarchy:
                match = patterns['조'].match(line_clean)
                if match:
                    # 이전 조 저장
                    if current_조:
                        cleaned_content = '\n'.join(current_content).strip()
                        if cleaned_content:
                            hierarchy = self._build_hierarchy(
                                current_hierarchy['편'], current_hierarchy['장'],
                                current_hierarchy['절'], current_조, current_조_제목
                            )
                            results.append({
                                '조항': hierarchy,
                                'content': cleaned_content
                            })
                        current_content = []

                    jo_num = match.group(1)
                    jo_title = match.group(2) or ''
                    jo_title = re.sub(r'[·\u2024]+.*$', '', jo_title).strip() if jo_title else ''
                    current_조 = jo_num
                    current_조_제목 = jo_title
                    is_hierarchy = True
                    
                    # 같은 라인에 내용이 있으면 추가
                    remaining_content = line_clean[match.end():].strip()
                    if remaining_content and not remaining_content.startswith('['):
                        current_content.append(remaining_content)
                    continue

            # 내용 추가 (편/장/절/조가 아닌 경우)
            if not is_hierarchy and current_조:
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조:
            cleaned_content = '\n'.join(current_content).strip()
            if cleaned_content:
                hierarchy = self._build_hierarchy(
                    current_hierarchy['편'], current_hierarchy['장'],
                    current_hierarchy['절'], current_조, current_조_제목
                )
                results.append({
                    '조항': hierarchy,
                    'content': cleaned_content
                })

        return results

    def parse_special_yakgwan(self, text):
        """
        KB 업무용/영업용/이륜 특별약관 파싱
        - **제X조(제목)** 형식
        """
        lines = text.split('\n')
        results = []

        # 조 패턴 (볼드는 clean_line에서 제거됨)
        조_pattern = re.compile(r'^제\s*(\d+)\s*조\s*[\(〔](.+?)[\)〕]')

        current_특약명 = ''
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 목차 라인 필터링
            if '┃' in stripped or '│' in stripped:
                continue

            # 특약명 찾기 (**KB업무용자동차보험 특별약관** 같은 형식)
            if stripped.startswith('**KB') and '특별약관' in stripped:
                # 이전 조 저장
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy('', '', '', current_조, current_조_제목, current_특약명)
                        results.append({
                            '조항': hierarchy,
                            'content': cleaned_content
                        })
                    current_조 = ''
                    current_조_제목 = ''
                    current_content = []

                current_특약명 = stripped.replace('*', '').strip()
                continue

            # 조 매칭
            line_clean = self.clean_line(stripped)
            match = 조_pattern.match(line_clean)
            if match:
                # 이전 조 저장
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy('', '', '', current_조, current_조_제목, current_특약명)
                        results.append({
                            '조항': hierarchy,
                            'content': cleaned_content
                        })

                jo_num = match.group(1)
                jo_title = match.group(2) or ''
                current_조 = jo_num  # 조 번호만 저장
                current_조_제목 = jo_title  # 제목은 별도 저장
                current_content = []
                continue

            # 내용 추가
            if current_조:
                # 목차 라인 제외
                dots_count = stripped.count('·') + stripped.count('\u2024')
                if dots_count > 10:
                    continue
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조:
            cleaned_content = '\n'.join(current_content).strip()
            if cleaned_content:
                hierarchy = self._build_hierarchy('', '', '', current_조, current_조_제목, current_특약명)
                results.append({
                    '조항': hierarchy,
                    'content': cleaned_content
                })

        return results
    
    def _build_hierarchy(self, 편='', 장='', 절='', 조='', 조_제목='', 특약명=''):
        """
        계층구조 문자열 생성: 편>장>절>조 형식
        비어있는 계층은 제외
        특약명이 있으면 맨 앞에 추가
        """
        parts = []
        
        # 특약명 (특별약관용)
        if 특약명:
            parts.append(특약명)
        
        # 편
        if 편:
            parts.append(편)
        
        # 장
        if 장:
            parts.append(장)
        
        # 절
        if 절:
            parts.append(절)
        
        # 조 (제목 포함)
        if 조:
            if 조_제목:
                parts.append(f"제{조}조({조_제목})")
            else:
                parts.append(f"제{조}조")
        
        return '>'.join(parts) if parts else ''
