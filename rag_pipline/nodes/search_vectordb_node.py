#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 SearchVectorDBNode
──────────────────────────────────────────────
분류된 질의 결과에 따라 PGVector에서 유사 청크 검색 수행
(single: 단일 보험사 / comparison: 여러 보험사)
──────────────────────────────────────────────
"""
from vectorstore.custom_pgvector import CustomPGVector


class SearchVectorDBNode:
    """단일 + 비교 질의 통합 검색 노드"""

    def __init__(self, conn_str: str):
        self.vectorstore = CustomPGVector(conn_str)

    def __call__(self, state):
        query = state["user_input"]
        query_type = state.get("query_type")
        companies = state.get("companies", [])

        print(f"\n🔍 [SearchVectorDBNode] query_type={query_type}, companies={companies}")

        if query_type == "single":
            if not companies:
                state["retrieved_docs"] = []
                return state
            comp = companies[0]
            results = self.vectorstore.similarity_search(query=query, k=5, filter={"보험사명": comp})
            state["retrieved_docs"] = results
            print(f"✅ [{comp}] 관련 문서 {len(results)}개 검색 완료")

        elif query_type == "comparison":
            comparison_results = {}
            for comp in companies:
                comparison_results[comp] = self.vectorstore.similarity_search(query=query, k=5, filter={"보험사명": comp})
                print(f"🔹 {comp}: {len(comparison_results[comp])}개 문서 검색됨")
            state["retrieved_docs"] = comparison_results
            print(f"✅ 비교 검색 완료 ({len(companies)}개 보험사 포함)")

        else:
            state["retrieved_docs"] = []
        return state
