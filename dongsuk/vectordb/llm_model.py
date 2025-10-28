from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 API 키 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def set_embedding_model():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY
    )

# 분류 모델 - 덜 보수적이고 비용 효율적
def set_classify_model():
    return ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.3  # 약간의 창의성으로 덜 보수적으로
    )

# 답변 모델
def set_llm_model():
    return ChatOpenAI(
        model="gpt-5-nano",
        openai_api_key=OPENAI_API_KEY,
        reasoning_effort="high"
    )

# 평가 모델
def set_score_model():
    return ChatOpenAI(
        model="gpt-5-nano",
        openai_api_key=OPENAI_API_KEY,
        frequency_penalty=0
    )