"""
CreateNode
──────────────────────────────────────────────
평가 통과(유의미 청크 존재) 시 실제 답변 생성 + 출처 표기.
──────────────────────────────────────────────
"""
from openai import OpenAI
from collections import defaultdict

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

        # ==========================================================
        # 1️⃣ 문서 내용 + 메타데이터 정리
        # ==========================================================
        company_docs = defaultdict(list)
        company_sources = defaultdict(set)

        for d in meaningful_chunks:
            text = getattr(d, "page_content", "")[:800]
            meta = getattr(d, "metadata", {}) or {}
            comp = meta.get("회사명", "기타")
            prod = meta.get("보험명", "보험상품")
            company_docs[comp].append(text)
            company_sources[comp].add(f"{comp} - {prod}")

        # ==========================================================
        # 2️⃣ 프롬프트 구성
        # ==========================================================
        if query_type == "comparison":
            # --- 회사별 구분된 컨텍스트 생성 ---
            context = ""
            for comp, docs in company_docs.items():
                joined = "\n".join(docs)
                context += f"\n\n[{comp} 관련 약관]\n{joined}"

            prompt = f"""
            당신은 자동차보험 전문가입니다.
            사용자는 여러 보험사를 비교하고 있습니다.
            아래 각 보험사별 약관 내용을 분석하여 **명확하고 공정한 비교 요약**을 작성하세요.

            사용자 질문:
            {query}

            참고 약관 내용:
            {context}

            작성 지침:
            - 두 보험사의 **공통점과 차이점**을 중심으로 비교하세요.
            - **보장 범위**, **혜택**, **할인/특약 조건**, **보험료**, **대상자 제한** 등 주요 항목별로 비교하세요.
            - 문장은 자연스럽고 이해하기 쉽게 작성하세요.
            - 특정 회사를 과도하게 추천하지 말고 객관적으로 표현하세요.
            - 각 회사 이름을 명확히 언급하며, 단락을 구분해 주세요.
            """

        else:
            # --- 단일 보험사 ---
            context = "\n".join(getattr(d, "page_content", "")[:800] for d in meaningful_chunks)
            prompt = f"""
            당신은 자동차보험 전문가입니다.
            사용자는 특정 보험사 또는 상품에 대한 정보를 요청했습니다.
            아래 약관 내용을 참고하여, **핵심 정보만 자연스럽게 요약**하세요.

            사용자 질문:
            {query}

            참고 약관 내용:
            {context}

            작성 지침:
            - 보장 내용, 혜택, 특약 조건을 중심으로 설명
            - 복잡한 문장 피하고 명확하고 이해하기 쉽게 표현
            - 객관적이고 전문가답게 답변
            """

        # ==========================================================
        # 3️⃣ LLM 호출
        # ==========================================================
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        answer = res.choices[0].message.content.strip()

        # ==========================================================
        # 4️⃣ 출처 추가
        # ==========================================================
        if company_sources:
            src_texts = []
            for comp, src in company_sources.items():
                joined = ", ".join(sorted(src))
                src_texts.append(f"{comp}: {joined}")
            sources_text = "출처:\n" + "\n".join(src_texts)
            answer = f"{answer}\n\n---\n{sources_text}"

        print("✅ 답변 생성 완료.")
        state["final_answer"] = answer
        return state
