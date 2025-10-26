#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 처리 파이프라인 - enhanced_pdf_extractor + text_merger 통합
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import re

try:
    import pymupdf4llm
    import pdfplumber
    TOOLS_AVAILABLE = True
except ImportError as e:
    TOOLS_AVAILABLE = False
    print(f"❌ 필요한 라이브러리: {e}")

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFPipeline:
    def __init__(self):
        """PDF 파이프라인 초기화"""
        self.results = []
    
    def process_pdf(self, pdf_path, output_dir=None):
        """PDF 완전 처리: 추출 → 병합 → 헤더 추가"""
        pdf_path = Path(pdf_path)
        
        if output_dir is None:
            output_dir = pdf_path.parent / f"{pdf_path.stem}_processed"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        logger.info(f"PDF 처리 시작: {pdf_path.name}")
        
        try:
            # 1. 다중 추출 (메모리에서만)
            extraction_contents = self._extract_multiple(pdf_path, output_dir)
            
            # 2. 병합 (메모리에서만)
            merged_content = self._merge_contents(extraction_contents, output_dir)
            
            # 3. 헤더 추가 및 최종 파일 저장
            final_file = self._add_headers(merged_content, output_dir)
            
            result = {
                'success': True,
                'pdf_file': str(pdf_path),
                'output_dir': str(output_dir),
                'final_file': final_file,
                'extraction_methods': list(extraction_contents.keys())
            }
            
            logger.info(f"✅ 처리 완료: {final_file}")
            return result
            
        except Exception as e:
            logger.error(f"❌ 처리 실패: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_multiple(self, pdf_path, output_dir):
        """여러 방법으로 추출 (메모리에서만 처리)"""
        contents = {}
        
        # PyMuPDF4LLM
        try:
            content = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=False, write_images=False)
            if content and len(content) > 100:
                contents['pymupdf4llm'] = content
                logger.info(f"  PyMuPDF4LLM: {len(content):,} 문자")
        except Exception as e:
            logger.warning(f"  PyMuPDF4LLM 실패: {e}")
        
        # pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                content = ""
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        content += f"=== 페이지 {page_num} ===\n{page_text}\n\n"
                
                if content and len(content) > 100:
                    contents['pdfplumber'] = content
                    logger.info(f"  pdfplumber: {len(content):,} 문자")
        except Exception as e:
            logger.warning(f"  pdfplumber 실패: {e}")
        
        return contents
    
    def _merge_contents(self, extraction_contents, output_dir):
        """추출 내용들 병합 (메모리에서만 처리)"""
        if not extraction_contents:
            raise Exception("병합할 내용이 없습니다")
        
        # 가장 긴 내용을 베이스로 선택
        base_method = None
        max_length = 0
        
        for method, content in extraction_contents.items():
            if len(content) > max_length:
                max_length = len(content)
                base_method = method
        
        merged_content = extraction_contents[base_method]
        
        # 병합 정보 추가
        merge_info = f"""
{'='*60}
텍스트 병합 정보
{'='*60}
병합 일시: {datetime.now().isoformat()}
베이스 방법: {base_method}
최종 길이: {len(merged_content):,} 문자
{'='*60}

"""
        
        final_content = merge_info + merged_content
        
        logger.info(f"  병합 완료: {len(final_content):,} 문자")
        return final_content
    
    def _add_headers(self, merged_content, output_dir):
        """헤더 추가"""
        # 헤더 패턴들
        patterns = [
            (r'^(◦\s*(알기 쉬운 자동차보험 이야기|보통약관|특별약관|관련 법령|교통사고 발생시 대처요령)(?:\s+\d+)?)', r'# \2'),
            (r'^(제([0-9]+)편\s+([^.\n]+?)(?:\s*\.+.*|\s+\d+)?$)', r'## 제\2편 \3'),
            (r'^(제([0-9]+)장\s+([^.\n]+?)(?:\s*\.+.*|\s+\d+)?$)', r'### 제\2장 \3'),
            (r'^(제([0-9]+)절\s+([^.\n]+?)(?:\s*\.+.*|\s+\d+)?$)', r'#### 제\2절 \3'),
        ]
        
        # 패턴 적용
        modified_content = merged_content
        headers_count = 0
        
        for pattern, replacement in patterns:
            matches = re.findall(pattern, modified_content, re.MULTILINE)
            headers_count += len(matches)
            modified_content = re.sub(pattern, replacement, modified_content, flags=re.MULTILINE)
        
        # 최종 파일 저장
        final_file = output_dir / f"{output_dir.name}_final.txt"
        with open(final_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        logger.info(f"  헤더 추가: {headers_count}개")
        return str(final_file)
    
    def process_directory(self, directory_path, output_dir=None):
        """디렉토리 내 모든 PDF 처리"""
        directory_path = Path(directory_path)
        pdf_files = list(directory_path.rglob("*.pdf"))
        
        if not pdf_files:
            logger.warning("PDF 파일을 찾을 수 없습니다")
            return []
        
        if output_dir is None:
            output_dir = directory_path / "pipeline_output"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True)
        
        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"처리 중 ({i}/{len(pdf_files)}): {pdf_file.name}")
            
            file_output_dir = output_dir / pdf_file.stem
            result = self.process_pdf(pdf_file, file_output_dir)
            results.append(result)
        
        return results

def main():
    """메인 함수"""
    if not TOOLS_AVAILABLE:
        return
    
    print("🚀 PDF 처리 파이프라인")
    print("=" * 30)
    
    pipeline = PDFPipeline()
    
    print("1. 단일 PDF 처리")
    print("2. 디렉토리 처리")
    print("3. 종료")
    
    choice = input("\n선택 (1/2/3): ").strip()
    
    if choice == "1":
        pdf_path = input("PDF 파일 경로: ").strip()
        result = pipeline.process_pdf(pdf_path)
        
        if result['success']:
            print(f"\n✅ 완료!")
            print(f"📄 최종 파일: {result['final_file']}")
        else:
            print(f"\n❌ 실패: {result['error']}")
    
    elif choice == "2":
        dir_path = input("디렉토리 경로: ").strip()
        results = pipeline.process_directory(dir_path)
        
        successful = len([r for r in results if r['success']])
        print(f"\n📊 결과: {successful}/{len(results)} 성공")
        
        for result in results:
            if result['success']:
                filename = Path(result['pdf_file']).name
                print(f"  ✅ {filename}")
            else:
                filename = Path(result.get('pdf_file', 'unknown')).name
                print(f"  ❌ {filename}")
    
    elif choice == "3":
        print("종료합니다.")

if __name__ == "__main__":
    main()