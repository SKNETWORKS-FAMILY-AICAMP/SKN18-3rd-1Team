"""
CreateNode
──────────────────────────────────────────────
평가 통과(유의미 청크 존재) 시 실제 답변 생성 + 출처 표기.
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

        # 1️⃣ 문서 내용 + 출처 메타데이터 추출
        context_parts = []
        sources = set()

        for d in meaningful_chunks:
            context_parts.append(d.page_content[:800])
            meta = d.metadata or {}
            company = meta.get("회사명")
            product = meta.get("보험명")
            if company and product:
                sources.add(f"{company} - {product}")
            elif company:
                sources.add(company)

        context = "\n\n".join(context_parts)

        # 2️⃣ 프롬프트 구성
        if query_type == "comparison":
            prompt = f"""
            당신은 보험 분석 전문가입니다.
            사용자는 두 개 이상의 보험사/상품을 비교하고자 합니다.
            아래 제공된 약관 내용과 출처 정보를 참고하여, 전문가 관점에서 핵심 차이와 특징을 정확하게 설명하세요.

            사용자 질문:
            {query}

            참고 약관 내용:
            {context}

            출력 반드시!!! 지켜야할 규칙:
            - 핵심 정보만 정확하게 제공
            - 문장은 자연스럽 내용을 이해하기 쉽게 풀어서 설명
            """
        else:
            prompt = f"""
            당신은 보험 분석 전문가입니다.
            사용자는 특정 보험사/상품에 대한 정보를 요청했습니다.
            아래 제공된 약관 내용과 출처 정보를 참고하여, 전문가 관점에서 자연스럽고 정확하게 답변을 작성하세요.

            사용자 질문:
            {query}

            참고 약관 내용:
            {context}

            출력 반드시!!! 지켜야할 규칙:
            - 핵심 정보만 정확하게 제공
            - 문장은 자연스럽 내용을 이해하기 쉽게 풀어서 설명
            - 하나의 보험사에 대해 자세하게 분석해서 설명해주는 말로 답변하기
            """

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )

        answer = res.choices[0].message.content.strip()

        # 4️⃣ 출처 추가
        if sources:
            sources_text = "출처: " + ", ".join(sorted(sources))
            answer = f"{answer}\n\n---\n{sources_text}"

        print("✅ 답변 생성 완료.")
        state["final_answer"] = answer
        return state