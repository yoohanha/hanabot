#!/usr/bin/env python3
# [5-1] LangGraph 에이전트 · 도구 반복 루프 (Agentic AI)

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

# [5-1] 4-1 · 4-2 도구 import (복사 금지)
labs_4_1_path = Path(__file__).parent.parent / "4-1"
labs_4_2_path = Path(__file__).parent.parent / "4-2"
sys.path.insert(0, str(labs_4_1_path))
sys.path.insert(0, str(labs_4_2_path))

from hana_tools import get_today, reserve_gpu_pc
from cancel_tool import cancel_gpu_pc

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import ToolMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import StreamWriter
from typing_extensions import TypedDict


# ============================================================================
# State 정의
# ============================================================================

class AgentState(TypedDict):
    """에이전트 상태"""
    messages: list  # 메시지 히스토리 (HumanMessage, AIMessage, ToolMessage)


# ============================================================================
# 도구 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TOOLS_DATA_DIR = labs_4_1_path / "data"
TOOLS_DATA_DIR.mkdir(parents=True, exist_ok=True)
RESERVES_FILE = TOOLS_DATA_DIR / "reserves_local.json"


# ============================================================================
# LLM 초기화
# ============================================================================

def create_agent_llm():
    """LLM 초기화 (5-1 규칙에 따라)"""
    today = datetime.now().strftime("%Y년 %m월 %d일")

    system_message = f"""당신은 하나봇 AI 에이전트입니다.
오늘 날짜: {today}
역할: 사용자의 GPU PC 예약 요청을 처리합니다.
도구: get_today (오늘 날짜), reserve_gpu_pc (예약), cancel_gpu_pc (취소)
주의: 사용자가 "다음 평일"이라고 하면 계산해서 예약하세요."""

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,          # [5-1] 에이전트 결정성 필요
        num_ctx=8192,          # [5-1] 컨텍스트 윈도우
        num_predict=512,       # [5-1] 최대 출력 토큰
        timeout=120            # [5-1] 타임아웃 120초
    )

    # 도구 바인딩
    tools = [get_today, reserve_gpu_pc, cancel_gpu_pc]
    llm_with_tools = llm.bind_tools(tools)

    return llm_with_tools, tools, system_message


# ============================================================================
# 노드: agent (모델 + bind_tools)
# ============================================================================

def agent_node(state: AgentState, llm_with_tools, system_msg: str) -> dict:
    """
    에이전트 노드: 모델이 도구를 선택하거나 최종 답변을 반환
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = state["messages"]

    # 시스템 메시지 추가 (첫 호출 시에만)
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=system_msg)] + messages

    # 모델 호출
    response = llm_with_tools.invoke(messages)

    # 메시지 히스토리에 추가
    return {"messages": messages + [response]}


# ============================================================================
# 그래프 생성
# ============================================================================

def create_agent_graph(llm_with_tools, tools, system_msg: str):
    """
    LangGraph StateGraph 생성
    - agent 노드: 모델 호출 (도구 선택 또는 최종 답변)
    - tools 노드: 도구 실행
    - tools_condition: tool_calls가 있으면 tools로, 없으면 END로
    """
    graph = StateGraph(AgentState)

    # 노드 추가
    graph.add_node(
        "agent",
        lambda state: agent_node(state, llm_with_tools, system_msg)
    )
    graph.add_node("tools", ToolNode(tools))

    # 엣지 추가
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        tools_condition,  # tool_calls 여부에 따라 분기
        {
            "tools": "tools",
            END: END
        }
    )
    graph.add_edge("tools", "agent")  # 도구 실행 후 agent로 돌아가기

    return graph.compile()


# ============================================================================
# 테스트 및 시각화
# ============================================================================

def save_mermaid_diagram(compiled_graph):
    """그래프를 Mermaid 다이어그램으로 저장"""
    diagram = compiled_graph.get_graph().draw_mermaid()

    output_file = Path(__file__).parent / "graph_agent.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# [5-1] LangGraph 에이전트 · 도구 반복 루프\n\n")
        f.write("```mermaid\n")
        f.write(diagram)
        f.write("\n```\n")

    print(f"✅ 그래프 저장: {output_file}")


def save_initial_reserves():
    """현재 예약 파일 저장 (복구용)"""
    if RESERVES_FILE.exists():
        with open(RESERVES_FILE, 'r', encoding='utf-8') as f:
            initial_reserves = json.load(f)
        return initial_reserves
    return []


def restore_reserves(initial_reserves):
    """예약 파일 복구"""
    with open(RESERVES_FILE, 'w', encoding='utf-8') as f:
        json.dump(initial_reserves, f, ensure_ascii=False, indent=2)


def test_agent():
    """에이전트 테스트"""
    # 그래프 생성
    llm_with_tools, tools, system_msg = create_agent_llm()
    compiled_graph = create_agent_graph(llm_with_tools, tools, system_msg)

    # 다이어그램 저장
    save_mermaid_diagram(compiled_graph)

    # 초기 예약 상태 저장
    initial_reserves = save_initial_reserves()

    print(f"\n{'='*80}")
    print("[5-1] LangGraph 에이전트 · 도구 반복 루프 테스트")
    print(f"{'='*80}\n")

    # 테스트 질문
    test_question = "나는 HANA-007, 다음 평일 오후 2시 GPU PC 1번 2시간 예약해줘"

    print(f"📌 질문: {test_question}\n")

    # 초기 상태
    initial_state = {
        "messages": [
            {"type": "human", "content": test_question}
        ]
    }

    # 상태를 올바른 형식으로 변환
    from langchain_core.messages import HumanMessage
    state = {
        "messages": [HumanMessage(content=test_question)]
    }

    # graph.stream() 사용 (매 단계 표시)
    print(f"{'─'*80}")
    print("🔄 에이전트 실행 (도구 반복 루프)\n")

    step_log = []
    tool_calls = []
    final_answer = ""

    try:
        for idx, step_output in enumerate(
            compiled_graph.stream(state, {"recursion_limit": 10})
        ):
            # step_output = {노드명: 상태}
            for node_name, node_state in step_output.items():
                messages = node_state.get("messages", [])

                if messages:
                    last_msg = messages[-1]
                    msg_type = type(last_msg).__name__

                    # 도구 호출 정보 추출
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tool_call in last_msg.tool_calls:
                            tool_name = tool_call.get("name", "?")
                            tool_args = tool_call.get("args", {})

                            print(f"  [{node_name}] 🔧 도구 호출")
                            print(f"      • 도구: {tool_name}")
                            print(f"      • 인자: {tool_args}\n")

                            tool_calls.append({
                                "node": node_name,
                                "tool": tool_name,
                                "args": tool_args
                            })

                    # 최종 답변
                    elif msg_type == "AIMessage" and not hasattr(last_msg, "tool_calls"):
                        final_answer = last_msg.content
                        print(f"  [{node_name}] 💬 최종 답변")
                        print(f"      {final_answer[:60]}{'...' if len(final_answer) > 60 else ''}\n")

    except Exception as e:
        print(f"❌ 에이전트 실행 오류: {str(e)}\n")

    print(f"{'─'*80}\n")

    # 결과 요약
    print(f"{'='*80}")
    print("📊 실행 결과")
    print(f"{'='*80}\n")

    print(f"도구 호출 횟수: {len(tool_calls)}\n")

    for idx, tool_call in enumerate(tool_calls, 1):
        node = tool_call["node"]
        tool = tool_call["tool"]
        args = tool_call["args"]

        print(f"[{idx}] {node:10} → {tool:20} {args}")

    # 메뉴 11번과 비교
    print(f"\n{'='*80}")
    print("📋 메뉴 11번 (for 루프) vs [5-1] LangGraph (stream 루프)")
    print(f"{'='*80}\n")

    comparison = [
        ("메뉴 11번 (4-4/interactive_with_guard.py)", "LangGraph (5-1/graph_agent.py)"),
        ("─"*35, "─"*35),
        ("for iteration in range(1, max_iterations + 1):", "for step_output in compiled_graph.stream(state):"),
        ("  response = llm_with_tools.invoke(messages)", "  for node_name, node_state in step_output.items():"),
        ("  if hasattr(response, 'tool_calls'):", "    if hasattr(last_msg, 'tool_calls'):"),
        ("    for tool_call in response.tool_calls:", "      for tool_call in last_msg.tool_calls:"),
        ("      tool_result = execute_tool(...)", "        [자동 도구 실행 (ToolNode)]"),
        ("      messages.append(ToolMessage(...))", "        [자동 메시지 추가]"),
        ("  else:", "    else:"),
        ("    break [최종 답변]", "      [END로 그래프 종료]"),
        ("", ""),
        ("장점: 명시적, 제어 가능", "장점: 선언적, 프레임워크 활용"),
        ("단점: 도구 로직 직접 구현", "단점: 프레임워크 이해 필요"),
    ]

    print("| 메뉴 11번 (4-4) | LangGraph (5-1) |")
    print("|---|---|")
    for menu_11, graph_5_1 in comparison[2:]:
        print(f"| {menu_11[:40]:40} | {graph_5_1[:40]:40} |")

    # 현재 예약 파일 확인
    print(f"\n{'='*80}")
    print("📁 예약 파일 상태")
    print(f"{'='*80}\n")

    if RESERVES_FILE.exists():
        with open(RESERVES_FILE, 'r', encoding='utf-8') as f:
            current_reserves = json.load(f)

        print(f"현재 예약: {len(current_reserves)}개\n")

        for idx, reserve in enumerate(current_reserves, 1):
            reserve_id = reserve.get("reserve_id", "?")
            student_id = reserve.get("student_id", "?")
            date = reserve.get("date", "?")
            start_time = reserve.get("start_time", "?")
            pc_num = reserve.get("pc_number", "?")

            print(f"  {idx}. {reserve_id} - {student_id} - {date} {start_time} (GPU-{pc_num})")

    else:
        current_reserves = []
        print("예약 파일이 없습니다.")

    # 예약 취소 (원래대로 복구)
    if current_reserves:
        print(f"\n{'─'*80}")
        print("🔄 예약 취소 (파일 복구 중...)\n")

        restore_reserves(initial_reserves)

        print(f"✅ 예약 파일 복구됨 (초기 상태: {len(initial_reserves)}개)\n")

    # JSON 저장
    result_file = DATA_DIR / "graph_agent_test.json"
    test_result = {
        "question": test_question,
        "tool_calls": tool_calls,
        "final_answer": final_answer,
        "tool_count": len(tool_calls)
    }

    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(test_result, f, ensure_ascii=False, indent=2)

    print(f"✅ 테스트 결과 저장: {result_file}")


def main():
    """메인 함수"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    test_agent()


if __name__ == "__main__":
    main()
