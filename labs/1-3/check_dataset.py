# [1-3] 파인튜닝 데이터셋 품질 검사
import sys
import os
import json
import re
import random
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 데이터 로드
data_dir = Path(__file__).parent.parent / "finetune"
train_path = data_dir / "hanabot_train.jsonl"
eval_path = data_dir / "hanabot_eval.jsonl"

train_data = []
eval_data = []

with open(train_path, "r", encoding="utf-8") as f:
    for line in f:
        train_data.append(json.loads(line))

with open(eval_path, "r", encoding="utf-8") as f:
    for line in f:
        eval_data.append(json.loads(line))

# RAG_PLAN.md 로드 (숫자 검증용)
rag_plan_path = Path(__file__).parent.parent.parent / "data" / "RAG_PLAN.md"
with open(rag_plan_path, "r", encoding="utf-8") as f:
    rag_content = f.read()

# 검증 함수
def check_format(text):
    """형식 검사: 3가지 규칙"""
    rules = {
        "시작": text.startswith("[하나봇]"),
        "항목": "- " in text,
        "끝": "문의해 주세요." in text
    }
    return rules

def check_numbers(text, rag_content):
    """숫자가 RAG_PLAN.md에 있는지 검사"""
    # 숫자 추출
    numbers = re.findall(r'\d+', text)
    missing = []

    for num in numbers:
        if num not in rag_content:
            missing.append(num)

    return missing

# 검증 실행
print("=" * 100)
print("데이터셋 품질 검사")
print("=" * 100)
print()

all_data = train_data + eval_data
all_conversations = []

for item in all_data:
    conv = item["conversations"]
    user_msg = conv[0]["content"]
    assistant_msg = conv[1]["content"]

    all_conversations.append({
        "question": user_msg,
        "answer": assistant_msg,
        "format": check_format(assistant_msg),
        "missing_numbers": check_numbers(assistant_msg, rag_content)
    })

# 통계 계산
rule_start = sum(1 for c in all_conversations if c["format"]["시작"])
rule_items = sum(1 for c in all_conversations if c["format"]["항목"])
rule_end = sum(1 for c in all_conversations if c["format"]["끝"])
all_pass = sum(1 for c in all_conversations if all(c["format"].values()))

# 중복 질문
all_questions = [c["question"] for c in all_conversations]
duplicates = len(all_questions) - len(set(all_questions))

# 숫자 검증 실패
number_issues = [c for c in all_conversations if c["missing_numbers"]]

# 결과 표
print("📊 형식 검사 (규칙별 통과 수)")
print("-" * 100)
print(f"총 대화: {len(all_conversations)}개")
print(f"  ✓ [하나봇] 시작: {rule_start}/{len(all_conversations)}")
print(f"  ✓ \"- \" 항목: {rule_items}/{len(all_conversations)}")
print(f"  ✓ \"문의해 주세요.\" 끝: {rule_end}/{len(all_conversations)}")
print(f"  ✓ 모두 통과: {all_pass}/{len(all_conversations)}")
print()

print("📋 중복 검사")
print("-" * 100)
print(f"중복 질문: {duplicates}개")
print()

print("🔢 숫자 검증 (RAG_PLAN.md 확인)")
print("-" * 100)
print(f"숫자 검증 실패: {len(number_issues)}개")
if number_issues:
    for item in number_issues[:3]:  # 처음 3개만 보여주기
        print(f"  Q: {item['question'][:40]}...")
        print(f"  문제 숫자: {item['missing_numbers']}")
        print(f"  A: {item['answer'][:60]}...")
        print()
print()

# 무작위 표본 5개
print("=" * 100)
print("무작위 표본 (5개)")
print("=" * 100)
print()

samples = random.sample(all_conversations, min(5, len(all_conversations)))
for i, item in enumerate(samples, 1):
    status = "✓" if all(item["format"].values()) else "⚠️"
    print(f"{status} [표본 {i}]")
    print(f"Q: {item['question']}")
    print(f"A: {item['answer']}")
    print()

# 최종 결과
print("=" * 100)
print("✅ 검사 완료")
print("=" * 100)
print(f"학습 데이터: {len(train_data)}개")
print(f"평가 데이터: {len(eval_data)}개")
print(f"형식 통과: {all_pass}/{len(all_conversations)} ({100*all_pass//len(all_conversations)}%)")
print(f"중복: {duplicates}개")
print(f"숫자 오류: {len(number_issues)}개")
