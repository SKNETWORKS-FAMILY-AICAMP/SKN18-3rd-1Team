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
INSURANCE_PRODUCTS = ["개인용자동차보험", "업무용자동차보험", "영업용자동차보험", "하루자동차보험", "이륜자동차보험"]

class QueryClassifierNode:
    """질문 분류 + 보험사 추출 노드"""

    def __call__(self, state):
        query = state["user_input"]

        prompt = f"""
        아래 질문에서 보험사 및 상품명을 찾아 표준화하세요.

        표준 보험사 목록:
        ["KB", "롯데", "삼성화재", "하나", "현대"]

        보험사 매핑 규칙:
        - "삼성", "삼성 손보", "삼성 다이렉트" → 삼성화재
        - "현대", "현대해상", "현대 다이렉트" → 현대
        - "국민", "KB 손보", "KB 다이렉트" → KB
        - "롯데", "롯데 손보", "롯데 다이렉트" → 롯데
        - "하나", "하나 손보", "하나다이렉트" → 하나

        단, "삼성전자", "현대차", "국민은행", "롯데제과", "하나은행", "증권" 등은 제외.


        표준 보험상품 목록:
        ["개인용", "업무용", "영업용", "이륜차", "원데이"]

        보험상품 매핑 규칙:
        - "개인", "개인용", "자차" → 개인용자동차보험
        - "업무", "회사차", "법인차, "공용차", "회사 업무", "관공서", "출퇴근", "개인사업자" → 업무용자동차보험
        - "영업", "영업용", "택시", "버스", "화물", "렌터카", "렌트", "운수", "택배", "배달", "용달", "학원차", "배송", "운송", "대여" → 영업용자동차보험
        - "이륜차", "자전거", "전동차", "스쿠터", "바이크", "킥보드", "오토바이" → 이륜자동차보험
        - "하루", "원데이", "일일","1일", "단기", "시간", "몇일" → 원데이자동차보험
        
        단, "원데이렌즈", "원데이클래스", "원데이투어", "자가진단", "버스정류장", "예약", "전동휠체어", "단기예금", "시간제근무" 등은 제외.


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
