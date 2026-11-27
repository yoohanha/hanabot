#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-5] Human in the Loop 그래프: Interrupt + 승인

import os
import sys
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Literal

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# [5-5] 3교시 team_graph import
sys.path.insert(0, str(Path(__file__).parent.parent / "5-3"))
from team_graph import TeamState, supervisor_node, rules_node, fee_node, booking_node, finish_node

# [5-5] 도구 import (복사 금지, import만)
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))
from hana_tools import reserve_gpu_pc

# [5-5] 가드 import
labs_4_4_path = Path(__file__).parent.parent / "4-4"
sys.path.insert(0, str(labs_4_4_path))
from guard_tool import ToolGuard

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

# [5-5] 데이터 경로
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# [5-5] 예약 정보 추출 (format="json")
# ============================================================================

def extract_reservation_params(question: str, student_id: str = "HANA-001") -> Dict[str, Any]:
    """[5-5] 질문에서 JSON 형식으로 예약 인자 추출."""
    from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        format="json"
    )

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
        json_match = re.search(r'\{[^{}]*\}', json_str, re.DOTALL)
        if json_match:
            params = json.loads(json_match.group(0))
            params["student_id"] = student_id
            return params
    except Exception as e:
        print(f"⚠️  추출 실패: {str(e)}")

    return {}


# ============================================================================
# [5-5] Interrupt 노드: 멈춤 + 정보 표시
# ============================================================================

def approval_node(state: TeamState) -> dict:
    """[5-5] Interrupt로 멈추고 사용자 승인 대기. 묻기만 함."""
    question = state.get("question", "")

    # 취소 감지
    if "취소" in question or "cancel" in question.lower():
        return handle_cancellation_approval(state)

    # 예약 정보 추출
    params = extract_reservation_params(question, state.get("student_id", "HANA-001"))

    if not params or params.get("action") != "reserve":
        return handle_cancellation_approval(state)

    # [5-5] 예약 정보 표시
    print("\n" + "=" * 70)
    print("🔔 GPU PC 예약 승인 대기")
    print("=" * 70)
    print(f"\n📅 날짜: {params.get('date', 'N/A')}")
    print(f"🕐 시작 시간: {params.get('start_time', 'N/A')}")
    print(f"⏱️  이용시간: {params.get('duration', 'N/A')}시간")
    print(f"🖥️  PC 번호: {params.get('pc_number', 'N/A')}번")
    print(f"👤 학번: {params.get('student_id', 'HANA-001')}")

    # [5-5] 가드 검사
    guard = ToolGuard(login_student_id=params.get("student_id", "HANA-001"), verbose=False)
    guard_passed, guard_msg = guard._check_arguments("reserve_gpu", params)

    if not guard_passed:
        print(f"\n⚠️  {guard_msg}")
        state["final_answer"] = f"❌ {guard_msg}"
        return {"next_worker": "FINISH"}

    # [5-5] 상태에 먼저 저장 (interrupt 전에)
    state["_hitl_params"] = params
    state["_hitl_type"] = "reserve"
    state["_hitl_approval"] = True

    # [5-5] Interrupt로 멈춤 (사용자 승인 대기)
    approval_data = {
        "type": "reservation",
        "date": params.get("date"),
        "start_time": params.get("start_time"),
        "duration": params.get("duration"),
        "pc_number": params.get("pc_number"),
        "student_id": params.get("student_id")
    }

    interrupt(value=approval_data)


def handle_cancellation_approval(state: TeamState) -> dict:
    """[5-5] 취소 승인 (Interrupt)."""
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

    # [5-5] 가드 검사
    guard = ToolGuard(login_student_id=latest.get("student_id", "HANA-001"), verbose=False)
    cancel_params = {
        "student_id": latest.get("student_id"),
        "reserve_id": latest.get("reserve_id"),
        "date": latest.get("date"),
        "start_time": latest.get("start_time")
    }
    guard_passed, guard_msg = guard._check_authorization("cancel_gpu", cancel_params)

    if not guard_passed:
        print(f"\n⚠️  {guard_msg}")
        state["final_answer"] = f"❌ {guard_msg}"
        return {"next_worker": "FINISH"}

    # [5-5] 상태에 먼저 저장
    state["_hitl_params"] = cancel_params
    state["_hitl_type"] = "cancel"
    state["_hitl_reserve_id"] = latest.get("reserve_id")
    state["_hitl_approval"] = True

    # [5-5] Interrupt로 멈춤
    cancel_data = {
        "type": "cancellation",
        "reserve_id": latest.get("reserve_id"),
        "date": latest.get("date"),
        "start_time": latest.get("start_time"),
        "pc_number": latest.get("pc_number"),
        "student_id": latest.get("student_id")
    }

    interrupt(value=cancel_data)


# ============================================================================
# [5-5] 실행 노드: 도구 호출 (.invoke 사용)
# ============================================================================

def execute_node(state: TeamState) -> dict:
    """[5-5] 승인된 요청 실행 (도구 호출)."""
    # [5-5] 거절 또는 미승인시 종료
    if not state.get("_hitl_approval"):
        state["final_answer"] = "❌ 요청이 거절되었습니다."
        return {"next_worker": "FINISH"}

    if state.get("_hitl_type") == "reserve":
        params = state.get("_hitl_params", {})

        try:
            # [5-5] .invoke 사용 (함수처럼 부르기 금지)
            result = reserve_gpu_pc.invoke(
                input={
                    "date": params.get("date"),
                    "start_time": params.get("start_time"),
                    "duration": params.get("duration"),
                    "pc_number": params.get("pc_number"),
                    "student_id": params.get("student_id", "HANA-001")
                }
            )

            # 결과 저장
            if not result.startswith("❌"):
                data_file = Path(__file__).parent.parent / "4-1" / "data" / "reserves_local.json"
                try:
                    with open(data_file, 'r', encoding='utf-8') as f:
                        reserves = json.load(f)
                except:
                    reserves = []

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

            state["final_answer"] = result
            return {"next_worker": "FINISH"}

        except Exception as e:
            print(f"❌ 예약 실행 오류: {str(e)}")
            state["final_answer"] = f"❌ {str(e)}"
            return {"next_worker": "FINISH"}

    elif state.get("_hitl_type") == "cancel":
        data_file = Path(__file__).parent.parent / "4-1" / "data" / "reserves_local.json"

        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                reserves = json.load(f)

            # 가장 최근 예약 삭제
            if reserves:
                reserves.pop()
                with open(data_file, 'w', encoding='utf-8') as f:
                    json.dump(reserves, f, ensure_ascii=False, indent=2)
                result = f"✓ 예약 {state.get('_hitl_reserve_id')} 취소됨"
            else:
                result = "❌ 취소할 예약이 없습니다."

            state["final_answer"] = result
            return {"next_worker": "FINISH"}

        except Exception as e:
            print(f"❌ 취소 오류: {str(e)}")
            state["final_answer"] = f"❌ {str(e)}"
            return {"next_worker": "FINISH"}

    return {"next_worker": "FINISH"}


# ============================================================================
# [5-5] 그래프 구성
# ============================================================================

def create_hitl_graph():
    """[5-5] Human in the Loop 그래프 (Interrupt + Command)."""
    graph = StateGraph(TeamState)

    # 노드 추가
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rules", rules_node)
    graph.add_node("fee", fee_node)
    graph.add_node("approval", approval_node)
    graph.add_node("execute", execute_node)
    graph.add_node("finish", finish_node)

    # 엣지 설정
    graph.add_edge(START, "supervisor")

    # 조건부 라우팅
    def route_next(state: TeamState) -> str:
        next_worker = state.get("next_worker", "FINISH")
        if next_worker == "RULES":
            return "rules"
        elif next_worker == "FEE":
            return "fee"
        elif next_worker == "BOOKING":
            return "approval"  # [5-5] booking 대신 approval
        else:
            return "finish"

    graph.add_conditional_edges("supervisor", route_next)
    graph.add_edge("rules", "supervisor")
    graph.add_edge("fee", "supervisor")
    graph.add_edge("approval", "execute")
    graph.add_edge("execute", "finish")
    graph.add_edge("finish", END)

    return graph


# ============================================================================
# [5-5] 메인 실행
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Human in the Loop 그래프 테스트")
    parser.add_argument("--question", default="내일 오후 2시에 GPU PC 1번 2시간 예약해줘", help="질문")
    parser.add_argument("--student-id", default="HANA-001", help="학번")
    args = parser.parse_args()

    # Thread ID 형식: 학번-타임스탬프
    thread_id = f"{args.student_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    print(f"🚀 Human in the Loop 그래프 테스트")
    print(f"📌 질문: {args.question}")
    print(f"👤 학번: {args.student_id}")
    print(f"🔗 Thread ID: {thread_id}")
    print("=" * 70)

    # [5-5] SqliteSaver 설정 (sqlite3.connect 사용)
    db_path = str(DATA_DIR / "checkpoints.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # 그래프 생성 및 컴파일
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
        "final_answer": "",
        "student_id": args.student_id
    }

    # 그래프 실행
    try:
        print("\n⏳ 그래프 실행 중...\n")
        result = compiled_graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}}
        )

        print("\n" + "=" * 70)
        print("✅ 최종 결과:")
        print("=" * 70)
        print(f"\n{result.get('final_answer', '결과 없음')}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
