# [1-2] RAG 없음 vs RAG 비교 채점
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

# 질문과 정답 키워드
test_cases = [
    ("지각 몇 번이면 결석이야?", ["3회", "3번"]),
    ("수료하려면 출석률이 얼마나 돼야 해?", ["80%", "80"]),
    ("실무반 수강료는 얼마야?", ["50만", "50만 원"]),
    ("화요일 오후에는 뭘 배워?", ["RAG"]),
    ("GPU PC는 하루에 몇 시간 쓸 수 있어?", ["4시간", "4시간"]),
    ("몇 시까지 있어도 돼?", ["21:00", "21시"]),
    ("결석은 언제까지 알려야 해?", ["전날 18시", "18시"]),
    ("몇 번 빠지면 결석이야?", ["지각 3회", "조퇴 2회"]),
    ("할인 같이 받을 수 있어?", ["중복 안 됨", "중복"]),
]

# RAG 준비
rag_plan_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "RAG_PLAN.md")
with open(rag_plan_path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "<!-- RAG_DOCS_START -->"
end_marker = "<!-- RAG_DOCS_END -->"
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

rag_docs = content[start_idx + len(start_marker):end_idx].strip()

headers_to_split_on = [
    ("#", "h1"),
    ("##", "h2"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
chunks = splitter.split_text(rag_docs)

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

embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(documents)

# LLM 초기화
llm = OllamaLLM(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL)

# RAG 프롬프트
rag_prompt = PromptTemplate(
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

rag_chain = rag_prompt | llm | StrOutputParser()

# 답변 채점 함수
def check_answer(answer, keywords):
    answer_lower = answer.lower()
    for keyword in keywords:
        if keyword.lower() in answer_lower:
            return "O"
    return "X"

# 테스트 실행
print("=" * 100)
print("하나 AI 학원 규정 - RAG 없음 vs RAG 비교")
print("=" * 100)
print()

results = []

for i, (question, keywords) in enumerate(test_cases, 1):
    # RAG 없이
    answer_no_rag = llm.invoke(question)
    score_no_rag = check_answer(answer_no_rag, keywords)

    # RAG로
    retrieved = vector_store.similarity_search_with_score(question, k=3)
    doc_text = "\n\n".join([
        f"{doc.metadata.get('title', '')}\n{doc.page_content}"
        for doc, score in retrieved
    ])
    answer_rag = rag_chain.invoke({
        "documents": doc_text,
        "question": question
    })
    score_rag = check_answer(answer_rag, keywords)

    results.append((question, score_no_rag, score_rag))
    print(f"[{i}] {question}")
    print(f"    RAG 없이: {score_no_rag} - {answer_no_rag[:50].strip()}...")
    print(f"    RAG:     {score_rag} - {answer_rag[:50].strip()}...")
    print()

# 결과 표
print("=" * 100)
print("채점 결과")
print("=" * 100)
print()

print(f"{'질문':<35} {'RAG 없이':<10} {'RAG':<10}")
print("-" * 55)

no_rag_score = 0
rag_score = 0

for question, score_no_rag, score_rag in results:
    print(f"{question:<35} {score_no_rag:<10} {score_rag:<10}")
    if score_no_rag == "O":
        no_rag_score += 1
    if score_rag == "O":
        rag_score += 1

print("-" * 55)
print(f"{'합계':<35} {no_rag_score}/9{'':<5} {rag_score}/9")
print()

improvement = rag_score - no_rag_score
print(f"✓ 성능 개선: RAG 없이 {no_rag_score}/9 · RAG로 {rag_score}/9 (+{improvement}점)")
