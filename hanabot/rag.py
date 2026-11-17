# [1-2] 하나봇 RAG 시스템
import os
from pathlib import Path

from hanabot.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaEmbeddings, OllamaLLM


def load_rag_docs():
    """RAG_PLAN.md에서 문서 추출 및 임베딩"""
    # RAG_PLAN.md 읽기
    rag_plan_path = Path(__file__).parent.parent / "data" / "RAG_PLAN.md"
    with open(rag_plan_path, "r", encoding="utf-8") as f:
        content = f.read()

    # RAG_DOCS 부분 추출
    start_marker = "<!-- RAG_DOCS_START -->"
    end_marker = "<!-- RAG_DOCS_END -->"
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("RAG_PLAN.md에서 마커를 찾을 수 없습니다")

    rag_docs = content[start_idx + len(start_marker):end_idx].strip()

    # # 와 ## 기준으로 분할
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

    # 임베딩 및 벡터 저장소
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(documents)

    return vector_store


def answer_question(question):
    """질문에 답변 (RAG 사용)"""
    # 벡터 저장소 로드
    vector_store = load_rag_docs()

    # LLM 초기화
    llm = OllamaLLM(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL)

    # 비슷한 조각 검색
    results = vector_store.similarity_search_with_score(question, k=3)

    # 문서 준비
    doc_text = "\n\n".join([
        f"{doc.metadata.get('title', '')}\n{doc.page_content}"
        for doc, score in results
    ])

    # RAG 프롬프트
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

    # 체인 구성 및 실행
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "documents": doc_text,
        "question": question
    })

    # 근거 추출
    sources = [doc.metadata.get('title', '') for doc, score in results]

    return response.strip(), sources


def answer_question_no_rag(question):
    """질문에 답변 (RAG 없음)"""
    llm = OllamaLLM(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL)
    return llm.invoke(question).strip()
