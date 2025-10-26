#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob
import csv
import re

def convert_file_to_csv(file_path):
    """단일 파일을 CSV로 변환합니다."""
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # #### 헤더가 있는지 확인
        if not re.search(r'^####', content, flags=re.MULTILINE):
            print(f"ℹ️  #### 헤더가 없어 변환하지 않음: {os.path.basename(file_path)}")
            return None, 0, 0
        
        # #### 헤더로 분할
        sections = re.split(r'^(####.+)$', content, flags=re.MULTILINE)
        
        csv_data = []
        
        # 첫 번째 부분 (헤더 이전 내용)이 있다면 추가
        if sections[0].strip():
            csv_data.append(["헤더 정보", sections[0].strip()])
        
        # 각 조와 내용 처리
        i = 1
        while i < len(sections):
            if i + 1 < len(sections):
                header = sections[i].strip()
                content_part = sections[i + 1].strip() if i + 1 < len(sections) else ""
                
                # 헤더에서 #### 제거
                clean_header = header.replace('####', '').strip()
                
                # CSV 데이터에 추가
                csv_data.append([clean_header, content_part])
                
                i += 2
            else:
                # 마지막 헤더만 있는 경우
                header = sections[i].strip()
                clean_header = header.replace('####', '').strip()
                csv_data.append([clean_header, ""])
                i += 1
        
        # 데이터가 없으면 변환하지 않음
        if len(csv_data) == 0:
            print(f"ℹ️  변환할 데이터가 없음: {os.path.basename(file_path)}")
            return None, 0, 0
        
        # CSV 파일 저장 경로 설정 (csv_data 폴더에 저장)
        base_name = os.path.basename(os.path.splitext(file_path)[0])
        csv_data_dir = "csv_data"
        os.makedirs(csv_data_dir, exist_ok=True)
        csv_file_path = os.path.join(csv_data_dir, base_name + ".csv")
        
        with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 헤더 행 작성
            writer.writerow(['조항', '내용'])
            
            # 데이터 행 작성
            writer.writerows(csv_data)
        
        print(f"✅ CSV 변환 완료: {os.path.basename(csv_file_path)}")
        print(f"   - 총 {len(csv_data)}개 행 생성")
        
        # 통계 정보
        total_chars = sum(len(row[1]) for row in csv_data)
        articles_count = len([row for row in csv_data if row[0] != "헤더 정보"])
        
        print(f"   - 조 개수: {articles_count}개")
        print(f"   - 전체 내용: {total_chars:,}자")
        
        return csv_file_path, len(csv_data), articles_count
        
    except Exception as e:
        print(f"❌ 오류 발생 ({file_path}): {e}")
        return None, 0, 0

def process_all_final_files(base_path="data"):
    """지정된 경로에서 *_final.txt 파일들을 찾아서 CSV로 변환합니다."""
    try:
        # *_final.txt 패턴으로 파일 검색
        pattern = os.path.join(base_path, "**", "*_final.txt")
        files = glob.glob(pattern, recursive=True)
        
        if not files:
            print(f"❌ {base_path} 경로에서 *_final.txt 파일을 찾을 수 없습니다.")
            return
        
        print(f"📁 {len(files)}개의 *_final.txt 파일을 발견했습니다:")
        for i, file_path in enumerate(files, 1):
            print(f"   {i}. {file_path}")
        
        print("\n🔄 CSV 변환 작업 시작...")
        print("=" * 80)
        
        processed_count = 0
        success_count = 0
        total_rows = 0
        total_articles = 0
        
        for file_path in files:
            print(f"\n처리 중: {os.path.basename(file_path)}")
            csv_path, rows, articles = convert_file_to_csv(file_path)
            
            if csv_path:
                success_count += 1
                total_rows += rows
                total_articles += articles
            
            processed_count += 1
        
        print("\n" + "=" * 80)
        print(f"✅ 전체 처리 완료!")
        print(f"   - 총 처리 파일: {processed_count}개")
        print(f"   - 성공한 파일: {success_count}개")
        print(f"   - 실패한 파일: {processed_count - success_count}개")
        print(f"   - 총 생성된 행: {total_rows:,}개")
        print(f"   - 총 조 개수: {total_articles:,}개")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def preview_csv_structure(file_path, max_rows=10):
    """파일의 CSV 변환 결과를 미리보기합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # #### 헤더로 분할
        sections = re.split(r'^(####.+)$', content, flags=re.MULTILINE)
        
        print(f"\n📋 {os.path.basename(file_path)} - CSV 변환 미리보기:")
        print("-" * 60)
        
        preview_data = []
        
        # 첫 번째 부분 처리
        if sections[0].strip():
            preview_data.append(["헤더 정보", len(sections[0].strip())])
        
        # 각 조 처리
        i = 1
        row_count = 0
        while i < len(sections) and row_count < max_rows:
            if i + 1 < len(sections):
                header = sections[i].strip()
                content_part = sections[i + 1].strip() if i + 1 < len(sections) else ""
                
                clean_header = header.replace('####', '').strip()
                preview_data.append([clean_header, len(content_part)])
                
                row_count += 1
                i += 2
            else:
                header = sections[i].strip()
                clean_header = header.replace('####', '').strip()
                preview_data.append([clean_header, 0])
                row_count += 1
                i += 1
        
        # 미리보기 출력
        for i, (조항, 내용_길이) in enumerate(preview_data, 1):
            print(f"{i:2d}. 조항: {조항[:50]}{'...' if len(조항) > 50 else ''}")
            print(f"    내용: {내용_길이:,}자")
        
        total_sections = len(re.findall(r'####.+', content))
        if total_sections > max_rows:
            print(f"... 외 {total_sections - max_rows}개 조 더")
        
        print(f"\n총 {total_sections}개의 조 발견")
            
    except Exception as e:
        print(f"❌ 미리보기 오류 ({file_path}): {e}")

def create_summary_report(base_path="data"):
    """변환된 CSV 파일들의 요약 보고서를 생성합니다."""
    try:
        # csv_data 폴더에서 *.csv 패턴으로 파일 검색
        csv_data_dir = "csv_data"
        if not os.path.exists(csv_data_dir):
            print("❌ csv_data 폴더를 찾을 수 없습니다.")
            return
        
        pattern = os.path.join(csv_data_dir, "*.csv")
        csv_files = glob.glob(pattern)
        
        if not csv_files:
            print("❌ CSV 파일을 찾을 수 없습니다.")
            return
        
        summary_content = "# CSV 변환 요약 보고서\n\n"
        summary_content += f"생성 일시: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        summary_content += f"총 CSV 파일 수: {len(csv_files)}개\n\n"
        
        summary_content += "## 파일별 상세 정보\n\n"
        
        total_rows = 0
        total_files = 0
        
        for csv_file in csv_files:
            try:
                with open(csv_file, 'r', encoding='utf-8-sig') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    row_count = len(rows) - 1  # 헤더 제외
                    
                file_name = os.path.basename(csv_file)
                file_size = os.path.getsize(csv_file)
                
                summary_content += f"### {file_name}\n"
                summary_content += f"- 행 수: {row_count}개\n"
                summary_content += f"- 파일 크기: {file_size:,} bytes\n"
                summary_content += f"- 경로: {csv_file}\n\n"
                
                total_rows += row_count
                total_files += 1
                
            except Exception as e:
                summary_content += f"### {os.path.basename(csv_file)} (오류)\n"
                summary_content += f"- 오류: {str(e)}\n\n"
        
        summary_content += f"## 전체 통계\n\n"
        summary_content += f"- 총 파일 수: {total_files}개\n"
        summary_content += f"- 총 행 수: {total_rows:,}개\n"
        summary_content += f"- 평균 행 수: {total_rows/total_files:.1f}개/파일\n"
        
        # 요약 파일 저장 (csv_data 폴더에 저장)
        csv_data_dir = "csv_data"
        os.makedirs(csv_data_dir, exist_ok=True)
        summary_path = os.path.join(csv_data_dir, "csv_conversion_summary.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        print(f"✅ 요약 보고서 생성: {summary_path}")
        
    except Exception as e:
        print(f"❌ 요약 보고서 생성 오류: {e}")

if __name__ == "__main__":
    print("🔧 조별 데이터 CSV 변환 도구")
    print("=" * 50)
    print("1. 특정 파일 변환")
    print("2. data 폴더 내 모든 *_final.txt 파일 변환")
    print("3. 특정 파일 구조 미리보기")
    print("4. CSV 요약 보고서 생성")
    
    choice = input("\n선택하세요 (1, 2, 3, 또는 4): ").strip()
    
    if choice == "1":
        file_path = input("파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            convert_file_to_csv(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    elif choice == "2":
        # 확인 메시지
        print("⚠️  이 작업은 모든 *_final.txt 파일을 CSV로 변환합니다.")
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            process_all_final_files()
        else:
            print("❌ 작업이 취소되었습니다.")
    
    elif choice == "3":
        file_path = input("미리보기할 파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            preview_csv_structure(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    elif choice == "4":
        create_summary_report()
    
    else:
        print("❌ 잘못된 선택입니다. 1, 2, 3, 또는 4를 입력해주세요.")