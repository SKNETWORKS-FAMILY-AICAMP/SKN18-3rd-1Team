-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS insurance_embeddings (
    unique_id TEXT PRIMARY KEY,
    company TEXT,
    product TEXT,
    clause TEXT,
    content TEXT,
    embedding VECTOR(3072)
);