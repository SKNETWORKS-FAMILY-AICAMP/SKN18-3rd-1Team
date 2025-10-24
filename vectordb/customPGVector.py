# customPGVector.py
from langchain.vectorstores.base import VectorStore
from typing import List, Dict, Any, Optional, Tuple
from langchain.schema import Document
from psycopg2.extras import Json
import json, os, psycopg2
from dotenv import load_dotenv   # ✅ 환경변수 로드 추가

from .embedding_models import get_embedding_model_openai

# Singleton 패턴 (중복 인스턴스 방지)
class Singleton(type(VectorStore)):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# PostgreSQL + pgvector 관리 클래스
class CustomPGVector(VectorStore, metaclass=Singleton):
    def __init__(self, conn_str: Optional[str] = None, embedding_fn=None, table: str = "documents"):
        # ✅ .env 불러오기
        load_dotenv()

        # .env에 PG_CONN_STR 있으면 그걸 우선 사용
        if conn_str is None:
            conn_str = os.getenv("PG_CONN_STR")

        if not conn_str:
            raise ValueError("❌ PostgreSQL 연결 문자열(conn_str)이 설정되지 않았습니다.")

        # ✅ DB 연결
        self.conn = psycopg2.connect(conn_str)
        self.embedding_fn = embedding_fn
        self.table = table

    # ----------------------------------------------
    # 나머지 코드는 기존 그대로 유지
    # ----------------------------------------------
    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding_fn,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        conn_str: str = None,
        table: str = "my_vectors",
        **kwargs,
    ):
        store = cls(conn_str=conn_str, embedding_fn=embedding_fn, table=table)
        store.add_texts(texts, metadatas=metadatas)
        return store

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        metadatas = metadatas or [{} for _ in texts]
        embeddings = self.embedding_fn.embed_documents(texts)

        with self.conn.cursor() as cur:
            for text, emb, meta in zip(texts, embeddings, metadatas):
                cur.execute(
                    f"""
                    INSERT INTO {self.table} (content, embedding, metadata)
                    VALUES (%s, %s, %s)
                    """,
                    (text, emb, Json(meta)),
                )
        self.conn.commit()

    def similarity_search(
        self, query: str, k: int = 4, filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        query_emb = self.embedding_fn.embed_query(query)
        params = []
        sql_query_template = f"SELECT content, metadata FROM {self.table}"
        where_clauses = []

        if filter:
            filter_json = json.dumps(filter)
            where_clauses.append("metadata @> %s::jsonb")
            params.append(filter_json)

        if where_clauses:
            sql_query_template += " WHERE 1=1 AND " + " AND ".join(where_clauses)

        sql_query_template += " ORDER BY embedding <-> %s::vector LIMIT %s"
        params.append(query_emb)
        params.append(k)

        with self.conn.cursor() as cur:
            cur.execute(sql_query_template, tuple(params))
            rows = self.__get_unique_documents(cur.fetchall())

        return [Document(page_content=row[0], metadata=row[1]) for row in rows]

    def similarity_search_with_score(self, query: str, k: int = 4) -> List[Tuple[Document, float]]:
        query_emb = self.embedding_fn.embed_query(query)

        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT content, metadata, (embedding <-> %s::vector) AS score
                FROM {self.table}
                ORDER BY score
                LIMIT %s
                """,
                (query_emb, k),
            )
            rows = self.__get_unique_documents(cur.fetchall())

        return [(Document(page_content=row[0], metadata=row[1]), float(row[2])) for row in rows]

    def __get_unique_documents(self, rows):
        unique_contents = set()
        unique_documents = []

        for row in rows:
            content = row[0]
            if content not in unique_contents:
                unique_contents.add(content)
                unique_documents.append(row)
        return unique_documents


# 테스트 실행부
if __name__ == "__main__":
    # .env 파일에 PG_CONN_STR이 없으면 기본값 사용
    os.environ.setdefault("PG_CONN_STR", "postgresql://admin:admin123@db:5432/vectordb")
    vectorstore = CustomPGVector(embedding_fn=get_embedding_model_openai())
    print("✅ Vectorstore 연결 성공")
