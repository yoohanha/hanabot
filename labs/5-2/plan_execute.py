#!/usr/bin/env python3
# [5-2] LangGraph 플랜-실행-쓰기 파이프라인

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [5-2] 4-1 도구 import
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))
from hana_tools import get_today, search_rules, calculate_course_fee, reserve_gpu_pc

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
from langgraph.graph.message import add_messages


# ============================================================================
# State 정의
# ============================================================================

class ExecutionState(TypedDict):
    """실행 상태"""
    question: str                                    # 사용자 질문
    plan: Annotated[list, add_messages]            # 계획 단계
    current_step_idx: int                          # 현재 단계 인덱스
    results: list                                  # 실행 결과 모음
    final_answer: str                              # 최종 답변


# ============================================================================
# 도구 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# LLM 초기화
# ============================================================================

def create_planner_llm():
    """플래너 LLM"""
    today = datetime.now().strftime("%Y년 %m월 %d일")

    system_message = f"""당신은 하나봇 AI 플래너입니다.
오늘 날짜: {today}
역할: 사용자의 질문을 단계별 계획으로 변환합니다.

사용 가능한 도구:
- get_today: 오늘 날짜 조회
- search_rules: 규정 검색
- calc_fee: 수강료 계산
- reserve_gpu: GPU PC 예약

응답은 반드시 JSON 배열입니다:
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


def create_writer_llm():
    """라이터 LLM (최종 답 작성)"""
    system_message = """당신은 하나봇 최종 답변 작성자입니다.
주어진 실행 결과들을 바탕으로 사용자의 질문에 최종 답변을 작성합니다.

규칙:
1. 제공된 결과만 사용하세요
2. 결과에 없는 정보는 추가하지 마세요
3. 명확하고 친근한 톤으로 작성하세요
4. 숫자가 필요하면 결과에서 가져오세요"""

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
# 노드: Planner
# ============================================================================

def planner_node(state: ExecutionState) -> dict:
    """
    질문을 계획으로 변환
    """
    question = state["question"]
    llm, system_msg = create_planner_llm()

    prompt = f"""질문: {question}

이 질문을 실행 단계로 계획해주세요."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        # JSON 파싱
        try:
            plan = json.loads(response_text)
            if isinstance(plan, dict) and "steps" in plan:
                plan = plan["steps"]
        except:
            plan = []

        return {
            "plan": plan if plan else [],
            "current_step_idx": 0,
            "results": []
        }

    except Exception as e:
        print(f"❌ 플래너 오류: {str(e)}")
        return {
            "plan": [],
            "current_step_idx": 0,
            "results": []
        }


# ============================================================================
# 노드: Executor
# ============================================================================

def executor_node(state: ExecutionState) -> dict:
    """
    현재 단계 실행
    """
    plan = state.get("plan", [])
    current_idx = state.get("current_step_idx", 0)
    results = state.get("results", [])

    # 더 이상 단계가 없으면 종료
    if current_idx >= len(plan):
        return {"results": results, "current_step_idx": current_idx}

    # [5-2] 현재 단계 가져오기
    current_step = plan[current_idx]
    step_num = current_step.get("step", current_idx + 1)
    tool_name = current_step.get("tool", "?")
    do_desc = current_step.get("do", "?")

    print(f"  [{step_num}] {do_desc} ({tool_name})")

    # [5-2] 도구 실행
    result_text = "실행 중..."
    try:
        if tool_name == "get_today":
            result_text = get_today.invoke({})

        elif tool_name == "search_rules":
            result_text = search_rules.invoke({"question": state["question"]})

        elif tool_name == "calc_fee":
            # 질문에서 과정, 개월 수, 할인 종류 추출 (간단히)
            course = "실무반" if "실무반" in state["question"] else "기초반"
            months = 1
            for word in state["question"].split():
                if word.isdigit() and 1 <= int(word) <= 12:
                    months = int(word)
                    break
            discount = "친구" if "친구" in state["question"] else "없음"

            result_text = calculate_course_fee.invoke({
                "course": course,
                "months": months,
                "discount_type": discount
            })

        elif tool_name == "reserve_gpu":
            # [5-2] 예약은 "이렇게 예약됩니다"까지만 (실제 저장 안 함)
            result_text = "⏳ GPU PC 예약 (실제 저장은 5교시 승인 후)"

    except Exception as e:
        result_text = f"오류: {str(e)}"

    # [5-2] 결과 저장
    result_preview = result_text[:50]
    if len(result_text) > 50:
        result_preview += "..."

    print(f"       → {result_preview}")

    results.append({
        "step": step_num,
        "tool": tool_name,
        "result": result_text
    })

    return {
        "results": results,
        "current_step_idx": current_idx + 1
    }


# ============================================================================
# 노드: Writer
# ============================================================================

def writer_node(state: ExecutionState) -> dict:
    """
    모은 결과로 최종 답 작성
    """
    question = state["question"]
    results = state.get("results", [])

    llm, system_msg = create_writer_llm()

    # [5-2] 결과들을 프롬프트로 구성
    results_text = "\n".join([
        f"- {r['tool']}: {r['result'][:100]}"
        for r in results
    ])

    prompt = f"""사용자 질문: {question}

실행 결과:
{results_text}

이 결과들을 바탕으로 최종 답변을 작성해주세요."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        final_answer = response.content.strip()

    except Exception as e:
        final_answer = f"답변 생성 오류: {str(e)}"

    return {"final_answer": final_answer}


# ============================================================================
# 조건 엣지
# ============================================================================

def should_continue(state: ExecutionState) -> str:
    """
    계속 실행할지 writer로 갈지 결정
    """
    plan = state.get("plan", [])
    current_idx = state.get("current_step_idx", 0)

    # [5-2] 더 이상 단계가 없으면 writer로
    if current_idx >= len(plan):
        return "writer"
    else:
        return "executor"


# ============================================================================
# 그래프 생성
# ============================================================================

def create_pipeline_graph():
    """플랜-실행-쓰기 파이프라인"""
    graph = StateGraph(ExecutionState)

    # [5-2] 노드 추가
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("writer", writer_node)

    # [5-2] 엣지 추가
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "writer": "writer"
        }
    )
    graph.add_edge("writer", END)

    return graph.compile()


# ============================================================================
# 테스트
# ============================================================================

def test_pipeline():
    """파이프라인 테스트"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    print(f"{'='*100}")
    print("[5-2] LangGraph 플랜-실행-쓰기 파이프라인")
    print(f"{'='*100}\n")

    # 테스트 질문 3개
    test_questions = [
        "지각 3번이면 어떻게 되고, 기초반 1개월 수강료는 얼마야?",
        "실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘",
        "내일 오후 2시 GPU PC 1번 2시간 예약해줘"
    ]

    # 그래프 생성
    pipeline = create_pipeline_graph()

    all_results = []

    for idx, question in enumerate(test_questions, 1):
        print(f"[질문 {idx}] {question}\n")

        # 초기 상태
        initial_state = {
            "question": question,
            "plan": [],
            "current_step_idx": 0,
            "results": [],
            "final_answer": ""
        }

        # [5-2] 파이프라인 실행
        try:
            print(f"{'─'*100}")
            print("🔄 실행 단계\n")

            result = pipeline.invoke(initial_state)

            # [5-2] 실행 단계와 결과 표시
            print(f"\n{'─'*100}")
            print("📊 실행 결과\n")

            results = result.get("results", [])
            for r in results:
                print(f"| {r['step']} | {r['tool']:20} | {r['result'][:50]}... |")

            # 최종 답
            final_answer = result.get("final_answer", "")
            print(f"\n💬 최종 답변:")
            print(f"{final_answer}\n")

            all_results.append({
                "question": question,
                "steps": results,
                "final_answer": final_answer
            })

        except Exception as e:
            print(f"❌ 실행 오류: {str(e)}\n")

    # 결과 저장
    result_file = DATA_DIR / "plan_execute_test.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"✅ 테스트 결과 저장: {result_file}")


def main():
    """메인 함수"""
    test_pipeline()


if __name__ == "__main__":
    main()
