# agents/classify_agent.py
# --------------------------------------------
# 목적: 질문이 도메인 관련인지 판별
# 출력: state["classification"] = "relevant" | "irrelevant"
# 모델: 네 환경의 llms.py에서 래핑된 LLM 사용
# --------------------------------------------

from langchain.prompts import PromptTemplate   # 프롬프트 템플릿 객체
from llms import get_llm_openai               # 기존 네 래퍼 함수 임포트(모델 선택 통일 목적)

# LLM 인스턴스 준비
llm = get_llm_openai(model_name="gpt-5-nano")  # 네가 쓰는 경량 모델 명시. llms.py의 시그니처 준수

# 프롬프트 템플릿 정의
prompt = PromptTemplate.from_template(
    # 분류 목적 설명. 출력 형식 단순화. 일관성 유지
    "다음 질문이 보험 약관 또는 보험 보상/계약/용어와 직접적으로 관련 있으면 '관련 있음', "
    "그 외면 '관련 없음'만 출력하세요.\n\n질문: {question}"
)

def classify_agent(state: dict) -> dict:
    """분류 에이전트. 입력: state, 출력: state 갱신"""
    question = state["question"]                         # 사용자 질문 추출
    completion = llm.invoke(prompt.format(question=question))  # LLM 호출. invoke/ __call__ 둘 중 지원되는 것 사용
    text = (completion if isinstance(completion, str) else getattr(completion, "content", "")).strip()  # 응답 정규화

    # 간단한 규칙으로 relevant/irrelevant 결정
    state["classification"] = "irrelevant" if "없" in text else "relevant"  # 한국어 응답 기준. "관련 없음" 포함시 부정 처리
    return state                                          # 갱신된 state 반환
