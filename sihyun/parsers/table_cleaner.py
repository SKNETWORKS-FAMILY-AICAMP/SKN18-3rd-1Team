"""
마크다운 표 형식 제거 유틸리티
"""
import re


def remove_markdown_tables(text: str) -> str:
    """
    마크다운 표 형식을 제거하고 텍스트만 남김

    예:
    |항목|내용|
    |---|---|
    |1|데이터|

    -> "항목 내용 1 데이터"
    """
    if not text:
        return text

    lines = text.split('\n')
    cleaned_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # 표 구분선 (|---|---|) 감지
        if re.match(r'^\|[\s\-:]+\|', stripped):
            in_table = True
            continue

        # 표 라인 (|...|...|) 감지
        if stripped.startswith('|') and stripped.endswith('|'):
            # 표 내용 추출 (| 제거하고 셀 내용만)
            cells = [cell.strip() for cell in stripped.split('|')[1:-1]]
            # 빈 셀이 아닌 것만
            cells = [c for c in cells if c and c not in ['', '-', '---', '–', '—']]
            if cells:
                cleaned_lines.append(' '.join(cells))
            continue

        # 일반 라인
        in_table = False
        if stripped:
            cleaned_lines.append(stripped)

    return '\n'.join(cleaned_lines)


def clean_special_chars(text: str) -> str:
    """
    특수 문자 및 불필요한 기호 정리
    """
    # HTML 태그 제거
    text = re.sub(r'<br\s*/?>', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)

    # 연속된 공백을 하나로
    text = re.sub(r'\s+', ' ', text)

    # 각 줄의 앞뒤 공백 제거
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join([l for l in lines if l])

    return text.strip()


def clean_content(text: str) -> str:
    """
    표 제거 + 특수문자 정리를 한번에
    """
    text = remove_markdown_tables(text)
    text = clean_special_chars(text)
    return text


if __name__ == "__main__":
    # 테스트
    test_text = """
    이것은 일반 텍스트입니다.

    |항목|내용|비고|
    |---|---|---|
    |1번|데이터1|중요|
    |2번|데이터2|일반|

    표 다음 텍스트입니다.

    |A|B|
    |---|---|
    |값1|값2|
    """

    result = clean_content(test_text)
    print("=== 원본 ===")
    print(test_text)
    print("\n=== 정리 후 ===")
    print(result)