# insert_vectordb.py
# ----------------------------------------------------------
# 목적 : CSV 파일 데이터를 VectorDB(pgvector)에 삽입
# 구조 : CSV → embedding_models → CustomPGVector.add_text()
# 사용 : python insert_vectordb.py data/preprocessing/보험약관.csv
# ----------------------------------------------------------

import sys                           # 명령행 인자 처리를 위함 (참고: Python 표준 모듈)
import pandas as pd                  # CSV 데이터 읽기용
from tqdm import tqdm                # 진행률 표시용
from customPGVector import CustomPGVector            # ✅ [출처] customPGVector.py
from embedding_models import get_embedding_model_openai  # ✅ [출처] embedding_models.py


# ----------------------------------------------------------
# 1️⃣ CSV → VectorDB 삽입 함수 정의
# ----------------------------------------------------------
def insert_csv_to_vectordb(csv_path: str):
    """
    CSV 파일을 읽어 pgvector 기반 데이터베이스에 삽입한다.
    각 row의 '내용' 텍스트를 임베딩하여 CustomPGVector.add_text()로 저장한다.
    """

    # --------------------------------------
    # (1) CSV 데이터 로드
    # --------------------------------------
    # pandas로 CSV 파일을 읽는다.
    # ✅ [참고] 1.CreateVectordb.ipynb 의 "df = pd.read_csv(...)" 부분
    df = pd.read_csv(csv_path)
    print(f"📄 CSV 로드 완료: {csv_path} ({len(df)}행)")

    # --------------------------------------
    # (2) 임베딩 함수 준비
    # --------------------------------------
    # embedding_models.py의 get_embedding_model_openai() 사용.
    # ✅ [출처] embedding_models.py 의 "def get_embedding_model_openai(): ..."
    embedding_fn = get_embedding_model_openai()

    # --------------------------------------
    # (3) CustomPGVector 인스턴스 생성
    # --------------------------------------
    # DB 연결 문자열은 기존 코드에서 그대로 사용.
    # ✅ [출처] customPGVector.py 의 "__init__" 시그니처 (conn_str, embedding_fn)
    vectorstore = CustomPGVector(
        conn_str="postgresql://admin:admin123@localhost:5432/vectordb",  # 필요 시 환경변수화 가능
        embedding_fn=embedding_fn
    )

    # --------------------------------------
    # (4) CSV 행 단위로 데이터 삽입
    # --------------------------------------
    # tqdm으로 진행률을 출력하며 각 행의 텍스트를 벡터화한다.
    # ✅ [참고] 1.CreateVectordb.ipynb 의 for loop 로우 단위 삽입 로직
    for _, row in tqdm(df.iterrows(), total=len(df), desc="📥 VectorDB 삽입 중"):
        # ‘내용’ 컬럼은 실제 텍스트 본문
        content = str(row.get("내용", "")).strip()
        if not content:
            continue

        # ‘조항’, ‘보험사명’, ‘상품명’은 메타데이터로 저장
        metadata = {
            "조항": str(row.get("조항", "")),
            "보험사명": str(row.get("보험사명", "")),
            "상품명": str(row.get("상품명", ""))
        }

        # CustomPGVector.add_text() 메서드를 호출해 벡터 + 메타데이터 저장
        # ✅ [출처] customPGVector.py 의 "def add_text(self, content, metadata=None):"
        vectorstore.add_text(content, metadata=metadata)

    print(f"✅ 총 {len(df)}개 데이터가 VectorDB에 저장 완료.")


# ----------------------------------------------------------
# 2️⃣ 메인 실행부
# ----------------------------------------------------------
if __name__ == "__main__":
    """
    명령행에서 CSV 경로를 받아 insert_csv_to_vectordb 실행.
    python insert_vectordb.py data/preprocessing/보험약관.csv
    """
    # 명령행 인자가 없을 경우 에러 출력 후 종료
    if len(sys.argv) < 2:
        print("⚠️ CSV 파일 경로를 입력하세요. 예: python insert_vectordb.py data/preprocessing/보험약관.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    insert_csv_to_vectordb(csv_path)
