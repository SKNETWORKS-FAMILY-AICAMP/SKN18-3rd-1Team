import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter

df = pd.read_csv("data/all.csv")

print(f"📊 원본 데이터: {len(df)}행")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", "\n", ".", " "]
)

rows = []

for _, row in df.iterrows():
    content = str(row.get("내용", "")).strip()
    if not content or content.lower() == "nan":
        continue

    chunks = splitter.split_text(content)

    for i, chunk in enumerate(chunks):
        insurance = str(row.get("보험사명", "")).strip()
        product = str(row.get("상품명", "")).strip()
        clause = str(row.get("조항(편 장 절 조)", "")).strip()

        # ✅ 고유 ID 생성 (RAG용)
        unique_id = f"{insurance}_{product}_{clause}_chunk{i+1}"

        rows.append({
            "unique_id": unique_id,
            "chunk_id": i + 1,
            "보험사명": insurance,
            "상품명": product,
            "조항(편 장 절 조)": clause,
            "chunk_length": len(chunk),
            "내용_chunk": chunk
        })

df_chunks = pd.DataFrame(rows)
df_chunks.to_csv("data/insurance_clauses_chunked.csv", index=False, encoding="utf-8-sig")

print(f"\n📈 데이터 변환 결과:")
print(f"  - 원본 행 수: {len(df):,}행")
print(f"  - 청크 후 행 수: {len(df_chunks):,}행")
print(f"  - 증가율: {len(df_chunks) / len(df):.1f}배")
print(f"✅ 완료! insurance_clauses_chunked.csv 파일이 생성되었습니다.") 
print(f"\n📋 청크 데이터 미리보기:")
print(df_chunks.head())
