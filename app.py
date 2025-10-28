# streamlit_app.py
import streamlit as st
from rag_pipline.build_graph import build_graph
from vectordb.custom_pgvector import CustomPGVector  # ✅ 전역 DB 연결 관리용

# --- DB 접속 정보 ---
CONN_STR = "postgresql://admin:admin123@localhost:5432/UNITvectordb"

# --- 페이지 설정 ---
st.set_page_config(page_title="보험 약관 RAG 챗봇", page_icon="🚗", layout="wide")

# 사이드바 스타일 커스터마이징
st.markdown("""
<style>
    .css-1d391kg {
        background-color: #fef5f5;
    }
    .css-1lcbmhc {
        background-color: #fef5f5;
    }
    .css-17eq0hr {
        background-color: #fef5f5;
    }
    section[data-testid="stSidebar"] {
        background-color: #fef5f5;
        color: #333333;
    }
    section[data-testid="stSidebar"] .css-ng1t4o {
        color: #333333;
    }
    section[data-testid="stSidebar"] .css-pkbazv {
        color: #333333;
    }
    section[data-testid="stSidebar"] h1 {
        color: #333333;
    }
    section[data-testid="stSidebar"] h3 {
        color: #333333;
    }
    section[data-testid="stSidebar"] .css-10trblm {
        color: #333333;
    }
    /* Expander 테두리 제거 */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        border: none !important;
        border-radius: 0 !important;
        background-color: transparent !important;
    }
    section[data-testid="stSidebar"] .streamlit-expanderContent {
        border: none !important;
        border-radius: 0 !important;
        background-color: transparent !important;
    }
    section[data-testid="stSidebar"] details {
        border: none !important;
    }
    section[data-testid="stSidebar"] summary {
        border: none !important;
        background-color: transparent !important;
    }
    section[data-testid="stSidebar"] .css-1kyxreq {
        border: none !important;
    }
    section[data-testid="stSidebar"] .css-nahz7x {
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚗 보험 약관 챗봇")
st.caption("자동으로 보험 약관 문서를 검색해 답변해주는 LangGraph 기반 챗봇")

# =====================================================================
# 🧭 Sidebar: 보험사 및 상품 Info Cards
# =====================================================================
with st.sidebar:
    # 헤더 섹션
    st.markdown("# 🏢 **보험사 정보**")
    st.caption("지원되는 보험사 및 상품")
    
    st.markdown("---")
    
    # 보험사별 정보를 더 깔끔하게 표시
    insurance_companies = [
        {
            "name": "현대해상",
            "color": "#0066CC",
            "disclosure_url": "https://www.hi.co.kr/serviceAction.do?menuId=100932",
            "products": [
                "개인용자동차보험",
                "업무용자동차보험", 
                "영업용자동차보험",
                "타임쉐어 자동차보험",
                "이륜자동차보험"
            ]
        },
        {
            "name": "삼성화재",
            "color": "#FF4444",
            "disclosure_url": "https://www.samsungfire.com/vh/page/VH.HPIF0103.do",
            "products": [
                "개인용자동차보험약관",
                "업무용자동차보험약관",
                "영업용자동차보험약관", 
                "원데이자동차보험약관",
                "이륜자동차보험약관"
            ]
        },
        {
            "name": "KB손해보험",
            "color": "#FFB800",
            "disclosure_url": "https://www.kbinsure.co.kr/CG802030001.ec",
            "products": [
                "개인용자동차보험",
                "업무용자동차보험",
                "영업용자동차보험",
                "이륜차자동차보험", 
                "하루자동차보험"
            ]
        },
        {
            "name": "롯데손해보험", 
            "color": "#00AA44",
            "disclosure_url": "https://www.lotteins.co.kr/web/C/D/H/cdh190.jsp",
            "products": [
                "롯데 개인용자동차보험",
                "롯데 업무용자동차보험",
                "롯데 영업용자동차보험",
                "롯데 원데이자동차보험",
                "롯데 이륜차자동차보험"
            ]
        },
        {
            "name": "하나손해보험",
            "color": "#8844AA",
            "disclosure_url": "https://m.hanainsure.co.kr/w/disclosure/product/saleProduct",
            "products": [
                "개인용자동차보험",
                "업무용자동차보험", 
                "영업용자동차보험",
                "이륜차자동차보험",
                "원데이자동차보험"
            ]
        }
    ]
    
    # 각 보험사 정보를 expander로 표시
    for company in insurance_companies:
        with st.expander(f"**{company['name']}**", expanded=False):
            # 상품 목록 표시
            st.markdown("**📋 보험 상품:**")
            for product in company['products']:
                st.markdown(f"• {product}")
            
            st.markdown("---")
            
            # 공시실 링크 버튼
            st.markdown("**🔗 공시정보:**")
            st.link_button(
                f"{company['name']} 공시실 바로가기",
                company['disclosure_url'],
                use_container_width=True
            )
    
    st.markdown("---")

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
    with st.spinner("답변 생성 중..."):
        print(f"💬 [APP] 사용자 질문: {user_input}")
        print("🚀 [APP] LangGraph 파이프라인 실행 중...")

        state = {"user_input": user_input, "retry_count": 0}

        try:
            final_state = st.session_state.graph_app.invoke(state)
            answer = final_state.get("final_answer", "저희 서비스에서 제공하지 않는 질문입니다. 다시 질문해 주세요.")
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
