# agents/analyze_agent.py
# --------------------------------------------
# 목적: 의미 해석/핵심 요지/위험 포인트 도출(분석 관점)
# 출력: state["analysis_result"] = dict | None
# 모델: llms.py 래핑 모델 사용
# --------------------------------------------

from langchain.prompts import PromptTemplate     # 프롬프트 템플릿
from llms import get_llm_openai                 # 네 LLM 래퍼

llm = get_llm_openai(model_name="gpt-5-nano")   # 동일 모델

# 분석 지향 프롬프트. 사용자 관점 요지/위험/확인 절차 제시
prompt = PromptTemplate.from_template(
    "당신은 보험 약관 분석 전문가입니다.\n"
    "다음 문단들을 읽고 사용자 관점에서 핵심 요지(Key Points), 리스크(Risks), "
    "확인할 절차(Checklist)를 간결히 정리하세요.\n"
    "가능하면 JSON 키 형태로 정리하세요: {keys:[], risks:[], checklist:[]}\n\n"
    "문단들:\n{chunks}"
)

def analyze_agent(state: dict) -> dict:
    """분석 에이전트. chunks 없으면 None 처리."""
    chunks = state.get("chunks") or []                 # chunks 확보
    if not chunks:                                     # 빈 경우
        state["analysis_result"] = None                # None 저장
        return state                                   # 조기 반환

    joined = "\n\n".join(chunks)                       # 프롬프트 입력 병합
    completion = llm.invoke(prompt.format(chunks=joined))  # 모델 호출
    text = (completion if isinstance(completion, str) else getattr(completion, "content", "")).strip()  # 응답 정규화

    state["analysis_result"] = {"summary": text}       # dict 형태로 저장
    return state                                       # 갱신 반환
