# nodes/retriever_node.py
from vectordb.connect_db import connect_DB
from vectordb.llm_model import set_embedding_model
from pgvector.psycopg2 import register_vector


class InsuranceRetrieverNode:
    """
    classify 결과를 기반으로 벡터 DB에서 유사한 chunk를 검색
    """
    def __init__(self, company_filter=None, product_filter=None, top_k=10):
        self.db = connect_DB()
        self.embedding_model = set_embedding_model()
        self.company_filter = company_filter
        self.product_filter = product_filter
        self.top_k = top_k

    def run(self, query):
        conn = self.db.get_connection()
        register_vector(conn)
        try:
            cur = conn.cursor()
            embedding = list(self.embedding_model.embed_query(query))

            sql = """
            SELECT clause, metadata, 1 - (embedding <=> %s::vector) AS score
            FROM insurance_vectordb
            WHERE (%s = '' OR metadata->>'보험사명' ILIKE %s)
              AND (%s = '' OR metadata->>'상품명' ILIKE %s)
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
            """

            comp_val = f"%{self.company_filter}%" if self.company_filter else ""
            prod_val = f"%{self.product_filter}%" if self.product_filter else ""

            cur.execute(
                sql,
                (
                    embedding,
                    self.company_filter or "",
                    comp_val,
                    self.product_filter or "",
                    prod_val,
                    embedding,
                    self.top_k,
                ),
            )

            rows = cur.fetchall()
            results = [
                {"text": row[0], "metadata": row[1], "score": float(row[2])}
                for row in rows
            ]

            print(f"=== 검색된 청크 수: {len(results)} ===")
            for r in results:
                print(f"- {r['metadata'].get('보험사명')} | {r['metadata'].get('상품명')} | score={r['score']:.3f}")

            return results
        finally:
            self.db.release_connection(conn)
