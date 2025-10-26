from vectordb.core.classifier import QueryClassifier
from vectordb.core.categorizer import QueryCategorizer
from vectordb.core.retriever import InsuranceRetriever
from vectordb.core.evaluator import ChunkEvaluator
from vectordb.core.generator import AnswerGenerator

class InsurancePipeline:
    """보험 RAG 파이프라인 - 전체 워크플로우 관리"""
    
    def __init__(self):
        self.classifier = QueryClassifier()
        self.categorizer = QueryCategorizer()
        self.retriever = InsuranceRetriever()
        self.evaluator = ChunkEvaluator()
        self.generator = AnswerGenerator()
    
    def process(self, question: str) -> dict:
        """전체 파이프라인 실행"""
        
        # 1. 분류
        classify_result = self.classifier.classify(question)
        if not classify_result["can_answer_with_data"]:
            return {"answer": "답변할 수 없는 질문입니다."}
        
        # 2. 카테고리 분류
        category_result = self.categorizer.categorize(
            question, 
            classify_result["company_filter"],
            classify_result["product_filter"]
        )
        
        # 3. 검색
        retrieve_result = self.retriever.retrieve_with_filters(
            question,
            classify_result["company_filter"],
            classify_result["product_filter"],
            category_result["category"]
        )
        
        # 4. 평가
        evaluate_result = self.evaluator.evaluate(
            question,
            retrieve_result["chunks"]
        )
        
        if evaluate_result["evaluation_result"] == "no":
            return {"answer": "관련 정보를 찾을 수 없습니다."}
        
        # 5. 답변 생성
        answer_result = self.generator.generate(
            question,
            evaluate_result["contents"],
            category_result["category"]
        )
        
        return answer_result

def main():
    pipeline = InsurancePipeline()
    
    questions = [
        "KB 개인용자동차보험 용어 정의",
        "자동차보험 비교",
        "오늘 날씨"
    ]
    
    for q in questions:
        print(f"\n질문: {q}")
        result = pipeline.process(q)
        print(f"답변: {result.get('answer', '오류')}")

if __name__ == "__main__":
    main()