# 보험 상담 RAG 어시스턴트 (SKN18-3rd-1Team)

보험 약관을 빠르게 분석해주는 LangGraph 기반 Retrieval-Augmented Generation(RAG) 파이프라인과 Streamlit 상담 UI를 제공합니다. 보험 상품 비교‧추천 상담 시 반복되는 질의에 신속하고 일관성 있는 답변을 제공하는 것이 목표입니다.

---

## 개요

- **사용자 경험**: Streamlit 채팅 UI에서 자연어 질문 입력 → LangGraph 파이프라인이 관련 약관을 검색해 답변 생성
- **데이터**: 자체 파싱한 보험 약관 PDF → CSV(`data/insurance_clauses.csv`) → pgvector 테이블에 임베딩 저장
- **모델 파이프라인**:
  1. 질문 분류(`QueryClassifierNode`)
  2. pgvector 유사도 검색(`SearchVectorDBNode`)
  3. 관련성 평가(`EvaluationNode`, 임계값 0.7)
  4. 부족 시 질문 재작성(`RewriteNode`, 최대 1회)
  5. 답변 생성(`CreateNode`) 및 근거 출처 표기

주요 구성 요소는 LangGraph, LangChain, OpenAI API, PostgreSQL + pgvector, PyMuPDF4LLM(약관 파서)입니다.

---

## 저장소 구조

```text
.
├─app.py                     # Streamlit 진입점
├─rag_pipline/               # LangGraph 파이프라인 및 벡터스토어 래퍼
│   ├─build_graph.py         # 그래프 정의(StateGraph)
│   ├─nodes/                 # LangGraph 노드(분류, 검색, 평가, 재작성, 생성)
│   ├─vectordb/custom_pgvector.py
│   └─vector_store.py        # CSV → pgvector 적재 스크립트
├─scripts/
│   ├─run_graph.py           # CLI 파이프라인 실행기
│   └─draw_graph.py          # LangGraph 구조 PNG 생성
├─pgvector/
│   ├─docker-compose.yml     # PostgreSQL + pgvector 서비스
│   └─init.sql               # 초기 테이블 스키마
├─data/                      # 파싱된 약관 CSV + 원천 PDF(회사별 폴더)
├─dongsuk/, sihyun/          # 실험용 RAG 파이프라인·파서 코드
├─requirements.txt
└─graph_structure.png        # LangGraph 다이어그램 예시
```

---

## LangGraph 파이프라인

| 노드 | 역할 | 세부 내용 |
| --- | --- | --- |
| `QueryClassifierNode` | 질의 분류 | `single`/`comparison`/`other` 분류, 비교 대상 보험사 추출 |
| `SearchVectorDBNode` | 문서 검색 | pgvector에서 회사 필터 기반 유사도 검색 |
| `EvaluationNode` | 관련성 평가 | OpenAI 모델로 chunk relevance(0~1) 산출, 평균 0.7 ↑ 시 통과 |
| `RewriteNode` | 질문 재작성 | 관련성이 낮으면 1회까지 질문 재작성 후 재검색 |
| `CreateNode` | 답변 생성 | 관련 chunks 기반 답변 작성, 사용된 회사·상품 정보를 출처로 표시 |

`graph_structure.png` 또는 `python scripts/draw_graph.py` 실행으로 파이프라인을 시각화할 수 있습니다.

---

## 실행 준비

### 1. 사전 요구 사항

- Python 3.10 이상
- Docker & Docker Compose
- OpenAI API Key (텍스트 임베딩/모델 호출용)

### 2. 의존성 설치

```bash
python -m venv .venv
.venv\Scripts\activate           # PowerShell 예시
pip install -r requirements.txt
```

### 3. 환경 변수

루트에 `.env` 파일을 생성해 API 키와 선택 옵션을 설정합니다.

```env
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-large   # 필요 시 변경
CONNECTION_STRING=postgresql://admin:admin123@localhost:5432/UNITvectordb
```

`rag_pipline/custom_pgvector.py`는 `EMBEDDING_MODEL`이 없을 경우 기본값을 사용하며, `dongsuk/vectordb` 모듈은 `CONNECTION_STRING`을 참조합니다.

### 4. pgvector 데이터베이스 기동

```bash
cd pgvector
docker compose up -d
```

- 기본 접속 정보: `admin / admin123`, 데이터베이스 `UNITvectordb`
- 최초 실행 시 `init.sql`이 `insurance_embeddings` 테이블을 생성합니다.

### 5. 임베딩 적재

```bash
python rag_pipline/vector_store.py
```

- `data/insurance_clauses.csv`를 chunk로 분할 후 OpenAI 임베딩을 생성해 `insurance_embeddings` 테이블에 저장합니다.
- OpenAI API 호출 비용이 발생하므로 키와 모델 설정을 확인하세요.

### 6. Streamlit 앱 실행

```bash
streamlit run app.py
```

브라우저에서 챗 UI가 열립니다. 최초 요청 시 pgvector 연결과 LangGraph 컴파일이 진행됩니다.

---

## 추가 실행 옵션

- **CLI 테스트**: `python scripts/run_graph.py` 실행 후 콘솔에서 질문을 입력해 파이프라인을 테스트할 수 있습니다.
- **그래프 PNG 출력**: `python scripts/draw_graph.py` 실행 시 `graph_structure.png` 파일이 갱신됩니다. (Mermaid 렌더링을 위해 LangGraph의 `xray` 기능 사용)

---

## 데이터 파이프라인

- `sihyun/parsers/`에 보험사/상품별 PDF 파서가 정리되어 있으며, `preprocess_v2.py`가 PDF → CSV 변환을 담당합니다.
- `data/` 하위에 보험사별 원천 PDF와 변환 결과 CSV(`insurance_clauses.csv`)가 위치합니다.
- 필요 시 새로운 PDF를 추가하고 파서를 확장해 CSV를 재생성한 뒤 `vector_store.py`로 임베딩을 새로 구축하세요.

---

## 실험용 모듈

- `dongsuk/` 폴더에는 초기 LangGraph 프로토타입과 모듈화된 vector DB 래퍼가 포함돼 있습니다.
- `rag_pipline/`의 본 파이프라인과 비교하며 커스터마이징 할 수 있습니다.

---

## 문제 해결 가이드

- **DB 연결 오류**: `docker compose ps`로 컨테이너 상태를 확인하고, `.env`의 `CONNECTION_STRING`과 `app.py` 내 `CONN_STR`이 동일한지 확인하세요.
- **OpenAI Rate Limit**: 임베딩 적재·답변 생성은 OpenAI 호출을 사용합니다. 키 권한과 요청 빈도를 점검하세요.
- **그래프 재컴파일 지연**: Streamlit 실행 시 LangGraph가 최초 1회 컴파일되므로 초기 요청이 다소 지연될 수 있습니다.

---

## 문의

SKN18-3rd-1Team – 프로젝트 관련 문의는 팀 리더 또는 저장소 이슈를 통해 전달해주세요.

*Made with ❤️ by SKN18-3rd-1Team*
