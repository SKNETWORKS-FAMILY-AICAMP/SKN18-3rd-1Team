#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 QueryClassifierNode
──────────────────────────────────────────────
사용자의 질문이 단일 보험사 관련인지, 여러 보험사 비교인지, 기타인지 분류하고
해당 보험사 목록(companies)을 함께 추출
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
        아래 질문을 분석해서 유형을 분류하세요:
        - single: 한 보험사만 언급된 단일 질의
        - comparison:
            1. 두개 이상의 보험사를 언급하고 보험사들끼리의 비교를 원하거나 다른 보험사를 추천해달라는 식의 비교 질의
            2. 하나만 언급되었지만 다른 보험 비교, 추천 같은 내용을 물어보는 질의
        - other: 보험사 언급이 없거나 판단 불가한 질문

        질문: "{query}"

        반드시 아래 형식으로만 답하세요.
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
        print(f"🧠 query_type={query_type}, companies={companies}")
        return state
