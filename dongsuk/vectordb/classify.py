from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from vectordb.llm_model import set_classify_model

class QueryClassifier:
    _llm_model = None   # 클래스 레벨 공유
    _prompt = None      # 클래스 레벨 공유

    def __init__(self):
        # LLM 모델 한 번만 생성
        if QueryClassifier._llm_model is None:
            QueryClassifier._llm_model = set_classify_model()
        if QueryClassifier._prompt is None:
            QueryClassifier._prompt = ChatPromptTemplate.from_template("""
            다음 보험 관련 질문을 아래 네 가지 중 하나로 분류하세요.

            질문: {question}

            분류 기준:
            1. analysis: 특정 보험사나 상품의 특징, 약관, 조건, 보장 내용 등에 대한 질문
            2. comparison: 두 개 이상 보험사나 상품을 비교하거나 차이점을 묻는 질문
            3. general: 보험 전반(예: 용어 설명, 절차, 일반 정보)에 대한 질문
            4. unknown: 분류 불가능하거나 보험과 관련 없는 질문

            출력 형식: analysis / comparison / general / unknown 중 하나만 출력
            """)

        self.llm = QueryClassifier._llm_model
        self.prompt = QueryClassifier._prompt

    def classify(self, question: str) -> str:
        chain = self.prompt | self.llm | StrOutputParser()
        result = chain.invoke({"question": question})
        return result.strip().lower()
