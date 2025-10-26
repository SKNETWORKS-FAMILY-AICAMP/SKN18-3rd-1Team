"""
RewriteNode
──────────────────────────────────────────────
추출한 Chunk에서 질문에 유의미한 답변이 없을 경우
질문 재작성 실행하는 노드 
max_try = 1
──────────────────────────────────────────────
"""
from openai import OpenAI
import re

client = OpenAI()

class RewriteNode:
    """
    ✅ 단일 + 비교 질문 모두 처리 가능한 통합 Rewrite 노드
    - query_type에 따라 프롬프트를 다르게 구성
    - max_retry: 재작성 시도 횟수 제한 (기본 1회)
    """
    def __init__(self, max_retry: int = 1):
        self.max_retry = max_retry

    def __call__(self, state):
        query = state["user_input"]
        query_type = state.get("query_type", "single")
        is_relevant = state.get("is_relevant", True)

        # 평가 통과 시 생략
        if is_relevant:
            print("✅ 평가 통과 — RewriteNode 생략")
            state["rewritten_query"] = query
            state["is_rewritten"] = False
            return state

        retry_count = state.get("retry_count", 0)
        if retry_count >= self.max_retry:
            print("⚠️ 최대 재작성 횟수 도달 — RewriteNode 종료")
            state["rewritten_query"] = query
            state["is_rewritten"] = False
            return state

        print(f"\n📝 [RewriteNode] 평가 미달 → 질문 리라이트 중... (시도 {retry_count + 1}/{self.max_retry})")

# prompt 재작성 필요
        if query_type == "single":
            prompt = f"""
            사용자의 질문이 특정 보험사 관련으로 너무 모호합니다.
            아래 질문을 더 구체적이고 명확하게 다시 써주세요.

            원래 질문: "{query}"

            규칙:
            - 질문의 핵심 의미는 바꾸지 마세요.

            출력 형식:
            rewritten_query: <수정된 질문>
            """
        else:
            prompt = f"""
            사용자의 비교 질문이 모호합니다.
            아래 질문을 두 개 이상의 보험사를 명시하고, 비교 기준이 뚜렷하게 보이도록 다시 써주세요.

            원래 질문: "{query}"

            규칙:
            - 문장은 자연스럽게 유지하세요.

            출력 형식:
            rewritten_query: <명확히 다시 작성된 비교 질문>
            """

        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            # temperature=0.7
        )

        text = res.choices[0].message.content.strip()
        match = re.search(r"rewritten_query\s*:\s*(.+)", text)
        rewritten = match.group(1).strip() if match else text

        # 상태 업데이트
        state["rewritten_query"] = rewritten
        state["is_rewritten"] = True
        state["retry_count"] = retry_count + 1

        print(f"🔁 리라이트 완료 → {rewritten}")
        return state
