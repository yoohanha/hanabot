#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-6] LLM 팩토리: .env 에서 모델 서버를 선택해 끼우기
# LLM_BACKEND=ollama (기본) | openai (OpenAI 호환 · vLLM · 사내 서버)

import os
import sys
from pathlib import Path
from typing import Any, Union

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()


def create_llm(**kwargs) -> Union[ChatOllama, ChatOpenAI]:
    """[5-6] 백엔드 선택해서 LLM 객체 생성 (.env 환경변수로 제어)

    환경변수:
    - LLM_BACKEND: "ollama" (기본) | "openai"
    - 올라마: OLLAMA_BASE_URL, CHAT_MODEL
    - OpenAI 호환: LLM_BASE_URL (/v1 붙임), LLM_API_KEY (없으면 ""), CHAT_MODEL

    예시:
      ollama: ollama.create_llm(temperature=0, format="json")
      OpenAI: llm.create_llm(temperature=0, max_tokens=512)
    """
    backend = os.getenv("LLM_BACKEND", "ollama").lower()

    if backend == "openai":
        base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"

        api_key = os.getenv("LLM_API_KEY", "")
        model = os.getenv("CHAT_MODEL", "llama3.1")

        print(f"📡 LLM: OpenAI 호환 ({base_url})")
        return ChatOpenAI(
            api_key=api_key or "not-needed",
            base_url=base_url,
            model=model,
            **kwargs
        )

    # 기본: ollama
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("CHAT_MODEL", "llama3.1")

    print(f"📡 LLM: Ollama ({base_url})")
    return ChatOllama(
        base_url=base_url,
        model=model,
        **kwargs
    )


if __name__ == "__main__":
    # [5-6] 테스트: Ollama 의 OpenAI 호환 주소(http://localhost:11434/v1) 로 비교
    # 같은 질문 3개를 두 방식으로 → [방식 · 답 · 걸린 시간] 표

    import time
    import json
    from langchain_core.messages import HumanMessage

    questions = [
        "안녕하세요. 간단히 소개해 주세요.",
        "오늘은 몇 월 며칠입니까?",
        "1+1은 몇입니까?"
    ]

    results = []

    # === Ollama 테스트 ===
    print("\n🧪 테스트 1: Ollama (기본)")
    print("=" * 60)
    for i, q in enumerate(questions, 1):
        os.environ["LLM_BACKEND"] = "ollama"
        llm = create_llm(temperature=0)

        start = time.time()
        resp = llm.invoke([HumanMessage(content=q)])
        elapsed = time.time() - start

        answer = resp.content[:50] if resp.content else "(답변 없음)"
        results.append({
            "방식": "Ollama",
            "질문": f"Q{i}",
            "답": answer,
            "시간(초)": f"{elapsed:.2f}"
        })
        print(f"Q{i}: {answer}")
        print(f"   ⏱️  {elapsed:.2f}초\n")

    # === OpenAI 호환 (Ollama /v1) 테스트 ===
    print("\n🧪 테스트 2: OpenAI 호환 (Ollama /v1)")
    print("=" * 60)
    os.environ["LLM_BACKEND"] = "openai"
    os.environ["LLM_BASE_URL"] = "http://localhost:11434/v1"
    os.environ["LLM_API_KEY"] = ""

    for i, q in enumerate(questions, 1):
        llm = create_llm(temperature=0)

        start = time.time()
        resp = llm.invoke([HumanMessage(content=q)])
        elapsed = time.time() - start

        answer = resp.content[:50] if resp.content else "(답변 없음)"
        results.append({
            "방식": "OpenAI호환",
            "질문": f"Q{i}",
            "답": answer,
            "시간(초)": f"{elapsed:.2f}"
        })
        print(f"Q{i}: {answer}")
        print(f"   ⏱️  {elapsed:.2f}초\n")

    # === 결과 표 ===
    print("\n📊 비교 표")
    print("=" * 80)
    print(f"{'방식':<12} {'질문':<8} {'답':<45} {'시간(초)':<8}")
    print("-" * 80)
    for r in results:
        print(f"{r['방식']:<12} {r['질문']:<8} {r['답']:<45} {r['시간(초)']:<8}")
