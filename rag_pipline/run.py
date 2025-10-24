# input에 따른 output 전체 실행
from graph.insurance_graph import build_insurance_graph

if __name__ == "__main__":
    graph = build_insurance_graph()
    query = input("질문을 입력하세요: ")
    result = graph.invoke({"user_input": query})
    print("\n💬 결과:\n", result.get("final_answer"))
