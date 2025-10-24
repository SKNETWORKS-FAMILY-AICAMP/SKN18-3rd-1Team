import pandas as pd
import os
import glob
from pathlib import Path

def combine_csv_files():
    """
    data 폴더 안의 보험사 폴더별로 있는 CSV 파일들을 하나로 합치는 함수
    결과는 results/all.csv에 저장됩니다.
    """
    
    # 기본 경로 설정
    data_dir = "data"
    output_file = "data/all.csv"
    
    # results 폴더가 없으면 생성
    os.makedirs("results", exist_ok=True)
    
    # 모든 CSV 파일을 저장할 리스트
    all_dataframes = []
    
    print(f"데이터 폴더 '{data_dir}' 스캔 중...")
    
    # data 폴더 내의 모든 하위 폴더 확인
    if not os.path.exists(data_dir):
        print(f"오류: '{data_dir}' 폴더가 존재하지 않습니다.")
        return
    
    # 각 보험사 폴더 처리
    insurance_folders = [f for f in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, f))]
    
    if not insurance_folders:
        print("보험사 폴더를 찾을 수 없습니다.")
        return
    
    print(f"발견된 보험사 폴더: {len(insurance_folders)}개")
    
    total_files_processed = 0
    
    for folder in insurance_folders:
        folder_path = os.path.join(data_dir, folder)
        print(f"\n처리 중: {folder}")
        
        # 해당 폴더의 모든 CSV 파일 찾기
        csv_pattern = os.path.join(folder_path, "*.csv")
        csv_files = glob.glob(csv_pattern)
        
        if not csv_files:
            print(f"  - {folder}에서 CSV 파일을 찾을 수 없습니다.")
            continue
        
        print(f"  - 발견된 CSV 파일: {len(csv_files)}개")
        
        # 각 CSV 파일 처리
        for csv_file in csv_files:
            try:
                # CSV 파일 읽기
                df = pd.read_csv(csv_file, encoding='utf-8')
                
                # 필요한 컬럼만 선택하고 새로운 데이터프레임 생성
                processed_df = pd.DataFrame()
                
                # 기존 컬럼에서 필요한 정보 매핑
                if '조항(편 장 절 조)' in df.columns:
                    processed_df['조항(편 장 절 조)'] = df['조항(편 장 절 조)']
                else:
                    processed_df['조항(편 장 절 조)'] = ''
                
                if '내용' in df.columns:
                    processed_df['내용'] = df['내용']
                else:
                    processed_df['내용'] = ''
                
                # 보험사명과 상품명 설정
                processed_df['보험사명'] = folder
                
                # 파일명에서 상품명 추출 (확장자 제거)
                product_name = os.path.splitext(os.path.basename(csv_file))[0]
                processed_df['상품명'] = product_name
                
                all_dataframes.append(processed_df)
                total_files_processed += 1
                
                print(f"    ✓ {os.path.basename(csv_file)} ({len(processed_df)}행)")
                
            except Exception as e:
                print(f"    ✗ 오류 - {os.path.basename(csv_file)}: {str(e)}")
                continue
    
    # 모든 데이터프레임 합치기
    if all_dataframes:
        print(f"\n총 {total_files_processed}개 파일 처리 완료")
        print("데이터 통합 중...")
        
        # 모든 데이터프레임을 하나로 합치기
        combined_df = pd.concat(all_dataframes, ignore_index=True, sort=False)
        
        # 결과 저장
        combined_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"✓ 통합 완료!")
        print(f"  - 총 행 수: {len(combined_df):,}행")
        print(f"  - 총 열 수: {len(combined_df.columns)}개")
        print(f"  - 저장 위치: {output_file}")
        
        # 컬럼 정보 출력 (4개 컬럼 확인)
        print(f"\n컬럼 목록:")
        expected_columns = ['조항(편 장 절 조)', '내용', '보험사명', '상품명']
        for i, col in enumerate(expected_columns, 1):
            print(f"  {i}. {col}")
            
    else:
        print("\n처리할 CSV 파일이 없습니다.")

def main():
    """메인 실행 함수"""
    print("=== CSV 파일 통합 프로그램 ===")
    combine_csv_files()
    print("\n프로그램 종료")

if __name__ == "__main__":
    main()