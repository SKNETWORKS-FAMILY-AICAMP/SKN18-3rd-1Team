#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 custom_pgvector.py
──────────────────────────────────────────────
PGVector 기반 벡터 검색 엔진 (검색 전용)
──────────────────────────────────────────────
- 단일/비교질문 판단 로직 없음
- OpenAI 임베딩 기반 쿼리 임베딩 생성
- PostgreSQL(pgvector)에서 유사도 검색 수행
──────────────────────────────────────────────
"""

import os
import psycopg2
from psycopg2.extras import Json
from pgvector.psycopg2 import register_vector
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import json


# ======================================================
# 1️⃣ 싱글톤 메타클래스
# ======================================================
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# ======================================================
# 2️⃣ CustomPGVector (검색 전용)
# ======================================================
class CustomPGVector(metaclass=Singleton):
    """
    ✅ 벡터 검색 엔진 역할만 수행
    - 쿼리 임베딩 생성
    - pgvector 유사도 검색 실행
    - 결과를 LangChain Document 리스트로 반환
    """

    def __init__(self, conn_str: str, table: str = "insurance_embeddings"):
        load_dotenv()
        self.conn = psycopg2.connect(conn_str)
        self.conn.autocommit = True
        self.table = table

        model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.embeddings = OpenAIEmbeddings(model=model_name)
        register_vector(self.conn)
        print(f"✅ CustomPGVector 초기화 완료 (table={self.table})")

    # ------------------------------------------------------------
    # ✅ 기본 유사도 검색
    # ------------------------------------------------------------
    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        - 사용자의 질문을 임베딩하고
        - PGVector 테이블에서 유사 문서를 검색
        - 메타데이터(JSONB) 필터링 가능
        """
        try:
            query_emb = self.embeddings.embed_query(query)
            params, where_clauses = [], []
            sql = f"SELECT content, metadata FROM {self.table}"

            # 🔹 메타데이터 필터 적용 (예: {"보험사명": "현대"})
            if filter:
                for key, value in filter.items():
                    where_clauses.append("metadata @> %s::jsonb")
                    params.append(json.dumps({key: value}))

            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)

            sql += " ORDER BY embedding <-> %s::vector LIMIT %s"
            params.extend([query_emb, k])

            with self.conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()

            documents = [
                Document(
                    page_content=row[0],
                    metadata=json.loads(row[1]) if isinstance(row[1], str) else row[1]
                )
                for row in rows
            ]
            return documents

        except Exception as e:
            print(f"⚠️ 유사도 검색 중 오류 발생: {e}")
            return []

    # ------------------------------------------------------------
    # ✅ 점수 포함 검색 (선택적)
    # ------------------------------------------------------------
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Document, float]]:
        """
        - 유사 문서와 함께 거리(score)를 반환
        - 낮을수록 유사도가 높음
        """
        try:
            query_emb = self.embeddings.embed_query(query)
            params, where_clauses = [], []
            sql = f"""
                SELECT content, metadata, (embedding <-> %s::vector) AS score
                FROM {self.table}
            """
            params.append(query_emb)

            if filter:
                sql += " WHERE metadata @> %s::jsonb"
                params.append(json.dumps(filter))

            sql += " ORDER BY score LIMIT %s"
            params.append(k)

            with self.conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()

            return [
                (
                    Document(
                        page_content=row[0],
                        metadata=json.loads(row[1]) if isinstance(row[1], str) else row[1]
                    ),
                    float(row[2])
                )
                for row in rows
            ]

        except Exception as e:
            print(f"⚠️ 검색(점수 포함) 중 오류 발생: {e}")
            return []
