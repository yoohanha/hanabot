# [1-2] 임베딩 및 벡터 검색
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from hanabot.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings

# RAG_PLAN.md 읽기
rag_plan_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "RAG_PLAN.md")
with open(rag_plan_path, "r", encoding="utf-8") as f:
    content = f.read()

# RAG_DOCS 부분만 추출
start_marker = "<!-- RAG_DOCS_START -->"
end_marker = "<!-- RAG_DOCS_END -->"
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

rag_docs = content[start_idx + len(start_marker):end_idx].strip()

# # 와 ## 기준으로 분할
headers_to_split_on = [
    ("#", "h1"),
    ("##", "h2"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
chunks = splitter.split_text(rag_docs)

# Document 객체로 변환
documents = []
for chunk in chunks:
    h1 = chunk.metadata.get("h1", "")
    h2 = chunk.metadata.get("h2", "")
    title = f"[# {h1} > ## {h2}]" if h2 else f"[# {h1}]"

    doc = Document(
        page_content=chunk.page_content,
        metadata={"title": title, **chunk.metadata}
    )
    documents.append(doc)

# 임베딩 모델 초기화
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

# 벡터 저장소 생성 및 문서 추가
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(documents)

print("=" * 80)
print(f"✓ {len(documents)}개 조각이 벡터 저장소에 저장됨")
print("=" * 80)
print()

# 검색 함수
def search_similar(query, k=3):
    print(f"질문: {query}")
    results = vector_store.similarity_search_with_score(query, k=k)

    for i, (doc, score) in enumerate(results, 1):
        print(f"\n  [{i}] 점수: {score:.4f}")
        print(f"      제목: {doc.metadata.get('title', 'N/A')}")
        print(f"      내용: {doc.page_content.strip()}")

    print()

# 예시 검색
search_similar("지각 몇 번이면 결석이야?")
search_similar("몇 시까지 있어도 돼?")
