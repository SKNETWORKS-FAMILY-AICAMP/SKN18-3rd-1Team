# graph/main_graph.py
# --------------------------------------------
# 목적: LangGraph 메인 플로우 정의
# 구조: classify → similarity_func → loop → (compare/analyze 병렬) → answer → END
# --------------------------------------------

from typing import TypedDict               # TypedDict 사용. 상태 키 타입 명시 목적
from langgraph.graph import StateGraph, END  # LangGraph 핵심 객체. 그래프 구성 및 종료 지점 지정

# 개별 에이전트 함수 임포트
from nodes.classify_agent import classify_agent   # 질문 관련성 분류 에이전트
from nodes.loop_agent import loop_agent           # 유사도 점수 기반 루프 제어 에이전트
from nodes.compare_agent import compare_agent     # 비교 에이전트
from nodes.analyze_agent import analyze_agent     # 분석 에이전트
from nodes.answer_agent import answer_agent       # 최종 응답 생성 에이전트


# --------------------------------------------
# 상태(State) 스키마 정의
# --------------------------------------------
class State(TypedDict):
    question: str             # 사용자 질문 텍스트
    classification: str       # "relevant" / "irrelevant" 분류 결과
    chunks: list              # 유사도 검색으로 가져온 문단 리스트
    similarity_score: float   # 평균 유사도 점수(0~1)
    compare_result: dict | None   # 비교 에이전트 산출물(사전 형태 또는 None)
    analysis_result: dict | None  # 분석 에이전트 산출물(사전 형태 또는 None)
    answer: str               # 최종 응답 텍스트


# --------------------------------------------
# 그래프 인스턴스 생성
# --------------------------------------------
graph = StateGraph(State)     # State 타입 전달. 내부 검증 및 IDE 타입 서포트 목적

# --------------------------------------------
# 노드 등록
# --------------------------------------------
graph.add_node("classify_agent", classify_agent)   # 분류 단계 노드
graph.add_node("loop_agent", loop_agent)           # 루프 제어 노드(내부에서 similarity_func 호출)
graph.add_node("compare_agent", compare_agent)     # 비교 노드
graph.add_node("analyze_agent", analyze_agent)     # 분석 노드
graph.add_node("answer_agent", answer_agent)       # 최종 응답 노드

# --------------------------------------------
# 분기 함수 정의
# --------------------------------------------
def route_after_loop(state):
    """loop_agent 후 비교/분석 분기"""
    question = state.get("question", "").lower()
    
    # 비교 키워드 체크
    compare_keywords = ["비교", "차이", "어떤게", "vs", "대비"]
    if any(keyword in question for keyword in compare_keywords):
        return "compare_agent"
    
    # 분석 키워드 체크  
    analyze_keywords = ["분석", "상세", "자세히", "어떻게", "왜"]
    if any(keyword in question for keyword in analyze_keywords):
        return "analyze_agent"
    
    # 기본값은 분석
    return "analyze_agent"

# --------------------------------------------
# 엣지(흐름) 정의
# --------------------------------------------

# 1) classify 결과에 따라 루프 진입 또는 종료
# 60-67번째 줄 수정:
graph.add_conditional_edges(
    "loop_agent",
    route_after_loop,  # 분기 함수 사용
    {
        "compare_agent": "compare_agent",
        "analyze_agent": "analyze_agent"
    }
)


# 2) loop_agent 결과에 따라 재분류 루프 또는 병렬 분기
graph.add_conditional_edges(
    "loop_agent",
    lambda s: "loop" if (s.get("similarity_score") or 0.0) < 0.7 else "route_decision",
    {
        "loop": "classify_agent",
        "route_decision": "route_decision"
    }
)

# route_decision 노드 추가 (기존 route_after_loop 함수 사용)
graph.add_node("route_decision", route_after_loop)

# route_decision에서 분기
graph.add_conditional_edges(
    "route_decision",
    route_after_loop,
    {
        "compare_agent": "compare_agent",
        "analyze_agent": "analyze_agent"
    }
)

# 연결
graph.add_edge("compare_agent", "analyze_agent")
graph.add_edge("analyze_agent", "answer_agent")

# 4) answer → END
graph.add_edge("answer_agent", END)                 # 최종 종료

# 5) 시작/종료 포인트 지정
graph.set_entry_point("classify_agent")             # 시작 노드 설정
graph.set_finish_point("answer_agent")              # 종료 지점 설정
