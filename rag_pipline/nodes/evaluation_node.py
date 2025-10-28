"""
EvaluationNode 
──────────────────────────────────────────────
검색된 문서(청크)가 질문과 얼마나 관련이 있는지를 평가하고,
유의미한 청크가 하나라도 있으면 CreateNode로,
없으면 RewriteNode로 이동
──────────────────────────────────────────────
"""
from openai import OpenAI
import numpy as np
import re

client = OpenAI()


class EvaluationNode:
    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold

    def __call__(self, state):
        query = state["user_input"]
        query_type = state.get("query_type", "single")
        retrieved = state.get("retrieved_docs")

        if not retrieved:
            state["is_relevant"] = False
            state["meaningful_chunks"] = []
            return state

        # ==========================================================
        # 단일 보험사 질의
        # ==========================================================
        if query_type == "single":
            docs = retrieved
            scores, meaningful = [], []
            for i, doc in enumerate(docs, 1):
                score = self._evaluate(query, doc.page_content, query_type)
                scores.append(score)
                if score >= self.threshold:
                    meaningful.append(doc)
                print(f"📄 문서 {i} → score={score:.2f}")

            avg = np.mean(scores) if scores else 0
            state.update({
                "evaluation_results": [{"score": s} for s in scores],
                "meaningful_chunks": meaningful,
                "is_relevant": True if docs else False  # ✅ 문서가 있으면 통과
            })
            print(f"✅ 평균 {avg:.2f} / 전체 청크 {len(docs)}개 → {'통과' if meaningful else '미달이지만 계속 진행'}")

        # ==========================================================
        # 비교 질의 (두 개 이상 보험사)
        # ==========================================================
        elif query_type == "comparison":
            pairs, meaningful = {}, []
            all_docs = []

            for comp, docs in retrieved.items():
                combined = "\n".join(d.page_content[:600] for d in docs)
                score = self._evaluate(query, combined, query_type)
                pairs[comp] = score
                all_docs.extend(docs)
                print(f"📄 [{comp}] → score={score:.2f}")

            avg = np.mean(list(pairs.values())) if pairs else 0
            state.update({
                "evaluation_results": pairs,
                "meaningful_chunks": all_docs,
                "is_relevant": True if all_docs else False  # ✅ 문서 있으면 통과
            })
            print(f"✅ 평균 {avg:.2f} / 전체 청크 {len(all_docs)}개 → {'통과' if avg >= self.threshold else '미달이지만 계속 진행'}")

        # ==========================================================
        # 기타
        # ==========================================================
        else:
            state["is_relevant"] = False
            state["meaningful_chunks"] = []

        return state

    # ==========================================================
    # 프롬프트 — comparison 전용 개선
    # ==========================================================
    def _evaluate(self, query, content, query_type="single"):
        if query_type == "comparison":
            # ✅ 비교형 질문에 맞는 평가 프롬프트
            prompt = f"""
            사용자의 질문: "{query}"
            문서 내용:
            {content[:1000]}

            위 질문은 여러 보험사를 비교하거나 추천을 요청하는 질문입니다.
            문서가 질문의 비교에 활용될 수 있는 실질적 정보
            (예: 보장 내용, 혜택, 할인, 특약, 가격, 조건 등)를 포함한다면
            0.8 이상 점수를 주십시오.

            0에서 1 사이 숫자 하나만 출력하세요. 추가 설명은 하지 마세요.
            """
        else:
            # ✅ 단일형 질문 기본 프롬프트
            prompt = f"""
            사용자의 질문: "{query}"
            문서 내용:
            {content[:1000]}

            문서가 질문과 직접적으로 관련되어 있다면 1,
            간접적이거나 약한 관련이라면 0.3~0.7,
            전혀 관련 없으면 0에 가깝게 점수를 매기세요.

            숫자 하나만 출력하세요.
            """

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        text = res.choices[0].message.content.strip()
        match = re.search(r"([0-1](?:\.\d+)?)", text)
        return float(match.group(1)) if match else 0.0
