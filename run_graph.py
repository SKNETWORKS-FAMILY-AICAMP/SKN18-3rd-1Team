"""
LangGraph 전체 파이프라인 실행 파일
"""

from build_graph import build_graph
from pprint import pprint

CONN_STR = "postgresql://admin:admin123@localhost:5432/UNITvectordb"

# 그래프 빌드 및 컴파일
graph = build_graph(conn_str=CONN_STR)
app = graph.compile()

# 초기 상태
state = {
    "user_input": "삼성화재 자동차보험 대물배상 한도 알려줘",
    "retry_count": 0
}

print("\n🚀 그래프 실행 시작...\n")
final_state = app.invoke(state)

print("\n🎯 최종 결과")
pprint(final_state.get("final_answer", "답변 생성 실패"))
print("\n🎯 최종 상태 전체 확인")
from pprint import pprint
pprint(final_state)
