"""
그래프 그리기
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rag_pipeline'))

from build_graph import build_graph

CONN_STR = "postgresql://admin:admin123@localhost:5432/UNITvectordb"

print("🧩 그래프 구조 시각화 중...")
graph = build_graph(conn_str=CONN_STR)
app = graph.compile()

# Mermaid 기반 시각화 (xray=True로 내부 조건 로직 포함)
png_bytes = app.get_graph(xray=True).draw_mermaid_png()

# 파일로 저장
output_path = "graph_structure.png"
with open(output_path, "wb") as f:
    f.write(png_bytes)

print(f"✅ 그래프 렌더링 완료 → {output_path}")
