from typing_extensions import TypedDict
from typing import List, Dict, Any, Optional

class RAGState(TypedDict):
    """보험 RAG 시스템의 상태 관리"""
    
    # === 사용자 입력 ===
    question: str                           # 현재 질문 (재작성될 수 있음)
    original_question: Optional[str]        # 원본 질문 (변경되지 않음)
    
    # === 1단계: 질문 분류 결과 ===
    can_answer_with_data: Optional[bool]    # 답변 가능 여부 (분기 조건 1)
    category: Optional[str]                 # analysis/comparison/general
    company_filter: Optional[str]           # 보험사 필터 (참고용)
    product_filter: Optional[str]           # 상품 필터 (참고용)
    
    # === 2단계: 검색 결과 ===
    retrieved_docs: Optional[List[Dict[str, Any]]]  # 검색된 모든 문서들
    total_found: Optional[int]              # 검색된 문서 개수
    
    # === 3단계: 평가 결과 ===
    relevant_docs: Optional[List[Dict[str, Any]]]   # 관련성 높은 문서들만
    evaluation_result: Optional[str]        # "yes"/"no" (분기 조건 2)
    avg_relevance: Optional[float]          # 평균 관련성 점수
    evaluation_message: Optional[str]       # 평가 상세 메시지
    
    # === 4단계: 질문 재작성 ===
    rewrite_count: Optional[int]            # 재작성 횟수 (최대 1회)
    rewritten_question: Optional[str]       # 재작성된 질문
    
    # === 5단계: 최종 답변 ===
    answer: Optional[str]                   # 생성된 답변
    sources: Optional[List[Dict[str, Any]]] # 답변 근거 자료
    generation_success: Optional[bool]      # 답변 생성 성공 여부
    
    # === 메타 정보 ===
    step: Optional[str]                     # 현재 진행 단계
    error_message: Optional[str]            # 오류 메시지