# [1-2] RAG_PLAN.md 분할 및 청킹
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from langchain_text_splitters import MarkdownHeaderTextSplitter

# RAG_PLAN.md 읽기
rag_plan_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "RAG_PLAN.md")
with open(rag_plan_path, "r", encoding="utf-8") as f:
    content = f.read()

# RAG_DOCS_START와 RAG_DOCS_END 사이만 추출
start_marker = "<!-- RAG_DOCS_START -->"
end_marker = "<!-- RAG_DOCS_END -->"
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    rag_docs = content[start_idx + len(start_marker):end_idx].strip()
else:
    print("마커를 찾을 수 없습니다")
    sys.exit(1)

# # 와 ## 기준으로 분할
headers_to_split_on = [
    ("#", "h1"),
    ("##", "h2"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
chunks = splitter.split_text(rag_docs)

print("=" * 80)
print(f"총 {len(chunks)}개 조각으로 분할됨")
print("=" * 80)
print()

# 첫 3개 조각 출력
for i, chunk in enumerate(chunks[:3], 1):
    h1 = chunk.metadata.get("h1", "")
    h2 = chunk.metadata.get("h2", "")

    if h2:
        title = f"[# {h1} > ## {h2}]"
    else:
        title = f"[# {h1}]"

    content_text = chunk.page_content.strip()

    print(f"[조각 {i}] {title}")
    print(f"{content_text}")
    print()
