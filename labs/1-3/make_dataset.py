# [1-3] 파인튜닝 학습 데이터 생성
import sys
import os
import json
import random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_ollama import OllamaLLM
from hanabot.config import CHAT_MODEL, OLLAMA_BASE_URL

# RAG_PLAN.md 읽기 및 조각 추출
rag_plan_path = Path(__file__).parent.parent.parent / "data" / "RAG_PLAN.md"
with open(rag_plan_path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "<!-- RAG_DOCS_START -->"
end_marker = "<!-- RAG_DOCS_END -->"
start_idx = content.find(start_marker)
end_idx = content.find(end_marker)
rag_docs = content[start_idx + len(start_marker):end_idx].strip()

# ## 기준으로 조각 나누기
headers_to_split_on = [("##", "h2")]
splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
chunks = splitter.split_text(rag_docs)

print("=" * 80)
print(f"데이터셋 생성 중... ({len(chunks)}개 조각)")
print("=" * 80)
print()

# LLM 초기화
llm = OllamaLLM(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL)

# 학습 데이터 생성
conversations = []

# 1. RAG_DOCS 조각별 데이터 생성
for i, chunk in enumerate(chunks, 1):
    section_title = chunk.metadata.get("h2", "")
    answer_text = chunk.page_content.strip()

    # 간단한 질문들 직접 생성 (LLM 호출 최소화)
    # 같은 의미의 질문 변형들
    questions = [
        f"{section_title}이 뭐예요?",
        f"{section_title}은 뭔가요?",
        f"{section_title}에 대해 알려줄래?",
        f"{section_title} 설명해 줄 수 있어?",
        f"{section_title}는?",
        f"{section_title} 어떻게 되는 거야?",
        f"{section_title}에 대해서",
        f"{section_title}를 알고 싶은데",
        f"{section_title}은 어떻게 되는 거예요?",
    ]

    # STYLE.md 형식으로 변환
    lines = answer_text.split("\n")
    sentences = [l.strip() for l in lines if l.strip()][:3]  # 최대 3개

    style_answer = "[하나봇]\n"
    for sentence in sentences:
        style_answer += f"- {sentence}\n"
    style_answer += "자세한 내용은 학원 데스크로 문의해 주세요."

    # 각 질문에 대해 대화 추가
    for question in questions:
        conversations.append({
            "conversations": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": style_answer}
            ]
        })

    print(f"✓ 조각 {i}/{len(chunks)}: {section_title} ({len(questions)}개 질문)")

print()

# 2. 규정에 없는 질문 30개 추가 (거절 예시)
rejection_questions = [
    "점심 메뉴 뭐야?",
    "강사 연락처 알려줘",
    "와이파이 비밀번호 뭐야?",
    "컴퓨터 비밀번호 초기화해줄 수 있어?",
    "택시비 얼마야?",
    "커피 맛있는데 뭐 쓰는 거야?",
    "주변 맛있는 식당 추천해줄래?",
    "내일 날씨 어때?",
    "주식 투자 조언 좀 해줄래?",
    "숙제 답 알려줄래?",
    "시험 출제자 이름이 뭐야?",
    "다른 학생 연락처 주면 안 될까?",
    "강의 영상 녹화해서 올려줄 수 있어?",
    "환불은 정말 안 돼?",
    "규정 무시해도 되나?",
    "지각 기록 지워줄 수 있어?",
    "결석 증명서 구매할 수 있어?",
    "시험 일찍 보게 해줄 수 있어?",
    "과제 제출 기한 연장 가능해?",
    "다른 사람 계정으로 출석 체크해줄 수 있어?",
    "실습실 비용 반값으로 줄 수 없을까?",
    "숙박 시설 있어?",
    "식사 제공해?",
    "부모님 소개 받고 싶은데 가능해?",
    "직업 소개 받을 수 있어?",
    "대출 기관 소개해줄 수 있어?",
    "보증금 없이 계약 가능해?",
    "계약금 환불 가능해?",
    "다른 과정도 무료로 들을 수 있어?",
    "친구 소개하면 보너스 주나?",
]

rejection_response = "규정에 없는 내용입니다."

for question in rejection_questions:
    conversations.append({
        "conversations": [
            {"role": "user", "content": question},
            {"role": "assistant", "content": rejection_response}
        ]
    })

print(f"✓ 거절 예시: {len(rejection_questions)}개 추가")
print()

# 3. 데이터 섞기 및 9:1 분할
random.shuffle(conversations)
split_idx = int(len(conversations) * 0.9)

train_data = conversations[:split_idx]
eval_data = conversations[split_idx:]

# 4. JSONL 저장
output_dir = Path(__file__).parent.parent / "finetune"
output_dir.mkdir(exist_ok=True)

train_path = output_dir / "hanabot_train.jsonl"
eval_path = output_dir / "hanabot_eval.jsonl"

with open(train_path, "w", encoding="utf-8") as f:
    for item in train_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

with open(eval_path, "w", encoding="utf-8") as f:
    for item in eval_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("=" * 80)
print("데이터셋 저장 완료")
print("=" * 80)
print(f"학습 데이터: {len(train_data)}개 ({train_path})")
print(f"평가 데이터: {len(eval_data)}개 ({eval_path})")
print(f"총: {len(conversations)}개")
print()

# 예시 3개 출력
print("=" * 80)
print("예시 (3개)")
print("=" * 80)
for i, item in enumerate(conversations[:3], 1):
    conv = item["conversations"]
    print(f"\n[예시 {i}]")
    print(f"Q: {conv[0]['content'][:60]}...")
    print(f"A: {conv[1]['content'][:60]}...")
