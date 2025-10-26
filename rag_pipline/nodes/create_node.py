"""
CreateNode
──────────────────────────────────────────────
평가 통과(유의미 청크 존재) 시 실제 답변 생성.
──────────────────────────────────────────────
"""
from openai import OpenAI

client = OpenAI()


class CreateNode:
    """최종 답변 생성 노드"""

    def __call__(self, state):
        query = state["user_input"]
        query_type = state.get("query_type", "single")
        meaningful_chunks = state.get("meaningful_chunks", [])

        if not meaningful_chunks:
            print("⚠️ 유의미한 청크가 없어 답변 생성 생략")
            state["final_answer"] = "관련된 정보를 찾을 수 없습니다."
            return state

        print("\n💬 [CreateNode] 답변 생성 중...")

        context = "\n\n".join(d.page_content[:800] for d in meaningful_chunks)
        if query_type == "comparison":
            prompt = f"""
            당신은 보험 분석 전문가입니다.
            사용자는 두 개 이상의 보험사/상품을 비교하고자 합니다.
            아래 제공된 약관 내용을 참고하여, 전문가 관점에서 핵심 차이와 특징을 정확하게 요약하세요.

            사용자 질문:
            {query}

            참고 약관 내용:
            ---
            {context}
            ---

            출력 규칙:
            - 전문가 관점으로 핵심 차이와 특징만 요약
            - 정보는 정확해야 하며, 추측이나 과장 금지
            - 문장은 자연스럽고 읽기 쉽게 작성
            - 불필요한 설명, 내부 평가 점수 등은 포함하지 않음
            """
        else:
            prompt = f"""
            당신은 보험 분석 전문가입니다.
            사용자는 특정 보험사/상품에 대한 정보를 요청했습니다.
            아래 제공된 약관 내용을 참고하여, 전문가 관점에서 자연스럽고 정확하게 답변을 작성하세요.

            사용자 질문:
            {query}

            참고 약관 내용:
            ---
            {context}
            ---

            출력 규칙:
            - 전문가 관점에서 핵심 정보를 정확하게 제공
            - 문장은 자연스럽고 이해하기 쉽게 작성
            - 불필요한 내용, 추측, 내부 평가 점수는 포함하지 않음
            """


        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )

        answer = res.choices[0].message.content.strip()
        print("✅ 답변 생성 완료.")
        state["final_answer"] = answer
        return state
