# 📄 rag_pipline/nodes/domain_filter_node.py
from openai import OpenAI

client = OpenAI()

class DomainFilterNode:
    """
    ✅ 질문이 '보험 약관 RAG' 대상인지 여부를 분류하는 노드
    - 보험 관련 / 자동차 보험 관련 질문만 True로 통과
    - 기타 잡담/비관련 질문은 False로 처리
    """

    def __call__(self, state):
        query = state["user_input"]

        prompt = f"""
        너는 질의 분류 전문가야.
        아래 질문이 '보험 관련 약관 RAG 시스템'으로 대답할 수 있는 질문인지 판단해.
        예를 들어 자동차보험, 보상, 대인배상, 자기차량손해, 보험금, 보장한도 같은 내용이면 True야.
        날씨, 음식, 인사말, 일반 상식 등은 False야.

        질문: "{query}"

        반드시 아래 형식으로 답변해:
        eligible: <True|False>
        """

        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}]
        )

        text = res.choices[0].message.content.lower()
        state["is_rag_eligible"] = "true" in text
        print(f"🎯 DomainFilterNode 결과 → {state['is_rag_eligible']}")
        return state
