"""
SearchVectorDBNode
──────────────────────────────────────────────
분류된 질의 결과에 따라 PGVector에서 유사 청크 검색 수행
(single: 단일 보험사 / comparison: 여러 보험사)
──────────────────────────────────────────────
"""

class SearchVectorDBNode:
    """단일 + 비교 질의 통합 검색 노드""" 
 
    def __init__(self, vectorstore): 
        """
        기존: conn_str를 받아 내부에서 CustomPGVector를 생성했음
        변경: 이미 연결된 vectorstore 인스턴스를 받아 재사용
        """
        self.vectorstore = vectorstore  # ✅ 기존 conn_str → vectorstore

    def __call__(self, state):
        query = state.get("user_input", "").strip()
        query_type = state.get("query_type")
        companies = state.get("companies", [])
        products = state.get("products", [])

        print(f"\n🔍 [SearchVectorDBNode] query_type={query_type}, companies={companies}, products={products}")

        # --- 단일 보험사 검색 ---
        if query_type == "single":
            if not companies:
                print("⚠️ 보험사 정보 없음 — 검색 스킵")
                state["retrieved_docs"] = []
                return state

            comp = companies[0]
            product = products[0] if products else None

            # ✅ 상품명까지 필터에 포함
            filter_kwargs = {"회사명": comp}
            if product:
                filter_kwargs["보험명"] = product

            results = self.vectorstore.similarity_search(
                query=query,
                k=10,
                filter=filter_kwargs
            )
            state["retrieved_docs"] = results

            print(f"✅ [{comp}] 관련 문서 {len(results)}개 검색 완료 (filter={filter_kwargs})")
            # ✅ 청크 내용 디버깅 출력
            for i, doc in enumerate(results, start=1):
                print(f"\n--- 📄 청크 {i} ---")
                print(f"내용: {getattr(doc, 'content', str(doc))[:300]}...")
                print(f"메타데이터: {getattr(doc, 'metadata', {})}")

        # --- 여러 보험사 비교 검색 ---
        elif query_type == "comparison":
            comparison_results = {}
            product = products[0] if products else None

            for comp in companies:
                filter_kwargs = {"회사명": comp}
                if product:
                    filter_kwargs["보험명"] = product

                results = self.vectorstore.similarity_search(
                    query=query,
                    k=10,
                    filter=filter_kwargs
                )
                comparison_results[comp] = results
                print(f"\n🔹 {comp}: {len(results)}개 문서 검색됨 (filter={filter_kwargs})")

                # ✅ 청크 내용 디버깅 출력
                for i, doc in enumerate(results, start=1):
                    print(f"   ├─ 📄 청크 {i}")
                    print(f"      내용: {getattr(doc, 'content', str(doc))[:200]}...")
                    print(f"      메타데이터: {getattr(doc, 'metadata', {})}")

            state["retrieved_docs"] = comparison_results
            print(f"✅ 비교 검색 완료 ({len(companies)}개 보험사 포함)")

        # --- 기타 (검색 불필요한 질의) ---
        else:
            print("ℹ️ RAG 비적용 질의 — 검색 스킵")
            state["retrieved_docs"] = []

        return state
