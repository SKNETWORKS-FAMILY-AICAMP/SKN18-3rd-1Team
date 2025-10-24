import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_pipline"))

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Any
from dotenv import load_dotenv

load_dotenv()

# === Import all nodes ===
from rag_pipline.nodes.domain_filter_node import DomainFilterNode
from rag_pipline.nodes.query_classifier_node import QueryClassifierNode
from rag_pipline.nodes.search_vectordb_node import SearchVectorDBNode
from rag_pipline.nodes.evaluation_node import EvaluationNode
from rag_pipline.nodes.rewrite_node import RewriteNode
from rag_pipline.nodes.create_node import CreateNode


# ===========================================
# ✅ 상태 정의
# ===========================================
class GraphState(TypedDict):
    user_input: str
    query_type: str
    companies: List[str]
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
# ✅ 그래프 빌드 함수
# ===========================================
def build_graph(conn_str: str):
    graph = StateGraph(GraphState)

    # --- 노드 등록 ---
    filter_node = DomainFilterNode()
    classifier = QueryClassifierNode()
    search = SearchVectorDBNode(conn_str=conn_str)
    eval_node = EvaluationNode(threshold=0.7)
    rewrite = RewriteNode(max_retry=1)
    creator = CreateNode()

    graph.add_node("filter", filter_node)
    graph.add_node("classifier", classifier)
    graph.add_node("search_vectordb", search)
    graph.add_node("evaluation", eval_node)
    graph.add_node("rewriting_question", rewrite)
    graph.add_node("create_answer", creator)

    # ===========================================
    # ✅ 1️⃣ filter 노드 — 보험 관련 여부 판단
    # ===========================================
    def route_from_filter(state: GraphState):
        if state.get("is_rag_eligible", False):
            return "yes"
        else:
            return "no"

    graph.add_conditional_edges(
        "filter",
        route_from_filter,
        {
            "yes": "classifier",
            "no": END
        }
    )

    # ===========================================
    # ✅ 2️⃣ classifier → search → evaluation
    # ===========================================
    graph.add_edge("classifier", "search_vectordb")
    graph.add_edge("search_vectordb", "evaluation")

    # ===========================================
    # ✅ 3️⃣ evaluation → rewrite / create / END
    # ===========================================
    def route_after_eval(state: GraphState):
        if state.get("is_relevant", False):
            return "create_answer"
        elif state.get("retry_count", 0) < 1:
            return "rewriting_question"
        else:
            return "end"

    graph.add_conditional_edges(
        "evaluation",
        route_after_eval,
        {
            "create_answer": "create_answer",
            "rewriting_question": "rewriting_question",
            "end": END
        }
    )

    # ===========================================
    # ✅ 4️⃣ rewrite → classifier (재분류 후 재검색)
    # ===========================================
    graph.add_edge("rewriting_question", "classifier")

    # ===========================================
    # ✅ 5️⃣ create → END
    # ===========================================
    graph.add_edge("create_answer", END)

    # ===========================================
    # ✅ Entry Point
    # ===========================================
    graph.set_entry_point("filter")

    return graph
