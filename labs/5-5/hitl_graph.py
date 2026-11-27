#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-5] Human in the Loop 그래프: 예약 승인 대기

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Literal

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# [5-5] 3교시 team_graph import
sys.path.insert(0, str(Path(__file__).parent.parent / "5-3"))
from team_graph import (
    TeamState,
    supervisor_node, rules_node, fee_node, booking_node, finish_node
)

# [5-5] 도구 import (복사 금지, import만)
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))
from hana_tools import reserve_gpu_pc

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt

# [5-5] 데이터 경로
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# [5-5] 예약 정보 추출 (format="json" 사용)
# ============================================================================

def extract_reservation_params(question: str, student_id: str = "HANA-001") -> Dict[str, Any]:
    """
    [5-5] 질문에서 JSON 형식으로 예약 인자 추출.
    LLM의 format="json" 설정으로 JSON 응답 받기.
    """
    from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
    from datetime import timedelta

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        format="json"
    )

    # 내일 날짜 미리 계산
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    prompt = f"""질문을 분석하여 GPU PC 예약 정보를 JSON으로 추출하세요.

질문: {question}

다음 정보를 추출하세요:
- action: "reserve" 또는 "cancel"
- date: "YYYY-MM-DD" 형식 (내일이면 {tomorrow})
- start_time: "HH:MM" 형식 (09:00, 14:00 등)
- duration: 2 또는 4 (시간)
- pc_number: 1~4 (PC 번호)

응답은 JSON 형식으로만 반환하세요:
{{"action": "reserve", "date": "{tomorrow}", "start_time": "14:00", "duration": 2, "pc_number": 1}}"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        json_str = response.content.strip()

        # JSON 추출
        json_match = re.search(r'\{[^{}]*\}', json_str, re.DOTALL)
        if json_match:
            params = json.loads(json_match.group(0))
            params["student_id"] = student_id
            return params
    except Exception as e:
        print(f"⚠️  추출 실패: {str(e)}")

    return {}


# ============================================================================
# [5-5] Interrupt 전에 예약 정보 표시 & 사람 승인
# ============================================================================

def show_approval_before_booking(state: TeamState) -> dict:
    """
    [5-5] booking 담당이 act 하기 직전에 interrupt로 멈추기.
    사람에게 예약 정보를 보여주고 y/n 받기.
    """
    question = state.get("question", "")

    # "취소" 단어 감지
    if "취소" in question or "cancel" in question.lower():
        return handle_cancellation(state)

    # 예약 정보 추출 (format="json" 사용)
    params = extract_reservation_params(question)

    if not params:
        # 추출 실패 → booking_node로 그냥 진행
        return {"next_worker": "booking"}

    if params.get("action") != "reserve":
        # 취소 → 취소 처리
        return handle_cancellation(state)

    # 예약 정보 표시
    print("\n" + "=" * 70)
    print("🔔 GPU PC 예약 승인 대기")
    print("=" * 70)
    print(f"\n📅 날짜: {params.get('date', 'N/A')}")
    print(f"🕐 시작 시간: {params.get('start_time', 'N/A')}")
    print(f"⏱️  이용시간: {params.get('duration', 'N/A')}시간")
    print(f"🖥️  PC 번호: {params.get('pc_number', 'N/A')}번")
    print(f"👤 학번: {params.get('student_id', 'HANA-001')}")
    print("\n승인하시겠습니까? (y/n): ", end="", flush=True)

    # 사람의 승인 받기
    decision = input().strip().lower()

    if decision == "y":
        # [5-5] 승인: 상태에 저장하고 계속
        state["_hitl_approval"] = True
        state["_hitl_params"] = params
        return state
    elif decision == "n":
        # 거절
        print("❌ 예약이 거절되었습니다.")
        state["final_answer"] = "❌ 예약이 거절되었습니다."
        state["next_worker"] = "FINISH"
        return state
    else:
        print("❌ y 또는 n을 입력하세요.")
        return show_approval_before_booking(state)  # 다시 묻기


# ============================================================================
# [5-5] 실제 예약 실행 (다음 노드)
# ============================================================================

def execute_booking_with_approval(state: TeamState) -> dict:
    """
    [5-5] 승인된 예약을 실제로 실행합니다.
    """
    if not state.get("_hitl_approval"):
        return {"next_worker": "FINISH"}

    params = state.get("_hitl_params", {})

    # tool.invoke로 실행 (복사 금지)
    try:
        result = reserve_gpu_pc(
            date=params.get("date"),
            start_time=params.get("start_time"),
            duration=params.get("duration"),
            pc_number=params.get("pc_number"),
            student_id=params.get("student_id", "HANA-001")
        )

        # 성공하면 reserves_local.json에 저장
        if not result.startswith("❌"):
            data_file = Path(__file__).parent.parent / "4-1" / "data" / "reserves_local.json"
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    reserves = json.load(f)
            except:
                reserves = []

            # 새 예약 추가
            new_reserve = {
                "reserve_id": f"R-{datetime.now().strftime('%Y%m%d')}-{len(reserves)+1:02d}",
                "student_id": params.get("student_id", "HANA-001"),
                "date": params.get("date"),
                "start_hour": int(params.get("start_time", "09:00").split(":")[0]),
                "start_time": params.get("start_time"),
                "duration": params.get("duration"),
                "pc_number": params.get("pc_number"),
                "created_at": datetime.now().isoformat()
            }
            reserves.append(new_reserve)

            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(reserves, f, ensure_ascii=False, indent=2)

            print(f"✓ 예약이 저장되었습니다.")

        # 도구 결과를 worker_responses에 추가
        new_responses = state.get("worker_responses", []) + [{
            "tool": "reserve_gpu_pc",
            "result": result[:100],
            "raw": result
        }]

        return {
            "worker_responses": new_responses,
            "next_worker": "FINISH"
        }

    except Exception as e:
        print(f"❌ 예약 실행 오류: {str(e)}")
        return {
            "worker_responses": state.get("worker_responses", []) + [{
                "tool": "reserve_gpu_pc",
                "result": f"오류: {str(e)}",
                "raw": f"오류: {str(e)}"
            }],
            "next_worker": "FINISH"
        }


# ============================================================================
# [5-5] 취소 처리
# ============================================================================

def handle_cancellation(state: TeamState) -> dict:
    """[5-5] GPU PC 예약 취소"""
    data_file = Path(__file__).parent.parent / "4-1" / "data" / "reserves_local.json"

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            reserves = json.load(f)
    except:
        print("❌ 예약 목록을 불러올 수 없습니다.")
        state["next_worker"] = "FINISH"
        return state

    if not reserves:
        print("❌ 예약이 없습니다.")
        state["next_worker"] = "FINISH"
        return state

    # 가장 최근 예약 표시
    latest = reserves[-1]

    print("\n" + "=" * 70)
    print("🔔 GPU PC 예약 취소 승인 대기")
    print("=" * 70)
    print(f"\n❌ 취소 대상:")
    print(f"  예약 ID: {latest.get('reserve_id')}")
    print(f"  📅 날짜: {latest.get('date')}")
    print(f"  🕐 시간: {latest.get('start_time')}")
    print(f"  🖥️  PC: {latest.get('pc_number')}번")
    print(f"  👤 학번: {latest.get('student_id')}")
    print("\n승인하시겠습니까? (y/n): ", end="", flush=True)

    decision = input().strip().lower()

    if decision == "y":
        # 취소 실행
        reserves.pop()
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(reserves, f, ensure_ascii=False, indent=2)
        result = f"✓ 예약 {latest.get('reserve_id')} 취소됨"
        print(result)
    elif decision == "n":
        result = "❌ 취소가 거절되었습니다."
        print(result)
    else:
        result = "❌ 잘못된 입력입니다."
        print(result)

    # 도구 결과 추가
    new_responses = state.get("worker_responses", []) + [{
        "tool": "cancel_gpu_pc",
        "result": result[:100],
        "raw": result
    }]

    return {
        "worker_responses": new_responses,
        "next_worker": "FINISH"
    }


# ============================================================================
# [5-5] 그래프 구성 (team_graph wrapping)
# ============================================================================

def create_hitl_graph():
    """
    [5-5] Human in the Loop 그래프.
    team_graph의 노드들에 approval 로직 추가.
    """
    graph = StateGraph(TeamState)

    # [5-5] team_graph의 노드들 사용 (import됨)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rules", rules_node)
    graph.add_node("fee", fee_node)
    graph.add_node("show_approval", show_approval_before_booking)
    graph.add_node("execute_booking", execute_booking_with_approval)
    graph.add_node("finish", finish_node)

    # 엣지 추가
    graph.add_edge(START, "supervisor")

    # Conditional routing
    def route_next(state: TeamState) -> str:
        next_worker = state.get("next_worker", "FINISH")
        if next_worker == "RULES":
            return "rules"
        elif next_worker == "FEE":
            return "fee"
        elif next_worker == "BOOKING":
            return "show_approval"  # [5-5] booking 전에 approval
        else:
            return "finish"

    graph.add_conditional_edges("supervisor", route_next)

    # Approval → Booking
    def approval_route(state: TeamState) -> str:
        """승인 결과에 따른 라우팅"""
        if state.get("_hitl_approval"):
            return "execute_booking"
        elif state.get("next_worker") == "FINISH":
            return "finish"
        else:
            return "finish"

    graph.add_conditional_edges("show_approval", approval_route)

    # 담당 → 지휘자
    graph.add_edge("rules", "supervisor")
    graph.add_edge("fee", "supervisor")
    graph.add_edge("execute_booking", "supervisor")

    # 최종
    graph.add_edge("finish", END)

    return graph


# ============================================================================
# [5-5] 테스트 & 실행
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Human in the Loop 그래프 테스트")
    parser.add_argument("--question", default="내일 오후 2시에 GPU PC 1번 2시간 예약해줘", help="질문")
    parser.add_argument("--student-id", default="HANA-001", help="학번")
    parser.add_argument("--thread-id", default=None, help="스레드 ID (기본: 학번-timestamp)")
    args = parser.parse_args()

    # Thread ID 설정 (형식: 학번-대화번호)
    if args.thread_id is None:
        conversation_num = datetime.now().strftime('%Y%m%d%H%M%S')
        args.thread_id = f"{args.student_id}-{conversation_num}"

    print(f"🚀 Human in the Loop 그래프 테스트")
    print(f"📌 질문: {args.question}")
    print(f"👤 학번: {args.student_id}")
    print(f"🔗 Thread ID: {args.thread_id}")
    print("=" * 70)

    # [5-5] 체크포인터 설정 (SqliteSaver)
    checkpointer = SqliteSaver(str(DATA_DIR / "checkpoints.db"))

    # 그래프 생성 & 컴파일
    graph = create_hitl_graph()
    compiled_graph = graph.compile(checkpointer=checkpointer)

    # 초기 상태
    initial_state = {
        "question": args.question,
        "messages": [],
        "remaining_requests": [],
        "next_worker": "RULES",
        "worker_responses": [],
        "call_count": 0,
        "final_answer": ""
    }

    # 그래프 실행
    try:
        print("\n⏳ 그래프 실행 중...\n")
        result = compiled_graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": args.thread_id}}
        )

        print("\n" + "=" * 70)
        print("✅ 최종 결과:")
        print("=" * 70)
        print(f"\n{result.get('final_answer', '결과 없음')}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
