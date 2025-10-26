# streamlit_app.py
import streamlit as st
from rag_pipline.build_graph import build_graph
from vectordb.custom_pgvector import CustomPGVector  # ✅ 전역 DB 연결 관리용

# --- DB 접속 정보 ---
CONN_STR = "postgresql://admin:admin123@localhost:5432/UNITvectordb"

# --- 페이지 설정 ---
st.set_page_config(page_title="보험 약관 RAG 챗봇", page_icon="🤖", layout="wide")

st.title("🤖 보험 약관 RAG 챗봇")
st.caption("자동으로 보험 약관 문서를 검색해 답변해주는 LangGraph 기반 챗봇")

# =====================================================================
# 1️⃣ 앱 전체에서 한 번만 DB 연결 (CustomPGVector)
# =====================================================================
if "vectorstore" not in st.session_state:
    print("🔗 [DB] 전역 PGVector 연결 생성 중...")
    try:
        st.session_state.vectorstore = CustomPGVector(CONN_STR)
        print("✅ [DB] PGVector 연결 완료 (앱 전역)")
    except Exception as e:
        st.error(f"❌ DB 연결 실패: {e}")
        st.stop()

# =====================================================================
# 2️⃣ LangGraph 빌드 (세션별 1회)
# =====================================================================
if "graph_app" not in st.session_state:
    print("🔄 [APP] 그래프 초기화 시작...")
    # ✅ 수정된 부분: conn_str이 아니라 vectorstore 전달
    graph = build_graph(st.session_state.vectorstore)
    st.session_state.graph_app = graph.compile()
    print("✅ [APP] 그래프 초기화 완료 - 세션에 저장됨")
else:
    print("♻️ [APP] 기존 그래프 재사용 중...")

# =====================================================================
# 3️⃣ 채팅 상태 초기화
# =====================================================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# =====================================================================
# 4️⃣ 사용자 입력 + LangGraph 실행
# =====================================================================
user_input = st.chat_input("질문을 입력하세요...")

if user_input:
    # 챗봇 로딩 애니메이션
    with st.spinner("답변 생성 중..."):
        print(f"💬 [APP] 사용자 질문: {user_input}")
        print("🚀 [APP] LangGraph 파이프라인 실행 중...")

        state = {"user_input": user_input, "retry_count": 0}

        try:
            final_state = st.session_state.graph_app.invoke(state)
            answer = final_state.get("final_answer", "답변 생성 실패")
            print("✅ [APP] 답변 생성 완료")
        except Exception as e:
            answer = f"⚠️ 오류 발생: {e}"
            print(f"❌ [APP] 오류 발생: {e}")

    # 대화 내용 저장
    st.session_state.chat_history.append(("user", user_input))
    st.session_state.chat_history.append(("bot", answer))

# =====================================================================
# 5️⃣ 대화 출력 (Streamlit 채팅 UI)
# =====================================================================
for role, message in st.session_state.chat_history:
    if role == "user":
        with st.chat_message("user"):
            st.write(message)
    else:
        with st.chat_message("assistant"):
            st.write(message)
