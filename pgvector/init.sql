CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS insurance_vectordb (
    id SERIAL PRIMARY KEY,
    clause TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_insurance_vectordb_embedding
ON insurance_vectordb
USING ivfflat (embedding vector_l2_ops)
WITH (lists = 100);
