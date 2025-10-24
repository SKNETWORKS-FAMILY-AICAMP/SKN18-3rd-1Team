import pymupdf4llm
import pathlib
import re

# 롯데 개인용 PDF 찾기
lotte_pdf = list(pathlib.Path('data/롯데').glob('*개인용*.pdf'))[0]
print(f'분석: {lotte_pdf.name}\n')

md_text = pymupdf4llm.to_markdown(str(lotte_pdf), page_chunks=False)
lines = md_text.split('\n')

# 보통약관 헤더
print('=== 보통약관 찾기 ===')
for i, line in enumerate(lines[:100]):
    if '보통약관' in line and len(line.strip()) < 20:
        print(f'라인 {i}: 보통약관 발견')
        # 주변 확인
        for j in range(max(0, i-2), min(i+10, len(lines))):
            print(f'  {j}: {lines[j][:80]}')

# 특별약관 헤더
print('\n=== 특별약관 찾기 (라인 100 이후) ===')
found = False
for i in range(100, min(500, len(lines))):
    if '특별약관' in lines[i] and len(lines[i].strip()) < 20:
        print(f'라인 {i}: 특별약관 발견')
        # 주변 확인
        for j in range(max(0, i-2), min(i+10, len(lines))):
            print(f'  {j}: {lines[j][:80]}')
        found = True
        break

if not found:
    print('특별약관 헤더를 찾지 못함')

# 제1조 출현 횟수
jo1_pattern = re.compile(r'^\*?\*?제\s*1\s*조')
jo1_lines = [i for i, line in enumerate(lines) if jo1_pattern.search(line.strip())]
print(f'\n제1조 총 {len(jo1_lines)}번 출현')
if jo1_lines:
    print(f'첫 번째 제1조: 라인 {jo1_lines[0]}')
    print(f'  내용: {lines[jo1_lines[0]][:80]}')
if len(jo1_lines) > 1:
    print(f'두 번째 제1조: 라인 {jo1_lines[1]}')
    print(f'  내용: {lines[jo1_lines[1]][:80]}')

# 제4편 찾기
print('\n=== 제4편 찾기 ===')
for i, line in enumerate(lines):
    if '제4편' in line.strip() or '제5편' in line.strip():
        print(f'라인 {i}: {line[:80]}')
