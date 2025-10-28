"""
SearchVectorDBNode
──────────────────────────────────────────────
분류된 질의 결과에 따라 PGVector에서 유사 청크 검색 수행
(single: 단일 보험사 / comparison: 여러 보험사)
──────────────────────────────────────────────
"""
from openai import OpenAI


class SearchVectorDBNode:
    """단일 + 비교 질의 통합 검색 노드"""

    def __init__(self, vectorstore):
        """
        기존: conn_str를 받아 내부에서 CustomPGVector를 생성했음
        변경: 이미 연결된 vectorstore 인스턴스를 받아 재사용
        """
        self.vectorstore = vectorstore
        self.client = OpenAI()

    # ✅ 회사별 비교질문을 구체적 정보탐색 질문으로 리라이트
    def _rewrite_for_company(self, query: str, company: str, product: str | None = None) -> str:
        prompt = f"""
        사용자의 질문: "{query}"
        보험사: {company}
        상품: {product or "자동차보험"}

        위 질문은 여러 보험사를 비교하는 질문입니다.
        '{company}'에 대한 정보를 검색하기 위한 구체적이고 간결한 질문으로 다시 써주세요.

        예시:
        - "{company} 자동차보험의 주요 보장, 혜택, 할인, 특약 조건은?"
        - "{company}의 {product or '자동차보험'} 특징과 장점을 알려줘."
        """

        res = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return res.choices[0].message.content.strip()

    # ✅ 실행 함수
    def __call__(self, state):
        query = state.get("user_input", "").strip()
        query_type = state.get("query_type")
        companies = state.get("companies", [])
        products = state.get("products", [])

        print(f"\n🔍 [SearchVectorDBNode] query_type={query_type}, companies={companies}, products={products}")

        # =======================================================
        # 단일 보험사 질의
        # =======================================================
        if query_type == "single":
            if not companies:
                print("⚠️ 보험사 정보 없음 — 검색 스킵")
                state["retrieved_docs"] = []
                return state

            comp = companies[0]
            product = products[0] if products else None

            filter_kwargs = {"회사명": comp}
            if product:
                filter_kwargs["보험명"] = product

            results = self.vectorstore.similarity_search(
                query=query,
                k=10,
                filter=filter_kwargs,
            )
            state["retrieved_docs"] = results

            print(f"✅ [{comp}] 관련 문서 {len(results)}개 검색 완료 (filter={filter_kwargs})")
            for i, doc in enumerate(results, start=1):
                print(f"\n--- 📄 청크 {i} ---")
                print(f"내용: {getattr(doc, 'content', str(doc))[:300]}...")
                print(f"메타데이터: {getattr(doc, 'metadata', {})}")

        # =======================================================
        # 비교 질의 (여러 보험사)
        # =======================================================
        elif query_type == "comparison":
            comparison_results = {}
            product = products[0] if products else None

            for comp in companies:
                # ✅ 회사별로 LLM 리라이트 적용
                rewritten_query = self._rewrite_for_company(query, comp, product)
                print(f"✏️ [{comp}] rewritten query → {rewritten_query}")

                # ✅ 필터 구성
                filter_kwargs = {"회사명": comp}
                if product:
                    filter_kwargs["보험명"] = product

                # ✅ 유사도 검색
                results = self.vectorstore.similarity_search(
                    query=rewritten_query,
                    k=10,
                    filter=filter_kwargs,
                )
                comparison_results[comp] = results

                # ✅ 디버깅 로그
                print(f"\n🔹 {comp}: {len(results)}개 문서 검색됨 (filter={filter_kwargs})")
                for i, doc in enumerate(results, start=1):
                    print(f"   ├─ 📄 청크 {i}")
                    print(f"      내용: {getattr(doc, 'content', str(doc))[:200]}...")
                    print(f"      메타데이터: {getattr(doc, 'metadata', {})}")

            # ✅ 결과 저장
            state["retrieved_docs"] = comparison_results
            print(f"✅ 비교 검색 완료 ({len(companies)}개 보험사 포함)")

        # =======================================================
        # 기타 (RAG 불필요 질의)
        # =======================================================
        else:
            print("ℹ️ RAG 비적용 질의 — 검색 스킵")
            state["retrieved_docs"] = []

        return state
