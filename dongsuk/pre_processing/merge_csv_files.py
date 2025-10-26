import pandas as pd
import glob
import os

def merge_csv_files():
    """csv_data 폴더의 모든 CSV 파일을 하나로 병합"""
    
    # csv_data 폴더의 모든 CSV 파일 경로 가져오기
    csv_files = glob.glob("csv_data/*.csv")
    
    print(f"발견된 CSV 파일들: {len(csv_files)}개")
    for file in csv_files:
        print(f"  - {file}")
    
    # 모든 CSV 파일을 읽어서 리스트에 저장
    dataframes = []
    
    for file in csv_files:
        try:
            df = pd.read_csv(file, encoding='utf-8')
            print(f"✓ {file} 읽기 완료 - {len(df)}행")
            dataframes.append(df)
        except UnicodeDecodeError:
            # UTF-8로 읽기 실패시 다른 인코딩 시도
            try:
                df = pd.read_csv(file, encoding='cp949')
                print(f"✓ {file} 읽기 완료 (cp949) - {len(df)}행")
                dataframes.append(df)
            except Exception as e:
                print(f"✗ {file} 읽기 실패: {e}")
    
    if not dataframes:
        print("병합할 데이터가 없습니다.")
        return
    
    # 모든 데이터프레임 병합
    merged_df = pd.concat(dataframes, ignore_index=True)
    
    print(f"\n병합 완료:")
    print(f"  - 총 행 수: {len(merged_df)}")
    print(f"  - 컬럼: {list(merged_df.columns)}")
    
    # 병합된 파일 저장
    output_file = "merged_insurance_data.csv"
    merged_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n병합된 파일이 '{output_file}'로 저장되었습니다.")
    
    # 각 상품별 데이터 개수 확인
    if '상품명' in merged_df.columns:
        print("\n상품별 데이터 개수:")
        product_counts = merged_df['상품명'].value_counts()
        for product, count in product_counts.items():
            print(f"  - {product}: {count}행")

if __name__ == "__main__":
    merge_csv_files()