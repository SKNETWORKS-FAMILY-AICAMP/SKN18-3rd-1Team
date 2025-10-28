"""
KB 손해보험 전용 파서
- 마크다운 헤더(##) 사용
- **X조** 형식 사용
- 보통약관/특별약관이 마크다운 헤더로 명확히 구분됨
"""

import re
from .base_parser import BaseParser


class KBParser(BaseParser):
    """KB 손해보험 PDF 파서"""

    def get_company_name(self):
        return "KB"

    def split_sections(self, md_text):
        """
        마크다운 헤더 기반으로 보통약관/특별약관 분리
        preprocess.py 로직 적용
        """
        lines = md_text.split('\n')
        line_char_positions = []
        char_pos = 0
        for line in lines:
            line_char_positions.append(char_pos)
            char_pos += len(line) + 1

        botong_start_idx = -1
        special_start_idx = -1

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 보통약관 헤더 찾기
            if botong_start_idx == -1:
                # 마크다운 헤더로 된 보통약관
                if '보통약관' in stripped and stripped.startswith('#'):
                    botong_start_idx = line_char_positions[i]
                # 일반 "보통약관" - 다음 라인에 실제 내용이 있는지 확인
                elif (stripped == '보통약관' or (stripped.startswith('보통약관') and len(stripped) < 20)):
                    # 다음 50라인 이내에 실제 조 내용이 있는지 확인
                    has_real_content = False
                    for j in range(i+1, min(i+50, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith('**') and '조' in next_line:
                            has_real_content = True
                            break
                        if len(next_line) > 50 and not next_line.startswith('제') and '·' not in next_line:
                            has_real_content = True
                            break
                    if has_real_content:
                        botong_start_idx = line_char_positions[i]

            # 특별약관 헤더 찾기
            if special_start_idx == -1 and botong_start_idx >= 0:
                # 마크다운 헤더로 된 특별약관
                if '특별약관' in stripped and stripped.startswith('#'):
                    if line_char_positions[i] > botong_start_idx:
                        special_start_idx = line_char_positions[i]
                        break
                # 일반 "특별약관" - 실제 내용 확인
                elif (stripped == '특별약관' or (stripped.startswith('특별약관') and len(stripped) < 20)):
                    if line_char_positions[i] > botong_start_idx:
                        has_real_content = False
                        for j in range(i+1, min(i+50, len(lines))):
                            next_line = lines[j].strip()
                            if next_line.startswith('**') and '조' in next_line:
                                has_real_content = True
                                break
                            if len(next_line) > 50 and not next_line.startswith('제') and '·' not in next_line:
                                has_real_content = True
                                break
                        if has_real_content:
                            special_start_idx = line_char_positions[i]
                            break

        # 헤더를 찾지 못한 경우 폴백
        if botong_start_idx == -1:
            first_idx = md_text.find('보통약관')
            if first_idx >= 0:
                second_idx = md_text.find('보통약관', first_idx + 10)
                if second_idx >= 0:
                    botong_start_idx = second_idx
                else:
                    botong_start_idx = first_idx

        if special_start_idx == -1:
            search_start = botong_start_idx if botong_start_idx >= 0 else 0
            search_start = max(search_start, 1000)
            special_start_idx = md_text.find('특별약관', search_start)

        if botong_start_idx >= 0 and special_start_idx >= 0:
            return md_text[botong_start_idx:special_start_idx], md_text[special_start_idx:]
        elif botong_start_idx >= 0:
            return md_text[botong_start_idx:], ""
        elif special_start_idx >= 0:
            return "", md_text[special_start_idx:]
        else:
            return md_text, ""

    def parse_botong_yakgwan(self, text):
        """
        KB 보통약관 파싱 (preprocess.py 로직 적용)
        - 편/장/절/조 구조 파싱
        """
        # 정규표현식 패턴 (preprocess.py와 동일)
        patterns = {
            '편': re.compile(r'^제\s*(\d+)\s*편\s+(.+?)(?:\s*[·\u2024]+.*)?$'),
            '장': re.compile(r'^제\s*(\d+)\s*장\s+(.+?)(?:\s*[·\u2024]+.*)?$'),
            '절': re.compile(r'^제\s*(\d+)\s*절\s+(.+?)(?:\s*[·\u2024]+.*)?$'),
            '조': re.compile(r'^(?:\*\*)?(?:제\s*)?(\d+)\s*조(?:\*\*)?\s*(?:[\(〔](.+?)[\)〕]|\s+(.+?))?(?:\s*[·\u2024]+.*)?$'),
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
                    jo_title = match.group(2) or match.group(3) or ''
                    jo_title = re.sub(r'[·\u2024]+.*$', '', jo_title).strip() if jo_title else ''
                    current_조 = jo_num
                    current_조_제목 = jo_title
                    is_hierarchy = True
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
        KB 특별약관 파싱
        - **X조** 형식과 제X조 형식 모두 지원
        """
        lines = text.split('\n')
        results = []

        # 조 패턴
        조_pattern = re.compile(r'^(?:\*\*)?(?:제\s*)?(\d+)\s*조(?:\*\*)?\s*(?:[\(〔](.+?)[\)〕]|\s+(.+?))?(?:\s*[·\u2024]+.*)?$')

        current_특약명 = ''
        current_조 = ''
        current_조_제목 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # 마크다운 헤더로 특약명 파악
            if stripped.startswith('##'):
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

                # 새 특약명
                current_특약명 = stripped.replace('#', '').strip()
                continue

            # 조 매칭
            # 먼저 목차 라인 필터링 (┃ 또는 │ 기호가 있으면 목차)
            if '┃' in stripped or '│' in stripped:
                continue

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
                jo_title = match.group(2) or match.group(3) or ''
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
