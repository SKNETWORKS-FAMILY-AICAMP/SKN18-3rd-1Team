"""
삼성화재 영업용 전용 파서
- 볼드 처리 없음
- 제1편 (공백과 점 없음)
- 일반 텍스트 형식
"""

import re
from .base_parser import BaseParser


class SamsungCommercialParser(BaseParser):
    """삼성화재 영업용 PDF 파서"""

    def get_company_name(self):
        return "삼성화재"

    def split_sections(self, md_text):
        """
        보통약관/특별약관 분리 - 삼성화재 영업용 구조
        - 보통약관: 본문 "제1편 용어의 정의" 시작
        - 특별약관: "1장. 운전자 연령제한" 본문 시작 (목차 제외)
        """
        import re
        
        # 1. 보통약관 본문 시작
        pyeon1_pattern = re.compile(r'제1편\s+용어의\s*정의')
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
        
        # 2. 특별약관 본문 시작: "1장. 운전자 연령제한" 찾기 (목차 아님)
        장1_pattern = re.compile(r'1장\.\s*운전자\s*연령제한')
        장1_matches = list(장1_pattern.finditer(md_text, botong_start_idx + 50000))
        
        if len(장1_matches) >= 2:
            # 두 번째가 본문 (첫 번째는 목차)
            special_idx = 장1_matches[1].start()
        elif len(장1_matches) == 1:
            # 하나만 있으면 근처에 "[1]" 패턴이 있는지 확인
            match_pos = 장1_matches[0].start()
            nearby_text = md_text[match_pos:match_pos+500]
            if re.search(r'\[1\]\s*운전자연령', nearby_text):
                # [1] 패턴이 있으면 본문
                special_idx = match_pos
            else:
                # 없으면 목차이므로 "자동차보험 특별약관" 헤더 이후에서 다시 찾기
                special_header = md_text.find('자동차보험 특별약관', botong_start_idx + 50000)
                if special_header > 0:
                    장_pattern2 = re.compile(r'1장\.\s*운전자')
                    장_matches2 = list(장_pattern2.finditer(md_text, special_header + 2000))
                    if 장_matches2:
                        special_idx = 장_matches2[0].start()
                    else:
                        special_idx = special_header
                else:
                    special_idx = match_pos
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
        """삼성화재 영업용 보통약관 파싱 - 볼드 없음"""
        lines = text.split('\n')
        results = []

        # 영업용은 공백/점 없음
        patterns = {
            '편': re.compile(r'^제(\d+)편\s+(.+)'),
            '장': re.compile(r'^제(\d+)장\s+(.+)'),
            '절': re.compile(r'^제(\d+)절\s+(.+)'),
            '조': re.compile(r'^제(\d+)조\s*[\(〔](.+?)[\)〕]'),
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
        """삼성화재 영업용 특별약관 파싱 - 편>장>[번호] 구조"""
        lines = text.split('\n')
        results = []

        # 패턴
        편_pattern = re.compile(r'^제(\d+)편\.\s*(.+)')
        장_pattern = re.compile(r'^(\d+)장\.\s*(.+)')
        특약_pattern = re.compile(r'^\[(\d+(?:-\d+)?)\]\s*(.+)')

        current_편 = ''
        current_장 = ''
        current_특약명 = ''
        current_content = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            is_hierarchy = False

            # 편 체크
            match = 편_pattern.match(stripped)
            if match:
                if current_특약명 and current_content:
                    results.append({
                        '약관구분': '특별약관',
                        '조항': self._build_special_hierarchy(current_편, current_장, current_특약명),
                        '내용': '\n'.join(current_content).strip()
                    })
                    current_content = []
                    current_특약명 = ''
                
                편번호 = match.group(1)
                편제목 = match.group(2).strip()
                current_편 = f"제{편번호}편({편제목})"
                current_장 = ''
                is_hierarchy = True

            # 장 체크
            if not is_hierarchy:
                match = 장_pattern.match(stripped)
                if match:
                    if current_특약명 and current_content:
                        results.append({
                            '약관구분': '특별약관',
                            '조항': self._build_special_hierarchy(current_편, current_장, current_특약명),
                            '내용': '\n'.join(current_content).strip()
                        })
                        current_content = []
                        current_특약명 = ''
                    
                    장번호 = match.group(1)
                    장제목 = match.group(2).strip()
                    current_장 = f"{장번호}장({장제목})"
                    is_hierarchy = True

            # [번호] 특약명 체크
            if not is_hierarchy:
                match = 특약_pattern.match(stripped)
                if match:
                    # 이전 특약 저장
                    if current_특약명 and current_content:
                        results.append({
                            '약관구분': '특별약관',
                            '조항': self._build_special_hierarchy(current_편, current_장, current_특약명),
                            '내용': '\n'.join(current_content).strip()
                        })
                        current_content = []
                    
                    특약번호 = match.group(1)
                    특약제목 = match.group(2).strip()
                    current_특약명 = f"[{특약번호}] {특약제목}"
                    is_hierarchy = True
                    continue

            # 내용 추가
            if not is_hierarchy and current_특약명:
                # 목차 필터링
                dots_count = stripped.count('·') + stripped.count('\u2024') + stripped.count('…')
                if dots_count > 10:
                    continue
                # 페이지 번호 필터링
                if re.match(r'^\*\*\d+\*\*$', stripped):
                    continue
                current_content.append(stripped)

        # 마지막 특약 저장
        if current_특약명 and current_content:
            results.append({
                '약관구분': '특별약관',
                '조항': self._build_special_hierarchy(current_편, current_장, current_특약명),
                '내용': '\n'.join(current_content).strip()
            })

        return results

    def _build_special_hierarchy(self, 편='', 장='', 특약명=''):
        """특별약관 계층구조 생성"""
        parts = []
        if 편:
            parts.append(편)
        if 장:
            parts.append(장)
        if 특약명:
            parts.append(특약명)
        return '>'.join(parts) if parts else ''

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

