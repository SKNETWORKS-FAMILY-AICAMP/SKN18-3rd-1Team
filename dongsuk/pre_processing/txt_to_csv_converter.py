#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT 파일을 CSV로 변환하는 스크립트
헤더 구조를 파싱해서 조항별로 분할하여 CSV 생성
"""

import os
import glob
import re
import pandas as pd
from pathlib import Path

def extract_metadata_from_path(file_path):
    """파일 경로에서 보험사명과 상품명을 추출"""
    path = Path(file_path)
    
    # 보험사명: 2상위 폴더
    parts = path.parts
    if len(parts) >= 3:
        보험사명 = parts[-3]  # data/삼성화재/상품폴더/파일.txt에서 삼성화재
    else:
        보험사명 = "알수없음"
    
    # 상품명: 파일명에서 _final 제거
    상품명 = path.stem.replace('_final', '')
    
    return 보험사명, 상품명

def remove_rows_until_definition(df):
    """'용어의 정의'가 포함된 조항이 있으면 그 행까지(포함) 삭제"""
    if df.empty:
        return df
    
    # "용어의 정의"가 포함된 행 찾기
    definition_mask = df['조항'].str.contains('용어의 정의', na=False)
    definition_indices = df[definition_mask].index.tolist()
    
    if definition_indices:
        # 첫 번째 "용어의 정의" 행의 인덱스
        first_definition_idx = definition_indices[0]
        
        # 해당 행까지(포함) 삭제
        df_filtered = df.iloc[first_definition_idx + 1:].reset_index(drop=True)
        
        print(f"   🗑️ '용어의 정의' 조항까지 {first_definition_idx + 1}개 행 삭제")
        return df_filtered
    
    return df

def is_meaningful_content(content):
    """내용이 의미있는 실제 조항 내용인지 판단"""
    if not content or len(content.strip()) < 10:
        return False
    
    # 목차나 무의미한 내용 패턴들
    meaningless_patterns = [
        r'^\.+$',  # 점선만 있는 경우
        r'^=+ 페이지 \d+ =+$',  # 페이지 표시
        r'^\d+$',  # 숫자만 있는 경우
        r'^[·\s]+$',  # 점과 공백만 있는 경우
        r'^목\s*차$',  # 목차 표시
        r'^제\d+절$',  # 절 제목만 있는 경우
        r'^제\d+장$',  # 장 제목만 있는 경우
        r'^제\d+편$',  # 편 제목만 있는 경우
    ]
    
    lines = content.strip().split('\n')
    meaningful_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 무의미한 패턴 체크
        is_meaningless = False
        for pattern in meaningless_patterns:
            if re.match(pattern, line):
                is_meaningless = True
                break
        
        if not is_meaningless:
            meaningful_lines.append(line)
    
    # 의미있는 내용이 충분히 있는지 확인
    meaningful_content = '\n'.join(meaningful_lines)
    return len(meaningful_content.strip()) >= 20  # 최소 20자 이상

def find_content_start_position(content):
    """실제 내용이 시작되는 위치를 찾음 (목차 부분 제외)"""
    lines = content.split('\n')
    
    # 실제 내용이 있는 조항을 찾기 위한 패턴
    # 조항 헤더 다음에 실제 내용(숫자로 시작하는 항목 등)이 있는 경우
    for i, line in enumerate(lines):
        line = line.strip()
        
        # 조항 헤더 찾기
        if re.match(r'^####\s*제\s*\d+\s*조', line):
            # 다음 몇 줄을 확인해서 실제 내용이 있는지 체크
            for j in range(i + 1, min(i + 10, len(lines))):
                next_line = lines[j].strip()
                if not next_line:
                    continue
                
                # 다음 헤더가 나오면 목차 부분
                if re.match(r'^#{1,4}\s*제\s*\d+\s*(편|장|절|조)', next_line):
                    break
                
                # 실제 내용 패턴 (숫자로 시작하는 항목, 가/나/다 항목 등)
                if re.match(r'^\d+\.', next_line) or \
                   re.match(r'^[가-힣]+\.', next_line) or \
                   len(next_line) > 20:  # 충분히 긴 내용
                    return i  # 이 조항부터 실제 내용 시작
    
    return 0  # 실제 내용을 찾지 못하면 처음부터

def parse_headers_and_content(content):
    """텍스트에서 헤더 구조를 파싱하고 조항별 내용을 추출"""
    # 실제 내용이 시작되는 부분부터 처리
    start_pos = find_content_start_position(content)
    lines = content.split('\n')[start_pos:]
    
    # 현재 계층 상태 추적
    current_편 = ""
    current_장 = ""
    current_절 = ""
    
    # 조항별 데이터 저장
    articles = []
    current_article = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        
        # 편 헤더 매칭
        편_match = re.match(r'^#\s*(제\s*\d+\s*편)', line)
        if 편_match:
            current_편 = 편_match.group(1)
            current_장 = ""
            current_절 = ""
            continue
        
        # 장 헤더 매칭
        장_match = re.match(r'^##\s*(제\s*\d+\s*장)', line)
        if 장_match:
            current_장 = 장_match.group(1)
            current_절 = ""
            continue
        
        # 절 헤더 매칭
        절_match = re.match(r'^###\s*(제\s*\d+\s*절)', line)
        if 절_match:
            current_절 = 절_match.group(1)
            continue
        
        # 조 헤더 매칭
        조_match = re.match(r'^####\s*(제\s*\d+\s*조(?:\([^)]+\))?)', line)
        if 조_match:
            # 이전 조항이 있으면 내용 검증 후 저장
            if current_article:
                content_text = '\n'.join(current_content).strip()
                if is_meaningful_content(content_text):
                    articles.append({
                        '조항': current_article,
                        '내용': content_text
                    })
            
            # 새로운 조항 시작
            조_이름 = 조_match.group(1)
            
            # 계층구조 조합
            조항_parts = []
            if current_편:
                조항_parts.append(current_편)
            if current_장:
                조항_parts.append(current_장)
            if current_절:
                조항_parts.append(current_절)
            조항_parts.append(조_이름)
            
            current_article = ' '.join(조항_parts)
            current_content = []
            continue
        
        # 일반 내용 라인 (목차가 아닌 실제 내용만)
        if current_article and line:
            # 페이지 표시나 무의미한 라인 제외
            if not re.match(r'^=+ 페이지 \d+ =+$', line) and \
               not re.match(r'^\.+$', line) and \
               not re.match(r'^\d+$', line) and \
               not re.match(r'^<별표.*>.*$', line):  # 별표 제외
                current_content.append(line)
    
    # 마지막 조항 저장 (내용 검증)
    if current_article:
        content_text = '\n'.join(current_content).strip()
        if is_meaningful_content(content_text):
            articles.append({
                '조항': current_article,
                '내용': content_text
            })
    
    return articles

def convert_txt_to_csv(file_path, output_dir=None):
    """단일 TXT 파일을 CSV로 변환"""
    try:
        print(f"📄 처리 중: {os.path.basename(file_path)}")
        
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 메타데이터 추출
        보험사명, 상품명 = extract_metadata_from_path(file_path)
        
        # 헤더와 내용 파싱
        articles = parse_headers_and_content(content)
        
        if not articles:
            print(f"   ⚠️ 의미있는 내용이 있는 조항을 찾을 수 없습니다.")
            return None
        
        # DataFrame 생성
        df_data = []
        for article in articles:
            df_data.append({
                '조항': article['조항'],
                '내용': article['내용'],
                '보험사명': 보험사명,
                '상품명': 상품명
            })
        
        df = pd.DataFrame(df_data)
        
        # "용어의 정의"가 포함된 행까지 삭제
        df = remove_rows_until_definition(df)
        
        # 출력 파일 경로 설정
        if output_dir is None:
            output_dir = Path(file_path).parent
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        # CSV 파일명 생성
        csv_filename = f"{상품명}_조항별.csv"
        csv_path = output_dir / csv_filename
        
        # CSV 저장
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        print(f"   ✅ 완료: {len(articles)}개 의미있는 조항 → {csv_path}")
        print(f"   📊 보험사: {보험사명}, 상품: {상품명}")
        
        # 내용 길이 통계
        if articles:
            avg_length = sum(len(article['내용']) for article in articles) / len(articles)
            print(f"   📝 평균 조항 길이: {avg_length:.0f}자")
        
        return str(csv_path)
        
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return None

def process_all_txt_files(base_path="data", output_base_dir="csv_data"):
    """모든 *_final.txt 파일을 CSV로 변환"""
    try:
        # *_final.txt 패턴으로 파일 검색
        pattern = os.path.join(base_path, "**", "*_final.txt")
        files = glob.glob(pattern, recursive=True)
        
        if not files:
            print(f"❌ {base_path} 경로에서 *_final.txt 파일을 찾을 수 없습니다.")
            return []
        
        print(f"📁 {len(files)}개의 *_final.txt 파일을 발견했습니다:")
        for i, file_path in enumerate(files, 1):
            print(f"   {i}. {file_path}")
        
        print(f"\n🔄 CSV 변환 작업 시작...")
        print("=" * 80)
        
        # 출력 디렉토리 생성
        output_dir = Path(output_base_dir)
        output_dir.mkdir(exist_ok=True)
        
        results = []
        successful = 0
        
        for file_path in files:
            result = convert_txt_to_csv(file_path, output_dir)
            if result:
                results.append(result)
                successful += 1
        
        print("\n" + "=" * 80)
        print(f"✅ 변환 완료!")
        print(f"   - 총 파일: {len(files)}개")
        print(f"   - 성공: {successful}개")
        print(f"   - 실패: {len(files) - successful}개")
        print(f"   - 출력 폴더: {output_dir}")
        
        return results
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return []

def preview_txt_structure(file_path, max_articles=5):
    """TXT 파일의 구조를 미리보기"""
    try:
        print(f"\n📋 {os.path.basename(file_path)} 구조 미리보기:")
        print("-" * 60)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 메타데이터 추출
        보험사명, 상품명 = extract_metadata_from_path(file_path)
        print(f"보험사명: {보험사명}")
        print(f"상품명: {상품명}")
        print("-" * 60)
        
        # 헤더와 내용 파싱
        articles = parse_headers_and_content(content)
        
        if articles:
            print(f"총 {len(articles)}개 조항 발견:")
            for i, article in enumerate(articles[:max_articles], 1):
                print(f"\n{i}. 조항: {article['조항']}")
                content_preview = article['내용'][:100] + "..." if len(article['내용']) > 100 else article['내용']
                print(f"   내용: {content_preview}")
            
            if len(articles) > max_articles:
                print(f"\n... 외 {len(articles) - max_articles}개 조항 더")
        else:
            print("❌ 조항을 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 미리보기 오류: {e}")

if __name__ == "__main__":
    print("🔧 TXT → CSV 변환 도구")
    print("📋 헤더 구조를 파싱하여 조항별 CSV 생성")
    print("=" * 50)
    print("1. 특정 파일 변환")
    print("2. 모든 *_final.txt 파일 변환")
    print("3. 특정 파일 구조 미리보기")
    
    choice = input("\n선택하세요 (1, 2, 또는 3): ").strip()
    
    if choice == "1":
        file_path = input("TXT 파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            convert_txt_to_csv(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    elif choice == "2":
        print("⚠️  모든 *_final.txt 파일을 CSV로 변환합니다.")
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            process_all_txt_files()
        else:
            print("❌ 작업이 취소되었습니다.")
    
    elif choice == "3":
        file_path = input("미리보기할 TXT 파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            preview_txt_structure(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    else:
        print("❌ 잘못된 선택입니다. 1, 2, 또는 3을 입력해주세요.")