#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-3] 팀 그래프: 지휘자 + 담당 에이전트 (Supervisor Pattern with LangGraph)

import os
import sys
import time
import json
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
    next_worker: str                                  # 다음 담당 (rules/fee/booking/FINISH)
    worker_responses: list                            # 담당 응답 모음
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
        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )

    def execute(self, task: str) -> str:
        """[5-3] 규정 검색"""
        try:
            result = search_rules.invoke({"question": task})
            return f"[규정] {str(result)[:300]}"
        except Exception as e:
            return f"[규정 오류] {str(e)}"


class FeeWorker:
    """수강료 담당"""
    def __init__(self):
        self.name = "fee"
        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )

    def execute(self, task: str) -> str:
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
            return f"[수강료] {str(result)[:300]}"
        except Exception as e:
            return f"[수강료 오류] {str(e)}"


class BookingWorker:
    """예약 담당 (dry-run)"""
    def __init__(self):
        self.name = "booking"
        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )
        self.guard = ToolGuard(login_student_id="HANA-001", verbose=False)

    def execute(self, task: str) -> str:
        """[5-3] 예약 (dry-run)"""
        try:
            # 오늘 날짜 확인
            today_str = get_today.invoke({})

            # 예약 정보 파싱 (간단한 패턴)
            q_lower = task.lower()

            if "내일" in q_lower:
                tomorrow = datetime.now() + timedelta(days=1)
                date_str = tomorrow.strftime("%Y-%m-%d")
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")

            # 시간, 지속시간, PC 번호 추출
            start_time = "14:00" if "오후 2시" in q_lower else "09:00"
            duration = 2 if "2시간" in q_lower else 1 if "1시간" in q_lower else 2
            pc_number = 1 if "1번" in q_lower else 2 if "2번" in q_lower else 1

            # dry-run 메시지
            return f"[예약 DRY-RUN] 날짜: {date_str}, 시간: {start_time}, 지속: {duration}시간, PC: {pc_number}번 (실제 저장은 5교시 승인 뒤)"
        except Exception as e:
            return f"[예약 오류] {str(e)}"


# ============================================================================
# 지휘자 (Supervisor)
# ============================================================================

class Supervisor:
    """팀 지휘자: 질문 분석 후 담당 지정"""

    def __init__(self):
        self.name = "supervisor"
        # [5-3] 오늘 날짜 포함
        today = datetime.now()
        self.today_str = today.strftime("%Y년 %m월 %d일 (%A)")

        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )

    def route(self, question: str, previous_responses: List[str], call_count: int) -> str:
        """[5-3] 다음 담당 선택"""

        responses_text = "\n".join(previous_responses) if previous_responses else "(아직 없음)"

        prompt = f"""당신은 팀의 지휘자입니다. 오늘은 {self.today_str} 입니다.

원래 질문: {question}

이전 담당 응답:
{responses_text}

남은 작업이 있는지 판단하세요:
1. 규정 조회 필요? → "rules"
2. 수강료 계산 필요? → "fee"
3. 예약/날짜 필요? → "booking"
4. 모든 작업 완료? → "FINISH"

응답은 "rules", "fee", "booking", 또는 "FINISH" 중 하나만 반환하세요."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        answer = response.content.strip().upper()

        # 가능한 옵션 중 선택
        if "RULES" in answer:
            return "rules"
        elif "FEE" in answer:
            return "fee"
        elif "BOOKING" in answer:
            return "booking"
        else:
            return "FINISH"


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
        return {"next_worker": "FINISH", "call_count": call_count}

    # 다음 담당 선택
    next_worker = supervisor.route(
        state["question"],
        state.get("worker_responses", []),
        call_count
    )

    print(f"\n[지휘자] → {next_worker} ({'답 정리' if next_worker == 'FINISH' else '호출 ' + str(call_count + 1) + '/4'})")
    if state.get("worker_responses"):
        print(f"  이유: {state['worker_responses'][-1][:80]}...")

    return {"next_worker": next_worker, "call_count": call_count + 1}


def rules_node(state: TeamState) -> dict:
    """[5-3] 규정 담당 노드"""
    print(f"  [담당: Rules] 규정 검색 중...", end=" ", flush=True)
    result = rules_worker.execute(state["question"])
    print("완료")

    new_responses = state.get("worker_responses", []) + [result]
    return {"worker_responses": new_responses, "next_worker": "supervisor"}


def fee_node(state: TeamState) -> dict:
    """[5-3] 수강료 담당 노드"""
    print(f"  [담당: Fee] 수강료 계산 중...", end=" ", flush=True)
    result = fee_worker.execute(state["question"])
    print("완료")

    new_responses = state.get("worker_responses", []) + [result]
    return {"worker_responses": new_responses, "next_worker": "supervisor"}


def booking_node(state: TeamState) -> dict:
    """[5-3] 예약 담당 노드 (dry-run)"""
    print(f"  [담당: Booking] 예약 처리 중...", end=" ", flush=True)
    result = booking_worker.execute(state["question"])
    print("완료")

    new_responses = state.get("worker_responses", []) + [result]
    return {"worker_responses": new_responses, "next_worker": "supervisor"}


def finish_node(state: TeamState) -> dict:
    """[5-3] 최종 답변 작성 노드"""
    responses_text = "\n".join(state.get("worker_responses", []))

    prompt = f"""담당자들의 응답을 바탕으로 최종 답변을 작성하세요:

원래 질문: {state["question"]}

담당자 응답:
{responses_text}

이를 종합한 최종 답변을 명확하고 간결하게 작성하세요."""

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

    if next_worker == "rules":
        return "rules"
    elif next_worker == "fee":
        return "fee"
    elif next_worker == "booking":
        return "booking"
    else:
        return "finish"


def route_after_worker(state: TeamState) -> Literal["supervisor"]:
    """[5-3] 담당 처리 후 지휘자로"""
    return "supervisor"


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
# 테스트
# ============================================================================

def run_team_test():
    """[5-3] 팀 협업 테스트"""

    test_question = "실무반 2개월 친구 할인 금액이랑 환불 규정 알려주고, 내일 오후 2시 GPU PC 1번 2시간 예약도 해줘"

    print(f"\n{'='*120}")
    print("[5-3] 팀 그래프: 지휘자 + 담당 에이전트")
    print(f"{'='*120}\n")

    print(f"[질문] {test_question}\n")
    print(f"{'─'*120}\n")

    # 초기 상태
    initial_state = {
        "question": test_question,
        "messages": [],
        "next_worker": "supervisor",
        "worker_responses": [],
        "call_count": 0,
        "final_answer": ""
    }

    # 그래프 실행
    graph = create_team_graph()

    start_time = time.time()

    try:
        result = graph.invoke(initial_state)

        elapsed_time = time.time() - start_time

        print(f"{'─'*120}\n")
        print(f"[실행 시간] {elapsed_time:.2f}초")
        print(f"[호출 횟수] {result.get('call_count', 0)}/4")
        print(f"[담당 응답] {len(result.get('worker_responses', []))}개")

        # 결과 저장
        output_data = {
            "question": test_question,
            "call_count": result.get("call_count", 0),
            "worker_responses": result.get("worker_responses", []),
            "final_answer": result.get("final_answer", ""),
            "elapsed_time": elapsed_time
        }

        output_file = DATA_DIR / "team_graph_test.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n[저장] {output_file}\n")

    except Exception as e:
        print(f"[ERROR] {str(e)}\n")


# ============================================================================
# 메인
# ============================================================================

def main():
    """메인 함수"""
    run_team_test()


if __name__ == "__main__":
    main()
