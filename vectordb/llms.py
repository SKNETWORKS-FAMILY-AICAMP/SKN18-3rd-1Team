from dotenv import load_dotenv
from langchain_openai import ChatOpenAI 

def get_llm_openai(model_name: str = "gpt-5-nano"):
    load_dotenv()
    return ChatOpenAI(
        model=model_name,
    )
