-- 1️⃣ pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;


CREATE TABLE insurance_embeddings (
    id SERIAL PRIMARY KEY,           -- 고유 ID
    content TEXT,                    -- 약관 텍스트
    embedding VECTOR(3072),          -- OpenAI text-embedding-3-large
    metadata JSONB                   -- 회사명 / 보험명 / 조항 등 메타데이터
);