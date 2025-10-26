from typing import Dict, Any

State = Dict[str, Any]

def classify_router(state: State) -> str:
    """classify_query 결과에 따른 라우팅"""
    if state.get("can_answer_with_data", False):
        return "category"
    else:
        return "end"

def evaluate_router(state: State) -> str:
    """evaluate_chunk 결과에 따른 라우팅"""
    if state.get("evaluation_result") == "yes":
        return "generate"
    elif state.get("retry_count", 0) == 0:
        return "rewrite"
    else:
        return "end"

def main():
    # 테스트
    test_cases = [
        {"can_answer_with_data": True},
        {"can_answer_with_data": False},
        {"evaluation_result": "yes"},
        {"evaluation_result": "no", "retry_count": 0},
        {"evaluation_result": "no", "retry_count": 1}
    ]
    
    print("=== Router 함수 테스트 ===")
    
    for i, test_state in enumerate(test_cases, 1):
        print(f"\n{i}. 테스트 상태: {test_state}")
        
        if "can_answer_with_data" in test_state:
            route = classify_router(test_state)
            print(f"   classify_router → {route}")
        
        if "evaluation_result" in test_state:
            route = evaluate_router(test_state)
            print(f"   evaluate_router → {route}")

if __name__ == "__main__":
    main()