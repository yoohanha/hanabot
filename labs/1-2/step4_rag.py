# [1-2] 완전한 RAG: 임베딩 + 검색 + LLM 답변
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from hanabot.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaEmbeddings, OllamaLLM

# RAG_PLAN.md 읽기 및 준비
rag_plan_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "RAG_PLAN.md")
with open(rag_plan_path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "<!-- RAG_DOCS_START -->"
end_marker = "<!-- RAG_DOCS_END -->"
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

rag_docs = content[start_idx + len(start_marker):end_idx].strip()

# 문서 분할
headers_to_split_on = [
    ("#", "h1"),
    ("##", "h2"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
chunks = splitter.split_text(rag_docs)

# Document 생성
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

# 벡터 저장소 초기화
embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(documents)

# LLM 초기화
llm = OllamaLLM(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL)

# 프롬프트 템플릿
prompt = PromptTemplate(
    input_variables=["documents", "question"],
    template="""다음 규정 문서를 읽고 질문에 답해주세요.

규정:
{documents}

질문: {question}

규칙:
- 문서에 있는 내용으로만 답하세요
- 문서에 없는 내용이면 "규정에 없는 내용입니다"라고만 답하세요
- 간결하게 답하세요
"""
)

# 체인 구성
chain = prompt | llm | StrOutputParser()

# RAG 검색 및 답변 함수
def answer_with_rag(question):
    # 비슷한 조각 3개 검색
    results = vector_store.similarity_search_with_score(question, k=3)

    # 문서 준비
    doc_text = "\n\n".join([
        f"{doc.metadata.get('title', '')}\n{doc.page_content}"
        for doc, score in results
    ])

    # LLM에서 답변 생성
    response = chain.invoke({
        "documents": doc_text,
        "question": question
    })

    # 근거 추출
    sources = [doc.metadata.get('title', '') for doc, score in results]

    print(f"질문: {question}")
    print(f"답변: {response.strip()}")
    print(f"근거: {', '.join(sources)}")
    print()

print("=" * 80)
print("하나 AI 학원 규정 - 완전한 RAG 시스템")
print("=" * 80)
print()

# 실행
answer_with_rag("지각 몇 번이면 결석이야?")
answer_with_rag("수료하려면 출석률이 얼마나 돼야 해?")
answer_with_rag("화요일 오후에는 뭘 배워?")
answer_with_rag("점심 메뉴 뭐야?")
