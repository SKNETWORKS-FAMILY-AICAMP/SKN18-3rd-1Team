import os
import json
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from tqdm import tqdm

# =====================================
# 1️⃣ 환경 변수 및 설정
# =====================================
load_dotenv(dotenv_path=".env")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
assert OPENAI_KEY, "❌ OPENAI_API_KEY가 설정되지 않았습니다 (.env 확인)."

CONNECTION_STRING = "postgresql://admin:admin123@localhost:5432/UNITvectordb"
TABLE_NAME = "insurance_embeddings"
CSV_PATH = "data/insurance_clauses.csv"


# =====================================
# 2️⃣ pgvector 테이블 준비
# =====================================
def setup_pgvector_and_table():
    conn = psycopg2.connect(CONNECTION_STRING)
    conn.autocommit = True
    cur = conn.cursor()
    register_vector(conn)

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")
    cur.execute(f"""
        CREATE TABLE {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding VECTOR(3072),
            metadata JSONB
        );
    """)
    print(f"✅ '{TABLE_NAME}' 테이블 생성 완료")
    cur.close()
    conn.close()

# =====================================
# 3️⃣ CSV 로드 및 청크 분할
# =====================================
def load_and_split_csv(csv_path: str):
    df = pd.read_csv(csv_path)
    print(f"📊 원본 CSV 로드: {len(df)}행")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " "]
    )

    records = []
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="텍스트 분할 중"):
        content = str(row.get("내용", "")).strip()
        if not content or content.lower() == "nan":
            continue

        chunks = splitter.split_text(content)
        company = str(row.get("회사명", "")).strip()
        product = str(row.get("보험명", "")).strip()
        clause = str(row.get("조항", "")).strip()

        for i, chunk in enumerate(chunks):
            unique_id = f"{company}_{product}_{clause}_chunk{i+1}"
            meta = {
                "회사명": company,
                "보험명": product,
                "조항": clause,
                "row_id": int(idx)
            }
            records.append((chunk, meta))


    print(f"✅ 분할 완료: {len(records)}개 청크 생성됨")
    return records

# =====================================
# 4️⃣ 임베딩 생성 및 DB 저장
# =====================================
def insert_embeddings(records):
    conn = psycopg2.connect(CONNECTION_STRING)
    conn.autocommit = True
    cur = conn.cursor()
    register_vector(conn)

    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    print("🚀 임베딩 생성 및 DB 저장 시작...")
    for i, (text, meta) in enumerate(tqdm(records, desc="Embedding Progress"), start=1):
        try:
            emb_vector = embeddings.embed_query(text)
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (content, embedding, metadata) VALUES (%s, %s, %s)",
                (text, emb_vector, json.dumps(meta, ensure_ascii=False))
            )
        except Exception as e:
            print(f"⚠️ 오류 (행 {i}): {e}")

    print(f"✅ {len(records)}개 데이터 저장 완료!")
    cur.close()
    conn.close()

# =====================================
# 5️⃣ 메인 실행
# =====================================
def main():
    setup_pgvector_and_table()
    records = load_and_split_csv(CSV_PATH)
    insert_embeddings(records)
    print("\nvectordb 구축 완료")

if __name__ == "__main__":
    main()
