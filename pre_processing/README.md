pre-processing 폴더 안에서

pdf_pipeline.py -> pymupdf4llm + pdfplumber 사용해서 상호보완 text 추출

remove_hash.py + add_headers_all_files.py -> 추출하면서 임의로 생긴 # 제거 후 조항에 #### 태그

remove_header_content.py -> 목차 이전의 텍스트 싹다 삭제

convert_all_to_csv.py -> csv로 변환 -> (조항,내용)