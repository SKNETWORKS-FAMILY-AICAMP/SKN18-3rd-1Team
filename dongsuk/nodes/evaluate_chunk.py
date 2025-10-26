# nodes/evaluate_chunk_node.py
from vectordb.llm_model import set_score_model

class EvaluateChunkNode:
    """
    retriever에서 가져온 chunk가 질문에 유효한지 판단
    """
    def __init__(self):
        self.model = set_score_model()

    def run(self, user_input: str, retrieved_chunks: list):
        """
        user_input: 사용자 질문
        retrieved_chunks: retriever에서 가져온 chunk 리스트 [{'text':..., 'metadata':..., 'score':...}, ...]
        """
        if not retrieved_chunks:
            return False, []

        valid_chunks = []
        for chunk in retrieved_chunks:
            prompt = f"질문: {user_input}\n이 내용이 질문에 답하는 데 도움이 되나요? 답: 예/아니오\n내용: {chunk['text']}"
            response = self.model.call(prompt)
            if "예" in response:
                valid_chunks.append(chunk)

        return bool(valid_chunks), valid_chunks
