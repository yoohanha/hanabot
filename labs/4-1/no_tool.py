#!/usr/bin/env python3
# [4-1] 도구 없이 llama3.1 질의 (3개 질문 답변 평가)

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
import requests


def ask_llama(question: str) -> str:
    """llama3.1에 질문하고 답변 받기"""
    url = f"{OLLAMA_BASE_URL}/api/generate"

    payload = {
        "model": CHAT_MODEL,
        "prompt": question,
        "stream": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as e:
        return f"오류: {str(e)}"


def evaluate_answer(question: str, answer: str, question_type: str) -> tuple[bool, str]:
    """
    답변 평가
    Returns: (맞음 여부, 이유)
    """
    if question_type == "date":
        # Q1: 오늘 몇 월 며칠이야?
        today = datetime.now()
        expected_month = today.month
        expected_day = today.day

        if str(expected_month) in answer and str(expected_day) in answer:
            return True, "정답"
        else:
            return False, "모름"

    elif question_type == "price":
        # Q2: 실무반 3개월에 친구 할인 받으면 얼마야?
        # 가상 학원 데이터이므로 LLM이 정확히 모를 가능성 높음
        if "모르" in answer or "알 수 없" in answer or "정보" not in answer:
            return False, "모름"
        elif any(char.isdigit() for char in answer):
            # 숫자가 있으면 추측하는 것 (검증 불가)
            return False, "추측/검증 불가"
        else:
            return False, "모름"

    elif question_type == "booking":
        # Q3: 내일 오후 2시에 GPU PC 2시간 예약해줘
        # 도구 없으므로 실행 불가
        if "예약" in answer or "완료" in answer:
            # 실제로 예약했다고 말하면 거짓
            return False, "실행 불가 (도구 없음)"
        else:
            # 도구가 없다고 인정하면 그나마 정직
            return False, "실행 불가 (도구 없음)"

    return False, "알 수 없음"


def main():
    print(f"🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    questions = [
        ("오늘 몇 월 며칠이야?", "date"),
        ("실무반 3개월에 친구 할인 받으면 얼마야?", "price"),
        ("내일 오후 2시에 GPU PC 2시간 예약해줘", "booking"),
    ]

    results = []

    for idx, (question, q_type) in enumerate(questions, 1):
        print(f"[질문 {idx}] {question}")
        answer = ask_llama(question)
        print(f"[답변] {answer[:100]}{'...' if len(answer) > 100 else ''}\n")

        is_correct, reason = evaluate_answer(question, answer, q_type)
        results.append({
            "질문": question,
            "답변": answer[:80] + ("..." if len(answer) > 80 else ""),
            "결과": "✅ 맞음" if is_correct else "❌ 틀림",
            "이유": reason
        })

    # 표 출력
    print("\n" + "="*100)
    print("📊 평가 결과")
    print("="*100)

    headers = ["#", "질문", "결과", "이유"]
    print(f"{headers[0]:<2} | {headers[1]:<40} | {headers[2]:<8} | {headers[3]:<20}")
    print("-"*100)

    for idx, result in enumerate(results, 1):
        print(f"{idx:<2} | {result['질문']:<40} | {result['결과']:<8} | {result['이유']:<20}")

    print("="*100)

    # 상세 결과
    print("\n📝 상세 답변")
    print("-"*100)
    for idx, result in enumerate(results, 1):
        print(f"\n[{idx}] {result['질문']}")
        print(f"    답변: {result['답변']}")
        print(f"    평가: {result['결과']} - {result['이유']}")


if __name__ == "__main__":
    main()
