#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob
import re

def add_headers_to_file(file_path):
    """파일에서 편>장>절>조 계층구조로 헤더를 추가합니다."""
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # 원본 내용 백업
        backup_path = file_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as backup_file:
            backup_file.write(content)
        
        # 정규식 패턴들 - 계층구조: 편(#) > 장(##) > 절(###) > 조(####)
        # 더 넓은 범위로 매칭하여 다양한 형태를 포함
        patterns = [
            # 편 패턴: 제1편, 제 1 편, `제1편 제목`, 제1편(제목) 등 → # 헤더
            (r'^[`\s]*(?:제\s*\d+\s*편)(?:\s*[^\n`]*)?[`\s]*$', lambda m: f"# {re.search(r'제\s*\d+\s*편', m.group(0)).group()}"),
            # 장 패턴: 제1장, 제 1 장, `제1장 제목`, 제1장(제목) 등 → ## 헤더  
            (r'^[`\s]*(?:제\s*\d+\s*장)(?:\s*[^\n`]*)?[`\s]*$', lambda m: f"## {re.search(r'제\s*\d+\s*장', m.group(0)).group()}"),
            # 절 패턴: 제1절, 제 1 절, `제1절 제목`, 제1절(제목) 등 → ### 헤더
            (r'^[`\s]*(?:제\s*\d+\s*절)(?:\s*[^\n`]*)?[`\s]*$', lambda m: f"### {re.search(r'제\s*\d+\s*절', m.group(0)).group()}"),
            # 조 패턴: 제1조, 제 1 조, 제1조(제목) 등 → #### 헤더 (이미 ####가 있으면 제외)
            (r'^(?!####)([`\s]*(?:제\s*\d+\s*조)(?:\s*[^\n`]*)?[`\s]*)$', lambda m: f"#### {re.search(r'제\s*\d+\s*조', m.group(0)).group()}"),
        ]
        
        original_content = content
        
        # 각 패턴 적용
        for pattern, replacement in patterns:
            if callable(replacement):
                # 람다 함수인 경우
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            else:
                # 일반 문자열인 경우
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # 변경사항이 있는지 확인
        changes_made = content != original_content
        
        if changes_made:
            # 파일에 다시 쓰기
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            
            # 변경된 헤더 개수 계산
            편_count = len(re.findall(r'^#\s*제\s*\d+\s*편', content, flags=re.MULTILINE))
            장_count = len(re.findall(r'^##\s*제\s*\d+\s*장', content, flags=re.MULTILINE))
            절_count = len(re.findall(r'^###\s*제\s*\d+\s*절', content, flags=re.MULTILINE))
            조_count = len(re.findall(r'^####\s*제\s*\d+\s*조', content, flags=re.MULTILINE))
            
            print(f"✅ 헤더 추가 완료: {file_path}")
            print(f"   - 편(#): {편_count}개")
            print(f"   - 장(##): {장_count}개")
            print(f"   - 절(###): {절_count}개")
            print(f"   - 조(####): {조_count}개")
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
        
        # 각 계층별 패턴 찾기 (더 넓은 범위)
        편_matches = re.findall(r'^[`\s]*(?:제\s*\d+\s*편)(?:\s*[^\n`]*)?[`\s]*$', content, flags=re.MULTILINE)
        장_matches = re.findall(r'^[`\s]*(?:제\s*\d+\s*장)(?:\s*[^\n`]*)?[`\s]*$', content, flags=re.MULTILINE)
        절_matches = re.findall(r'^[`\s]*(?:제\s*\d+\s*절)(?:\s*[^\n`]*)?[`\s]*$', content, flags=re.MULTILINE)
        조_matches = re.findall(r'^(?!####)[`\s]*(?:제\s*\d+\s*조)(?:\s*[^\n`]*)?[`\s]*$', content, flags=re.MULTILINE)
        
        print(f"\n📋 {os.path.basename(file_path)}에서 발견된 패턴:")
        print("-" * 60)
        
        if 편_matches:
            print(f"📖 편: {len(편_matches)}개")
            for i, match in enumerate(편_matches[:5], 1):
                print(f"   {i}. {match}")
            if len(편_matches) > 5:
                print(f"   ... 외 {len(편_matches) - 5}개 더")
        
        if 장_matches:
            print(f"📚 장: {len(장_matches)}개")
            for i, match in enumerate(장_matches[:5], 1):
                print(f"   {i}. {match}")
            if len(장_matches) > 5:
                print(f"   ... 외 {len(장_matches) - 5}개 더")
        
        if 절_matches:
            print(f"📄 절: {len(절_matches)}개")
            for i, match in enumerate(절_matches[:5], 1):
                print(f"   {i}. {match}")
            if len(절_matches) > 5:
                print(f"   ... 외 {len(절_matches) - 5}개 더")
        
        if 조_matches:
            print(f"📝 조: {len(조_matches)}개")
            for i, match in enumerate(조_matches[:10], 1):
                print(f"   {i}. {match}")
            if len(조_matches) > 10:
                print(f"   ... 외 {len(조_matches) - 10}개 더")
        
        total = len(편_matches) + len(장_matches) + len(절_matches) + len(조_matches)
        if total == 0:
            print("❌ 편/장/절/조 패턴을 찾을 수 없습니다.")
        else:
            print(f"\n📊 총 {total}개의 헤더가 추가될 예정입니다.")
            
    except Exception as e:
        print(f"❌ 미리보기 오류 ({file_path}): {e}")

if __name__ == "__main__":
    print("🔧 계층구조 헤더 추가 도구")
    print("📋 편(#) > 장(##) > 절(###) > 조(####)")
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