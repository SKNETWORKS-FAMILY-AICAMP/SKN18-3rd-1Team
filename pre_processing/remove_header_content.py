#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob
import re

def remove_content_before_first_header(file_path):
    """파일에서 첫 번째 #### 헤더 이전의 모든 내용을 삭제합니다."""
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 원본 내용 백업
        backup_path = file_path + '.pre_header_backup'
        with open(backup_path, 'w', encoding='utf-8') as backup_file:
            backup_file.write(content)
        
        # 첫 번째 #### 헤더 찾기
        first_header_match = re.search(r'^####', content, flags=re.MULTILINE)
        
        if first_header_match:
            # 첫 번째 #### 헤더부터 끝까지의 내용만 유지
            header_start_pos = first_header_match.start()
            cleaned_content = content[header_start_pos:]
            
            # 삭제된 내용 계산
            removed_content = content[:header_start_pos]
            removed_lines = len(removed_content.split('\n'))
            removed_chars = len(removed_content)
            
            # 파일에 다시 쓰기
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(cleaned_content)
            
            print(f"✅ 헤더 이전 내용 삭제 완료: {file_path}")
            print(f"   - 삭제된 내용: {removed_lines}줄, {removed_chars}자")
            print(f"   - 백업 파일: {backup_path}")
            
            return True
        else:
            # #### 헤더가 없으면 백업 파일 삭제
            os.remove(backup_path)
            print(f"ℹ️  #### 헤더를 찾을 수 없음: {file_path}")
            return False
        
    except Exception as e:
        print(f"❌ 오류 발생 ({file_path}): {e}")
        return False

def process_all_final_files(base_path="data"):
    """지정된 경로에서 *_final.txt 파일들을 찾아서 헤더 이전 내용을 삭제합니다."""
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
        
        print("\n🔄 헤더 이전 내용 삭제 작업 시작...")
        print("=" * 80)
        
        processed_count = 0
        changed_count = 0
        
        for file_path in files:
            print(f"\n처리 중: {os.path.basename(file_path)}")
            if remove_content_before_first_header(file_path):
                changed_count += 1
            processed_count += 1
        
        print("\n" + "=" * 80)
        print(f"✅ 처리 완료!")
        print(f"   - 총 처리 파일: {processed_count}개")
        print(f"   - 변경된 파일: {changed_count}개")
        print(f"   - 변경되지 않은 파일: {processed_count - changed_count}개")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

def preview_header_content(file_path, preview_lines=10):
    """파일의 첫 번째 #### 헤더 이전 내용을 미리보기합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 첫 번째 #### 헤더 찾기
        first_header_match = re.search(r'^####', content, flags=re.MULTILINE)
        
        if first_header_match:
            header_start_pos = first_header_match.start()
            before_header = content[:header_start_pos]
            
            if before_header.strip():
                lines = before_header.split('\n')
                print(f"\n📋 {os.path.basename(file_path)} - 첫 번째 #### 헤더 이전 내용:")
                print("-" * 60)
                print(f"총 {len(lines)}줄, {len(before_header)}자")
                print("-" * 60)
                
                # 처음 몇 줄만 표시
                for i, line in enumerate(lines[:preview_lines], 1):
                    print(f"{i:2d}: {line}")
                
                if len(lines) > preview_lines:
                    print(f"... 외 {len(lines) - preview_lines}줄 더")
                
                # 첫 번째 헤더도 표시
                first_header_line = content[header_start_pos:].split('\n')[0]
                print(f"\n첫 번째 헤더: {first_header_line}")
            else:
                print(f"\n✅ {os.path.basename(file_path)} - 첫 번째 #### 헤더 이전에 내용이 없습니다.")
        else:
            print(f"\n❌ {os.path.basename(file_path)} - #### 헤더를 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 미리보기 오류 ({file_path}): {e}")

if __name__ == "__main__":
    print("🔧 헤더 이전 내용 삭제 도구")
    print("=" * 50)
    print("1. 특정 파일 처리")
    print("2. data 폴더 내 모든 *_final.txt 파일 처리")
    print("3. 특정 파일 미리보기")
    
    choice = input("\n선택하세요 (1, 2, 또는 3): ").strip()
    
    if choice == "1":
        file_path = input("파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            remove_content_before_first_header(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    elif choice == "2":
        # 확인 메시지
        print("⚠️  이 작업은 모든 *_final.txt 파일에서 첫 번째 #### 헤더 이전의 모든 내용을 삭제합니다.")
        confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            process_all_final_files()
        else:
            print("❌ 작업이 취소되었습니다.")
    
    elif choice == "3":
        file_path = input("미리보기할 파일 경로를 입력하세요: ").strip()
        if os.path.exists(file_path):
            preview_header_content(file_path)
        else:
            print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
    
    else:
        print("❌ 잘못된 선택입니다. 1, 2, 또는 3을 입력해주세요.")