#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob
import re

def add_headers_to_file(file_path):
    """파일에서 '제 (숫자) 조' 패턴에 #### 헤더를 추가합니다."""
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 원본 내용 백업
        backup_path = file_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as backup_file:
            backup_file.write(content)
        
        # 정규식 패턴들 - 다양한 형태의 조 패턴 매칭
        patterns = [
            # 제1조, 제 1조, 제1조(제목), 제 1 조 등
            (r'^(제\s*\d+\s*조(?:\([^)]+\))?)(?:\s*[·\.\s]*.*)?$', r'#### \1'),
        ]
        
        original_content = content
        
        # 각 패턴 적용
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # 변경사항이 있는지 확인
        changes_made = content != original_content
        
        if changes_made:
            # 파일에 다시 쓰기
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            # 변경된 조 개수 계산
            header_count = len(re.findall(r'^####\s*제\s*\d+\s*조', content, flags=re.MULTILINE))
            
            print(f"✅ 헤더 추가 완료: {file_path}")
            print(f"   - {header_count}개의 조에 #### 헤더 추가")
            print(f"   - 백업 파일: {backup_path}")
        else:
            # 변경사항이 없으면 백업 파일 삭제
            os.remove(backup_path)
            print(f"ℹ️  변경사항 없음: {file_path}")
        
        return changes_made
        
    except Exception as e:
        print(f"❌ 오류 발생 ({file_path}): {e}")
        return False

def process_all_final_files(base_path="data"):
    """지정된 경로에서 *_final.txt 파일들을 찾아서 헤더를 추가합니다."""
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
        
        print("\n🔄 헤더 추가 작업 시작...")
        print("=" * 80)
        
        processed_count = 0
        changed_count = 0
        
        for file_path in files:
            print(f"\n처리 중: {os.path.basename(file_path)}")
            if add_headers_to_file(file_path):
                changed_count += 1
            processed_count += 1
        
        print("\n" + "=" * 80)
        print(f"✅ 처리 완료!")
        print(f"   - 총 처리 파일: {processed_count}개")
        print(f"   - 변경된 파일: {changed_count}개")
        print(f"   - 변경되지 않은 파일: {processed_count - changed_count}개")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def preview_changes(file_path, max_lines=20):
    """파일의 변경 사항을 미리보기합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 조 패턴 찾기
        matches = re.findall(r'^(제\s*\d+\s*조(?:\([^)]+\))?).*$', content, flags=re.MULTILINE)
        
        if matches:
            print(f"\n📋 {os.path.basename(file_path)}에서 발견된 조 패턴 (최대 {max_lines}개):")
            print("-" * 60)
            for i, match in enumerate(matches[:max_lines], 1):
                print(f"   {i:2d}. {match}")
            
            if len(matches) > max_lines:
                print(f"   ... 외 {len(matches) - max_lines}개 더")
            
            print(f"\n   총 {len(matches)}개의 조 발견")
        else:
            print(f"\n❌ {os.path.basename(file_path)}에서 조 패턴을 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 미리보기 오류 ({file_path}): {e}")

if __name__ == "__main__":
    print("🔧 조 헤더 추가 도구")
    print("=" * 50)
    print("1. 특정 파일 처리")
    print("2. data 폴더 내 모든 *_final.txt 파일 처리")
    print("3. 특정 파일 미리보기")
    
    choice = input("\n선택하세요 (1, 2, 또는 3): ").strip()
    
    if choice == "1":
        file_path = input("파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            add_headers_to_file(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    elif choice == "2":
        # 확인 메시지
        confirm = input("⚠️  모든 *_final.txt 파일을 처리하시겠습니까? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            process_all_final_files()
        else:
            print("❌ 작업이 취소되었습니다.")
    
    elif choice == "3":
        file_path = input("미리보기할 파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            preview_changes(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    else:
        print("❌ 잘못된 선택입니다. 1, 2, 또는 3을 입력해주세요.")