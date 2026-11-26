#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-2] LangGraph 플랜-실행-쓰기-검토 파이프라인 (실제 도구 실행)

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
    plan: list                                      # 계획 단계 (도구 인자 포함)
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
    [5-2] 질문으로부터 계획 생성 (규칙 기반 + LLM)
    """
    question = state["question"]
    llm = create_llm()

    # [5-2] 규칙 기반 계획 (자주 나오는 패턴)
    plan = []
    q_lower = question.lower()

    # 패턴 1: 주차 / 주차료 / 주차비
    if any(x in q_lower for x in ["주차", "parking"]):
        plan = [
            {"step": 1, "do": "규정에서 주차 정보 검색", "tool": "search_rules", "args": {"question": question}}
        ]

    # 패턴 2: 수강료 / 가격 계산 (과정명과 개월수)
    elif any(x in q_lower for x in ["수강료", "가격", "비용", "얼마", "돈", "fee", "charge"]):
        # 2a: 할인이 포함된 경우
        if any(x in q_lower for x in ["친구", "재수강", "할인", "discount"]):
            plan = [
                {"step": 1, "do": "규정에서 과정 정보 검색", "tool": "search_rules", "args": {"question": question}},
                {"step": 2, "do": "수강료 계산 (할인 포함)", "tool": "calculate_course_fee",
                 "args": {"course": "실무반" if "실무반" in q_lower else "기초반",
                         "months": 2 if "2개월" in q_lower else 1 if "1개월" in q_lower else 3,
                         "discount_type": "친구" if "친구" in q_lower else "재수강" if "재수강" in q_lower else "없음"}}
            ]
        else:
            plan = [
                {"step": 1, "do": "수강료 조회", "tool": "search_rules", "args": {"question": question}}
            ]

    # 패턴 3: GPU PC 예약
    elif any(x in q_lower for x in ["gpu", "pc", "예약", "reserve"]):
        plan = [
            {"step": 1, "do": "오늘 날짜 확인", "tool": "get_today", "args": {}},
            {"step": 2, "do": "규정에서 GPU PC 정보 검색", "tool": "search_rules", "args": {"question": question}}
        ]

    # 패턴 4: 기타 규정
    else:
        plan = [
            {"step": 1, "do": "규정 검색", "tool": "search_rules", "args": {"question": question}}
        ]

    return {"plan": plan}


# ============================================================================
# [5-2] 노드: Executor (계획 실행)
# ============================================================================

def executor_node(state: ReflectionState) -> dict:
    """
    [5-2] 계획에 따라 도구 실행
    """
    plan = state.get("plan", [])
    results = []

    if not plan:
        print(f"\n[단계별 실행]")
        print(f"  (계획이 없습니다)\n")
        return {"results": results}

    print(f"\n[계획 단계 목록]")
    for step_item in plan:
        step_num = step_item.get("step", "?")
        do_desc = step_item.get("do", "")
        tool_name = step_item.get("tool", "")
        print(f"  STEP {step_num}: {do_desc} (도구: {tool_name})")
    print()

    print(f"[단계별 실행]")

    for step_item in plan:
        try:
            step_num = step_item.get("step", 0)
            do_desc = step_item.get("do", "")
            tool_name = step_item.get("tool", "")
            args = step_item.get("args", {})

            print(f"  STEP {step_num}: {do_desc}")
            print(f"    도구: {tool_name}, 인자: {args}")

            # [5-2] 도구 실행 (.invoke 형태)
            result = ""
            if tool_name == "get_today":
                result = get_today.invoke({})
            elif tool_name == "search_rules":
                result = search_rules.invoke(args)
            elif tool_name == "calculate_course_fee":
                result = calculate_course_fee.invoke(args)
            elif tool_name == "reserve_gpu_pc":
                result = reserve_gpu_pc.invoke(args)

            # 결과 저장 (앞 50자)
            result_preview = str(result)[:50] if result else "(빈 결과)"
            print(f"    결과: {result_preview}...\n")
            results.append({
                "step": step_num,
                "tool": tool_name,
                "args": args,
                "result": str(result)
            })

        except Exception as e:
            print(f"    오류: {str(e)}\n")
            results.append({
                "step": step_item.get("step", "?"),
                "tool": tool_name,
                "args": args,
                "result": f"오류: {str(e)}"
            })

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
        f"- STEP {r['step']} ({r['tool']}): {r.get('result', '')}"
        for r in results
    ])

    prompt = f"""사용자 질문: {question}

도구 실행 결과:
{results_text}

이 도구 결과를 바탕으로 사용자 질문에 대한 답변을 작성하세요.
한국어로 명확하고 직접적으로 답변하세요."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        final_answer = response.content.strip()
    except Exception as e:
        final_answer = f"답변 생성 오류: {str(e)}"

    print(f"[최종 답변]")
    print(f"  {final_answer[:80]}...\n")

    return {"final_answer": final_answer}


# ============================================================================
# [5-2] 노드: Reflector (검토)
# ============================================================================

def reflector_node(state: ReflectionState) -> dict:
    """
    [5-2] 답변 검토 (도구 결과 검증)
    """
    question = state.get("question", "")
    final_answer = state.get("final_answer", "")
    results = state.get("results", [])
    llm = create_llm()  # [5-2] 오타 수정: create_llama() → create_llm()

    # 1. 도구 결과 검증
    if not results:
        print(f"[검토 결과]")
        print(f"  FAIL: 도구 실행 결과가 없습니다\n")
        return {
            "reflection_pass": False,
            "reflection_feedback": "도구 실행 결과가 없습니다"
        }

    # 2. 도구 결과가 비어있는지 확인
    has_content = any(r.get("result") and "오류" not in r.get("result", "") for r in results)
    if not has_content:
        print(f"[검토 결과]")
        print(f"  FAIL: 모든 도구 결과가 오류입니다\n")
        return {
            "reflection_pass": False,
            "reflection_feedback": "모든 도구 결과가 오류입니다"
        }

    # 3. LLM 검토
    results_text = "\n".join([
        f"- STEP {r['step']} ({r['tool']}): {r.get('result', '')[:100]}"
        for r in results
    ])

    prompt = f"""사용자 질문: {question}

답변: {final_answer}

도구 실행 결과:
{results_text}

이 답변이 다음을 만족하는지 확인해주세요:
1. 답의 숫자/시간이 도구 결과에 있는가
2. 질문의 모든 요청을 답했는가

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

    print(f"[검토 결과]")
    print(f"  {'PASS' if pass_flag else 'FAIL'}: {feedback}\n")

    return {
        "reflection_pass": pass_flag,
        "reflection_feedback": feedback
    }


def create_llama():
    """LLM 생성 (오타 수정)"""
    return create_llm()


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

    # [5-2] 피드백을 반영해 재계획
    llm = create_llm()
    question = state["question"]

    prompt = f"""질문: {question}

이전 검토 피드백: {feedback}

피드백을 반영해 더 나은 단계를 JSON 배열로 만드세요.

[JSON 형식 가이드]
각 단계:
{{
  "step": N,
  "do": "설명",
  "tool": "도구이름",
  "args": {{도구 인자}}
}}

사용 가능한 도구:
- get_today() - 인자 없음
- search_rules(question: str)
- calculate_course_fee(course, months, discount_type)
- reserve_gpu_pc(date, start_time, duration, pc_number, student_id)

응답은 JSON 배열만 반환하세요:
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        response_text = response.content.strip()

        # [5-2] JSON 추출
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            plan = json.loads(json_text)
            if isinstance(plan, list) and plan:
                return {"plan": plan, "retry_count": retry_count + 1}

        # [5-2] 재계획 실패
        print(f"[재계획 실패] JSON 파싱 실패\n")
        return {"plan": [], "retry_count": retry_count + 1}

    except Exception as e:
        # [5-2] 재계획 오류
        print(f"[재계획 실패] {str(e)}\n")
        return {"plan": [], "retry_count": retry_count + 1}


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
            print(f"{'─'*120}\n")
            print(f"[결과] 검토: {'PASS' if result.get('reflection_pass') else 'FAIL'}")
            print(f"[재시도] {result.get('retry_count', 0)}회\n")

        except Exception as e:
            print(f"[ERROR] 실행 오류: {str(e)}\n")

        print(f"{'─'*120}\n")


# ============================================================================
# 메인
# ============================================================================

def main():
    """메인 함수"""
    interactive_mode()


if __name__ == "__main__":
    main()
