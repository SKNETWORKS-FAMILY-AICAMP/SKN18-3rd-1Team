# agents/compare_agent.py
# --------------------------------------------
# 목적: 검색된 chunk 간 차이/공통점 도출(비교 관점)
# 출력: state["compare_result"] = dict | None
# 모델: llms.py 래핑 모델 사용
# --------------------------------------------

from langchain.prompts import PromptTemplate    # 프롬프트 템플릿
from llms import get_llm_openai                # 네 LLM 래퍼

llm = get_llm_openai(model_name="gpt-5-nano")  # 동일 모델 사용. 일관성 유지

# 비교 지향 프롬프트. 구조화 출력을 JSON 유사 포맷으로 유도
prompt = PromptTemplate.from_template(
    "당신은 보험 약관 비교 전문가입니다.\n"
    "다음 문단들을 상호 비교하여 핵심 '공통점', '차이점', '주의 조항'을 간결히 요약하세요.\n"
    "가능하면 JSON 키 형태로 정리하세요: {common:[], diff:[], caution:[]}\n\n"
    "문단들:\n{chunks}"
)

def compare_agent(state: dict) -> dict:
    """비교 에이전트. chunks 없으면 None 처리."""
    chunks = state.get("chunks") or []                # chunks 확보
    if not chunks:                                    # 빈 경우
        state["compare_result"] = None                # None 저장
        return state                                  # 조기 반환

    joined = "\n\n".join(chunks)                      # 프롬프트 입력 병합
    completion = llm.invoke(prompt.format(chunks=joined))  # 모델 호출
    text = (completion if isinstance(completion, str) else getattr(completion, "content", "")).strip()  # 응답 정규화

    state["compare_result"] = {"summary": text}       # 간단히 dict 래핑. 후처리 확장 여지 마련
    return state                                      # 갱신 반환
