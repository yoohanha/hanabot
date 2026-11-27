#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-4] CrewAI 멀티 에이전트 시스템

import os
import sys
import importlib.util
from pathlib import Path
from typing import Optional

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

# [5-4] labs/4-1/hana_tools.py 모듈 동적 로드 (숫자-문자 모듈명 대응)
def load_hana_tools():
    spec = importlib.util.spec_from_file_location(
        "hana_tools",
        PROJECT_ROOT / "labs" / "4-1" / "hana_tools.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

hana_tools_module = load_hana_tools()

from crewai import Agent, Crew, Task, Process
from crewai.tools import tool
from crewai import LLM

# [5-4] crewai 는 ChatOllama 를 받지 않음 → crewai 의 LLM("ollama/모델") 사용
llm = LLM(
    model="ollama/" + os.getenv("CHAT_MODEL", "llama3.1"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    temperature=0,
)


# ============================================================================
# [5-4] CrewAI 도구 정의 (labs/4-1 도구 감싸기)
# ============================================================================

@tool
def search_rules_tool(question: str) -> str:
    """
    규정 문서에서 정보를 검색합니다.

    Args:
        question (str): 규정에 관한 질문
        예: "환불 기준이 뭐야?", "실무반은 몇 주 과정이야?"

    Returns:
        str: 규정 문서에서 찾은 답변
    """
    result = hana_tools_module.search_rules.invoke({"question": question})
    return result


# [5-4] result_as_answer: 도구 결과를 그대로 답으로 (모델이 숫자를 옮겨 적다 0 을 빠뜨리는 것 방지)
@tool("calculate_course_fee_tool", result_as_answer=True)
def calculate_course_fee_tool(course: str, months: int, discount_type: str = "없음") -> str:
    """
    수강료를 계산하고 반환합니다.

    Args:
        course (str): 과정 이름 ("기초반" 또는 "실무반")
        months (int): 개월 수 (정수, 1개월 이상)
        discount_type (str): 할인 종류
            - "없음": 정상 가격
            - "재수강": 50% 할인
            - "친구": 10% 할인

    Returns:
        str: 금액 계산 결과 (원 단위) 및 세부 정보
    """
    result = hana_tools_module.calculate_course_fee.invoke({
        "course": course,
        "months": months,
        "discount_type": discount_type
    })
    return result


# ============================================================================
# [5-4] 에이전트 정의
# ============================================================================

# 1. 규정 담당 에이전트
agent_rules = Agent(
    role="규정 검색 담당",
    goal="학원 규정에서 필요한 정보를 정확하게 찾아냅니다.",
    backstory=(
        "당신은 하나 AI 학원의 규정 전문가입니다. "
        "학원의 모든 규정, 환불 정책, 출석 규칙을 꿰뚫고 있습니다. "
        "학생들이 궁금해하는 규정을 명확하게 설명하는 것이 역할입니다."
    ),
    tools=[search_rules_tool],
    llm=llm,
    verbose=True,
    memory=False,
    max_iter=3,
)

# 2. 수강료 담당 에이전트
agent_fee = Agent(
    role="수강료 계산 담당",
    goal="학생이 받을 수 있는 할인을 적용하여 정확한 수강료를 계산합니다.",
    backstory=(
        "당신은 하나 AI 학원의 수강료 계산 전문가입니다. "
        "기초반과 실무반의 월 수강료를 알고 있으며, "
        "재수강 할인(50%), 친구 할인(10%) 등의 규정을 정확히 적용합니다. "
        "학생이 얼마를 내야 하는지 명확하게 알려주는 것이 역할입니다."
    ),
    tools=[calculate_course_fee_tool],
    llm=llm,
    verbose=True,
    memory=False,
    max_iter=3,
)

# 3. 상담 정리 담당 에이전트
agent_summary = Agent(
    role="상담 정리 담당",
    goal="앞의 두 에이전트 결과를 종합하여 학생에게 알기 쉬운 답변을 작성합니다.",
    backstory=(
        "당신은 하나 AI 학원의 상담 담당 직원입니다. "
        "학생이 묻는 질문에 대해 규정 담당과 수강료 담당이 찾은 정보를 "
        "종합하여 명확하고 친근한 답변을 작성합니다. "
        "학생이 쉽게 이해할 수 있도록 정리하는 것이 역할입니다."
    ),
    llm=llm,
    verbose=True,
    memory=False,
    max_iter=3,
)


# ============================================================================
# [5-4] 태스크 정의 함수 (Process.sequential)
# ============================================================================

def create_tasks(user_question: str):
    """사용자 질문에 따라 태스크를 동적으로 생성합니다."""

    # 1. 규정 찾기 태스크
    task_find_rules = Task(
        description=(
            f"학생의 질문: '{user_question}'\n"
            "이 질문에서 규정 관련 부분(환불 정책, 과정 정보, 운영시간 등)을 찾아 조회합니다. "
            "search_rules_tool을 사용하여 규정 문서에서 정보를 찾으세요."
        ),
        expected_output="규정 문서에서 찾은 환불 정책, 과정 정보, 운영 규정 등",
        agent=agent_rules,
    )

    # 2. 수강료 계산 태스크
    task_calculate_fee = Task(
        description=(
            f"학생의 질문: '{user_question}'\n"
            "이 질문에서 과정 이름, 개월 수, 할인 종류를 파악합니다. "
            "calculate_course_fee_tool을 사용하여 정확한 수강료를 계산하세요."
        ),
        expected_output="할인이 적용된 최종 수강료 금액 및 세부 계산 과정",
        agent=agent_fee,
    )

    # 3. 답변 정리 태스크 (context에 위 두 태스크 결과 포함)
    task_summarize = Task(
        description=(
            f"학생의 최종 질문: '{user_question}'\n"
            "앞의 두 태스크에서 찾은 규정과 계산된 수강료를 종합하여, "
            "학생에게 알기 쉬운 최종 답변을 작성합니다. "
            "규정 담당의 결과와 수강료 담당의 결과만 사용해서 명확한 답변을 구성하세요. "
            "금액은 수강료 담당 결과의 숫자를 글자 그대로 옮기세요 (0 의 개수를 바꾸지 말 것)."
        ),
        expected_output="학생이 이해하기 쉬운 종합 답변 (수강료 + 환불 규정)",
        agent=agent_summary,
        context=[task_find_rules, task_calculate_fee],
    )

    return [task_find_rules, task_calculate_fee, task_summarize]


# ============================================================================
# [5-4] 크루 생성 및 실행
# ============================================================================

def run_crew(user_question: str) -> str:
    """
    CrewAI 크루를 실행하고 결과를 반환합니다.

    Args:
        user_question (str): 학생의 질문

    Returns:
        str: 최종 답변
    """
    # 사용자 질문에 따라 태스크 생성
    tasks = create_tasks(user_question)

    crew = Crew(
        agents=[agent_rules, agent_fee, agent_summary],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()
    return result


if __name__ == "__main__":
    # [5-4] 대화형 실행 (run.py 15번): 질문 → 에이전트 과정 표시(verbose) → 최종 답 · q 로 종료
    #       python crew_hana.py --test 는 정해진 질문 하나만 실행
    import time
    line = "=" * 70
    if "--test" in sys.argv:
        questions = iter(["실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘"])
    else:
        questions = None
        print(line)
        print("[5-4] CrewAI 팀 · 대화형 모드 (규정 담당 → 수강료 담당 → 상담 정리 담당)")
        print("  예시: 실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘")
        print("  한 번에 1~5분 걸릴 수 있어요 · q 를 입력하면 종료")
        print(line)

    while True:
        if questions is not None:
            user_question = next(questions, None)
            if user_question is None:
                break
        else:
            user_question = input(chr(10) + "[INPUT] 질문 (q 종료): ").strip()
            if user_question.lower() == "q":
                print("종료합니다.")
                break
            if not user_question:
                continue

        print(line)
        print(f"📌 질문: {user_question}")
        print(line)
        start = time.time()
        try:
            result = run_crew(user_question)
        except Exception as e:
            result = f"❌ 실행 실패: {e}"
        print(line)
        print(f"📋 최종 답변 ({time.time() - start:.0f}초):")
        print(line)
        print(result)
