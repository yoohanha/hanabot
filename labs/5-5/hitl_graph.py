#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-5] Human in the Loop 그래프: interrupt 로 멈추고 사람의 답(y · n · 수정)으로 이어가기

import sys
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# [5-5] 3교시 team_graph import (복사 금지)
sys.path.insert(0, str(Path(__file__).parent.parent / "5-3"))
from team_graph import TeamState, supervisor_node, rules_node, fee_node, finish_node

# [5-5] 도구 import (복사 금지, import만)
sys.path.insert(0, str(Path(__file__).parent.parent / "4-1"))
from hana_tools import reserve_gpu_pc
sys.path.insert(0, str(Path(__file__).parent.parent / "4-2"))
from cancel_tool import cancel_gpu_pc

# [5-5] 4-4 도구 가드 import (검사 함수만 사용 · guard() 는 안에 input() 이 있어 쓰지 않음)
sys.path.insert(0, str(Path(__file__).parent.parent / "4-4"))
from guard_tool import ToolGuard

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import interrupt, Command

# [5-5] 데이터 경로 (예약 파일은 labs/4-1/data 만)
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESERVES_FILE = Path(__file__).parent.parent / "4-1" / "data" / "reserves_local.json"


# ============================================================================
# [5-5] 상태: 3교시 TeamState 에 승인용 칸을 더함
# (노드 안에서 state["칸"] = 값 은 저장되지 않음 → 반드시 return {...} 로 바꾸기)
# ============================================================================

class HitlState(TeamState, total=False):
    student_id: str      # 로그인 학번 (가드 기준)
    hitl_type: str       # "reserve" · "cancel"
    hitl_params: dict    # 승인 카드에 보여줄 인자
    decision: str        # 사람의 답: y · n · 수정 내용 · blocked


# ============================================================================
# [5-5] 예약 정보 추출 (format="json")
# ============================================================================

def _next_weekday(word: str) -> str:
    """'다음 주 월요일' 같은 말을 날짜로 (모델이 날짜 계산을 자주 틀려서 코드로 계산)"""
    days = ["월", "화", "수", "목", "금", "토", "일"]
    today = datetime.now()
    for i, d in enumerate(days):
        if f"{d}요일" in word:
            ahead = (i - today.weekday()) % 7 or 7
            if "다음 주" in word or "다음주" in word:
                ahead = (7 - today.weekday()) + i
            return (today + timedelta(days=ahead)).strftime("%Y-%m-%d")
    if "모레" in word:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    if "내일" in word:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    return ""


def extract_reservation_params(question: str, student_id: str) -> Dict[str, Any]:
    """[5-5] 질문에서 예약 인자를 JSON 으로 뽑기 · 날짜는 코드로 보정"""
    from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

    llm = ChatOllama(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0, format="json")
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""오늘은 {today} 입니다. 질문에서 GPU PC 예약 정보를 JSON 으로만 뽑으세요.
형식: {{"date": "YYYY-MM-DD", "start_time": "HH:MM", "duration": 2, "pc_number": 1}}
- 오후 2시 = 14:00 · duration 은 시간 수 · pc_number 는 PC 번호
질문: {question}"""
    params: Dict[str, Any] = {}
    try:
        text = llm.invoke([HumanMessage(content=prompt)]).content
        m = re.search(r"\{.*\}", text, re.DOTALL)
        params = json.loads(m.group(0)) if m else {}
    except Exception as e:
        print(f"⚠️  추출 실패: {e}")

    # 코드로 보정 (모델이 틀려도 질문 글자에서 다시 읽기)
    date = _next_weekday(question)
    if date:
        params["date"] = date
    m = re.search(r"(오전|오후)?\s*(\d{1,2})\s*시(?!간)", question)
    if m:
        hour = int(m.group(2))
        if m.group(1) == "오후" and hour < 12:
            hour += 12
        params["start_time"] = f"{hour:02d}:00"
    m = re.search(r"(\d+)\s*시간", question)
    if m:
        params["duration"] = int(m.group(1))
    m = re.search(r"(?:PC|pc|피시)\s*(\d+)\s*번?|(\d+)\s*번\s*(?:PC|pc)", question)
    if m:
        params["pc_number"] = int(m.group(1) or m.group(2))

    params["student_id"] = student_id
    params["duration"] = int(params.get("duration", 2) or 2)
    params["pc_number"] = int(params.get("pc_number", 1) or 1)
    return params


def apply_edit(params: Dict[str, Any], edit: str) -> Dict[str, Any]:
    """[5-5] '3시로' · '6시간으로' · 'PC 2번으로' 수정 내용을 인자에 반영"""
    new = dict(params)
    m = re.search(r"(\d+)\s*시간", edit)
    if m:
        new["duration"] = int(m.group(1))
    m = re.search(r"(오전|오후)?\s*(\d{1,2})\s*시(?!간)", edit)
    if m:
        hour = int(m.group(2))
        # '3시' 처럼 오전/오후가 없으면 수업 시간(9~21시)에 맞게 오후로 봄
        if m.group(1) == "오후" or (m.group(1) is None and hour < 9):
            hour += 12
        new["start_time"] = f"{hour:02d}:00"
    m = re.search(r"(?:PC|pc|피시)\s*(\d+)|(\d+)\s*번", edit)
    if m:
        new["pc_number"] = int(m.group(1) or m.group(2))
    date = _next_weekday(edit)
    if date:
        new["date"] = date
    return new


def _load_reserves() -> list:
    try:
        return json.loads(RESERVES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


# ============================================================================
# [5-5] 노드
# ============================================================================

def prepare_node(state: HitlState) -> dict:
    """[5-5] 예약 담당: 예약인지 취소인지 보고 승인 카드에 넣을 인자 준비"""
    question = state.get("question", "")
    login = state.get("student_id", "HANA-001")

    if "취소" in question or "cancel" in question.lower():
        # 질문에 학번이 있으면 그 학번의 예약, 없으면 내 예약 중 가장 최근 것
        m = re.search(r"HANA-\d{3}", question.upper())
        owner = m.group(0) if m else login
        mine = [r for r in _load_reserves() if r.get("student_id") == owner]
        if not mine:
            return {"hitl_type": "cancel", "hitl_params": {"student_id": owner},
                    "decision": "blocked", "final_answer": f"❌ {owner} 의 예약이 없어요"}
        r = mine[-1]
        params = {"reserve_id": r.get("reserve_id"), "date": r.get("date"),
                  "start_time": r.get("start_time"), "duration": r.get("duration"),
                  "pc_number": r.get("pc_number"), "student_id": owner}
        return {"hitl_type": "cancel", "hitl_params": params, "decision": ""}

    params = extract_reservation_params(question, login)
    return {"hitl_type": "reserve", "hitl_params": params, "decision": ""}


def guard_node(state: HitlState) -> dict:
    """[5-5] 4-4 가드 검사 (처음 인자 · 수정한 인자 모두 여기를 지남)"""
    if state.get("decision") == "blocked":
        return {}
    params = state.get("hitl_params", {})
    guard = ToolGuard(login_student_id=state.get("student_id", "HANA-001"))
    # 4-4 가드는 도구 이름을 "reserve_gpu" · "cancel_gpu" 로 알아봄
    name = "reserve_gpu" if state.get("hitl_type") == "reserve" else "cancel_gpu"
    ok, msg = guard._check_authorization(name, params)
    if ok:
        ok, msg = guard._check_arguments(name, params)
    if not ok:
        print(f"⚠️  가드가 막음: {msg}")
        return {"decision": "blocked", "final_answer": msg}
    return {}


def approve_node(state: HitlState) -> dict:
    """[5-5] 멈추고 사람에게 묻기만 함 (재개하면 이 노드가 처음부터 다시 돌기 때문에 실행은 하지 않음)"""
    card = {"type": "reservation" if state.get("hitl_type") == "reserve" else "cancellation",
            **state.get("hitl_params", {})}
    answer = interrupt(card)            # 사람의 답이 여기로 돌아옴
    return {"decision": str(answer).strip()}


def modify_node(state: HitlState) -> dict:
    """[5-5] 수정 내용으로 인자를 바꿈 → 가드 → 다시 승인 (바로 실행하지 않음)"""
    new = apply_edit(state.get("hitl_params", {}), state.get("decision", ""))
    print(f"✏️  바뀐 인자: {new}")
    return {"hitl_params": new, "decision": ""}


def execute_node(state: HitlState) -> dict:
    """[5-5] 사람이 y 라고 한 뒤에만 실제 도구 실행 (.invoke)"""
    params = state.get("hitl_params", {})
    if state.get("hitl_type") == "reserve":
        result = reserve_gpu_pc.invoke({
            "date": params.get("date"), "start_time": params.get("start_time"),
            "duration": params.get("duration"), "pc_number": params.get("pc_number"),
            "student_id": params.get("student_id"),
        })
    else:
        result = cancel_gpu_pc.invoke({"reservation_id": params.get("reserve_id")})
    return _done(state, result)


def reject_node(state: HitlState) -> dict:
    """[5-5] 거절 · 가드 차단: 아무것도 실행하지 않음"""
    if state.get("decision") == "blocked":
        return _done(state, f"🛡️ 가드가 막았어요: {state.get('final_answer', '')}")
    what = "예약" if state.get("hitl_type") == "reserve" else "취소"
    return _done(state, f"🙅 거절해서 {what}하지 않았어요")


def _done(state: HitlState, text: str) -> dict:
    """결과를 담당 응답에 넣고 지휘자에게 돌아감 (3교시 finish_node 가 최종 답에 합침)"""
    responses = state.get("worker_responses", []) + [{"tool": "reserve_gpu_pc", "result": text, "raw": text}]
    return {"worker_responses": responses, "final_answer": text}


# ============================================================================
# [5-5] 그래프 구성
# ============================================================================

def route_supervisor(state: HitlState) -> str:
    nxt = state.get("next_worker", "FINISH")
    return {"RULES": "rules", "FEE": "fee", "BOOKING": "prepare"}.get(nxt, "finish")


def route_guard(state: HitlState) -> str:
    return "reject" if state.get("decision") == "blocked" else "approve"


def route_approve(state: HitlState) -> str:
    d = state.get("decision", "").lower()
    if d in ("y", "yes", "승인"):
        return "execute"
    if d in ("n", "no", "거절"):
        return "reject"
    return "modify"                     # 그 밖의 답은 수정 내용


def create_hitl_graph():
    """[5-5] supervisor → (rules · fee · 예약[준비 → 가드 → 승인 → 실행/거절/수정]) → finish"""
    g = StateGraph(HitlState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("rules", rules_node)
    g.add_node("fee", fee_node)
    g.add_node("prepare", prepare_node)
    g.add_node("guard", guard_node)
    g.add_node("approve", approve_node)
    g.add_node("modify", modify_node)
    g.add_node("execute", execute_node)
    g.add_node("reject", reject_node)
    g.add_node("finish", finish_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", route_supervisor)
    g.add_edge("rules", "supervisor")
    g.add_edge("fee", "supervisor")
    g.add_edge("prepare", "guard")
    g.add_conditional_edges("guard", route_guard)
    g.add_conditional_edges("approve", route_approve)
    g.add_edge("modify", "guard")       # 수정해도 가드를 다시 지남
    g.add_edge("execute", "supervisor")
    g.add_edge("reject", "supervisor")
    g.add_edge("finish", END)
    return g


def open_checkpointer(path: Path = DATA_DIR / "checkpoints.db") -> SqliteSaver:
    """[5-5] 파일에 저장하는 체크포인터 (프로그램을 꺼도 멈춘 자리를 기억)"""
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))


def initial_state(question: str, student_id: str) -> dict:
    return {"question": question, "messages": [], "remaining_requests": [], "next_worker": "",
            "worker_responses": [], "call_count": 0, "final_answer": "", "student_id": student_id}


# ============================================================================
# [5-5] 터미널 실행: 멈추면 묻고, 꺼도 같은 thread_id 로 다시 켜면 이어짐
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Human in the Loop 그래프 (터미널)")
    parser.add_argument("--question", default="다음 주 월요일 오후 2시에 GPU PC 1번 2시간 예약해줘")
    parser.add_argument("--student-id", default="HANA-007")
    parser.add_argument("--thread-id", default="", help="이어서 할 대화 번호 (예: HANA-007-1)")
    args = parser.parse_args()

    thread_id = args.thread_id or f"{args.student_id}-1"
    config = {"configurable": {"thread_id": thread_id}}
    app = create_hitl_graph().compile(checkpointer=open_checkpointer())

    print(f"🔗 thread_id: {thread_id}")
    if app.get_state(config).next:
        print("⏸️  이전에 멈춘 요청이 있어요. 이어서 진행합니다.")
        result = {"__interrupt__": app.get_state(config).tasks[0].interrupts}
    else:
        print(f"📌 질문: {args.question}")
        result = app.invoke(initial_state(args.question, args.student_id), config)

    while "__interrupt__" in result:
        card = result["__interrupt__"][0].value
        print("\n[승인 카드]", json.dumps(card, ensure_ascii=False))
        answer = input("y 승인 · n 거절 · 수정 내용(예: 3시로): ")
        result = app.invoke(Command(resume=answer), config)

    print("\n✅ 최종 답:", result.get("final_answer", ""))
