#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-4] CrewAI 테스트 실행 (Ollama 필요)

import sys
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from crew_hana import run_crew as run_crew_sequential
from crew_hierarchical import run_crew_hierarchical

TEST_QUESTIONS = [
    "실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘",
    "기초반 3개월 재수강 가격은?",
    "환불은 개강 전에 취소하면 얼마 돌려받아?",
]

def simple_validate(question: str, answer: str) -> bool:
    """간단한 답변 검증"""
    answer_lower = answer.lower()

    if "2개월" in question or "친구" in question:
        return "90" in answer or "900" in answer
    elif "3개월" in question or "재수강" in question:
        return "45" in answer or "450" in answer
    elif "개강 전" in question:
        return "전액" in answer or "100" in answer

    return False

results = {
    "sequential": [],
    "hierarchical": [],
}

print("=" * 80)
print("[5-4] CrewAI 테스트 실행")
print("=" * 80)
print()

for idx, question in enumerate(TEST_QUESTIONS, 1):
    print(f"\n질문 {idx}: {question}")
    print("-" * 80)

    # Sequential
    try:
        start = time.time()
        ans = run_crew_sequential(question)
        elapsed = time.time() - start
        is_correct = simple_validate(question, ans)
        results["sequential"].append({
            "question": question,
            "time": round(elapsed, 2),
            "correct": is_correct
        })
        print(f"Sequential: {elapsed:.2f}초 - {'✓' if is_correct else '✗'}")
    except Exception as e:
        results["sequential"].append({
            "question": question,
            "time": 0,
            "correct": False,
            "error": str(e)[:50]
        })
        print(f"Sequential: 오류 - {str(e)[:50]}")

    # Hierarchical
    try:
        start = time.time()
        ans = run_crew_hierarchical(question)
        elapsed = time.time() - start
        is_correct = simple_validate(question, ans)
        results["hierarchical"].append({
            "question": question,
            "time": round(elapsed, 2),
            "correct": is_correct
        })
        print(f"Hierarchical: {elapsed:.2f}초 - {'✓' if is_correct else '✗'}")
    except Exception as e:
        results["hierarchical"].append({
            "question": question,
            "time": 0,
            "correct": False,
            "error": str(e)[:50]
        })
        print(f"Hierarchical: 오류 - {str(e)[:50]}")

# 결과 저장
with open("test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 80)
print("결과 저장됨: test_results.json")

# 통계
seq_times = [r["time"] for r in results["sequential"]]
hier_times = [r["time"] for r in results["hierarchical"]]
seq_correct = sum(1 for r in results["sequential"] if r["correct"])
hier_correct = sum(1 for r in results["hierarchical"] if r["correct"])

print(f"\nSequential: {sum(seq_times)/3:.2f}초 | {seq_correct}/3 정답")
print(f"Hierarchical: {sum(hier_times)/3:.2f}초 | {hier_correct}/3 정답")
