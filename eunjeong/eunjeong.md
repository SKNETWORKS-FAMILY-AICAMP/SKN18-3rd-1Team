# 📁 디렉토리 및 파일 구조

### 🔧 설정 파일들  
- **`.env`** - 환경 변수 설정 (API 키, DB 연결 정보)
- **`.gitignore`** - Git 버전 관리에서 제외할 파일 목록
- **`requirements.txt`** - Python 패키지 의존성 목록 (LangChain, OpenAI, pgvector 등)
- **`docker-compose.yml`** - PostgreSQL + pgvector 데이터베이스 컨테이너 설정
- **`init.sql`** - PostgreSQL 초기화 스크립트 (pgvector 확장 및 테이블 생성)

### 📊 데이터 관련
- **`data/`** - 보험 약관 원본 데이터 저장소
  - `insurance_clauses.csv` - 모든 보험사 약관을 통합한 최종 CSV 파일
  - `현대/`, `삼성화재/`, `KB/`, `하나/`, `롯데/`, `DB손해보험 약관/` - 각 보험사별 원본 데이터W

### 🤖 RAG 파이프라인 (`rag_pipeline/`)
- **`build_graph.py`** - LangGraph 기반 RAG 워크플로우 정의 및 빌드
- **`nodes/`** - LangGraph 워크플로우의 각 노드 구현체들
  - `query_classifier_node.py` - 사용자 질문 분류 (단일/비교/기타)
  - `search_vectordb_node.py` - 벡터 데이터베이스 검색 수행
  - `evaluation_node.py` - 검색 결과 관련성 평가
  - `rewrite_node.py` - 질문 재작성 (검색 결과 미흡 시)
  - `create_node.py` - 최종 답변 생성
- **`vectordb/`** - 벡터 데이터베이스 관련 유틸리티
  - `custom_pgvector.py` - PGVector 기반 벡터 검색 엔진 (검색 전용)
  - `vector_store.py` - 임베딩 생성 및 데이터베이스 저장 유틸리티

### 🔗 실행 스크립트 (`scripts/`)
- **`run_graph.py`** - 구축된 그래프를 실행하여 질의응답 수행
- **`draw_graph.py`** - 워크플로우 구조를 시각화하여 PNG 이미지로 저장

### 📈 시각화
- **`graph_structure.png`** - LangGraph 워크플로우 구조 다이어그램

### 🔄 데이터 처리 플로우

1. **데이터 준비** → 보험 약관 CSV 파일을 `data/insurance_clauses.csv`에 준비
2. **벡터 저장소 구축** (`vector_store.py`) → 텍스트 청킹, 임베딩 생성 및 pgvector DB 저장
3. **RAG 파이프라인 실행** (`run_graph.py`) → 사용자 질의에 대한 지능형 답변 생성
   - 질문 분류 → 벡터 검색 → 관련성 평가 → 답변 생성 (필요시 질문 재작성)
4. **워크플로우 시각화** (`draw_graph.py`) → 그래프 구조를 PNG로 출력