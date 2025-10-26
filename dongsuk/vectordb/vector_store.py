import pandas as pd
import json
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pgvector.psycopg2 import register_vector
from connect_db import connect_DB
from llm_model import set_embedding_model

class InsuranceVectorStore:
    def __init__(self):
        self.embedding_model = set_embedding_model()
        self.db = connect_DB()
    
    def load_csv(self, file_path: str):
        df = pd.read_csv(file_path)
        docs = [Document(
            page_content=str(row["내용"]),
            metadata={
                "조항": str(row["조항"]),
                "보험사명": str(row["회사명"]),  # 회사명 → 보험사명으로 매핑
                "상품명": str(row["보험명"]),   # 보험명 → 상품명으로 매핑
                "row_id": i
            }
        ) for i, row in df.iterrows()]
        return docs
    
    def chunk_split(self, documents):
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = []
        
        for doc in documents:
            split_docs = splitter.split_documents([doc])
            for chunk_doc in split_docs:
                chunks.append({
                    "text": chunk_doc.page_content,
                    "metadata": chunk_doc.metadata
                })
        return chunks
    
    def create_embeddings(self, chunks):
        for chunk in chunks:
            embedding = self.embedding_model.embed_query(chunk["text"])
            chunk["embedding"] = embedding
        return chunks
    
    def store_to_vectordb(self, chunks):
        conn = self.db.get_connection()
        register_vector(conn)
        
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM insurance_vectordb;")
                
                for chunk in chunks:
                    cur.execute("""
                        INSERT INTO insurance_vectordb (clause, embedding, metadata)
                        VALUES (%s, %s, %s)
                    """, (
                        chunk["text"],
                        chunk["embedding"],
                        json.dumps(chunk["metadata"], ensure_ascii=False)
                    ))
            conn.commit()
        finally:
            self.db.release_connection(conn)

def main():
    store = InsuranceVectorStore()
    
    docs = store.load_csv("csv_data/insurance_clauses.csv")  # 새로운 파일 경로
    chunks = store.chunk_split(docs)
    embedded_chunks = store.create_embeddings(chunks)
    store.store_to_vectordb(embedded_chunks)
    
    print("벡터 데이터베이스 구축 완료!")

if __name__ == "__main__":
    main()