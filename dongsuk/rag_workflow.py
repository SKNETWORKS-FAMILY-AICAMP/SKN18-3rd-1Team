import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langgraph.graph import StateGraph, END
from state import RAGState
from dotenv import load_dotenv

load_dotenv()

# === Import node functions ===
from node import (
    classify_node,
    retriever_node,
    evaluate_node,
    rewrite_node,
    generate_node
)

def build_rag_graph():
    """보험 RAG 워크플로우 그래프 생성"""
    
    graph = StateGraph(RAGState)
    
    # --- 노드 등록 ---
    graph.add_node("classify", classify_node)
    graph.add_node("retriever", retriever_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)
    
    # ===========================================
    # ✅ 1️⃣ classify → retriever / END
    # ===========================================
    def route_from_classify(state: RAGState):
        if state.get("can_answer_with_data", False):
            return "retriever"
        else:
            return "end"
    
    graph.add_conditional_edges(
        "classify",
        route_from_classify,
        {
            "retriever": "retriever",
            "end": END
        }
    )
    
    # ===========================================
    # ✅ 2️⃣ retriever → evaluate
    # ===========================================
    graph.add_edge("retriever", "evaluate")
    
    # ===========================================
    # ✅ 3️⃣ evaluate → generate / rewrite / END
    # ===========================================
    def route_after_evaluate(state: RAGState):
        if state.get("evaluation_result") == "yes":
            return "generate"
        elif state.get("rewrite_count", 0) < 1:  # 최대 1회 재작성
            return "rewrite"
        else:
            # 재작성 횟수 초과시 END로 이동 (답변 생성하지 않음)
            print("⚠️ 재작성 횟수 초과 - 답변할 수 없습니다")
            return "end"
    
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "generate": "generate",
            "rewrite": "rewrite",
            "end": END
        }
    )
    
    # ===========================================
    # ✅ 4️⃣ rewrite → retriever (루프백)
    # ===========================================
    graph.add_edge("rewrite", "retriever")
    
    # ===========================================
    # ✅ 5️⃣ generate → END
    # ===========================================
    graph.add_edge("generate", END)
    
    # ===========================================
    # ✅ Entry Point
    # ===========================================
    graph.set_entry_point("classify")
    
    return graph.compile()

def run_rag_pipeline(question: str) -> RAGState:
    """RAG 파이프라인 실행"""
    
    print(f"🚀 RAG 파이프라인 시작: '{question}'")
    print("=" * 60)
    
    # 초기 상태
    initial_state = RAGState(
        question=question,
        original_question=None,
        can_answer_with_data=None,
        category=None,
        company_filter=None,
        product_filter=None,
        retrieved_docs=None,
        total_found=None,
        relevant_docs=None,
        evaluation_result=None,
        avg_relevance=None,
        evaluation_message=None,
        rewrite_count=None,
        rewritten_question=None,
        answer=None,
        sources=None,
        generation_success=None,
        step=None,
        error_message=None
    )
    
    # 워크플로우 실행
    workflow = build_rag_graph()
    final_state = workflow.invoke(initial_state)
    
    print("=" * 60)
    print("✅ RAG 파이프라인 완료!")
    
    return final_state

def visualize_graph():
    """워크플로우 그래프 시각화"""
    try:
        print("📊 워크플로우 그래프 생성 중...")
        
        # 그래프 생성
        workflow = build_rag_graph()
        
        # 그래프 구조 출력
        print("\n🔗 워크플로우 구조:")
        print("=" * 50)
        print("START")
        print("  ↓")
        print("classify (질문 분류)")
        print("  ↓ [답변가능?]")
        print("  ├─ YES → retriever (벡터 검색)")
        print("  └─ NO  → END")
        print("              ↓")
        print("         evaluate (문서 평가)")
        print("              ↓ [관련문서?]")
        print("              ├─ YES → generate (답변 생성) → END")
        print("              ├─ NO + 재작성가능 → rewrite (질문 재작성)")
        print("              └─ NO + 재작성한계 → END")
        print("                         ↓ [최대 1회]")
        print("                    retriever ← (루프백)")
        print("=" * 50)
        
        return workflow
        
    except Exception as e:
        print(f"❌ 그래프 시각화 오류: {e}")
        return None

def main():
    """메인 함수 - 그래프 시각화 또는 대화형 테스트"""
    print("=== 보험 RAG 시스템 (LangGraph) ===")
    print("1. 그래프 구조 보기")
    print("2. 대화형 테스트")
    print("3. 종료")
    
    choice = input("\n선택하세요 (1/2/3): ").strip()
    
    if choice == "1":
        visualize_graph()
        
    elif choice == "2":
        print("\n💡 전체 워크플로우를 테스트할 수 있습니다.")
        
        while True:
            question = input("\n질문을 입력하세요 (종료: 'quit'): ").strip()
            
            if question.lower() in ['quit', 'exit', '종료']:
                print("시스템을 종료합니다.")
                break
            
            if not question:
                print("질문을 입력해주세요.")
                continue
            
            try:
                # RAG 파이프라인 실행
                result = run_rag_pipeline(question)
                
                # 결과 출력
                print(f"\n📋 최종 결과:")
                print(f"   원본 질문: {result.get('original_question')}")
                if result.get('rewritten_question'):
                    print(f"   재작성 질문: {result.get('rewritten_question')}")
                
                # 답변이 있는 경우만 출력
                if result.get('answer'):
                    print(f"   답변: {result.get('answer')}")
                    if result.get('sources'):
                        print(f"   참고 자료: {len(result['sources'])}개")
                else:
                    print("   답변: 죄송합니다. 관련된 정보를 찾을 수 없어 답변을 드릴 수 없습니다.")
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                
    elif choice == "3":
        print("시스템을 종료합니다.")
    else:
        print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    main()