# chatbot.py
import os
import sys

# 현재 파일(chatbot.py)이 있는 프로젝트 루트를 Python 모듈 탐색 경로에 추가
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from graph.main_graph import graph

# --- LangGraph 실행부 ---
app = graph.compile()

# 사용자 입력 받기
question = input("질문을 입력하세요: ")

state = {
    "question": question  # 사용자 입력 사용
}

result = app.invoke(state)
print("답변:", result.get("answer", "답변을 생성할 수 없습니다."))