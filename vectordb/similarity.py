# utils/similarity.py
# --------------------------------------------
# 목적: 단순 함수로 벡터 검색 + 유사도 계산 수행
# 구현: 네가 쓰는 pgvector 커스텀 래퍼를 그대로 사용
# 출력: (chunks, avg_score)
# --------------------------------------------
# utils/similarity.py
import os, sys
from typing import List, Tuple                        # 타입 힌트
from .customPGVector import CustomPGVector
from .embedding_models import get_embedding_model_openai

# 벡터스토어 인스턴스 생명주기: 매 호출마다 생성하면 비용 발생
# 간결성 위해 모듈 전역에 보관. 실제 서비스면 DI/싱글턴 패턴 권장
_embedding_fn = get_embedding_model_openai()         # 임베딩 함수 핸들 확보
_vectorstore = CustomPGVector(                       # 네 래퍼 생성자 시그니처에 맞춰 세팅
    conn_str="postgresql://admin:admin123@localhost:5432/vectordb",  # 네가 사용 중인 로컬 테스트 DSN 예시
    embedding_fn=_embedding_fn                       # 임베딩 함수 주입
)

def similarity_func(question: str, top_k: int = 3) -> Tuple[List[str], float]:
    """
    입력: question 텍스트
    동작: pgvector에서 top_k 검색, 스코어 기반 평균 계산
    출력: (chunk 텍스트 리스트, 평균 유사도 스코어)
    """
    # 1) 벡터 검색 실행. 네 래퍼의 search 시그니처에 맞춰 호출
    #    기대 반환: [{"content": "...", "score": 0.83}, ...] 형태
    results = _vectorstore.search(query=question, top_k=top_k)

    # 2) 결과 비어있으면 기본값 반환
    if not results:
        return [], 0.0

    # 3) 평균 스코어 계산
    scores = [score for _, score in results]
    avg = sum(scores) / max(len(scores), 1)

    # 4) chunk 텍스트 리스트 구성
    chunks = [doc.page_content for doc, _ in results]

    # 5) (chunks, 평균) 반환
    return chunks, float(avg)
