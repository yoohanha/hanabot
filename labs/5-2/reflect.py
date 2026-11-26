#!/usr/bin/env python3
# [5-2] LangGraph 플랜-실행-쓰기-검토 파이프라인

import os
import sys
import json
import re
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

class ReflectionState(TypedDict):
    """검토 상태"""
    question: str                                    # 사용자 질문
    plan: list                                      # 계획 단계
    current_step_idx: int                          # 현재 단계 인덱스
    results: list                                  # 실행 결과
    final_answer: str                              # 최종 답변
    reflection_pass: bool                          # 검토 통과 여부
    reflection_feedback: str                        # 검토 피드백
    retry_count: int                               # 재계획 횟수


# ============================================================================
# 도구 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# LLM 초기화
# ============================================================================

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


# ============================================================================
# [5-2] 노드: Planner (계획 생성)
# ============================================================================

def planner_node(state: ReflectionState) -> dict:
    """
    [5-2] 질문으로부터 계획 생성
    """
    question = state["question"]
    llm = create_llm()

    prompt = f"""질문: {question}

이 질문을 해결하기 위한 단계를 JSON 배열로 만드세요.
각 단계는 {{step: N, do: "설명", tool: "도구이름"}} 형식입니다.
사용할 수 있는 도구: get_today, search_rules, calculate_course_fee, reserve_gpu_pc

예: [{{"step": 1, "do": "규정 검색", "tool": "search_rules"}}, {{"step": 2, "do": "가격 계산", "tool": "calculate_course_fee"}}]

JSON 배열만 반환하세요:"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        # JSON 파싱
        try:
            plan = json.loads(response_text)
            if not isinstance(plan, list):
                plan = []
        except:
            plan = []

    except Exception as e:
        plan = []

    return {"plan": plan}


# ============================================================================
# [5-2] 노드: Executor (계획 실행)
# ============================================================================

def executor_node(state: ReflectionState) -> dict:
    """
    [5-2] 계획에 따라 도구 실행
    """
    question = state["question"]
    plan = state.get("plan", [])
    results = []

    print(f"\n[단계별 실행]")

    for step_item in plan:
        try:
            step_num = step_item.get("step", 0)
            do_desc = step_item.get("do", "")
            tool_name = step_item.get("tool", "")

            print(f"  STEP {step_num}: {do_desc} (도구: {tool_name})")

            # 도구 실행
            result = ""
            if tool_name == "get_today":
                result = get_today()
            elif tool_name == "search_rules":
                result = search_rules(question)
            elif tool_name == "calculate_course_fee":
                result = calculate_course_fee(question)
            elif tool_name == "reserve_gpu_pc":
                result = reserve_gpu_pc(question)

            # 결과 저장 (앞 50자)
            result_preview = str(result)[:50] if result else "(빈 결과)"
            print(f"    결과: {result_preview}...")
            results.append({"tool": tool_name, "result": str(result)})

        except Exception as e:
            print(f"    오류: {str(e)}")
            results.append({"tool": tool_name, "result": f"오류: {str(e)}"})

    return {"results": results}


# ============================================================================
# [5-2] 노드: Writer (답변 작성)
# ============================================================================

def writer_node(state: ReflectionState) -> dict:
    """
    [5-2] 도구 결과로부터 최종 답변 작성
    """
    question = state["question"]
    results = state.get("results", [])
    llm = create_llm()

    # 도구 결과 텍스트
    results_text = "\n".join([
        f"- {r['tool']}: {r.get('result', '')}"
        for r in results
    ])

    prompt = f"""사용자 질문: {question}

도구 결과:
{results_text}

이 도구 결과를 바탕으로 사용자 질문에 대한 답변을 작성하세요.
한국어로 명확하고 직접적으로 답변하세요."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        final_answer = response.content.strip()
    except Exception as e:
        final_answer = f"답변 생성 오류: {str(e)}"

    print(f"\n[최종 답변]")
    print(f"  {final_answer[:80]}...")

    return {"final_answer": final_answer}


# ============================================================================
# [5-2] 노드: Reflector (검토)
# ============================================================================

def reflector_node(state: ReflectionState) -> dict:
    """
    [5-2] 답변 검토
    """
    question = state.get("question", "")
    final_answer = state.get("final_answer", "")
    results = state.get("results", [])
    llm = create_llm()

    # 도구 결과 텍스트
    results_text = "\n".join([
        f"- {r['tool']}: {r.get('result', '')[:100]}"
        for r in results
    ])

    prompt = f"""사용자 질문: {question}

답변: {final_answer}

도구 실행 결과:
{results_text}

이 답변이 다음 검토 기준을 만족하는지 확인해주세요:
1. 답의 숫자가 도구 결과에 있는가
2. 날짜가 오늘 기준으로 정확한가
3. 질문의 모든 요청을 답했는가

응답은 JSON: {{"pass": true/false, "issues": ["이유1", ...]}}"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        # JSON 파싱
        try:
            review = json.loads(response_text)
        except:
            review = {"pass": False, "issues": ["검토 JSON 파싱 오류"]}

        pass_flag = review.get("pass", False)
        issues = review.get("issues", [])

    except Exception as e:
        pass_flag = False
        issues = [f"검토 오류: {str(e)}"]

    # 검토 결과
    feedback = " | ".join(issues) if issues else "모든 기준 통과"

    print(f"\n[검토 결과]")
    print(f"  {'PASS' if pass_flag else 'FAIL'}: {feedback}")

    return {
        "reflection_pass": pass_flag,
        "reflection_feedback": feedback
    }


# ============================================================================
# 조건 엣지
# ============================================================================

def should_finalize(state: ReflectionState) -> str:
    """
    [5-2] 검토 통과 여부로 END 또는 planner로
    """
    retry_count = state.get("retry_count", 0)

    if state.get("reflection_pass", False) or retry_count >= 2:
        return "end"
    else:
        return "retry"


# ============================================================================
# [5-2] 재계획 노드들
# ============================================================================

def replanner_node(state: ReflectionState) -> dict:
    """[5-2] 재계획 (피드백 반영)"""
    retry_count = state.get("retry_count", 0)
    feedback = state.get("reflection_feedback", "")

    print(f"\n[재계획 시도 {retry_count + 1}회]")
    print(f"  이유: {feedback}\n")

    # 피드백을 반영해 재계획
    llm = create_llm()
    question = state["question"]

    prompt = f"""질문: {question}

이전 검토 피드백: {feedback}

피드백을 반영해 더 나은 단계를 JSON 배열로 만드세요.
사용할 수 있는 도구: get_today, search_rules, calculate_course_fee, reserve_gpu_pc

예: [{{"step": 1, "do": "규정 검색", "tool": "search_rules"}}]

JSON 배열만 반환하세요:"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()
        try:
            plan = json.loads(response_text)
            if not isinstance(plan, list):
                plan = []
        except:
            plan = []
    except:
        plan = []

    return {
        "plan": plan,
        "retry_count": retry_count + 1
    }


def re_executor_node(state: ReflectionState) -> dict:
    """[5-2] 재실행"""
    return executor_node(state)


def re_writer_node(state: ReflectionState) -> dict:
    """[5-2] 재작성"""
    return writer_node(state)


# ============================================================================
# 그래프 생성
# ============================================================================

def create_reflection_pipeline():
    """검토 파이프라인"""
    graph = StateGraph(ReflectionState)

    # 노드 추가
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reflector", reflector_node)
    graph.add_node("replanner", replanner_node)
    graph.add_node("re_executor", re_executor_node)
    graph.add_node("re_writer", re_writer_node)

    # [5-2] 엣지 추가
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "writer")
    graph.add_edge("writer", "reflector")
    graph.add_conditional_edges(
        "reflector",
        should_finalize,
        {
            "end": END,
            "retry": "replanner"
        }
    )
    graph.add_edge("replanner", "re_executor")
    graph.add_edge("re_executor", "re_writer")
    graph.add_edge("re_writer", "reflector")

    return graph.compile()


# ============================================================================
# 대화형 모드
# ============================================================================

def interactive_mode():
    """[5-2] 대화형 모드"""
    print(f"\n[AI] Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"[NET] Ollama 주소: {OLLAMA_BASE_URL}\n")

    print(f"{'='*120}")
    print("[5-2] 에이전틱 AI · 계획 · 실행 · 검토 대화")
    print(f"{'='*120}\n")

    print("[INFO] 사용 방법:")
    print("  1. 학번을 입력하세요 (예: HANA-001)")
    print("  2. 질문을 입력하세요")
    print("  3. 계획 → 실행 → 검토 과정을 보세요")
    print("  4. q를 입력해서 종료\n")

    while True:
        # 학번 입력
        student_id = input("[INPUT] 학번 입력 (q 종료): ").strip()
        if student_id.lower() == 'q':
            print("\n프로그램을 종료합니다.\n")
            break

        if not student_id:
            print("[ERROR] 학번을 입력하세요.\n")
            continue

        # 질문 입력
        question = input("[INPUT] 질문 입력: ").strip()
        if not question:
            print("[ERROR] 질문을 입력하세요.\n")
            continue

        print()
        print(f"{'─'*120}")

        # 초기 상태
        initial_state = {
            "question": question,
            "plan": [],
            "current_step_idx": 0,
            "results": [],
            "final_answer": "",
            "reflection_pass": False,
            "reflection_feedback": "",
            "retry_count": 0
        }

        # 파이프라인 실행
        pipeline = create_reflection_pipeline()

        try:
            result = pipeline.invoke(initial_state)

            # 최종 결과 표시
            print(f"\n{'─'*120}\n")
            print(f"[결과] 검토: {'PASS' if result.get('reflection_pass') else 'FAIL'}")
            print(f"[재시도] {result.get('retry_count', 0)}회\n")

        except Exception as e:
            print(f"[ERROR] 실행 오류: {str(e)}\n")

        print(f"{'─'*120}\n")


# ============================================================================
# 테스트 모드
# ============================================================================

def test_reflection_pipeline():
    """검토 파이프라인 테스트"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    print(f"{'='*120}")
    print("[5-2] LangGraph 플랜-실행-쓰기-검토 파이프라인")
    print(f"{'='*120}\n")

    # 테스트 케이스: 정상 + 오류
    test_cases = [
        {
            "question": "지각 3번이면 어떻게 되고, 기초반 1개월 수강료는 얼마야?",
            "results": [
                {"tool": "search_rules", "result": "지각 3회는 결석 1회로 처리됩니다."},
                {"tool": "calculate_course_fee", "result": "기초반 1개월: 300,000원"}
            ]
        },
        {
            "question": "실무반 2개월 친구 할인 수강료 알려줘",
            "results": [
                {"tool": "calculate_course_fee", "result": "실무반 2개월 친구 할인: 900,000원"},
            ]
        },
        {
            "question": "내일 오후 2시 GPU PC 1번 2시간 예약해줘",
            "results": [
                {"tool": "get_today", "result": "오늘: 2026년 11월 26일 (목)"},
                {"tool": "reserve_gpu_pc", "result": "예약이 완료되었습니다."}
            ]
        }
    ]

    for idx, test_case in enumerate(test_cases, 1):
        question = test_case["question"]

        print(f"[질문 {idx}] {question}\n")

        # 초기 상태
        initial_state = {
            "question": question,
            "plan": [],
            "current_step_idx": 0,
            "results": [],
            "final_answer": "",
            "reflection_pass": False,
            "reflection_feedback": "",
            "retry_count": 0
        }

        # 파이프라인 생성 및 실행
        pipeline = create_reflection_pipeline()

        try:
            result = pipeline.invoke(initial_state)
            print()

        except Exception as e:
            print(f"실행 오류: {str(e)}\n")


def main():
    """메인 함수"""
    # 커맨드라인 인자 확인
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # 테스트 모드
        test_reflection_pipeline()
    else:
        # 대화형 모드
        interactive_mode()


if __name__ == "__main__":
    main()
