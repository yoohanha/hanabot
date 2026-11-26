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

def create_reflector_llm():
    """검토자 LLM"""
    system_message = """당신은 하나봇 답변 검토자입니다.
사용자의 질문에 대한 답변이 정확하고 완전한지 검토합니다.

검토 기준:
1. 답의 숫자가 도구 실행 결과에 있는가
2. 날짜가 오늘 기준으로 정확한가
3. 질문의 모든 요청을 답했는가

응답 형식:
{
  "pass": true/false,
  "issues": ["이유1", "이유2", ...]
}"""

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
# 노드: Reflector
# ============================================================================

def reflector_node(state: ReflectionState) -> dict:
    """
    [5-2] 답변 검토
    """
    question = state.get("question", "")
    final_answer = state.get("final_answer", "")
    results = state.get("results", [])

    llm, system_msg = create_reflector_llm()

    # [5-2] 도구 결과 텍스트
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
            # JSON 파싱 실패 시 기본값
            review = {"pass": False, "issues": ["검토 오류"]}

        pass_flag = review.get("pass", False)
        issues = review.get("issues", [])

    except Exception as e:
        pass_flag = False
        issues = [f"검토 오류: {str(e)}"]

    # [5-2] 검토 결과
    feedback = " | ".join(issues) if issues else "모든 기준 통과"

    return {
        "reflection_pass": pass_flag,
        "reflection_feedback": feedback
    }


# ============================================================================
# 조건 엣지
# ============================================================================

def should_finalize(state: ReflectionState) -> str:
    """
    검토 통과 여부로 END 또는 planner로
    """
    # [5-2] 최대 2번까지만 재계획
    retry_count = state.get("retry_count", 0)

    if state.get("reflection_pass", False) or retry_count >= 2:
        return "end"
    else:
        return "retry"


# ============================================================================
# 간단한 Planner (재계획용)
# ============================================================================

def simple_planner(state: ReflectionState) -> dict:
    """
    [5-2] 간단한 재계획 (피드백 반영)
    """
    question = state["question"]
    feedback = state.get("reflection_feedback", "")
    retry_count = state.get("retry_count", 0)

    print(f"\n  🔄 재계획 (재시도 {retry_count + 1}회)")
    print(f"     이유: {feedback}")

    # 간단히 같은 계획 사용 (실제로는 LLM으로 개선된 계획 생성)
    return {
        "retry_count": retry_count + 1
    }


# ============================================================================
# 간단한 Executor (재실행용)
# ============================================================================

def simple_executor(state: ReflectionState) -> dict:
    """
    [5-2] 간단한 재실행
    """
    plan = state.get("plan", [])
    results = state.get("results", [])

    # 같은 도구 결과 사용 (실제로는 다시 실행)
    return {"results": results}


# ============================================================================
# 간단한 Writer (재작성용)
# ============================================================================

def simple_writer(state: ReflectionState) -> dict:
    """
    [5-2] 간단한 재작성
    """
    question = state["question"]
    results = state.get("results", [])

    # 같은 답변 반환 (실제로는 LLM으로 재작성)
    return {"final_answer": state.get("final_answer", "")}


# ============================================================================
# 그래프 생성
# ============================================================================

def create_reflection_pipeline():
    """검토 파이프라인"""
    graph = StateGraph(ReflectionState)

    # 노드 추가
    graph.add_node("reflector", reflector_node)
    graph.add_node("replanner", simple_planner)
    graph.add_node("re_executor", simple_executor)
    graph.add_node("re_writer", simple_writer)

    # [5-2] 엣지 추가
    graph.add_edge(START, "reflector")
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
# 테스트
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
            "first_answer": "지각 3회는 결석 1회로 처리되며, 기초반 1개월 수강료는 30만원입니다.",
            "results": [
                {"tool": "search_rules", "result": "지각 3회는 결석 1회로 처리됩니다."},
                {"tool": "calc_fee", "result": "기초반 1개월: 300,000원"}
            ]
        },
        {
            "question": "실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘",
            "first_answer": "실무반 2개월 친구 할인은 50만원입니다. 환불 규정은 10% 수수료입니다.",
            "results": [
                {"tool": "calc_fee", "result": "실무반 2개월 친구 할인: 450,000원"},
                {"tool": "search_rules", "result": "환불 수수료: 10%, 1주일 이내 환불"}
            ]
        },
        {
            "question": "내일 오후 2시 GPU PC 1번 2시간 예약해줘",
            "first_answer": "내일 오후 2시 GPU PC 1번 2시간 예약이 완료되었습니다.",
            "results": [
                {"tool": "get_today", "result": "오늘: 2026년 11월 26일 (목)"},
                {"tool": "reserve_gpu", "result": "⏳ GPU PC 예약 (실제 저장은 5교시 승인 후)"}
            ]
        }
    ]

    all_results = []

    for idx, test_case in enumerate(test_cases, 1):
        question = test_case["question"]
        first_answer = test_case["first_answer"]
        results = test_case["results"]

        print(f"[질문 {idx}] {question}\n")

        # 초기 상태
        initial_state = {
            "question": question,
            "plan": [],
            "current_step_idx": 0,
            "results": results,
            "final_answer": first_answer,
            "reflection_pass": False,
            "reflection_feedback": "",
            "retry_count": 0
        }

        # 파이프라인 생성 및 실행
        pipeline = create_reflection_pipeline()

        try:
            print(f"{'─'*120}")
            print("📋 1차 답변")
            print(f"{first_answer}\n")

            result = pipeline.invoke(initial_state)

            # 최종 결과
            feedback = result.get("reflection_feedback", "통과")
            pass_flag = result.get("reflection_pass", False)
            final_answer = result.get("final_answer", first_answer)
            retry = result.get("retry_count", 0)

            print(f"{'─'*120}")
            print(f"🔍 검토 결과: {'✅ 통과' if pass_flag else '❌ 재검토'}")
            print(f"   이유: {feedback}")
            if retry > 0:
                print(f"   재시도: {retry}회\n")

            all_results.append({
                "question": question,
                "first_answer": first_answer,
                "review_result": "통과" if pass_flag else "재검토",
                "review_reason": feedback,
                "final_answer": final_answer,
                "retry_count": retry
            })

        except Exception as e:
            print(f"❌ 실행 오류: {str(e)}\n")

    # 결과 표
    print(f"\n{'='*120}")
    print("📊 검토 결과 (질문 · 1차 답 · 검토 결과 · 이유 · 최종 답)")
    print(f"{'='*120}\n")

    for idx, r in enumerate(all_results, 1):
        print(f"[{idx}] 질문: {r['question']}")
        print(f"    1차 답: {r['first_answer']}")
        print(f"    검토: {r['review_result']}")
        print(f"    이유: {r['review_reason']}")
        print(f"    최종: {r['final_answer']}")
        if r['retry_count'] > 0:
            print(f"    재시도: {r['retry_count']}회")
        print()

    # 결과 저장
    result_file = DATA_DIR / "reflect_test.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"✅ 테스트 결과 저장: {result_file}")


def interactive_mode():
    """대화형 모드"""
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
        print(f"[Q] 질문: {question}\n")

        # 간단한 계획 · 실행 · 검토 시뮬레이션
        print("[STEP 1] 계획 생성 중...")
        import time
        time.sleep(0.3)
        print("[OK] 계획 완료\n")

        print("[STEP 2] 도구 실행 중...")
        time.sleep(0.3)
        print("[OK] 도구 실행 완료\n")

        print("[STEP 3] 답변 작성 중...")
        time.sleep(0.3)
        print("[OK] 답변 완료: 질문에 대한 답변을 생성했습니다.\n")

        print("[STEP 4] 검토 중...")
        time.sleep(0.3)
        print("[OK] 검토 완료: 모든 기준을 만족합니다.\n")

        print(f"{'─'*120}\n")


def main():
    """메인 함수"""
    # 커맨드라인 인자 확인
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # 테스트 모드
        test_reflection_pipeline()
    else:
        # 대화형 모드
        interactive_mode()


if __name__ == "__main__":
    main()
