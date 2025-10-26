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
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    def __call__(self, state):
        query = state["user_input"]
        query_type = state.get("query_type", "single")
        retrieved = state.get("retrieved_docs")

        if not retrieved:
            state["is_relevant"] = False
            state["meaningful_chunks"] = []
            return state

        # -------- 단일 보험사 --------
        if query_type == "single":
            docs = retrieved
            scores, meaningful = [], []
            for i, doc in enumerate(docs, 1):
                score = self._evaluate(query, doc.page_content)
                scores.append(score)
                if score >= self.threshold:
                    meaningful.append(doc)
                print(f"📄 문서 {i} → score={score}")
            avg = np.mean(scores) if scores else 0
            state.update({
                "evaluation_results": [{"score": s} for s in scores],
                "meaningful_chunks": meaningful,
                "is_relevant": len(meaningful) > 0
            })
            print(f"✅ 평균 {avg:.2f} / 유의미 청크 {len(meaningful)}개 → {'통과' if meaningful else '미달'}")

        # -------- 비교 질의 --------
        elif query_type == "comparison":
            pairs, meaningful = {}, []
            for comp, docs in retrieved.items():
                combined = "\n".join(d.page_content[:600] for d in docs)
                score = self._evaluate(query, combined)
                pairs[comp] = score
                if score >= self.threshold:
                    meaningful.extend(docs)
                print(f"📄 [{comp}] → score={score}")
            avg = np.mean(list(pairs.values())) if pairs else 0
            state.update({
                "evaluation_results": pairs,
                "meaningful_chunks": meaningful,
                "is_relevant": len(meaningful) > 0
            })
            print(f"✅ 평균 {avg:.2f} / 유의미 청크 {len(meaningful)}개 → {'통과' if meaningful else '미달'}")
        else:
            state["is_relevant"] = False
            state["meaningful_chunks"] = []
        return state

# Prompt 수정하기
    def _evaluate(self, query, content):
        prompt = f"질문: {query}\n문서: {content[:700]}\n\n관련성 점수를 0~1 사이로 출력해."
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        text = res.choices[0].message.content
        match = re.search(r"([0-1](?:\.\d+)?)", text)
        return float(match.group(1)) if match else 0.0
