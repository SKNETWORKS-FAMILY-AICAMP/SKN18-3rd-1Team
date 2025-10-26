"""
QueryClassifierNode
──────────────────────────────────────────────
사용자의 질문이 단일 보험사 관련인지, 여러 보험사 비교인지, 기타인지 분류하고
해당 보험사 목록(companies)을 함께 추출
기타일 경우는 END
──────────────────────────────────────────────
"""
from openai import OpenAI

client = OpenAI()
INSURANCE_COMPANIES = ["현대", "하나", "삼성화재", "KB", "DB", "롯데", "하나"]


class QueryClassifierNode:
    """질문 분류 + 보험사 추출 노드"""

    def __call__(self, state):
        query = state["user_input"]

        prompt = f"""
아래 질문을 분석하여 유형을 분류하세요. 분류 기준과 예시를 최대한 상세히 적용해야 합니다.

분류 기준:
1. single
    - 특정 보험사 또는 보험 상품을 명시하고, 그 보험의 특징, 보장 내용, 조건, 약관, 혜택, 가입/청구/해지 절차 등 이해를 요청하는 질문
    - 다른 보험과 비교하거나 추천을 요구하지 않음
    - 예시: "삼성화재 자동차보험의 보장 항목은 무엇인가요?" 

2. comparison
    - 두 개 이상의 보험사 또는 상품을 명시하고, 서로 비교하거나 추천을 요청하는 질문
    - 한 개 보험사만 언급되더라도 다른 보험과 비교하거나 추천을 묻는 경우
    - 예시: "삼성화재와 현대해상의 자동차보험 중 어느 것이 더 낫나요?"
    - 예시: "삼성화재 자동차보험과 다른 보험사를 비교해서 추천해 주세요"

3. other
    - 보험사 언급이 없거나, 질문이 불분명하여 single/comparison으로 분류할 수 없는 경우
    - 보험과 관련 없는 질문도 포함

질문: "{query}"

응답 형식:
category: <single|comparison|other>
        """

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
        )

        answer = response.choices[0].message.content.lower()
        if "comparison" in answer:
            query_type = "comparison"
        elif "single" in answer:
            query_type = "single"
        else:
            query_type = "other"

        found = [c for c in INSURANCE_COMPANIES if c in query]

        if query_type == "comparison":
            if len(found) == 1:
                companies = [c for c in INSURANCE_COMPANIES if c != found[0]]
            else:
                companies = found
        elif query_type == "single":
            companies = found[:1] if found else []
        else:
            companies = []

        state["query_type"] = query_type
        state["companies"] = companies

        state["is_rag_eligible"] = query_type in ["single", "comparison"]

        print(f"🧠 query_type={query_type}, companies={companies}, is_rag_eligible={state['is_rag_eligible']}")
        return state
