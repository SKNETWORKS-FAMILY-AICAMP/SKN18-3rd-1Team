# agents/loop_agent.py
# --------------------------------------------
# 목적: similarity_func 호출 → 점수 판단 → 다음 분기 준비
# 출력: state["chunks"], state["similarity_score"] 갱신
# --------------------------------------------

from vectordb.similarity import similarity_func      # 단순 함수 임포트

def loop_agent(state: dict) -> dict:
    """루프 제어 에이전트. 유사도 계산 후 score 저장."""
    question = state["question"]                  # 질문 추출
    chunks, score = similarity_func(question)     # 벡터 검색 + 평균 스코어 계산

    state["chunks"] = chunks                      # 검색 결과 저장
    state["similarity_score"] = score             # 점수 저장
    # 그래프에서 임계치 비교 후 분기 처리. 임계치는 main_graph에서 수행
    return state                                  # 갱신된 state 반환
