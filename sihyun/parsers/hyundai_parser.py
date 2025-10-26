"""
현대해상 전용 파서
- 페이지 헤더로 보통약관/특별약관이 반복 출현 (187회, 635회)
- 마크다운 헤더 없음
- 실제 본문 찾기 위해 페이지 헤더 필터링 필요
"""

import re
from .base_parser import BaseParser


class HyundaiParser(BaseParser):
    """현대해상 PDF 파서"""

    def get_company_name(self):
        return "현대"

    def split_sections(self, md_text):
        """
        페이지 헤더 필터링하여 보통약관/특별약관 분리
        현대는 보통약관/특별약관이 각 페이지에 반복 출현하므로
        실제 조 패턴이 시작되는 위치를 기준으로 분리
        """
        # 간단한 방법: 텍스트에서 최소 1000자 이후부터 찾기
        botong_idx = md_text.find('보통약관')

        # 보통약관 이후 충분히 떨어진 곳에서 특별약관 찾기
        special_idx = -1
        if botong_idx >= 0:
            search_start = botong_idx + 5000  # 최소 5000자 이후부터 특별약관 찾기
            special_idx = md_text.find('특별약관', search_start)

        if botong_idx >= 0 and special_idx > 0:
            return md_text[botong_idx:special_idx], md_text[special_idx:]
        elif botong_idx >= 0:
            # 특별약관을 못 찾은 경우, 절반으로 나누기
            mid = len(md_text) // 2
            return md_text[botong_idx:mid], md_text[mid:]
        else:
            return md_text, ""

    def parse_botong_yakgwan(self, text):
        """롯데 보통약관 파싱 - 제X조(제목) 형식"""
        lines = text.split('\n')
        results = []

        patterns = {
            '편': re.compile(r'^#+\s*제?\s*([0-9IVXivx]+)\s*편\s+(.+)'),
            '장': re.compile(r'^#+\s*제?\s*(\d+)\s*장\s+(.+)'),
            '절': re.compile(r'^#+\s*제?\s*(\d+)\s*절\s+(.+)'),
            '조': re.compile(r'^제\s*(\d+)\s*조\s*(?:[\(〔](.+?)[\)〕])?(?:\s*[·\u2024\.]+.*)?$'),
        }

        current_편 = ''
        current_장 = ''
        current_절 = ''
        current_조 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('#') and '보통약관' in stripped:
                continue

            # 편 매칭
            match = patterns['편'].match(stripped)
            if match:
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy_botong(current_편, current_장, current_절, current_조)
                        results.append({
                            '조항': hierarchy,
                            '내용': cleaned_content
                        })
                    current_조 = ''
                    current_content = []

                current_편 = f"제{match.group(1)}편({match.group(2)})"
                current_장 = ''
                current_절 = ''
                continue

            # 장 매칭
            match = patterns['장'].match(stripped)
            if match:
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy_botong(current_편, current_장, current_절, current_조)
                        results.append({
                            '조항': hierarchy,
                            '내용': cleaned_content
                        })
                    current_조 = ''
                    current_content = []

                current_장 = f"제{match.group(1)}장({match.group(2)})"
                current_절 = ''
                continue

            # 절 매칭
            match = patterns['절'].match(stripped)
            if match:
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy_botong(current_편, current_장, current_절, current_조)
                        results.append({
                            '조항': hierarchy,
                            '내용': cleaned_content
                        })
                    current_조 = ''
                    current_content = []

                current_절 = f"제{match.group(1)}절({match.group(2)})"
                continue

            # 조 매칭
            line_clean = self.clean_line(stripped)
            match = patterns['조'].match(line_clean)
            if match:
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy_botong(current_편, current_장, current_절, current_조)
                        results.append({
                            '조항': hierarchy,
                            '내용': cleaned_content
                        })

                jo_num = match.group(1)
                jo_title = match.group(2) or ''
                current_조 = f"제{jo_num}조({jo_title})" if jo_title else f"제{jo_num}조"
                current_content = []
                continue

            # 내용 추가
            if current_조:
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('.')
                if dots_count > 10:
                    continue
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조:
            cleaned_content = '\n'.join(current_content).strip()
            if cleaned_content:
                hierarchy = self._build_hierarchy_botong(current_편, current_장, current_절, current_조)
                results.append({
                    '조항': hierarchy,
                    '내용': cleaned_content
                })

        return results

    def _build_hierarchy_botong(self, pyeon, jang, jeol, jo):
        """보통약관 계층 구조 생성"""
        parts = []
        if pyeon:
            parts.append(pyeon)
        if jang:
            parts.append(jang)
        if jeol:
            parts.append(jeol)
        if jo:
            parts.append(jo)
        return '>'.join(parts)

    def parse_special_yakgwan(self, text):
        """롯데 특별약관 파싱"""
        lines = text.split('\n')
        results = []

        조_pattern = re.compile(r'^제\s*(\d+)\s*조\s*(?:[\(〔](.+?)[\)〕])?(?:\s*[·\u2024\.]+.*)?$')

        current_특약명 = ''
        current_조 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith('##'):
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy_special(current_특약명, current_조)
                        results.append({
                            '조항': hierarchy,
                            '내용': cleaned_content
                        })
                    current_조 = ''
                    current_content = []

                current_특약명 = stripped.replace('#', '').strip()
                continue

            # 조 매칭
            line_clean = self.clean_line(stripped)
            match = 조_pattern.match(line_clean)
            if match:
                if current_조:
                    cleaned_content = '\n'.join(current_content).strip()
                    if cleaned_content:
                        hierarchy = self._build_hierarchy_special(current_특약명, current_조)
                        results.append({
                            '조항': hierarchy,
                            '내용': cleaned_content
                        })

                jo_num = match.group(1)
                jo_title = match.group(2) or ''
                current_조 = f"제{jo_num}조({jo_title})" if jo_title else f"제{jo_num}조"
                current_content = []
                continue

            # 내용 추가
            if current_조:
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('.')
                if dots_count > 10:
                    continue
                current_content.append(stripped)

        # 마지막 조 저장
        if current_조:
            cleaned_content = '\n'.join(current_content).strip()
            if cleaned_content:
                hierarchy = self._build_hierarchy_special(current_특약명, current_조)
                results.append({
                    '조항': hierarchy,
                    '내용': cleaned_content
                })

        return results

    def _build_hierarchy_special(self, special_name, jo):
        """특별약관 계층 구조 생성"""
        parts = []
        if special_name:
            parts.append(special_name)
        if jo:
            parts.append(jo)
        return '>'.join(parts)
