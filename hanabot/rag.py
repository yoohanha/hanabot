# [1-2] 하나봇 RAG 시스템
# [1-4] Langfuse 추적 추가
import os
import time
from pathlib import Path

from hanabot.config import CHAT_MODEL, EMBED_MODEL, OLLAMA_BASE_URL, LANGFUSE_ENABLED, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import OllamaEmbeddings, OllamaLLM

# [1-4] Langfuse 초기화 (선택사항)
langfuse_handler = None
if LANGFUSE_ENABLED:
    try:
        from langfuse.decorators import observe
        from langfuse import Langfuse

        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY
        )
        langfuse_handler = langfuse
    except Exception as e:
        print(f"⚠️  Langfuse 연결 실패: {e}")
        langfuse_handler = None

# [1-4] 기본 RAG 프롬프트 (Langfuse 연결 실패 시 사용)
DEFAULT_PROMPT_TEMPLATE = """다음 규정 문서를 읽고 질문에 답해주세요.

규정:
{documents}

질문: {question}

규칙:
- 문서에 있는 내용으로만 답하세요
- 문서에 없는 내용이면 "규정에 없는 내용입니다"라고만 답하세요
- 간결하게 답하세요
"""

# [1-4] 프로그램 시작 시 한 번만 임베딩 (캐싱)
_vector_store = None
_prompt_cache = None


def get_prompt(label=None):
    """Langfuse에서 프롬프트 가져오기 (또는 기본값 사용)

    Args:
        label: Langfuse 프롬프트 라벨 (기본: "production")

    Returns:
        (prompt_template, prompt_version): PromptTemplate과 버전 정보
    """
    # 캐시 사용 (label이 없을 때만)
    global _prompt_cache
    if _prompt_cache is not None and label is None:
        return _prompt_cache

    prompt_version = "default"
    prompt_template = DEFAULT_PROMPT_TEMPLATE
    prompt_label = label or "production"

    # Langfuse에서 프롬프트 가져오기
    if langfuse_handler:
        try:
            langfuse_prompt = langfuse_handler.get_prompt(
                name="hanabot-rag",
                label=prompt_label
            )
            if langfuse_prompt and langfuse_prompt.prompt:
                prompt_template = langfuse_prompt.prompt
                prompt_version = f"v{langfuse_prompt.version}"
        except Exception as e:
            # 연결 실패 시 기본 프롬프트 사용
            pass

    # 프롬프트 캐시 저장 (label이 없을 때만)
    prompt_obj = PromptTemplate(
        input_variables=["documents", "question"],
        template=prompt_template
    )

    if label is None:
        _prompt_cache = (prompt_obj, prompt_version)

    return (prompt_obj, prompt_version)

def get_vector_store():
    """벡터 저장소 조회 (캐싱된 버전 사용)"""
    global _vector_store
    if _vector_store is None:
        _vector_store = load_rag_docs()
    return _vector_store


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


def answer_question(question, model=None, label=None):
    """질문에 답변 (RAG 사용)

    Args:
        question: 질문 텍스트
        model: 사용할 모델 이름 (기본: config.CHAT_MODEL)
    """
    # [1-4] Langfuse 추적 시작
    trace = None
    prompt_version = "default"
    if langfuse_handler:
        try:
            # 프롬프트 버전 미리 확인
            _, prompt_version = get_prompt()

            trace = langfuse_handler.trace(
                name="hanabot-rag",
                input={"question": question},
                metadata={"prompt_version": prompt_version}
            )
        except Exception:
            pass

    try:
        # 벡터 저장소 로드 (캐싱된 버전)
        vector_store = get_vector_store()

        # LLM 초기화
        model_name = model or CHAT_MODEL
        llm = OllamaLLM(model=model_name, base_url=OLLAMA_BASE_URL)

        # [1-4] Retrieve 단계
        retrieve_start = time.time()
        results = vector_store.similarity_search_with_score(question, k=3)
        retrieve_time = time.time() - retrieve_start

        # 조각 정보 추출
        retrieved_docs = [
            {
                "title": doc.metadata.get('title', ''),
                "score": score
            }
            for doc, score in results
        ]

        if trace:
            try:
                trace.span(
                    name="retrieve",
                    input={"question": question},
                    output={
                        "documents": retrieved_docs,
                        "count": len(results)
                    },
                    duration=int(retrieve_time * 1000)
                )
            except Exception:
                pass

        # 문서 준비
        doc_text = "\n\n".join([
            f"{doc.metadata.get('title', '')}\n{doc.page_content}"
            for doc, score in results
        ])

        # [1-4] Langfuse 프롬프트 가져오기 (또는 기본값)
        prompt, prompt_version = get_prompt(label=label)

        # [1-4] Generate 단계
        generate_start = time.time()
        chain = prompt | llm | StrOutputParser()
        response = chain.invoke({
            "documents": doc_text,
            "question": question
        })
        generate_time = time.time() - generate_start

        if trace:
            try:
                trace.span(
                    name="generate",
                    input={"model": model_name, "prompt_version": prompt_version},
                    output={
                        "answer": response.strip(),
                        "model": model_name,
                        "prompt_version": prompt_version
                    },
                    duration=int(generate_time * 1000)
                )
            except Exception:
                pass

        # 근거 추출
        sources = [doc.metadata.get('title', '') for doc, score in results]

        return response.strip(), sources

    finally:
        # [1-4] Trace 종료
        if trace:
            try:
                trace.set_outcome({"success": True})
            except Exception:
                pass


def answer_question_no_rag(question, model=None):
    """질문에 답변 (RAG 없음)

    Args:
        question: 질문 텍스트
        model: 사용할 모델 이름 (기본: config.CHAT_MODEL)
    """
    model_name = model or CHAT_MODEL
    llm = OllamaLLM(model=model_name, base_url=OLLAMA_BASE_URL)
    return llm.invoke(question).strip()
