#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 CreateNode
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
            사용자의 질문: {query}
            아래는 각 보험사 관련 약관 내용입니다.
            ---
            {context}
            ---
            두 보험사의 차이를 비교 분석하여 핵심만 간결히 요약해줘.
            """
        else:
            prompt = f"""
            사용자의 질문: {query}
            관련 약관 내용:
            ---
            {context}
            ---
            위 내용을 참고해 자연스럽고 정확한 답변을 작성해줘.
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
