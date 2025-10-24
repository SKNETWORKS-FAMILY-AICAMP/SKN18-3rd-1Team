import csv
import pathlib
import pymupdf
import pymupdf4llm
import re
from typing import Iterable, Dict, List

def extract_company_and_insurance_name(filename: str) -> tuple[str, str]:
    """
    파일명에서 회사명과 보험명을 추출
    예: 'KB_개인용자동차보험' -> ('KB', '개인용자동차보험')
    """
    # 파일명에서 확장자 제거
    name = pathlib.Path(filename).stem

    # 언더스코어나 회사명 패턴으로 분리
    company_patterns = ['KB', '롯데', '삼성화재', '하나', '현대']

    for company in company_patterns:
        if company.lower() in name.lower() or company in name:
            # 회사명 이후 텍스트를 보험명으로
            parts = name.split('_')
            if len(parts) >= 2:
                company_name = parts[0]
                insurance_name = '_'.join(parts[1:])
            else:
                # 회사명 패턴 매칭
                if company.lower() in name.lower():
                    idx = name.lower().find(company.lower())
                    company_name = name[idx:idx+len(company)]
                    insurance_name = name[idx+len(company):]
                else:
                    company_name = company
                    insurance_name = name.replace(company, '').strip('_-')

            # 날짜 패턴 제거 (2025-09-01 등)
            insurance_name = re.sub(r'\d{4}-\d{2}-\d{2}', '', insurance_name).strip('_-')
            return company_name, insurance_name

    # 매칭 실패 시 기본값
    return "미분류", name

def parse_hierarchy_structure(md_text: str) -> List[Dict]:
    """
    마크다운 텍스트에서 보통약관과 특별약관을 구분하여 파싱

    Returns:
        List[Dict]: [
            {
                '약관구분': '보통약관' or '특별약관',
                '편': '제1편 용어의 정의',
                '장': '제1장 ...',
                '절': '제1절 ...',
                '특약명': '특별약관명',
                '조': '제1조 (용어의 정의)',
                'content': '실제 내용...'
            },
            ...
        ]
    """
    # 개선된 보통약관/특별약관 분리 로직
    # 목차가 아닌 실제 본문 섹션 헤더를 찾기

    lines = md_text.split('\n')
    botong_start_idx = -1
    special_start_idx = -1

    # 라인 번호를 문자 인덱스로 변환하기 위한 누적 길이 계산
    line_char_positions = []
    char_pos = 0
    for line in lines:
        line_char_positions.append(char_pos)
        char_pos += len(line) + 1  # +1 for newline

    #  실제 본문 섹션 헤더 찾기
    botong_last_pyeon = -1  # 보통약관의 마지막 편 라인 번호

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 보통약관 헤더: 독립된 라인의 "보통약관" (목차 제외)
        # 다음 라인에 "제1편"이 있으면 본문 시작으로 간주
        if botong_start_idx == -1 and stripped == '보통약관':
            # 다음 몇 라인에 제1편이 있는지 확인
            for j in range(i+1, min(i+5, len(lines))):
                if '제1편' in lines[j] or '제 1 편' in lines[j]:
                    botong_start_idx = line_char_positions[i]
                    break

        # 보통약관의 마지막 편 찾기 (제4편 또는 제5편)
        if botong_start_idx != -1 and special_start_idx == -1:
            if '제4편' in stripped or '제5편' in stripped or '제 4 편' in stripped or '제 5 편' in stripped:
                botong_last_pyeon = i

        # 특별약관 헤더: 독립된 라인의 "특별약관" (목차 제외)
        # 보통약관 이후에 나오는 것만 찾기
        if special_start_idx == -1 and stripped == '특별약관' and i > 100:
            # 목차가 아닌 실제 섹션 헤더인지 확인
            # 이전이나 다음에 제1편 패턴이 있으면 본문 시작으로 간주
            for j in range(max(0, i-3), min(i+10, len(lines))):
                if ('제1편' in lines[j] or '제 1 편' in lines[j]) and j != i:
                    special_start_idx = line_char_positions[i]
                    break

    # 특별약관 헤더를 찾지 못한 경우, 보통약관의 마지막 편 이후를 특별약관으로 간주
    if special_start_idx == -1 and botong_last_pyeon > 0:
        # 보통약관 이후에 제1조가 다시 나타나면 특별약관 시작으로 간주
        # (특별약관의 각 특약들이 제1조부터 시작하는 경우가 많음)
        import re
        jo1_pattern = re.compile(r'^\*?\*?제\s*1\s*조')

        for i in range(botong_last_pyeon + 100, min(len(lines), botong_last_pyeon + 5000)):
            if jo1_pattern.search(lines[i].strip()):
                # 제1조를 찾았으면 특별약관 시작으로 간주
                special_start_idx = line_char_positions[i]
                break

    # 보통약관/특별약관 헤더를 찾지 못한 경우 기존 방식 사용
    if botong_start_idx == -1:
        botong_start_idx = md_text.find('보통약관')
    if special_start_idx == -1:
        # 특별약관은 보통약관 이후에 있어야 함
        special_start_idx = md_text.find('특별약관', botong_start_idx if botong_start_idx >= 0 else 0)

    results = []

    # 보통약관과 특별약관의 순서 확인
    if botong_start_idx >= 0 and special_start_idx >= 0:
        # 둘 다 있는 경우
        if botong_start_idx < special_start_idx:
            # 보통약관 -> 특별약관 순서
            botong_text = md_text[botong_start_idx:special_start_idx]
            special_text = md_text[special_start_idx:]
        else:
            # 특별약관 -> 보통약관 순서 (드문 경우)
            special_text = md_text[special_start_idx:botong_start_idx]
            botong_text = md_text[botong_start_idx:]
    elif botong_start_idx >= 0:
        # 보통약관만 있는 경우
        botong_text = md_text[botong_start_idx:]
        special_text = None
    elif special_start_idx >= 0:
        # 특별약관만 있는 경우
        botong_text = None
        special_text = md_text[special_start_idx:]
    else:
        # 둘 다 없는 경우
        return results

    # 보통약관 파싱
    if botong_text:
        botong_results = parse_botong_yakgwan(botong_text)
        results.extend(botong_results)

    # 특별약관 파싱
    if special_text:
        special_results = parse_special_yakgwan(special_text)
        results.extend(special_results)

    return results

def parse_botong_yakgwan(md_text: str) -> List[Dict]:
    """
    보통약관 파싱: 보통약관 > 편 > 장 > 절 > 조 구조
    """

    # 계층 구조 패턴 정의
    patterns = {
        '편': re.compile(r'^제\s*(\d+)\s*편\s+(.+)$'),
        '장': re.compile(r'^제\s*(\d+)\s*장\s+(.+)$'),
        '절': re.compile(r'^제\s*(\d+)\s*절\s+(.+)$'),
        '조': re.compile(r'^\*?\*?제?\s*(\d+)\s*조\s*(?:[\(〔](.+?)[\)〕]|\s+(.+?))?$'),
    }

    results = []
    current_hierarchy = {
        '편': '',
        '장': '',
        '절': ''
    }
    current_조 = ''
    current_content = []

    lines = md_text.split('\n')

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if line_stripped.startswith('#'):
            continue

        if '····' in line_stripped or '··········' in line_stripped:
            continue

        is_hierarchy = False
        line_clean = re.sub(r'\*+', '', line_stripped)

        # 편 체크
        match = patterns['편'].match(line_clean)
        if match:
            title = match.group(2).strip()

            # 편이 바뀌기 전에 현재 조 저장
            if current_조 and current_content:
                results.append({
                    '약관구분': '보통약관',
                    '편': current_hierarchy['편'],
                    '장': current_hierarchy['장'],
                    '절': current_hierarchy['절'],
                    '특약명': '',
                    '조': current_조,
                    'content': '\n'.join(current_content).strip()
                })
                current_content = []
                # current_조는 초기화하지 않음 (원본 데이터에서 조 번호가 계속 이어짐)

            title = re.sub(r'[·\u2024]+.*$', '', title).strip()
            title = re.sub(r'[｛｝\[\]].*$', '', title).strip()
            if len(title) > 30:
                title = title[:30]
            current_hierarchy['편'] = f"제{match.group(1)}편 {title}".strip() if title else f"제{match.group(1)}편"
            current_hierarchy['장'] = ''
            current_hierarchy['절'] = ''
            is_hierarchy = True

        # 장 체크
        if not is_hierarchy:
            match = patterns['장'].match(line_clean)
            if match:
                if current_조 and current_content:
                    results.append({
                        '약관구분': '보통약관',
                        '편': current_hierarchy['편'],
                        '장': current_hierarchy['장'],
                        '절': current_hierarchy['절'],
                        '특약명': '',
                        '조': current_조,
                        'content': '\n'.join(current_content).strip()
                    })
                    current_content = []
                    # current_조는 초기화하지 않음 (원본 데이터에서 조 번호가 계속 이어짐)

                title = match.group(2).strip()
                title = re.sub(r'[·\u2024]+.*$', '', title).strip()
                title = re.sub(r'[｛｝\[\]].*$', '', title).strip()
                if len(title) > 30:
                    title = title[:30]
                current_hierarchy['장'] = f"제{match.group(1)}장 {title}".strip() if title else f"제{match.group(1)}장"
                current_hierarchy['절'] = ''
                is_hierarchy = True

        # 절 체크
        if not is_hierarchy:
            match = patterns['절'].match(line_clean)
            if match:
                if current_조 and current_content:
                    results.append({
                        '약관구분': '보통약관',
                        '편': current_hierarchy['편'],
                        '장': current_hierarchy['장'],
                        '절': current_hierarchy['절'],
                        '특약명': '',
                        '조': current_조,
                        'content': '\n'.join(current_content).strip()
                    })
                    current_content = []
                    # current_조는 초기화하지 않음 (원본 데이터에서 조 번호가 계속 이어짐)

                title = match.group(2).strip()
                title = re.sub(r'[·\u2024]+.*$', '', title).strip()
                title = re.sub(r'[｛｝\[\]].*$', '', title).strip()
                if len(title) > 30:
                    title = title[:30]
                current_hierarchy['절'] = f"제{match.group(1)}절 {title}".strip() if title else f"제{match.group(1)}절"
                is_hierarchy = True

        # 조 체크
        if not is_hierarchy:
            match = patterns['조'].match(line_clean)
            if match:
                if current_조 and current_content:
                    results.append({
                        '약관구분': '보통약관',
                        '편': current_hierarchy['편'],
                        '장': current_hierarchy['장'],
                        '절': current_hierarchy['절'],
                        '특약명': '',
                        '조': current_조,
                        'content': '\n'.join(current_content).strip()
                    })
                    current_content = []

                jo_title = match.group(2) if match.group(2) else (match.group(3) if match.group(3) else "")
                if jo_title:
                    jo_title = jo_title.strip()
                    current_조 = f"제{match.group(1)}조 ({jo_title})"
                else:
                    current_조 = f"제{match.group(1)}조"
                is_hierarchy = True

        if not is_hierarchy and current_조:
            if not re.match(r'^\d+\s*KB', line_stripped) and not re.match(r'^KB.*\d+$', line_stripped):
                current_content.append(line)

    # 마지막 조 저장
    if current_조 and current_content:
        results.append({
            '약관구분': '보통약관',
            '편': current_hierarchy['편'],
            '장': current_hierarchy['장'],
            '절': current_hierarchy['절'],
            '특약명': '',
            '조': current_조,
            'content': '\n'.join(current_content).strip()
        })

    return results

def parse_special_yakgwan(md_text: str) -> List[Dict]:
    """
    특별약관 파싱: 특별약관 > 특약명 > 조 구조
    
    특약명 패턴:
    1. 롯데: "제1편 긴급출동 서비스"
    2. KB 등: 특약명이 별도 구조 (조 단위로만 구분)
    """
    patterns = {
        # 특약명 패턴 1: "제X편 특약명" (롯데)
        '특약_편': re.compile(r'^제\s*(\d+)\s*편\s+(.+)$'),
        # 특약명 패턴 2: "제X편 ｢특약명｣" (일부 회사)
        '특약_괄호': re.compile(r'^제\s*(\d+)\s*편\s+[｢「](.+?)[｣」]'),
        # 조 패턴
        '조': re.compile(r'^\*?\*?제?\s*(\d+)\s*조\s*(?:[\(〔](.+?)[\)〕]|\s+(.+?))?$'),
    }

    results = []
    current_특약명 = ''
    current_조 = ''
    current_content = []

    lines = md_text.split('\n')

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        if line_stripped.startswith('#'):
            continue

        if '····' in line_stripped or '··········' in line_stripped:
            continue

        is_hierarchy = False
        line_clean = re.sub(r'\*+', '', line_stripped)

        # 특약명 체크 - 패턴 1: 괄호 형식 (우선순위 높음)
        match = patterns['특약_괄호'].match(line_clean)
        if match:
            # 이전 조 저장
            if current_조 and current_content:
                results.append({
                    '약관구분': '특별약관',
                    '편': '',
                    '장': '',
                    '절': '',
                    '특약명': current_특약명,
                    '조': current_조,
                    'content': '\n'.join(current_content).strip()
                })
                current_content = []
                current_조 = ''

            special_name = match.group(2).strip()
            # 불필요한 텍스트 제거
            special_name = re.sub(r'에서 보상하는 손해.*$', '', special_name).strip()
            special_name = re.sub(r'[·\u2024]+.*$', '', special_name).strip()
            current_특약명 = special_name
            is_hierarchy = True
        
        # 특약명 체크 - 패턴 2: 제X편 형식 (롯데 등)
        if not is_hierarchy:
            match = patterns['특약_편'].match(line_clean)
            if match and len(line_clean) < 100:  # 너무 긴 라인은 제외
                # 이전 조 저장
                if current_조 and current_content:
                    results.append({
                        '약관구분': '특별약관',
                        '편': '',
                        '장': '',
                        '절': '',
                        '특약명': current_특약명,
                        '조': current_조,
                        'content': '\n'.join(current_content).strip()
                    })
                    current_content = []
                    current_조 = ''

                special_name = match.group(2).strip()
                # 불필요한 텍스트 제거
                special_name = re.sub(r'에서 보상하는 손해.*$', '', special_name).strip()
                special_name = re.sub(r'[·\u2024]+.*$', '', special_name).strip()
                special_name = re.sub(r'\d+\s*$', '', special_name).strip()  # 끝의 숫자 제거 (페이지 번호)
                if len(special_name) > 3:  # 너무 짧은 이름 제외
                    current_특약명 = f"제{match.group(1)}편 {special_name}"
                    is_hierarchy = True

        # 조 체크
        if not is_hierarchy:
            match = patterns['조'].match(line_clean)
            if match:
                if current_조 and current_content:
                    results.append({
                        '약관구분': '특별약관',
                        '편': '',
                        '장': '',
                        '절': '',
                        '특약명': current_특약명,
                        '조': current_조,
                        'content': '\n'.join(current_content).strip()
                    })
                    current_content = []

                jo_title = match.group(2) if match.group(2) else (match.group(3) if match.group(3) else "")
                if jo_title:
                    jo_title = jo_title.strip()
                    current_조 = f"제{match.group(1)}조 ({jo_title})"
                else:
                    current_조 = f"제{match.group(1)}조"
                is_hierarchy = True

        if not is_hierarchy and current_조:
            if not re.match(r'^\d+\s*KB', line_stripped) and not re.match(r'^KB.*\d+$', line_stripped):
                current_content.append(line)

    # 마지막 조 저장
    if current_조 and current_content:
        results.append({
            '약관구분': '특별약관',
            '편': '',
            '장': '',
            '절': '',
            '특약명': current_특약명,
            '조': current_조,
            'content': '\n'.join(current_content).strip()
        })

    return results

def clean_content(content: str) -> str:
    """
    page_content용 텍스트 정제
    표는 마크다운 기호(|, -, 등)를 제거하고 데이터만 유지
    """
    # 이미지 제거
    content = re.sub(r"!\[.*?\]\(.*?\)", "", content)

    # 표 처리 및 마크다운 기호 제거
    lines = content.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # 표 라인인지 확인 (|로 시작하고 |로 구분)
        if '|' in stripped and stripped.startswith('|'):
            # 구분선 라인은 제거 (|---|---|)
            if re.match(r'^\|[\s\-:]+\|', stripped):
                continue

            # 표 데이터 라인: | 제거하고 데이터만 유지
            # | 항목1 | 항목2 | -> 항목1, 항목2
            cells = [cell.strip() for cell in stripped.split('|') if cell.strip()]
            if cells:
                cleaned_lines.append(', '.join(cells))
        else:
            # 표가 아니면 마크다운 기호 제거
            line = re.sub(r"[#*_>`~]+", " ", line)
            line = re.sub(r"={2,}|-{2,}|_{2,}", " ", line)
            cleaned_lines.append(line)

    content = '\n'.join(cleaned_lines)

    # 목차, 페이지 번호 제거
    content = re.sub(r"(?i)^ *목차.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"(?i)(page\s*\d+|\d+\s*페이지)", " ", content)

    # URL 제거
    content = re.sub(r"https?://\S+|www\.\S+", "", content)

    # 연속 공백 정리
    content = re.sub(r" +", " ", content)
    content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)
    content = content.strip()

    return content

def iter_pdf_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    """모든 PDF 파일을 순회"""
    return root.rglob("*.pdf")

def convert_all_pdfs_to_single_csv(pdf_root: pathlib.Path, output_csv_path: pathlib.Path):
    """
    PDF 전체를 순회하며 편-장-절-조 구조로 파싱 후 CSV 저장 편-장-절-조 = 조항에 담기

    CSV 컬럼: 회사명, 보험명, 조항, 내용
    """
    if not pdf_root.exists():
        raise FileNotFoundError(f"PDF 폴더를 찾을 수 없습니다: {pdf_root}")

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)

    total, success, skipped, total_rows = 0, 0, 0, 0

    with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        # 새로운 컬럼 구조: 회사명, 보험명, 조항, 내용
        writer.writerow(["회사명", "보험명", "조항", "내용"])

        for pdf_file in iter_pdf_files(pdf_root):
            total += 1

            # 파일명에서 회사명과 보험명 추출
            company_name, insurance_name = extract_company_and_insurance_name(pdf_file.name)

            try:
                print(f"[{total}] 처리 중: {pdf_file.name}")

                # PDF를 마크다운으로 변환
                md_text = pymupdf4llm.to_markdown(str(pdf_file))

                # 편-장-절-조 구조로 파싱
                sections = parse_hierarchy_structure(md_text)

                if not sections:
                    print(f"[경고] 구조 파싱 실패: {pdf_file.name} - 조 항목을 찾을 수 없음")
                    skipped += 1
                    continue

                # 각 조별로 CSV 행 작성
                for section in sections:
                    # 내용 정제
                    cleaned_content = clean_content(section['content'])

                    if not cleaned_content.strip():
                        continue

                    # 조항 경로 생성
                    clause_path_parts = []

                    # 약관 구분 추가
                    if section.get('약관구분'):
                        clause_path_parts.append(section['약관구분'])

                    # 보통약관인 경우: 보통약관 > 편 > 장 > 절 > 조
                    if section.get('약관구분') == '보통약관':
                        if section.get('편'):
                            clause_path_parts.append(section['편'])
                        if section.get('장'):
                            clause_path_parts.append(section['장'])
                        if section.get('절'):
                            clause_path_parts.append(section['절'])
                        if section.get('조'):
                            clause_path_parts.append(section['조'])

                    # 특별약관인 경우: 특별약관 > 특약명 > 조
                    elif section.get('약관구분') == '특별약관':
                        if section.get('특약명'):
                            clause_path_parts.append(section['특약명'])
                        if section.get('조'):
                            clause_path_parts.append(section['조'])

                    clause_path = ' > '.join(clause_path_parts)

                    # CSV 행 작성
                    writer.writerow([
                        company_name,
                        insurance_name,
                        clause_path,
                        cleaned_content
                    ])
                    total_rows += 1

                success += 1
                print(f"[완료] [{company_name}] {insurance_name} - {len(sections)}개 조항 저장")

            except pymupdf.FileDataError:
                print(f"[경고] 손상된 PDF 건너뜀: {pdf_file}")
                skipped += 1
            except RuntimeError as err:
                print(f"[경고] 열 수 없음: {pdf_file} ({err})")
                skipped += 1
            except Exception as err:
                print(f"[경고] 처리 실패: {pdf_file} ({err})")
                skipped += 1

    print(f"\n[결과] 총 {total}개 PDF 중 {success}개 성공, {skipped}개 실패")
    print(f"[결과] 총 {total_rows}개의 조항(행) 저장")
    print(f"[결과] 결과 파일: {output_csv_path}")

if __name__ == "__main__":
    base_dir = pathlib.Path(__file__).resolve().parent
    pdf_root_dir = base_dir / "data"
    results_root_dir = base_dir / "results" / "pdftocsv"
    results_root_dir.mkdir(parents=True, exist_ok=True)

    all_csv_path = results_root_dir / "insurance_clauses.csv"

    print("=" * 80)
    print("보험 약관 전처리 시작")
    print(f"입력 폴더: {pdf_root_dir}")
    print(f"출력 파일: {all_csv_path}")
    print("=" * 80)

    convert_all_pdfs_to_single_csv(pdf_root_dir, all_csv_path)