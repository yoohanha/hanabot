#!/usr/bin/env python3
# [5-2] 빠른 테스트: 1개 질문만 3가지 방식으로 비교

import os
import sys
import time
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


def create_llm():
    """LLM 생성"""
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        num_ctx=8192,
        num_predict=512,
        timeout=120
    )
    return llm


def method_a(question: str) -> tuple:
    """A 방식: 한 번에 답"""
    llm = create_llm()
    start = time.time()
    response = llm.invoke([HumanMessage(content=question)])
    elapsed = time.time() - start
    return response.content.strip(), elapsed


def method_b(question: str) -> tuple:
    """B 방식: 계획+실행"""
    llm = create_llm()
    start = time.time()

    plan_response = llm.invoke([HumanMessage(content=f"질문: {question}\n응답: 단계로 계획만")])
    exec_response = llm.invoke([HumanMessage(content=f"질문: {question}\n위 계획에 따라 답변하세요.")])

    elapsed = time.time() - start
    return exec_response.content.strip(), elapsed


def method_c(question: str) -> tuple:
    """C 방식: 계획+실행+검토"""
    llm = create_llm()
    start = time.time()

    plan_response = llm.invoke([HumanMessage(content=f"질문: {question}\n응답: 단계로 계획만")])
    exec_response = llm.invoke([HumanMessage(content=f"질문: {question}\n위 계획에 따라 답변하세요.")])
    review_response = llm.invoke([HumanMessage(content=f"답변: {exec_response.content}\n이 답변이 정확한가?")])

    elapsed = time.time() - start
    return exec_response.content.strip(), elapsed


def main():
    print(f"🤖 모델: {CHAT_MODEL}")
    print(f"📡 Ollama: {OLLAMA_BASE_URL}\n")

    question = "지각 3번이면 어떻게 되나?"
    answer_key = "지각 3회는 결석 1회로 처리"

    print(f"[질문] {question}\n")
    print(f"[정답] {answer_key}\n")

    # A 방식
    print("⏳ A 방식 (한 번에 답)...")
    a_ans, a_time = method_a(question)
    print(f"✅ A. {a_ans[:50]}... ({a_time:.1f}초)\n")

    # B 방식
    print("⏳ B 방식 (계획+실행)...")
    b_ans, b_time = method_b(question)
    print(f"✅ B. {b_ans[:50]}... ({b_time:.1f}초)\n")

    # C 방식
    print("⏳ C 방식 (계획+실행+검토)...")
    c_ans, c_time = method_c(question)
    print(f"✅ C. {c_ans[:50]}... ({c_time:.1f}초)\n")

    print(f"합계: A={a_time:.1f}초 | B={b_time:.1f}초 | C={c_time:.1f}초")


if __name__ == "__main__":
    main()
