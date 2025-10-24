#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📘 build_pgvector_from_csv_manual.py
─────────────────────────────────────────────
LangChain 자동 저장 ❌  
직접 테이블 생성 + 임베딩 + INSERT 방식으로 저장 ✅
─────────────────────────────────────────────
"""

import os
import psycopg2
import pandas as pd
import json
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from langchain_openai import OpenAIEmbeddings
from tqdm import tqdm

# =====================================
# 1️⃣ 환경 변수 로드
# =====================================
load_dotenv(dotenv_path=".env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_KEY, "❌ OPENAI_API_KEY가 설정되지 않았습니다 (.env 확인)."

# =====================================
# 2️⃣ PostgreSQL 연결 설정
# =====================================
CONNECTION_STRING = "postgresql://admin:admin123@localhost:5432/UNITvectordb"
TABLE_NAME = "insurance_embeddings"
CSV_PATH = "data/insurance_clauses_chunked.csv"


# =====================================
# 3️⃣ pgvector 확장 + 테이블 생성
# =====================================
def setup_pgvector_and_table():
    conn = psycopg2.connect(CONNECTION_STRING)
    conn.autocommit = True
    cursor = conn.cursor()
    register_vector(conn)

    # pgvector 확장 설치
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 기존 테이블 있으면 삭제하고 새로 생성
    cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
    cursor.execute(f"""
        CREATE TABLE {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR(3072),
            metadata JSONB
        );
    """)
    print(f"✅ '{TABLE_NAME}' 테이블 생성 완료")
    cursor.close()
    conn.close()


# =====================================
# 4️⃣ CSV 불러오기
# =====================================
def load_csv(csv_path: str):
    df = pd.read_csv(csv_path)
    print(f"📊 CSV 로드 완료: {len(df)}개 행")

    records = []
    for _, row in df.iterrows():
        text = str(row.get("내용_chunk", "")).strip()
        if not text or len(text) < 10:
            continue
        meta = {
            "보험사명": row.get("보험사명", ""),
            "상품명": row.get("상품명", ""),
            "조항": row.get("조항(편 장 절 조)", ""),
            "unique_id": row.get("unique_id", "")
        }
        records.append((text, meta))
    print(f"📄 변환 완료: {len(records)}개 문서")
    return records


# =====================================
# 5️⃣ 임베딩 생성 및 DB 저장
# =====================================
def insert_embeddings(records):
    conn = psycopg2.connect(CONNECTION_STRING)
    conn.autocommit = True
    cursor = conn.cursor()
    register_vector(conn)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    print("🚀 임베딩 생성 및 DB 저장 시작...")
    for i, (text, meta) in enumerate(tqdm(records, desc="Embedding Progress"), start=1):
        try:
            emb_vector = embeddings.embed_query(text)
            cursor.execute(
                f"INSERT INTO {TABLE_NAME} (content, embedding, metadata) VALUES (%s, %s, %s)",
                (text, emb_vector, json.dumps(meta))
            )
        except Exception as e:
            print(f"⚠️ 오류 (행 {i}): {e}")
    print(f"✅ {len(records)}개 데이터 저장 완료!")
    cursor.close()
    conn.close()


# =====================================
# 6️⃣ 전체 파이프라인 실행
# =====================================
if __name__ == "__main__":
    setup_pgvector_and_table()
    records = load_csv(CSV_PATH)
    insert_embeddings(records)
    print("\n🎉 전체 과정 완료!")
