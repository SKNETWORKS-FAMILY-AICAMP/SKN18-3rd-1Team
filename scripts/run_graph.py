from rag_pipline.build_graph import build_graph
from pprint import pprint

CONN_STR = "postgresql://admin:admin123@localhost:5432/UNITvectordb"

def run_pipeline(user_input: str):
    """사용자 질문을 받아 LangGraph 파이프라인 실행"""
    graph = build_graph(conn_str=CONN_STR)
    app = graph.compile()

    state = {"user_input": user_input, "retry_count": 0}
    final_state = app.invoke(state)
    return final_state.get("final_answer", "답변 생성 실패")

if __name__ == "__main__":
    question = input("질문을 입력하세요: ")
    print(run_pipeline(question))
