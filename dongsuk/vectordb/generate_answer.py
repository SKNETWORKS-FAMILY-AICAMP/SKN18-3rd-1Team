from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 같은 폴더 내 모듈 import
try:
    from .llm_model import set_llm_model
except ImportError:
    from llm_model import set_llm_model

def _get_prompt_for_answer_generation():
    """답변 생성을 위한 프롬프트 템플릿 반환"""
    template = """# **보험 전문가 답변 시스템**

당신은 **보험 약관 전문가**입니다.
주어진 보험 약관 정보를 바탕으로 사용자의 질문에 **정확하고 도움이 되는 답변**을 제공하세요.

## 질문 정보
- **질문**: {question}
- **카테고리**: {category}
- **대상 보험사**: {company_filter}
- **대상 상품**: {product_filter}

## 참고 자료
{context}

## 답변 가이드라인
1. **정확성**: 주어진 참고 자료만을 바탕으로 답변
2. **구체성**: 관련 조항이나 구체적 내용 인용
3. **명확성**: 이해하기 쉽고 체계적으로 구성
4. **솔직함**: 참고 자료에 없는 내용은 "제공된 자료에서 확인할 수 없습니다"라고 명시

## 답변 형식
{answer_style}

## 답변"""
    
    return PromptTemplate.from_template(template=template)

class AnswerGenerator:
    def __init__(self):
        self.llm = set_llm_model()
    
    def generate_answer(self, question: str, relevant_docs: list, category: str = "general", 
                      company_filter: str = None, product_filter: str = None) -> dict:
        """관련 문서들을 바탕으로 최종 답변 생성"""
        
        if not relevant_docs:
            return {
                "question": question,
                "answer": "죄송합니다. 질문과 관련된 정보를 찾을 수 없어 답변드릴 수 없습니다.",
                "sources": [],
                "generation_success": False
            }
        
        # 카테고리별 답변 스타일 설정
        if category == "comparison":
            answer_style = """
**비교 분석 형태로 답변하세요:**
- 각 보험사/상품별 차이점을 명확히 구분
- 장단점을 객관적으로 비교
- 표나 목록 형태로 정리하여 가독성 향상
"""
        elif category == "analysis":
            answer_style = """
**상세 분석 형태로 답변하세요:**
- 관련 조항과 구체적 내용을 포함
- 단계별로 자세히 설명
- 예시나 구체적 상황을 들어 설명
"""
        else:
            answer_style = """
**명확하고 이해하기 쉽게 답변하세요:**
- 핵심 내용을 간결하게 정리
- 전문 용어는 쉽게 풀어서 설명
- 실용적인 정보 위주로 구성
"""
        
        # 컨텍스트 구성
        context_parts = []
        sources = []
        
        for i, doc in enumerate(relevant_docs, 1):
            company = doc.get("metadata", {}).get("보험사명", "N/A")
            product = doc.get("metadata", {}).get("상품명", "N/A")
            clause = doc.get("metadata", {}).get("조항", "N/A")
            content = doc.get("content", "")
            
            context_parts.append(f"""[참고자료 {i}]
보험사: {company}
상품: {product}
조항: {clause}
내용: {content}""")
            
            sources.append({
                "company": company,
                "product": product,
                "clause": clause
            })
        
        context = "\n\n".join(context_parts)
        
        parser = StrOutputParser()
        prompt = _get_prompt_for_answer_generation()
        chain = prompt | self.llm | parser
        
        try:
            answer = chain.invoke({
                "question": question,
                "category": category,
                "company_filter": company_filter or "지정 없음",
                "product_filter": product_filter or "지정 없음",
                "context": context,
                "answer_style": answer_style
            })
            
            return {
                "question": question,
                "answer": answer.strip(),
                "sources": sources,
                "generation_success": True,
                "category": category,
                "total_sources": len(relevant_docs)
            }
            
        except Exception as e:
            print(f"❌ 답변 생성 오류: {e}")
            return {
                "question": question,
                "answer": f"답변 생성 중 오류가 발생했습니다: {str(e)}",
                "sources": sources,
                "generation_success": False,
                "error": str(e)
            }

def test_generator():
    """답변 생성 시스템 테스트"""
    try:
        print("=== 답변 생성 시스템 테스트 ===")
        
        print("1. 답변 생성기 초기화 중...")
        generator = AnswerGenerator()
        
        print("\n=== 전체 파이프라인 테스트 (분류 → 검색 → 평가 → 답변생성) ===")
        
        # 다른 모듈들 import
        from vectordb.classify_query import QueryClassifier
        from vectordb.retriever import InsuranceRetriever
        from vectordb.evaluate_chunk import ChunkEvaluator
        
        classifier = QueryClassifier()
        retriever = InsuranceRetriever()
        evaluator = ChunkEvaluator()
        
        print("\n=== 질문을 입력하세요 (종료: 'quit' 또는 'exit') ===")
        
        while True:
            question = input("\n질문: ").strip()
            
            if question.lower() in ['quit', 'exit', '종료']:
                print("테스트를 종료합니다.")
                break
            
            if not question:
                print("질문을 입력해주세요.")
                continue
            
            print(f"\n🔄 전체 파이프라인 실행: '{question}'")
            
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
            
            # 4단계: 답변 생성
            if eval_result['evaluation_result'] == "yes":
                print("4. 답변 생성 중...")
                answer_result = generator.generate_answer(
                    question,
                    eval_result['relevant_docs'],
                    classify_result['category'],
                    classify_result['company_filter'],
                    classify_result['product_filter']
                )
                
                if answer_result['generation_success']:
                    print(f"\n✅ 답변 생성 완료!")
                    print(f"📋 질문: {answer_result['question']}")
                    print(f"📝 답변:\n{answer_result['answer']}")
                    print(f"📚 참고 자료: {answer_result['total_sources']}개")
                    print(f"🏷️ 카테고리: {answer_result['category']}")
                else:
                    print(f"❌ 답변 생성 실패: {answer_result.get('error', '알 수 없는 오류')}")
            else:
                print("❌ 관련 문서 없음 → 답변 생성 불가")
                print(f"   이유: {eval_result['message']}")
            
            print("-" * 80)
            
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def main():
    test_generator()

if __name__ == "__main__":
    main()