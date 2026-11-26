#!/usr/bin/env python3
# [5-1] 대화형 모드 테스트 스크립트

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [5-1] 4-1 · 4-2 도구 import
labs_4_1_path = Path(__file__).parent.parent / "4-1"
labs_4_2_path = Path(__file__).parent.parent / "4-2"
sys.path.insert(0, str(labs_4_1_path))
sys.path.insert(0, str(labs_4_2_path))

from hana_tools import get_today, reserve_gpu_pc
from cancel_tool import cancel_gpu_pc

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict


# ============================================================================
# State 정의
# ============================================================================

class AgentState(TypedDict):
    """에이전트 상태"""
    messages: list


# ============================================================================
# LLM 초기화
# ============================================================================

def create_agent_llm():
    """LLM 초기화"""
    from datetime import datetime

    today = datetime.now().strftime("%Y년 %m월 %d일")

    system_message = f"""당신은 하나봇 AI 에이전트입니다.
오늘 날짜: {today}
역할: 학원 관련 질문을 답변하고, 학생의 관심사를 기억합니다."""

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        num_ctx=8192,
        num_predict=512,
        timeout=120
    )

    tools = [get_today, reserve_gpu_pc, cancel_gpu_pc]
    llm_with_tools = llm.bind_tools(tools)

    return llm_with_tools, tools, system_message


# ============================================================================
# 노드: agent
# ============================================================================

def agent_node(state: AgentState, llm_with_tools, system_msg: str) -> dict:
    """에이전트 노드"""
    from langchain_core.messages import SystemMessage

    messages = state["messages"]

    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=system_msg)] + messages

    response = llm_with_tools.invoke(messages)
    return {"messages": messages + [response]}


# ============================================================================
# 그래프 생성
# ============================================================================

def create_agent_graph_with_memory(llm_with_tools, tools, system_msg: str):
    """그래프 생성"""
    graph = StateGraph(AgentState)

    graph.add_node("agent", lambda state: agent_node(state, llm_with_tools, system_msg))
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END}
    )
    graph.add_edge("tools", "agent")

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# ============================================================================
# 대화형 테스트
# ============================================================================

def demo_conversation():
    """데모 대화"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    llm_with_tools, tools, system_msg = create_agent_llm()
    compiled_graph = create_agent_graph_with_memory(llm_with_tools, tools, system_msg)

    print(f"{'='*100}")
    print("💬 LangGraph 에이전트 · 메모리 (대화형 화면 예시)")
    print(f"{'='*100}\n")

    # 테스트 질문들
    conversations = [
        ("HANA-007", "나는 HANA-007, 실무반에 관심 있어"),
        ("HANA-007", "내 관심 과정의 2개월 수강료 알려줘"),
    ]

    for idx, (thread_id, question) in enumerate(conversations, 1):
        config = {"configurable": {"thread_id": thread_id}}
        state = {"messages": [HumanMessage(content=question)]}

        print(f"[{idx}] {thread_id}: {question}\n")
        print(f"{'─'*100}")

        try:
            step_num = 0
            tool_results = {}

            # [5-1] agent와 tools 노드를 번갈아 표시
            for step_output in compiled_graph.stream(
                state,
                config=config,
                stream_mode="updates"
            ):
                step_num += 1

                for node_name, node_state in step_output.items():
                    messages = node_state.get("messages", [])

                    if messages:
                        last_msg = messages[-1]
                        msg_type = type(last_msg).__name__

                        # [5-1] agent 노드
                        if node_name == "agent":
                            if msg_type == "AIMessage" and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                tool_names = [tc.get("name", "?") for tc in last_msg.tool_calls]
                                print(f"  [{step_num}] {node_name:10} → 도구 선택: {', '.join(tool_names)}")
                                for tc in last_msg.tool_calls:
                                    tool_results[tc.get("id", "?")] = tc.get("name", "?")

                            elif msg_type == "AIMessage":
                                answer = last_msg.content
                                print(f"  [{step_num}] {node_name:10} → 최종 답변: {answer[:50]}{'...' if len(answer) > 50 else ''}")

                        # [5-1] tools 노드
                        elif node_name == "tools":
                            tool_messages = [m for m in messages if type(m).__name__ == "ToolMessage"]
                            for tm in tool_messages:
                                # 도구 이름 찾기
                                tool_name = "?"
                                for tool in tools:
                                    if tool.name in str(tm.content)[:50]:
                                        tool_name = tool.name
                                        break

                                result_preview = str(tm.content)[:50]
                                if len(str(tm.content)) > 50:
                                    result_preview += "..."

                                print(f"  [{step_num}] {node_name:10} → {tool_name:20} {result_preview}")

            # [5-1] 메모리 상태 확인
            saved_state = compiled_graph.get_state(config)
            message_count = len(saved_state.values.get("messages", []))
            print(f"\n  💾 메모리: {message_count}개 메시지 저장됨\n")

        except Exception as e:
            print(f"❌ 오류: {str(e)}\n")


if __name__ == "__main__":
    demo_conversation()
