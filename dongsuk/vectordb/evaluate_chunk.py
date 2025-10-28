import json
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

# 같은 폴더 내 모듈 import
try:
    from .llm_model import set_score_model
except ImportError:
    from llm_model import set_score_model

class EvaluationResponse(BaseModel):
    evaluation_score: int  # 0~100
    evaluation_detail: str

def _get_prompt_for_evaluation():
    """평가를 위한 프롬프트 템플릿 반환"""
    template = """# **검색 문서 관련성 평가**

당신은 **벡터DB 기반 검색 결과 평가 전문가**입니다.
사용자의 질문과 문서 내용이 얼마나 관련이 높은지 **0~100점**으로 평가하세요.

## 평가 기준
- **100점:** 질문의 핵심 답변을 직접 포함
- **70~99점:** 매우 유사하거나 직접적인 관련
- **50~69점:** 부분적으로 관련 있음
- **0~49점:** 관련성 낮음 (무시)

## 출력 형식 (JSON)
{{"evaluation_score": (0~100), "evaluation_detail": "간단한 이유 설명"}}

---
# 질문: {question}
# 문서 내용: {document}"""
    
    return PromptTemplate.from_template(template=template)

class ChunkEvaluator:
    def __init__(self):
        self.llm = set_score_model()
    
    def evaluate_chunks(self, question: str, retrieved_docs: list) -> dict:
        """검색된 문서들의 관련성을 평가하여 필터링"""
        
        if not retrieved_docs:
            return {
                "question": question,
                "relevant_docs": [],
                "relevance_scores": [],
                "avg_relevance": 0.0,
                "evaluation_result": "no",
                "message": "검색된 문서가 없습니다."
            }
        
        parser = JsonOutputParser(pydantic_object=EvaluationResponse)
        prompt = _get_prompt_for_evaluation()
        chain = prompt | self.llm | parser
        
        relevant_docs = []
        relevance_scores = []
        low_relevance_messages = []
        
        print(f"📊 {len(retrieved_docs)}개 문서 평가 중...")
        
        for i, doc in enumerate(retrieved_docs, 1):
            try:
                result = chain.invoke({
                    "question": question,
                    "document": doc["content"]
                })
                
                score = result["evaluation_score"]
                detail = result["evaluation_detail"]
                
                print(f"   {i}. 점수: {score}점 - {detail}")
                
                if score >= 50:  # 50점 이상만 관련 문서로 간주
                    relevant_docs.append(doc)
                    relevance_scores.append(score)
                else:
                    low_relevance_messages.append(f"문서 {i}: {detail}")
                    
            except Exception as e:
                print(f"   {i}. 평가 오류: {e}")
                continue
        
        # 결과 계산
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        evaluation_result = "yes" if relevant_docs else "no"
        
        message = ""
        if not relevant_docs:
            message = "관련성이 높은 문서를 찾을 수 없습니다. " + "; ".join(low_relevance_messages[:3])
        
        print(f"✅ 평가 완료: {len(relevant_docs)}개 관련 문서 선별 (평균 점수: {avg_relevance:.1f}점)")
        
        return {
            "question": question,
            "relevant_docs": relevant_docs,
            "relevance_scores": relevance_scores,
            "avg_relevance": avg_relevance,
            "evaluation_result": evaluation_result,
            "message": message,
            "total_evaluated": len(retrieved_docs),
            "total_relevant": len(relevant_docs)
        }

def test_evaluator():
    """평가 시스템 테스트 - retriever 결과 기반"""
    try:
        print("=== 문서 평가 시스템 테스트 ===")
        
        print("1. 평가기 및 검색기 초기화 중...")
        from vectordb.classify_query import QueryClassifier
        from vectordb.retriever import InsuranceRetriever
        
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
            
            print(f"   검색 결과: {search_result['total_found']}개")
            
            # 3단계: 평가
            print("3. 문서 관련성 평가 중...")
            eval_result = evaluator.evaluate_chunks(question, search_result['retrieved_docs'])
            
            print(f"\n📋 평가 결과:")
            print(f"   평가 결과: {eval_result['evaluation_result']}")
            print(f"   관련 문서: {eval_result['total_relevant']}/{eval_result['total_evaluated']}개")
            print(f"   평균 점수: {eval_result['avg_relevance']:.1f}점")
            
            if eval_result['message']:
                print(f"   메시지: {eval_result['message']}")
            
            print("-" * 60)
            
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

def main():
    test_evaluator()

if __name__ == "__main__":
    main()