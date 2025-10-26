"""
회사별 전용 파서를 사용한 보험 PDF 전처리 스크립트 (버전 2)
각 회사의 PDF 구조에 맞는 최적화된 파서 사용
"""

import pathlib
import csv
from parsers import (
    KBParser, KBBusinessParser,
    LotteParser, LotteBusinessParser, LotteWheelParser,
    SamsungBusinessParser, SamsungCommercialParser, SamsungWheelParser, SamsungOnedayParser, SamsungPersonalParser,
    HanaParser, HyundaiParser
)


# 회사명 -> 파서 클래스 매핑
COMPANY_PARSERS = {
    'kb': KBParser,  # 기본 (개인용)
    '롯데': LotteParser,
    '삼성화재': SamsungPersonalParser,
    '하나': HanaParser,
    '현대': HyundaiParser,
}

# KB 파일명별 특수 파서 매핑
KB_SPECIAL_PARSERS = {
    '업무용': KBBusinessParser,
    '영업용': KBBusinessParser,
    '이륜': KBBusinessParser,
}

# 롯데 파일명별 특수 파서 매핑
LOTTE_SPECIAL_PARSERS = {
    '업무용': LotteBusinessParser,
    '영업용': LotteBusinessParser,
    '이륜': LotteWheelParser,  # 이륜차 전용 파서
}

# 삼성화재 파일명별 특수 파서 매핑
SAMSUNG_SPECIAL_PARSERS = {
    '업무용': SamsungBusinessParser,
    '영업용': SamsungCommercialParser,
    '이륜': SamsungWheelParser,
    '원데이': SamsungOnedayParser,
    '개인용': SamsungPersonalParser,
}


def get_insurance_name_from_filename(filename):
    """파일명에서 보험명 추출"""
    name = filename.replace('.pdf', '')
    # 회사명_보험명 형식에서 보험명만 추출
    if '_' in name:
        parts = name.split('_', 1)
        if len(parts) > 1:
            return parts[1]
    return name


def get_parser_for_kb_file(filename, default_parser):
    """KB 파일명에 따라 적절한 파서 선택"""
    # KB 특수 파일명 체크
    for keyword, parser_class in KB_SPECIAL_PARSERS.items():
        if keyword in filename:
            return parser_class
    # 기본 파서 (개인용)
    return default_parser


def get_parser_for_lotte_file(filename, default_parser):
    """롯데 파일명에 따라 적절한 파서 선택"""
    # 롯데 특수 파일명 체크
    for keyword, parser_class in LOTTE_SPECIAL_PARSERS.items():
        if keyword in filename:
            return parser_class
    # 기본 파서 (개인용)
    return default_parser


def get_parser_for_samsung_file(filename, default_parser):
    """삼성화재 파일명에 따라 적절한 파서 선택"""
    # 삼성화재 특수 파일명 체크
    for keyword, parser_class in SAMSUNG_SPECIAL_PARSERS.items():
        if keyword in filename:
            return parser_class
    # 기본 파서 (개인용/원데이)
    return default_parser


def process_single_pdf(pdf_path, parser_class, company_name=''):
    """단일 PDF 파일 처리"""
    # KB인 경우 파일명에 따라 파서 선택
    if company_name == 'kb':
        parser_class = get_parser_for_kb_file(pdf_path.name, parser_class)
    # 롯데인 경우 파일명에 따라 파서 선택
    elif company_name == '롯데':
        parser_class = get_parser_for_lotte_file(pdf_path.name, parser_class)
    # 삼성화재인 경우 파일명에 따라 파서 선택
    elif company_name == '삼성화재':
        parser_class = get_parser_for_samsung_file(pdf_path.name, parser_class)
    
    # print(f"  처리 중: {pdf_path.name} (파서: {parser_class.__name__})")

    try:
        # 파서 생성 및 파싱
        parser = parser_class(pdf_path)
        result = parser.parse()

        # 보험명 추출
        insurance_name = get_insurance_name_from_filename(pdf_path.name)

        # 결과 정리
        parsed_data = []

        def _is_glossary_clause(entry):
            """
            제1조(용어의 정의)만 필터링 (제1편 전체가 아니라 제1조만)
            """
            title = entry.get('조항', entry.get('항', entry.get('제목', '')))
            if not title:
                return False
            normalized = title.replace(' ', '')

            # 용어의 정의가 제목에 있는지 확인
            has_glossary = (
                '용어의정의' in normalized
                or '용어정의' in normalized
                or '용어의정리' in normalized
            )

            if not has_glossary:
                return False

            # 제1조인지 확인 (제1조만 제외)
            # 조항에 "제1조"나 "1조"가 포함되어 있고 용어정의가 있으면 제외
            if '제1조' in normalized or '>1조(' in normalized:
                return True

            return False

        for item in result['botong_yakgwan']:
            if _is_glossary_clause(item):
                continue
            parsed_data.append({
                '회사명': result['company'],
                '보험명': insurance_name,
                '약관구분': '보통약관',
                '조항': item.get('조항', item.get('항', '')),
                '내용': item.get('내용', item.get('content', ''))
            })

        for item in result['special_yakgwan']:
            if _is_glossary_clause(item):
                continue
            parsed_data.append({
                '회사명': result['company'],
                '보험명': insurance_name,
                '약관구분': '특별약관',
                '조항': item.get('조항', item.get('항', '')),
                '내용': item.get('내용', item.get('content', ''))
            })

        # print(f"    OK - 보통약관: {len(result['botong_yakgwan'])}개, 특별약관: {len(result['special_yakgwan'])}개")
        return parsed_data

    except Exception as e:
        # print(f"    ERROR - 오류: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """메인 실행 함수"""
    base_dir = pathlib.Path(__file__).parent
    data_dir = base_dir / 'data'
    output_dir = base_dir / 'results' / 'pdftocsv'
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV 파일 초기화 (헤더 작성)
    output_file = output_dir / 'insurance_clauses_v2.csv'
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = ['회사명', '보험명', '약관구분', '조항', '내용']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

    all_results = []
    summary = {}

    print("="*80)
    print("회사별 전용 파서를 사용한 보험 PDF 전처리")
    print("="*80)
    print(f"결과 저장: {output_file}")
    print()

    # 각 회사 폴더 처리
    for company_folder, parser_class in COMPANY_PARSERS.items():
        company_path = data_dir / company_folder

        if not company_path.exists():
            print(f"[{company_folder}] 폴더가 없습니다. 건너뜀.")
            continue

        print(f"[{company_folder}] 처리 시작")

        # 해당 회사의 모든 PDF 파일 처리
        pdf_files = list(company_path.glob('*.pdf'))

        if not pdf_files:
            print(f"  PDF 파일이 없습니다.")
            continue

        company_results = []
        for pdf_path in pdf_files:
            result = process_single_pdf(pdf_path, parser_class, company_folder)
            
            # 즉시 CSV에 append
            if result:
                with open(output_file, 'a', encoding='utf-8-sig', newline='') as f:
                    fieldnames = ['회사명', '보험명', '약관구분', '조항', '내용']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writerows(result)
                print(f"    → CSV에 {len(result)}개 조항 저장 완료")
            
            company_results.extend(result)

        all_results.extend(company_results)

        # 통계
        botong_count = sum(1 for r in company_results if r['약관구분'] == '보통약관')
        special_count = sum(1 for r in company_results if r['약관구분'] == '특별약관')

        summary[company_folder] = {
            'pdf_count': len(pdf_files),
            'botong_count': botong_count,
            'special_count': special_count,
            'total': len(company_results)
        }

        print(f"  완료: PDF {len(pdf_files)}개, 총 {len(company_results)}개 조항 (보통약관: {botong_count}, 특별약관: {special_count})")
        print()

    # 최종 요약
    if all_results:
        print("="*80)
        print("전체 요약")
        print("="*80)
        print()

        total_botong = sum(s['botong_count'] for s in summary.values())
        total_special = sum(s['special_count'] for s in summary.values())

        for company, stats in summary.items():
            print(f"[{company}]")
            print(f"  - PDF 파일: {stats['pdf_count']}개")
            print(f"  - 보통약관: {stats['botong_count']}개")
            print(f"  - 특별약관: {stats['special_count']}개")
            print(f"  - 합계: {stats['total']}개")
            print()

        print(f"전체 합계: {len(all_results)}개 조항")
        print(f"  - 보통약관: {total_botong}개")
        print(f"  - 특별약관: {total_special}개")
        print()
        print(f"[OK] 최종 결과: {output_file}")
        print(f"   (각 PDF 처리 시마다 실시간으로 저장되었습니다)")
        print()

        # 문제 있는 케이스 확인
        problems = []
        for company, stats in summary.items():
            if stats['botong_count'] == 0 and stats['pdf_count'] > 0:
                problems.append(f"{company}: 보통약관 0개")

        if problems:
            print("[!] 주의가 필요한 케이스:")
            for prob in problems:
                print(f"  - {prob}")
        else:
            print("[OK] 모든 PDF가 정상적으로 파싱되었습니다!")

    else:
        print("처리된 데이터가 없습니다.")


if __name__ == '__main__':
    main()
