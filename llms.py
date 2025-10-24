from dotenv import load_dotenv
from langchain_openai import ChatOpenAI 

# GPT 모델 불러오는 함수임
# 보험약관 RAG에서 답변 생성에 사용함
def get_llm_openai(model_name: str = "gpt-5-nano"): # 추후 모델 바꿀 예정
    load_dotenv()  # .env 파일에서 API 키 불러옴
    # ChatOpenAI 객체 반환함
    # model_name으로 사용할 GPT 버전 지정함
    return ChatOpenAI(
        model=model_name,
    )

# 테스트용 코드
if __name__ == "__main__":
    llm = get_llm_openai()
    print("✅ LLM 모델 불러오기 성공함")
