#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-3] 역할 에이전트 (Specialized Agents with Tool Specialization)

import os
import sys
import time
import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [5-3] 도구 import (복사 금지)
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))
from hana_tools import get_today, search_rules, calculate_course_fee, reserve_gpu_pc

# [5-3] 4-4 가드 import
labs_4_4_path = Path(__file__).parent.parent / "4-4"
sys.path.insert(0, str(labs_4_4_path))
from guard_tool import ToolGuard

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
from langgraph.graph.message import add_messages


# ============================================================================
# State 정의
# ============================================================================

class AgentState(TypedDict):
    """에이전트 상태"""
    question: str                                      # 사용자 질문
    messages: Annotated[list, add_messages]          # 메시지 히스토리
    selected_tool: str                                # 선택된 도구
    result: str                                       # 실행 결과
    answer: str                                       # 최종 답변


# ============================================================================
# 데이터 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 역할 에이전트: Rules Agent (규정 검색)
# ============================================================================

class RulesAgent:
    """규정 검색 담당 에이전트"""

    def __init__(self):
        self.name = "Rules Agent"
        self.tools = {"search_rules": search_rules}
        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )

    def get_system_message(self) -> str:
        """[5-3] 시스템 메시지"""
        return """당신은 규정 검색 담당 에이전트입니다.

당신의 역할:
- 규정 문서에서 정보 검색 (search_rules 도구만 사용)
- 주차, 수업시간, 예약 등 규정 관련 질문에만 답변

중요 원칙:
- 내 담당이 아니면 '담당 아님' 이라고만 답변하세요
- 수강료 계산, 예약, 취소 등은 다른 에이전트 담당입니다
- 명확한 답변을 제공하세요"""

    def run(self, question: str) -> Dict[str, Any]:
        """[5-3] 에이전트 실행"""
        start_time = time.time()

        # LLM에 질문하고 도구 선택 판단
        prompt = f"""{self.get_system_message()}

사용자 질문: {question}

이 질문에 답할 수 있으면 search_rules 도구를 사용하세요.
담당이 아니면 '담당 아님' 이라고만 답하세요.

도구 사용 여부를 판단하고 답변하세요."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        answer = response.content.strip()

        # 도구 사용 여부 판단
        selected_tool = "search_rules" if "담당 아님" not in answer else "none"

        # 도구 실행
        result = ""
        if selected_tool == "search_rules":
            try:
                result = search_rules.invoke({"question": question})
                answer = f"검색 결과: {str(result)[:200]}"
            except Exception as e:
                answer = f"오류: {str(e)}"
                selected_tool = "error"

        elapsed_time = time.time() - start_time

        return {
            "tool": selected_tool,
            "result": result,
            "answer": answer,
            "time": elapsed_time
        }


# ============================================================================
# 역할 에이전트: Fee Agent (수강료 계산)
# ============================================================================

class FeeAgent:
    """수강료 계산 담당 에이전트"""

    def __init__(self):
        self.name = "Fee Agent"
        self.tools = {"calculate_course_fee": calculate_course_fee}
        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )

    def get_system_message(self) -> str:
        """[5-3] 시스템 메시지"""
        return """당신은 수강료 계산 담당 에이전트입니다.

당신의 역할:
- 수강료 계산 (calculate_course_fee 도구만 사용)
- 과정, 개월수, 할인 종류로 수강료 계산
- "기초반", "실무반", 개월수, "친구"/"재수강"/"없음" 할인

중요 원칙:
- 내 담당이 아니면 '담당 아님' 이라고만 답변하세요
- 규정 조회, 예약, 취소 등은 다른 에이전트 담당입니다
- 금액은 명확하게 제시하세요"""

    def run(self, question: str) -> Dict[str, Any]:
        """[5-3] 에이전트 실행"""
        start_time = time.time()

        # LLM에 질문하고 도구 선택 판단
        prompt = f"""{self.get_system_message()}

사용자 질문: {question}

이 질문이 수강료 계산이면 calculate_course_fee를 사용하세요.
담당이 아니면 '담당 아님' 이라고만 답하세요.

(예: "기초반 3개월 친구 할인" → course="기초반", months=3, discount_type="친구")"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        answer = response.content.strip()

        # 도구 사용 여부 판단
        selected_tool = "calculate_course_fee" if "담당 아님" not in answer else "none"

        # 도구 실행 (간단한 패턴 인식)
        result = ""
        if selected_tool == "calculate_course_fee":
            try:
                # 질문에서 과정, 개월, 할인 추출
                q_lower = question.lower()
                course = "실무반" if "실무반" in q_lower else "기초반" if "기초반" in q_lower else "기초반"
                months = 2 if "2개월" in q_lower else 1 if "1개월" in q_lower else 3
                discount_type = "친구" if "친구" in q_lower else "재수강" if "재수강" in q_lower else "없음"

                result = calculate_course_fee.invoke({
                    "course": course,
                    "months": months,
                    "discount_type": discount_type
                })
                answer = f"계산 결과: {str(result)[:200]}"
            except Exception as e:
                answer = f"오류: {str(e)}"
                selected_tool = "error"

        elapsed_time = time.time() - start_time

        return {
            "tool": selected_tool,
            "result": result,
            "answer": answer,
            "time": elapsed_time
        }


# ============================================================================
# 역할 에이전트: Booking Agent (예약/취소 + 가드)
# ============================================================================

class BookingAgent:
    """GPU 예약/취소 담당 에이전트 (가드레일 포함)"""

    def __init__(self):
        self.name = "Booking Agent"
        self.tools = {
            "get_today": get_today,
            "reserve_gpu_pc": reserve_gpu_pc
        }
        self.guard = ToolGuard(login_student_id="HANA-001", verbose=True)
        self.guard.reset_session()
        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )

    def get_system_message(self) -> str:
        """[5-3] 시스템 메시지"""
        return """당신은 GPU PC 예약/취소 담당 에이전트입니다.

당신의 역할:
- 오늘 날짜 확인 (get_today)
- GPU PC 예약/취소 (reserve_gpu_pc 도구)
- 예약 정보: 날짜, 시간, 지속시간, PC번호, 학번

중요 원칙:
- 내 담당이 아니면 '담당 아님' 이라고만 답변하세요
- 규정 조회, 수강료 계산 등은 다른 에이전트 담당입니다
- 예약/취소는 가드레일 검사를 통과해야 합니다"""

    def run(self, question: str) -> Dict[str, Any]:
        """[5-3] 에이전트 실행"""
        start_time = time.time()

        # LLM에 질문하고 도구 선택 판단
        prompt = f"""{self.get_system_message()}

사용자 질문: {question}

이 질문이 예약/취소/날짜 확인이면 해당 도구를 사용하세요.
담당이 아니면 '담당 아님' 이라고만 답하세요."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        answer = response.content.strip()

        # 도구 사용 여부 판단
        selected_tool = "none"
        if "담당 아님" not in answer:
            if "날짜" in question or "오늘" in question:
                selected_tool = "get_today"
            elif "예약" in question or "reserve" in question.lower():
                selected_tool = "reserve_gpu_pc"

        # 도구 실행
        result = ""
        if selected_tool == "get_today":
            try:
                result = get_today.invoke({})
                answer = f"오늘: {str(result)}"
            except Exception as e:
                answer = f"오류: {str(e)}"
                selected_tool = "error"
        elif selected_tool == "reserve_gpu_pc":
            answer = "예약은 터미널에서 y/n 승인이 필요합니다"

        elapsed_time = time.time() - start_time

        return {
            "tool": selected_tool,
            "result": result,
            "answer": answer,
            "time": elapsed_time
        }


# ============================================================================
# 테스트 케이스
# ============================================================================

def run_agents_test():
    """[5-3] 에이전트 테스트"""

    # 에이전트 초기화
    rules_agent = RulesAgent()
    fee_agent = FeeAgent()
    booking_agent = BookingAgent()

    # 테스트 케이스
    test_cases = [
        # Rules Agent 테스트
        ("Rules Agent", rules_agent, [
            "무료 주차는 몇시간이야?",           # 담당
            "실무반 2개월에 친구 할인 받으면 얼마?"  # 담당 아님
        ]),
        # Fee Agent 테스트
        ("Fee Agent", fee_agent, [
            "기초반 3개월 친구 할인 수강료는?",    # 담당
            "무료 주차 정책을 알려줘"             # 담당 아님
        ]),
        # Booking Agent 테스트
        ("Booking Agent", booking_agent, [
            "오늘 몇 월 며칠이야?",              # 담당
            "규정에서 주차 시간을 찾아줄래?"       # 담당 아님
        ])
    ]

    # 결과 저장
    results = []

    print(f"\n{'='*120}")
    print("[5-3] 역할 에이전트 테스트")
    print(f"{'='*120}\n")

    for agent_name, agent, questions in test_cases:
        print(f"[{agent_name}]")
        print(f"{'─'*120}\n")

        for question in questions:
            result = agent.run(question)

            results.append({
                "agent": agent_name,
                "question": question,
                "tool": result["tool"],
                "answer": result["answer"][:60] + "..." if len(result["answer"]) > 60 else result["answer"],
                "time": f"{result['time']:.2f}s"
            })

            print(f"질문: {question}")
            print(f"도구: {result['tool']}")
            print(f"답변: {result['answer'][:100]}")
            print(f"시간: {result['time']:.2f}초\n")

    # 표 출력
    print(f"\n{'='*120}")
    print("[결과 표]")
    print(f"{'='*120}\n")

    print(f"{'에이전트':<20} {'질문':<40} {'도구':<25} {'답변':<30} {'시간':<10}")
    print(f"{'-'*125}")

    for r in results:
        agent_col = r["agent"][:20]
        question_col = r["question"][:40]
        tool_col = r["tool"][:25]
        answer_col = r["answer"][:30]
        time_col = r["time"]

        print(f"{agent_col:<20} {question_col:<40} {tool_col:<25} {answer_col:<30} {time_col:<10}")

    print(f"\n{'='*120}\n")

    # JSON 저장
    output_file = DATA_DIR / "agents_test.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[저장] {output_file}")


# ============================================================================
# 메인
# ============================================================================

def main():
    """메인 함수"""
    run_agents_test()


if __name__ == "__main__":
    main()
