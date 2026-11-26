#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-3] 팀 그래프: 지휘자 + 담당 에이전트 (Supervisor Pattern with LangGraph)

import os
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal

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

class TeamState(TypedDict):
    """팀 협업 상태"""
    question: str                                      # 원래 질문
    messages: Annotated[list, add_messages]          # 메시지 히스토리
    # [5-3] 남은 요청 목록 추가
    remaining_requests: list                          # 남은 요청 (금액/환불/예약/규정 등)
    next_worker: str                                  # 다음 담당 (rules/fee/booking/FINISH)
    worker_responses: list                            # 담당 응답 모음 (도구 결과만)
    call_count: int                                   # 담당 호출 횟수
    final_answer: str                                 # 최종 답변


# ============================================================================
# 데이터 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 담당 에이전트들 (Agents)
# ============================================================================

class RulesWorker:
    """규정 담당"""
    def __init__(self):
        self.name = "rules"

    def execute(self, task: str) -> Dict[str, Any]:
        """[5-3] 규정 검색 (결과만 반환)"""
        try:
            result = search_rules.invoke({"question": task})
            result_text = str(result)

            # [5-3] 결과에 없는 내용은 "규정에 없음" 반환
            if "없습니다" in result_text or "찾을 수 없습니다" in result_text or not result_text.strip():
                return {"tool": "search_rules", "result": "규정에 없음", "raw": result_text}

            return {"tool": "search_rules", "result": result_text[:200], "raw": result_text}
        except Exception as e:
            return {"tool": "search_rules", "result": f"오류: {str(e)}", "raw": ""}


class FeeWorker:
    """수강료 담당"""
    def __init__(self):
        self.name = "fee"

    def execute(self, task: str) -> Dict[str, Any]:
        """[5-3] 수강료 계산"""
        try:
            q_lower = task.lower()
            course = "실무반" if "실무반" in q_lower else "기초반" if "기초반" in q_lower else "기초반"
            months = 2 if "2개월" in q_lower else 1 if "1개월" in q_lower else 3
            discount_type = "친구" if "친구" in q_lower else "재수강" if "재수강" in q_lower else "없음"

            result = calculate_course_fee.invoke({
                "course": course,
                "months": months,
                "discount_type": discount_type
            })

            result_text = str(result)
            return {"tool": "calculate_course_fee", "result": result_text[:200], "raw": result_text}
        except Exception as e:
            return {"tool": "calculate_course_fee", "result": f"오류: {str(e)}", "raw": ""}


class BookingWorker:
    """예약 담당 (dry-run)"""
    def __init__(self):
        self.name = "booking"
        self.guard = ToolGuard(login_student_id="HANA-001", verbose=False)

    def execute(self, task: str) -> Dict[str, Any]:
        """[5-3] 예약 (dry-run)"""
        try:
            q_lower = task.lower()

            if "내일" in q_lower:
                tomorrow = datetime.now() + timedelta(days=1)
                date_str = tomorrow.strftime("%Y-%m-%d")
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")

            start_time = "14:00" if "오후 2시" in q_lower else "09:00"
            duration = 2 if "2시간" in q_lower else 1 if "1시간" in q_lower else 2
            pc_number = 1 if "1번" in q_lower else 2 if "2번" in q_lower else 1

            result_text = f"날짜: {date_str}, 시간: {start_time}, 지속: {duration}시간, PC: {pc_number}번 (DRY-RUN, 실제 저장은 5교시 승인 뒤)"
            return {"tool": "reserve_gpu_pc", "result": result_text, "raw": result_text}
        except Exception as e:
            return {"tool": "reserve_gpu_pc", "result": f"오류: {str(e)}", "raw": ""}


# ============================================================================
# 지휘자 (Supervisor)
# ============================================================================

class Supervisor:
    """팀 지휘자: 질문 분석 후 담당 지정"""

    def __init__(self):
        self.name = "supervisor"
        today = datetime.now()
        self.today_str = today.strftime("%Y년 %m월 %d일 (%A)")

        # [5-3] format="json" 추가
        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120,
            format="json"
        )

    def route(self, question: str, remaining_requests: List[str], previous_responses: List[Dict]) -> Dict[str, str]:
        """[5-3] 다음 담당 선택 (JSON 형식 + reason)"""

        # [5-3] 남은 요청 정리
        requests_text = "\n".join([f"- {r}" for r in remaining_requests]) if remaining_requests else "(완료됨)"

        responses_text = "\n".join([
            f"- {r.get('tool', '?')}: {r.get('result', '')[:100]}"
            for r in previous_responses
        ]) if previous_responses else "(아직 없음)"

        prompt = f"""당신은 팀의 지휘자입니다. 오늘은 {self.today_str} 입니다.

원래 질문: {question}

남은 요청:
{requests_text}

담당 응답:
{responses_text}

다음 담당을 선택하세요. JSON 형식으로:
{{"next": "rules" | "fee" | "booking" | "FINISH", "reason": "왜 이 담당인지"}}

각 담당 역할:
- rules: 규정 검색 (주차, 수업시간, 환불 기준 등)
- fee: 수강료 계산 (가격 · 할인)
- booking: 예약 처리 (날짜 · 시간 · PC)"""

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            answer_text = response.content.strip()

            # [5-3] JSON 추출
            json_match = re.search(r'\{[^{}]*\}', answer_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                next_worker = result.get("next", "FINISH").upper()
                reason = result.get("reason", "판단")
                return {"next": next_worker, "reason": reason}

            return {"next": "FINISH", "reason": "JSON 파싱 실패"}
        except Exception as e:
            return {"next": "FINISH", "reason": f"지휘자 오류: {str(e)}"}


# ============================================================================
# 그래프 노드들
# ============================================================================

supervisor = Supervisor()
rules_worker = RulesWorker()
fee_worker = FeeWorker()
booking_worker = BookingWorker()


def supervisor_node(state: TeamState) -> dict:
    """[5-3] 지휘자 노드: 다음 담당 결정"""
    call_count = state.get("call_count", 0)

    # [5-3] 최대 호출 횟수 초과 시 종료
    if call_count >= 4:
        return {"next_worker": "FINISH"}

    # [5-3] 다음 담당 선택 (reason 포함)
    route_result = supervisor.route(
        state["question"],
        state.get("remaining_requests", []),
        state.get("worker_responses", [])
    )

    next_worker = route_result["next"]
    reason = route_result["reason"]

    print(f"\n[지휘자] → {next_worker}")
    print(f"  이유: {reason}")

    return {
        "next_worker": next_worker,
        "call_count": call_count + 1
    }


def rules_node(state: TeamState) -> dict:
    """[5-3] 규정 담당 노드"""
    print(f"  [담당: Rules] 검색 중...", end=" ", flush=True)
    result = rules_worker.execute(state["question"])
    print(f"완료")

    new_responses = state.get("worker_responses", []) + [result]
    # [5-3] 남은 요청에서 "규정" 제거
    remaining = [r for r in state.get("remaining_requests", []) if "규정" not in r and "환불" not in r]

    return {
        "worker_responses": new_responses,
        "next_worker": "supervisor",
        "remaining_requests": remaining
    }


def fee_node(state: TeamState) -> dict:
    """[5-3] 수강료 담당 노드"""
    print(f"  [담당: Fee] 계산 중...", end=" ", flush=True)
    result = fee_worker.execute(state["question"])
    print(f"완료")

    new_responses = state.get("worker_responses", []) + [result]
    # [5-3] 남은 요청에서 "금액/수강료" 제거
    remaining = [r for r in state.get("remaining_requests", []) if "금액" not in r and "수강료" not in r]

    return {
        "worker_responses": new_responses,
        "next_worker": "supervisor",
        "remaining_requests": remaining
    }


def booking_node(state: TeamState) -> dict:
    """[5-3] 예약 담당 노드 (dry-run)"""
    print(f"  [담당: Booking] 처리 중...", end=" ", flush=True)
    result = booking_worker.execute(state["question"])
    print(f"완료")

    new_responses = state.get("worker_responses", []) + [result]
    # [5-3] 남은 요청에서 "예약" 제거
    remaining = [r for r in state.get("remaining_requests", []) if "예약" not in r]

    return {
        "worker_responses": new_responses,
        "next_worker": "supervisor",
        "remaining_requests": remaining
    }


def finish_node(state: TeamState) -> dict:
    """[5-3] 최종 답변 작성 (도구 결과만 사용)"""
    # [5-3] 도구 결과만으로 답변 작성
    responses_text = "\n".join([
        f"- {r.get('tool', '?')}: {r.get('raw', '')}"
        for r in state.get("worker_responses", [])
    ])

    prompt = f"""도구들의 실행 결과만으로 답변을 작성하세요.
질문: {state["question"]}

도구 결과:
{responses_text}

이 결과들을 조합해서 명확한 답변을 작성하세요.
결과에 없는 내용은 절대 추가하지 마세요."""

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        num_ctx=8192,
        num_predict=512,
        timeout=120
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    final_answer = response.content.strip()

    print(f"\n[최종 답변]")
    print(f"  {final_answer[:150]}...\n")

    return {"final_answer": final_answer}


# ============================================================================
# 조건 엣지
# ============================================================================

def route_after_supervisor(state: TeamState) -> Literal["rules", "fee", "booking", "finish"]:
    """[5-3] 지휘자 결정 후 라우팅"""
    next_worker = state.get("next_worker", "FINISH")

    if next_worker == "RULES":
        return "rules"
    elif next_worker == "FEE":
        return "fee"
    elif next_worker == "BOOKING":
        return "booking"
    else:
        return "finish"


# ============================================================================
# 그래프 생성
# ============================================================================

def create_team_graph():
    """[5-3] 팀 그래프 생성"""
    graph = StateGraph(TeamState)

    # 노드 추가
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rules", rules_node)
    graph.add_node("fee", fee_node)
    graph.add_node("booking", booking_node)
    graph.add_node("finish", finish_node)

    # 엣지 추가
    graph.add_edge(START, "supervisor")

    # [5-3] 조건 엣지: 지휘자 결정
    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "rules": "rules",
            "fee": "fee",
            "booking": "booking",
            "finish": "finish"
        }
    )

    # 담당 → 지휘자
    graph.add_edge("rules", "supervisor")
    graph.add_edge("fee", "supervisor")
    graph.add_edge("booking", "supervisor")

    # 최종 → 종료
    graph.add_edge("finish", END)

    return graph.compile()


# ============================================================================
# 대화형 모드
# ============================================================================

def interactive_mode():
    """[5-3] 대화형 모드"""
    print(f"\n{'='*120}")
    print("[5-3] 멀티 에이전트 팀 · 대화형 모드")
    print(f"{'='*120}\n")

    print("[안내]")
    print("  1. 학번을 입력하세요")
    print("  2. 질문을 입력하세요 (예시 표시 안내)")
    print("  3. 지휘자가 담당을 지정합니다")
    print("  4. q를 입력하면 종료\n")

    while True:
        # 학번 입력
        student_id = input("[INPUT] 학번 (q 종료): ").strip()
        if student_id.lower() == 'q':
            print("\n프로그램을 종료합니다.\n")
            break

        if not student_id:
            print("[ERROR] 학번을 입력하세요.\n")
            continue

        # 질문 입력 안내
        print("\n[입력 예시]")
        print("  - 무료 주차는 몇시간이야?")
        print("  - 기초반 1개월은 얼마야?")
        print("  - 실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘")

        question = input("\n[INPUT] 질문: ").strip()
        if not question:
            print("[ERROR] 질문을 입력하세요.\n")
            continue

        print(f"\n{'-'*120}\n")

        # [5-3] 초기 상태: 남은 요청 추출
        remaining_requests = []
        q_lower = question.lower()
        if any(x in q_lower for x in ["금액", "얼마", "가격", "수강료", "비용"]):
            remaining_requests.append("금액 계산")
        if any(x in q_lower for x in ["환불", "취소", "규정"]):
            remaining_requests.append("환불 규정")
        if any(x in q_lower for x in ["예약", "보기", "시간", "gpu", "pc"]):
            remaining_requests.append("예약/날짜")
        if any(x in q_lower for x in ["주차", "시간표", "규칙", "규정"]):
            remaining_requests.append("규정 조회")

        initial_state = {
            "question": question,
            "messages": [],
            "remaining_requests": remaining_requests,
            "next_worker": "supervisor",
            "worker_responses": [],
            "call_count": 0,
            "final_answer": ""
        }

        # 파이프라인 실행
        graph = create_team_graph()

        try:
            result = graph.invoke(initial_state)

            print(f"{'-'*120}\n")
            print(f"[결과] 호출: {result.get('call_count', 0)}/4회\n")

        except Exception as e:
            print(f"[ERROR] {str(e)}\n")


# ============================================================================
# 메인
# ============================================================================

def main():
    """메인 함수"""
    interactive_mode()


if __name__ == "__main__":
    main()
