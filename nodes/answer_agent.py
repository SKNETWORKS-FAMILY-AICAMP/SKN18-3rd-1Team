# agents/answer_agent.py
# --------------------------------------------
# 목적: compare/analyze 결과 병합 → 사용자 응답 생성
# 특징: 둘 중 하나만 존재해도 안전 동작
# 출력: state["answer"] = 최종 텍스트
# --------------------------------------------

def answer_agent(state: dict) -> dict:
    """최종 응답 생성 에이전트. 병렬 산출물 병합."""
    compare = state.get("compare_result")      # 비교 결과 획득(dict 또는 None)
    analysis = state.get("analysis_result")    # 분석 결과 획득(dict 또는 None)

    # 병합 로직. 부분 실행 대응
    if compare and analysis:                   # 둘 다 존재
        merged = (
            "【비교 요약】\n"
            f"{compare.get('summary','')}\n\n"
            "【분석 요약】\n"
            f"{analysis.get('summary','')}"
        )
    elif compare:                              # 비교만 존재
        merged = "【비교 요약】\n" + compare.get("summary", "")
    elif analysis:                             # 분석만 존재
        merged = "【분석 요약】\n" + analysis.get("summary", "")
    else:                                      # 둘 다 없음
        merged = "유의미한 정보를 찾지 못했습니다. 질문을 구체화해 주세요."

    state["answer"] = merged                   # 최종 텍스트 저장
    return state                               # 갱신 반환
