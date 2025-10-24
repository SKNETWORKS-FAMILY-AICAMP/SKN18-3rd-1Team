from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# .env 파일에서 OpenAI API 키 불러옴
# 텍스트를 숫자 벡터로 바꾸는 모델 가져옴
def get_embedding_model_openai(
    model_name: str = "text-embedding-3-large"):  # 기본 모델 large (3072차원)

    load_dotenv()  # .env 파일 불러오기
    print(f"[Embedding Model Loaded] {model_name} (차원: 3072)")

    # OpenAI 임베딩 모델 객체 반환함
    # 문장 하나가 3072개의 숫자로 표현됨
    return OpenAIEmbeddings(
        model=model_name,
        dimensions=3072
    )

# 테스트용 코드. 직접 실행할 때만 동작함
if __name__ == "__main__":
    embedding = get_embedding_model_openai()
    print(embedding.embed_query("자동차보험의 대물배상은 무엇인가요?"))