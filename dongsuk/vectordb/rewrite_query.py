from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 같은 폴더 내 모듈 import
try:
    from .llm_model import set_llm_model
except ImportError:
    from llm_model import set_llm_model

def _get_prompt_for_rewriting_question():
    """질문 재작성을 위한 프롬프트 템플릿 반환"""
    template = """# **질문 재작성 작업**

당신은 **RAG 검색 품질 개선 전문가**입니다.
사용자의 질문을 벡터DB 검색에 최적화된 문장으로 **한국어로 재작성**하세요.

## 참고 자료
아래는 이전 단계에서 평가된 메시지입니다.
이를 참고하여 더 명확하고 구체적인 질문으로 바꿔주세요.

---
# 평가 메시지: {message}
# 원본 질문: {question}
---

## 재작성 가이드라인
1. **구체적으로**: 모호한 표현을 구체적인 보험 용어로 변경
2. **검색 친화적으로**: 벡터 검색에 유리한 키워드 포함
3. **맥락 추가**: 보험 관련 맥락을 명확히 표현
4. **자연스럽게**: 한국어로 자연스러운 문장 구성

## 출력 형식
- 오직 하나의 재작성된 문장만 출력합니다.
- 설명이나 추가 문구 없이 질문만 작성합니다."""
    
    return PromptTemplate.from_template(template=template)

class QueryRewriter:
    def __init__(self):
        self.llm = set_llm_model()
    
    def rewrite_question(self, question: str, evaluation_message: str) -> dict:
        """검색 품질 향상을 위한 질문 재작성"""
        
        parser = StrOutputParser()
        prompt = _get_prompt_for_rewriting_question()
        chain = prompt | self.llm | parser
        
        try:
            rewritten_question = chain.invoke({
                "question": question,
                "message": evaluation_message
            })
            
            # 결과 정리 (혹시 모를 추가 텍스트 제거)
            rewritten_question = rewritten_question.strip()
            
            return {
                "original_question": question,
                "rewritten_question": rewritten_question,
                "evaluation_message": evaluation_message,
                "rewrite_success": True
            }
            
        except Exception as e:
            print(f"❌ 질문 재작성 오류: {e}")
            return {
                "original_question": question,
                "rewritten_question": question,  # 실패시 원본 반환
                "evaluation_message": evaluation_message,
                "rewrite_success": False,
                "error": str(e)
            }

def test_rewriter():
    """질문 재작성 시스템 테스트"""
    try:
        print("=== 질문 재작성 시스템 테스트 ===")
        
        print("1. 재작성기 초기화 중...")
        rewriter = QueryRewriter()
        
        print("\n=== 전체 파이프라인 테스트 (분류 → 검색 → 평가 → 재작성) ===")
        
        # 다른 모듈들 import
        from vectordb.classify_query import QueryClassifier
        from vectordb.retriever import InsuranceRetriever
        from vectordb.evaluate_chunk import ChunkEvaluator
        
        classifier = QueryClassifier()
        retriever = InsuranceRetriever()
        evaluator = ChunkEvaluator()
        
        print("\n=== 질문을 입력하세요 (종료: 'quit' 또는 'exit') ===")
        print("💡 관련성이 낮은 질문을 입력하면 재작성 과정을 볼 수 있습니다.")
        
        while True:
            question = input("\n질문: ").strip()
            
            if question.lower() in ['quit', 'exit', '종료']:
                print("테스트를 종료합니다.")
                break
            
            if not question:
                print("질문을 입력해주세요.")
                continue
            
            print(f"\n🔄 파이프라인 실행: '{question}'")
            
            # 1단계: 질문 분류
            print("1. 질문 분류 중...")
            classify_result = classifier.classify(question)
            
            if not classify_result['can_answer_with_data']:
                print("❌ 답변할 수 없는 질문입니다.")
                continue
            
            # 2단계: 검색
            print("2. 검색 중...")
            search_result = retriever.search_question(
                question,
                classify_result['company_filter'],
                classify_result['product_filter'],
                classify_result['category'] or "general",
                limit=5
            )
            
            # 3단계: 평가
            print("3. 문서 관련성 평가 중...")
            eval_result = evaluator.evaluate_chunks(question, search_result['retrieved_docs'])
            
            # 4단계: 분기 처리
            if eval_result['evaluation_result'] == "yes":
                print("✅ 관련 문서 발견! → generate_answer.py로 진행")
                print(f"   관련 문서: {eval_result['total_relevant']}개")
                print(f"   평균 점수: {eval_result['avg_relevance']:.1f}점")
            else:
                print("❌ 관련 문서 없음 → 질문 재작성 진행")
                
                # 5단계: 질문 재작성
                print("4. 질문 재작성 중...")
                rewrite_result = rewriter.rewrite_question(question, eval_result['message'])
                
                if rewrite_result['rewrite_success']:
                    print(f"✅ 재작성 완료!")
                    print(f"   원본: {rewrite_result['original_question']}")
                    print(f"   재작성: {rewrite_result['rewritten_question']}")
                    print(f"   이유: {eval_result['message']}")
                    
                    # 재작성된 질문으로 다시 검색해볼지 물어보기
                    retry = input("\n재작성된 질문으로 다시 검색해보시겠습니까? (y/N): ").strip().lower()
                    if retry in ['y', 'yes']:
                        print(f"\n🔄 재검색: '{rewrite_result['rewritten_question']}'")
                        # 재검색 로직은 여기서 구현 가능
                        print("   (재검색 기능은 추후 구현)")
                else:
                    print(f"❌ 재작성 실패: {rewrite_result.get('error', '알 수 없는 오류')}")
            
            print("-" * 80)
            
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def main():
    test_rewriter()

if __name__ == "__main__":
    main()