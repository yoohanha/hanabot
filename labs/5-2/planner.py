#!/usr/bin/env python3
# [5-2] LangGraph 플래너 · 단계 계획 생성

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Any

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [5-2] 4-1 도구 import
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


# ============================================================================
# 도구 경로 및 도구 목록
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# [5-2] 사용 가능한 도구
AVAILABLE_TOOLS = ["get_today", "search_rules", "calc_fee", "reserve_gpu"]


# ============================================================================
# LLM 초기화
# ============================================================================

def create_planner_llm():
    """LLM 초기화 (5-2 플래너용)"""
    today = datetime.now().strftime("%Y년 %m월 %d일")

    system_message = f"""당신은 하나봇 AI 플래너입니다.
오늘 날짜: {today}
역할: 사용자의 질문을 단계별 계획으로 변환합니다.

사용 가능한 도구:
- get_today: 오늘 날짜 조회
- search_rules: 규정 검색
- calc_fee: 수강료 계산
- reserve_gpu: GPU PC 예약

계획 수립 규칙:
1. 질문을 분석하여 필요한 도구 단계를 파악합니다
2. 날짜가 필요하면 첫 번째 단계는 반드시 get_today입니다
3. 각 단계마다 do(수행내용)와 tool(도구)을 명시합니다
4. JSON 배열 형식으로 반환합니다

응답은 반드시 다음 형식이어야 합니다:
[
  {{"step": 1, "do": "...", "tool": "도구명"}},
  {{"step": 2, "do": "...", "tool": "도구명"}}
]

중요: JSON 배열만 반환하세요. 다른 텍스트는 없습니다."""

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        num_ctx=8192,
        num_predict=512,
        timeout=120
    )

    return llm, system_message


# ============================================================================
# 플래너 노드
# ============================================================================

def planner_node(question: str, max_retries: int = 2) -> dict:
    """
    질문을 단계 계획으로 변환

    Returns:
        dict: {"success": bool, "steps": list, "error": str}
    """
    llm, system_msg = create_planner_llm()

    prompt = f"""질문: {question}

이 질문을 실행 단계로 계획해주세요. JSON 형식으로만 응답합니다."""

    for attempt in range(1, max_retries + 1):
        try:
            # [5-2] LLM 호출
            response = llm.invoke([HumanMessage(content=prompt)])
            response_text = response.content.strip()

            # [5-2] JSON 파싱 시도
            try:
                plan = json.loads(response_text)

                # 형식 검증
                if "steps" not in plan:
                    plan = {"steps": plan} if isinstance(plan, list) else plan

                if not isinstance(plan.get("steps", []), list):
                    raise ValueError("steps는 배열이어야 합니다")

                # [5-2] 날짜 필요 여부 확인
                has_date_keyword = any(
                    keyword in question
                    for keyword in ["내일", "오늘", "날짜", "며칠", "언제", "평일"]
                )

                if has_date_keyword and len(plan.get("steps", [])) > 0:
                    first_step = plan["steps"][0]
                    # [5-2] 첫 단계가 get_today가 아니면 추가
                    if first_step.get("tool") != "get_today":
                        plan["steps"].insert(0, {
                            "step": 1,
                            "do": "오늘 날짜 확인",
                            "tool": "get_today"
                        })
                        # 단계 번호 재정렬
                        for i, step in enumerate(plan["steps"], 1):
                            step["step"] = i

                return {
                    "success": True,
                    "steps": plan.get("steps", []),
                    "error": None
                }

            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    print(f"  ⚠️  [재시도 {attempt}] JSON 파싱 실패: {str(e)[:50]}")
                    continue
                else:
                    return {
                        "success": False,
                        "steps": [],
                        "error": "계획 실패: JSON 형식 오류"
                    }

        except Exception as e:
            return {
                "success": False,
                "steps": [],
                "error": f"계획 실패: {str(e)[:50]}"
            }

    return {
        "success": False,
        "steps": [],
        "error": "계획 실패: 최대 재시도 횟수 초과"
    }


# ============================================================================
# 테스트
# ============================================================================

def test_planner():
    """플래너 테스트"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    print(f"{'='*100}")
    print("[5-2] LangGraph 플래너 · 단계 계획 생성")
    print(f"{'='*100}\n")

    # 테스트 질문 3개
    test_questions = [
        "지각 3번이면 어떻게 되고, 기초반 1개월 수강료는 얼마야?",
        "실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘",
        "내일 오후 2시 GPU PC 1번 2시간 예약해줘"
    ]

    results = []

    for idx, question in enumerate(test_questions, 1):
        print(f"[질문 {idx}] {question}\n")

        # [5-2] 플래너 실행
        result = planner_node(question)

        if result["success"]:
            steps = result["steps"]
            print(f"  ✅ 계획 생성됨 ({len(steps)}단계):\n")

            for step in steps:
                step_num = step.get("step", "?")
                do = step.get("do", "?")
                tool = step.get("tool", "?")
                print(f"    [{step_num}] {do} → {tool}")

        else:
            print(f"  ❌ {result['error']}")

        results.append({
            "question": question,
            "success": result["success"],
            "steps": result["steps"],
            "error": result["error"]
        })

        print()

    # 결과 표
    print(f"{'='*100}")
    print("📊 계획 결과 (질문 · 단계 수 · 도구 순서)")
    print(f"{'='*100}\n")

    print("| # | 질문 | 단계 수 | 도구 순서 | 상태 |")
    print("|---|------|--------|---------|------|")

    for idx, result in enumerate(results, 1):
        question = result["question"][:40]
        step_count = len(result["steps"])

        if result["success"]:
            tools = " → ".join([s.get("tool", "?") for s in result["steps"]])
            status = "✅"
        else:
            tools = "-"
            status = "❌"

        print(f"| {idx} | {question:40} | {step_count} | {tools:30} | {status} |")

    # JSON 저장
    result_file = DATA_DIR / "planner_test.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 계획 결과 저장: {result_file}")


def main():
    """메인 함수"""
    test_planner()


if __name__ == "__main__":
    main()
