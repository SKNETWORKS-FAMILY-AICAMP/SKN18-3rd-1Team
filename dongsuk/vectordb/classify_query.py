import os
import psycopg2
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from vectordb.llm_model import set_classify_model

load_dotenv()

class ClassifyResponse(BaseModel):
    can_answer: bool
    category: str | None = None
    company_filter: str | None = None
    product_filter: str | None = None

def _get_prompt_for_classification():
    """분류를 위한 프롬프트 템플릿 반환"""
    template = """보험 관련 질문을 분류하세요.

보험사: {companies}
상품: {products}
질문: {question}

질문이 들어왔을때 오탈자나 문법적 오류가 있을 수 있음.
이런 오류가 있을 경우 약한 추론을 통해서 사용자가 어떤 단어를 쓰고자 했는지 추측해서 질문을 분류해야함

분류 기준:
1. analysis: 특정 보험사나 상품의 특징, 보장 내용, 조건, 약관, 혜택, 절차 등에 대한 이해나 설명을 요청하는 경우
2. comparison: 두 개 이상 보험사나 상품을 비교하거나, 차이점·유리한 점 등을 묻는 경우
3. 위 두 카테고리에 해당하지 않으면 답변 불가능

출력 형식은 JSON 형식으로 다음과 같습니다:
{{"can_answer": true/false, "category": "analysis|comparison|null", "company_filter": "보험사명_또는_null", "product_filter": "상품명_또는_null"}}"""
    
    return PromptTemplate.from_template(template=template)

class QueryClassifier:
    def __init__(self):
        self.companies = self._get_companies()
        self.products = self._get_products()
        self.llm = set_classify_model()
    
    def _get_companies(self):
        try:
            conn = psycopg2.connect(os.getenv("CONNECTION_STRING"))
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT metadata->>'보험사명' FROM insurance_vectordb WHERE metadata->>'보험사명' IS NOT NULL")
                return [row[0] for row in cur.fetchall() if row[0] and row[0] != 'nan']
        except:
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _get_products(self):
        try:
            conn = psycopg2.connect(os.getenv("CONNECTION_STRING"))
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT metadata->>'상품명' FROM insurance_vectordb WHERE metadata->>'상품명' IS NOT NULL")
                return [row[0] for row in cur.fetchall() if row[0] and row[0] != 'nan']
        except:
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def classify(self, question: str) -> dict:
        if not self.companies and not self.products:
            return {"can_answer_with_data": False, "category": None, "company_filter": None, "product_filter": None}
        
        parser = JsonOutputParser(pydantic_object=ClassifyResponse)
        prompt = _get_prompt_for_classification()
        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({
                "question": question,
                "companies": ", ".join(self.companies),
                "products": ", ".join(self.products)
            })
            
            return {
                "can_answer_with_data": result["can_answer"],
                "category": result["category"] if result["can_answer"] else None,
                "company_filter": result["company_filter"],
                "product_filter": result["product_filter"]
            }
        except:
            return {"can_answer_with_data": False, "category": None, "company_filter": None, "product_filter": None}

def test_classify():
    """분류 시스템 테스트 - 사용자 입력 받기"""
    try:
        print("=== 분류 시스템 테스트 시작 ===")
        
        print("1. 분류기 초기화 중...")
        classifier = QueryClassifier()
        
        print(f"2. 보험사: {classifier.companies}")
        print(f"3. 상품: {classifier.products}")
        
        if not classifier.companies and not classifier.products:
            print("❌ 데이터가 없습니다. 벡터 DB를 확인하세요.")
            return
        
        print("\n=== 질문을 입력하세요 (종료: 'quit' 또는 'exit') ===")
        
        while True:
            question = input("\n질문: ").strip()
            
            if question.lower() in ['quit', 'exit', '종료']:
                print("테스트를 종료합니다.")
                break
            
            if not question:
                print("질문을 입력해주세요.")
                continue
            
            print("분류 중...")
            result = classifier.classify(question)
            
            print(f"답변가능: {result['can_answer_with_data']}")
            print(f"카테고리: {result['category']}")
            print(f"보험사: {result['company_filter']}")
            print(f"상품: {result['product_filter']}")
            
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_classify()