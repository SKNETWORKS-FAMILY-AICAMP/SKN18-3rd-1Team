"""
LangGraph 전체 파이프라인 실행 파일
"""
import os
from rag_pipline.build_graph import build_graph
from pprint import pprint

CONN_STR = "postgresql://admin:admin123@localhost:5432/UNITvectordb"

def main():
    # 사용자 입력 받기
    user_input = input("질문을 입력하세요: ").strip()
    if not user_input:
        print("❌ 입력이 비어 있습니다. 종료합니다.")
        return

    # 그래프 빌드 및 컴파일
    print("\n🧩 그래프 빌드 중...\n")
    graph = build_graph(conn_str=CONN_STR)
    app = graph.compile()

    # 초기 상태 설정
    state = {
        "user_input": user_input,
        "retry_count": 0
    }

    # 그래프 실행
    print("\n🚀 그래프 실행 시작...\n")
    final_state = app.invoke(state)

    # 결과 출력
    print("\n🎯 최종 결과")
    pprint(final_state.get("final_answer", "답변 생성 실패"))

    print("\n📦 최종 상태 전체 확인")
    pprint(final_state)

if __name__ == "__main__":
    main()
