#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob

def remove_hash_symbols(file_path):
    """파일에서 모든 # 문자를 제거합니다."""
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # # 문자 제거
        cleaned_content = content.replace('#', '')
        
        # 파일에 다시 쓰기
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(cleaned_content)
        
        print(f"✅ 파일에서 # 문자를 모두 제거했습니다: {file_path}")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def find_and_process_files(base_path="data"):
    """지정된 경로에서 *_final.txt 파일들을 찾아서 # 문자를 제거합니다."""
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
        
        print("\n🔄 # 문자 제거 작업 시작...")
        
        for file_path in files:
            remove_hash_symbols(file_path)
        
        print(f"\n✅ 총 {len(files)}개 파일 처리 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    # 사용자에게 선택 옵션 제공
    print("🔧 # 문자 제거 도구")
    print("=" * 50)
    print("1. 특정 파일 처리")
    print("2. data 폴더 내 모든 *_final.txt 파일 처리")
    
    choice = input("\n선택하세요 (1 또는 2): ").strip()
    
    if choice == "1":
        file_path = input("파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            remove_hash_symbols(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    elif choice == "2":
        find_and_process_files()
    
    else:
        print("❌ 잘못된 선택입니다. 1 또는 2를 입력해주세요.")