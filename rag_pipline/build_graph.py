import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_pipeline"))

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Any
from dotenv import load_dotenv

load_dotenv()

# === Import all nodes ===
from nodes.query_classifier_node import QueryClassifierNode
from nodes.search_vectordb_node import SearchVectorDBNode
from nodes.evaluation_node import EvaluationNode
from nodes.rewrite_node import RewriteNode
from nodes.create_node import CreateNode


# ===========================================
# ✅ 상태 정의
# ===========================================
class GraphState(TypedDict):
    user_input: str
    query_type: str
    companies: List[str]
    products: List[str]
    retrieved_docs: Any
    meaningful_chunks: List[Any]
    evaluation_results: Any
    is_relevant: bool
    rewritten_query: str
    is_rewritten: bool
    retry_count: int
    final_answer: str
    is_rag_eligible: bool


# ===========================================
# 조건 함수
# ===========================================
def is_classifier_yes(state: GraphState) -> str:
    """분류 결과에 따라 RAG 수행 여부 결정"""
    if state.get("is_rag_eligible", False):
        return "search_vectordb"
    return "end"


def is_evaluation_yes(state: GraphState) -> str:
    """검색 결과의 적합도 평가 후 흐름 결정"""
    if state.get("is_relevant", False):
        return "create_answer"
    elif state.get("retry_count", 0) < 1:
        return "rewriting_question"
    return "end"


# ===========================================
# 그래프 빌드 함수
# ===========================================
def build_graph(vectorstore):
    """
    이미 생성된 PGVector 인스턴스를 주입받아서 그래프를 빌드함.
    (Streamlit에서 전역 CustomPGVector 인스턴스를 전달)
    """
    graph = StateGraph(GraphState)

    # --- 노드 등록 ---
    classifier = QueryClassifierNode()
    search = SearchVectorDBNode(vectorstore=vectorstore)  # ✅ 기존 conn_str 대신 vectorstore 주입
    eval_node = EvaluationNode(threshold=0.7)
    rewrite = RewriteNode(max_retry=1)
    creator = CreateNode()

    # --- 노드 추가 ---
    graph.add_node("classifier", classifier)
    graph.add_node("search_vectordb", search)
    graph.add_node("evaluation", eval_node)
    graph.add_node("rewriting_question", rewrite)
    graph.add_node("create_answer", creator)

    # ===========================================
    # ✅ 1️⃣ classifier → (search_vectordb or END)
    # ===========================================
    graph.add_conditional_edges(
        "classifier",
        is_classifier_yes,
        {"search_vectordb": "search_vectordb", "end": END},
    )

    # ===========================================
    # ✅ 2️⃣ search → evaluation
    # ===========================================
    graph.add_edge("search_vectordb", "evaluation")

    # ===========================================
    # ✅ 3️⃣ evaluation → rewrite / create / END
    # ===========================================
    graph.add_conditional_edges(
        "evaluation",
        is_evaluation_yes,
        {
            "create_answer": "create_answer",
            "rewriting_question": "rewriting_question",
            "end": END,
        },
    )

    # ===========================================
    # ✅ 4️⃣ rewrite → classifier
    # ===========================================
    graph.add_edge("rewriting_question", "classifier")

    # ===========================================
    # ✅ 5️⃣ create → END
    # ===========================================
    graph.add_edge("create_answer", END)

    # ===========================================
    # ✅ Entry Point
    # ===========================================
    graph.set_entry_point("classifier")

    return graph
