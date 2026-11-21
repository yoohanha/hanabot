#!/usr/bin/env python3
# [4-1] LangChain @tool과 bind_tools를 사용한 에이전트

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
from web.services import calc_fee

# LangChain 임포트
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


# ============================================================================
# 도구 정의 (Tools with Korean docstrings)
# ============================================================================

@tool
def get_today() -> str:
    """
    오늘의 날짜와 요일을 반환합니다.

    에이전트가 현재 날짜를 알아야 할 때 사용합니다.
    예: "오늘 몇 월 며칠이야?" 같은 질문에 대답할 때

    Returns:
        str: "2026년 11월 21일 (금)" 형식의 날짜 문자열
    """
    today = datetime.now()
    days = ["월", "화", "수", "목", "금", "토", "일"]
    weekday = days[today.weekday()]
    return f"{today.year}년 {today.month}월 {today.day}일 ({weekday})"


@tool
def calculate_course_fee(course: str, months: int, discount_type: str = "없음") -> str:
    """
    수강료를 계산하고 반환합니다.

    에이전트가 과정별 가격을 계산해야 할 때 사용합니다.
    예: "실무반 3개월에 친구 할인 받으면 얼마야?" 같은 질문에 대답할 때

    Args:
        course: 과정 이름 ("기초반" 또는 "실무반")
        months: 개월 수 (정수)
        discount_type: 할인 종류 ("없음", "재수강", "친구")

    Returns:
        str: 금액 계산 결과 (원)
    """
    try:
        result = calc_fee(course, months, discount_type)
        if 'error' in result:
            return f"오류: {result['error']}"
        return result.get('message', '')
    except Exception as e:
        return f"계산 실패: {str(e)}"


# ============================================================================
# 에이전트 초기화
# ============================================================================

def create_agent_with_tools():
    """도구와 함께 LLM 초기화"""
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )

    # 도구 바인딩
    tools = [get_today, calculate_course_fee]
    llm_with_tools = llm.bind_tools(tools)

    return llm_with_tools, tools


# ============================================================================
# 에이전트 실행
# ============================================================================

def run_agent_question(llm_with_tools, question: str, question_num: int) -> dict:
    """
    에이전트로 질문 실행

    Returns:
        dict: {'question', 'tools_used', 'final_answer'}
    """
    print(f"\n{'='*80}")
    print(f"[질문 {question_num}] {question}")
    print('='*80)

    # 1. 에이전트에 질문 전송
    print(f"\n📝 [질문 전송]")

    response = llm_with_tools.invoke([HumanMessage(content=question)])

    # 2. 응답 분석
    print(f"\n🤔 [LLM 응답 분석]")
    tools_called = []

    # tool_calls가 있는지 확인
    if hasattr(response, 'tool_calls') and response.tool_calls:
        for tool_call in response.tool_calls:
            tool_name = tool_call.get('name', '알 수 없음')
            tool_args = tool_call.get('args', {})
            tools_called.append({
                'name': tool_name,
                'args': tool_args
            })
            print(f"   • 도구: {tool_name}")
            print(f"   • 인자: {tool_args}")

    # 3. 최종 답변 추출
    print(f"\n💬 [최종 답변]")
    final_answer = response.content if hasattr(response, 'content') else str(response)
    print(f"   {final_answer[:200]}")

    return {
        'question': question,
        'tools_used': tools_called,
        'final_answer': final_answer
    }


# ============================================================================
# 도구 없이 실행 (비교용)
# ============================================================================

def run_without_tools(question: str, question_num: int) -> str:
    """도구 없이 LLM에 질문"""
    print(f"\n{'='*80}")
    print(f"[질문 {question_num} - 도구 없음] {question}")
    print('='*80)

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )

    try:
        response = llm.invoke([HumanMessage(content=question)])
        answer = response.content if hasattr(response, 'content') else str(response)
        print(f"\n💬 [답변]\n   {answer[:200]}")
        return answer
    except Exception as e:
        error_msg = f"오류: {str(e)}"
        print(f"\n❌ {error_msg}")
        return error_msg


# ============================================================================
# 비교표 작성
# ============================================================================

def print_comparison_table(results_with_tools: list, results_without_tools: list):
    """도구 사용 여부 비교표"""
    print(f"\n\n{'='*100}")
    print("📊 도구 사용 여부 비교")
    print('='*100)

    headers = ["질문", "도구 사용", "도구 종류", "도구 결과", "최종 답변"]
    print(f"\n{'질문':<40} | {'도구 사용':<10} | {'도구 종류':<15} | {'결과':<50}")
    print("-"*130)

    for idx, (with_tools, without_tools) in enumerate(zip(results_with_tools, results_without_tools), 1):
        question = with_tools['question']

        # 도구 사용 여부
        if with_tools['tools_used']:
            tool_names = ", ".join([t['name'] for t in with_tools['tools_used']])
            tools_used = "✅ 사용"
        else:
            tool_names = "없음"
            tools_used = "❌ 미사용"

        # 답변 길이 제한
        answer = with_tools['final_answer'][:40] + "..." if len(with_tools['final_answer']) > 40 else with_tools['final_answer']

        print(f"{idx}. {question:<37} | {tools_used:<10} | {tool_names:<15} | {answer:<50}")

    print("="*130)


# ============================================================================
# 메인
# ============================================================================

def main():
    print(f"🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    # 도구 초기화
    llm_with_tools, tools = create_agent_with_tools()

    # 질문 목록 (도구 필요한 질문들)
    questions = [
        "오늘 몇 월 며칠이야?",
        "실무반 3개월에 친구 할인 받으면 얼마야?",
    ]

    results_with_tools = []
    results_without_tools = []

    # ========== 1. 도구 사용하여 실행 ==========
    print(f"\n\n{'#'*80}")
    print("# 1단계: 도구와 함께 실행 (Tool-Augmented)")
    print(f"{'#'*80}\n")

    for idx, question in enumerate(questions, 1):
        try:
            result = run_agent_question(llm_with_tools, question, idx)
            results_with_tools.append(result)
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            results_with_tools.append({
                'question': question,
                'tools_used': [],
                'final_answer': f"오류: {str(e)}"
            })

    # ========== 2. 도구 없이 실행 (비교용) ==========
    print(f"\n\n{'#'*80}")
    print("# 2단계: 도구 없이 실행 (Without Tools)")
    print(f"{'#'*80}\n")

    for idx, question in enumerate(questions, 1):
        try:
            answer = run_without_tools(question, idx)
            results_without_tools.append(answer)
        except Exception as e:
            results_without_tools.append(f"오류: {str(e)}")

    # ========== 3. 비교표 ==========
    print_comparison_table(results_with_tools, results_without_tools)


if __name__ == "__main__":
    main()
