from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings


def get_embedding_model_openai(
    model_name: str = "text-embedding-3-small"):
    
    load_dotenv()
    return OpenAIEmbeddings(
        model=model_name
    )

if __name__ == "__main__":
    embedding = get_embedding_model_openai()
    print(embedding.embed_query("Hello, world!"))
