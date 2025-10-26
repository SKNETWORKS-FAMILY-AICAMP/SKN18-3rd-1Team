from vectordb.connect_db import connect_DB
from vectordb.llm_model import set_embedding_model
from pgvector.psycopg2 import register_vector, Vector

class InsuranceRetriever:
    def __init__(self, classify_result: dict, top_k: int = 5):
        """
        classify_result 예시:
        {
            "can_answer_with_data": True,
            "category": "analysis",
            "company_filter": "삼성화재",
            "product_filter": "운전자보험"
        }
        """
        self.db = connect_DB()               # 싱글톤 DB 객체
        self.embedding_model = set_embedding_model()  # 싱글톤 임베딩
        self.classify_result = classify_result
        self.top_k = top_k

        # 필터 설정
        if classify_result.get("can_answer_with_data"):
            self.company_filter = classify_result.get("company_filter")
            self.product_filter = classify_result.get("product_filter")
        else:
            self.company_filter = None
            self.product_filter = None

    def search(self, query: str):
        """
        classify 결과에 따라 DB에서 top-k chunk 검색
        """
        if not self.classify_result.get("can_answer_with_data", False):
            return []

        conn = self.db.get_connection()
        try:
            register_vector(conn)  # pgvector adapter 등록
            cur = conn.cursor()

            # embedding 생성 후 Vector 타입으로 변환
            embedding = self.embedding_model.embed_query(query)
            embedding = Vector(embedding)  # 중요: 반드시 Vector 타입

            # company filter
            companies = self.company_filter.split(",") if self.company_filter else None

            sql = """
                SELECT clause, metadata, embedding <=> %s AS distance
                FROM insurance_vectordb
                WHERE (%s IS NULL OR company = ANY(%s))
                  AND (%s IS NULL OR product = %s)
                ORDER BY embedding <=> %s
                LIMIT %s;
            """

            cur.execute(
                sql,
                (
                    embedding,        # vector 비교
                    companies,        # company 필터
                    companies,
                    self.product_filter,
                    self.product_filter,
                    embedding,        # 정렬 기준
                    self.top_k
                )
            )

            rows = cur.fetchall()
            results = [
                {
                    "text": row[0],
                    "metadata": row[1],
                    "score": 1 - float(row[2])  # distance → 유사도 점수
                }
                for row in rows
            ]
            return results
        finally:
            self.db.release_connection(conn)
