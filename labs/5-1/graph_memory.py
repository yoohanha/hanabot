#!/usr/bin/env python3
# [5-1] LangGraph 에이전트 · 메모리 (체크포인터)

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

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
from langchain_core.messages import ToolMessage, BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver  # [5-1] 메모리 체크포인터
from typing_extensions import TypedDict


# ============================================================================
# State 정의
# ============================================================================

class AgentState(TypedDict):
    """에이전트 상태"""
    messages: list  # 메시지 히스토리 (스레드별로 저장됨)


# ============================================================================
# 도구 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# LLM 초기화
# ============================================================================

def create_agent_llm():
    """LLM 초기화 (5-1 규칙에 따라)"""
    today = datetime.now().strftime("%Y년 %m월 %d일")

    system_message = f"""당신은 하나봇 AI 에이전트입니다.
오늘 날짜: {today}
역할: 학원 관련 질문을 답변하고, 학생의 관심사를 기억합니다.
도구: get_today (오늘 날짜), reserve_gpu_pc (예약), cancel_gpu_pc (취소)
주의: 대화 맥락을 활용하여 학생의 선호사항을 반영하세요."""

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
    """에이전트 노드: 모델이 도구를 선택하거나 최종 답변을 반환"""
    from langchain_core.messages import SystemMessage

    messages = state["messages"]

    # 시스템 메시지 추가 (첫 호출 시에만)
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=system_msg)] + messages

    # 모델 호출
    response = llm_with_tools.invoke(messages)

    # 메시지 히스토리에 추가
    return {"messages": messages + [response]}


# ============================================================================
# 그래프 생성 (체크포인터 포함)
# ============================================================================

def create_agent_graph_with_memory(llm_with_tools, tools, system_msg: str):
    """
    LangGraph StateGraph 생성 · 메모리 체크포인터 추가
    - InMemorySaver: 메모리에 상태 저장
    - thread_id: 학번으로 구분
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

    # [5-1] 메모리 체크포인터 추가 (InMemorySaver)
    memory = MemorySaver()
    compiled_graph = graph.compile(checkpointer=memory)

    return compiled_graph


# ============================================================================
# 테스트 및 시각화
# ============================================================================

def save_mermaid_diagram(compiled_graph):
    """그래프를 Mermaid 다이어그램으로 저장"""
    diagram = compiled_graph.get_graph().draw_mermaid()

    output_file = Path(__file__).parent / "graph_memory.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# [5-1] LangGraph 에이전트 · 메모리 (체크포인터)\n\n")
        f.write("```mermaid\n")
        f.write(diagram)
        f.write("\n```\n\n")
        f.write("## 체크포인터 (InMemorySaver)\n\n")
        f.write("- **스레드 ID (thread_id)**: 학번 (HANA-007, HANA-002 등)\n")
        f.write("- **메모리**: 각 학번별로 대화 히스토리 저장\n")
        f.write("- **복구**: 같은 학번으로 다시 물으면 이전 대화 맥락 활용\n")

    print(f"✅ 그래프 저장: {output_file}")


def test_memory_agent():
    """메모리 기능 테스트"""
    # 그래프 생성
    llm_with_tools, tools, system_msg = create_agent_llm()
    compiled_graph = create_agent_graph_with_memory(llm_with_tools, tools, system_msg)

    # 다이어그램 저장
    save_mermaid_diagram(compiled_graph)

    print(f"\n{'='*100}")
    print("[5-1] LangGraph 에이전트 · 메모리 테스트")
    print(f"{'='*100}\n")

    # 테스트 대화 (3개)
    test_conversations = [
        {
            "thread_id": "HANA-007",
            "question": "나는 HANA-007, 실무반에 관심 있어",
            "description": "관심 과정 등록"
        },
        {
            "thread_id": "HANA-007",
            "question": "내 관심 과정의 2개월 수강료 알려줘",
            "description": "이전 맥락 활용 (기억)"
        },
        {
            "thread_id": "HANA-002",
            "question": "내 관심 과정의 2개월 수강료 알려줘",
            "description": "HANA-007의 맥락 없음 (기억 안 함)"
        }
    ]

    results = []

    print(f"{'─'*100}")
    print("🔄 대화 실행\n")

    for idx, conv in enumerate(test_conversations, 1):
        thread_id = conv["thread_id"]
        question = conv["question"]
        description = conv["description"]

        print(f"[{idx}] {description}")
        print(f"    학번: {thread_id}")
        print(f"    질문: {question}\n")

        # config에 thread_id 설정 ([5-1] 메모리 활용)
        config = {"configurable": {"thread_id": thread_id}}

        # 초기 상태
        state = {
            "messages": [HumanMessage(content=question)]
        }

        # 에이전트 실행
        try:
            final_state = compiled_graph.invoke(state, config=config)

            # 최종 답변 추출
            messages = final_state.get("messages", [])
            if messages:
                last_msg = messages[-1]
                answer = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                answer_preview = answer[:60] + ("..." if len(answer) > 60 else "")
            else:
                answer_preview = "답변 없음"

            # 체크포인터에서 저장된 메시지 수 조회
            saved_state = compiled_graph.get_state(config)
            message_count = len(saved_state.values.get("messages", []))

            # 메모리 여부 판정
            # - HANA-007의 2번째 질문: 메시지 수 증가 (메모리 활용)
            # - HANA-002의 질문: 메시지 수 1 (새로운 스레드)
            if idx == 2 and thread_id == "HANA-007":
                has_memory = "✅ 기억함" if message_count > 2 else "❌ 기억 안 함"
            elif idx == 3 and thread_id == "HANA-002":
                has_memory = "❌ 기억 안 함 (다른 학번)" if message_count <= 2 else "⚠️ 기억함 (오류)"
            elif idx == 1:
                has_memory = "-"
            else:
                has_memory = "-"

            print(f"    💬 답변: {answer_preview}")
            print(f"    📌 저장된 메시지: {message_count}개")
            print(f"    {has_memory}\n")

            results.append({
                "thread_id": thread_id,
                "question": question,
                "answer": answer_preview,
                "has_memory": has_memory,
                "message_count": message_count
            })

        except Exception as e:
            print(f"    ❌ 오류: {str(e)}\n")
            results.append({
                "thread_id": thread_id,
                "question": question,
                "answer": f"오류: {str(e)[:40]}",
                "has_memory": "❌",
                "message_count": 0
            })

    print(f"{'─'*100}\n")

    # 결과 표
    print(f"{'='*100}")
    print("📊 메모리 테스트 결과 (학번 · 질문 · 답 · 기억했나)")
    print(f"{'='*100}\n")

    print("| # | 학번 | 질문 | 답 | 기억 | 메시지 |")
    print("|---|------|--------|--------|------|--------|")

    for idx, result in enumerate(results, 1):
        thread_id = result["thread_id"]
        question = result["question"][:40]
        answer = result["answer"][:35]
        memory_status = result["has_memory"]
        msg_count = result["message_count"]

        print(f"| {idx} | {thread_id} | {question:40} | {answer:35} | {memory_status:10} | {msg_count} |")

    # 상세 분석
    print(f"\n{'='*100}")
    print("🔍 상세 분석")
    print(f"{'='*100}\n")

    # HANA-007: 1번 → 2번 메시지 증가 (메모리 활용)
    if len(results) >= 2:
        msg_count_1 = results[0]["message_count"]
        msg_count_2 = results[1]["message_count"]
        print(f"✅ HANA-007 (같은 학번, 2번 질문):")
        print(f"   1번 질문 후: {msg_count_1}개 메시지")
        print(f"   2번 질문 후: {msg_count_2}개 메시지")
        if msg_count_2 > msg_count_1:
            print(f"   → 메모리 활용 ✅ (이전 대화 기억함)\n")
        else:
            print(f"   → 메모리 미활용 ❌\n")

    # HANA-002: 새로운 스레드 (메모리 없음)
    if len(results) >= 3:
        msg_count_3 = results[2]["message_count"]
        print(f"❌ HANA-002 (다른 학번, HANA-007의 맥락 없음):")
        print(f"   첫 질문: {msg_count_3}개 메시지")
        if msg_count_3 <= 2:
            print(f"   → 메모리 없음 ✅ (새로운 스레드 생성)\n")
        else:
            print(f"   → 오류 (다른 학번이 메모리를 공유함) ❌\n")

    # JSON 저장
    result_file = DATA_DIR / "graph_memory_test.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ 테스트 결과 저장: {result_file}")

    # 메모리 구조 설명
    print(f"\n{'='*100}")
    print("💾 체크포인터 메모리 구조")
    print(f"{'='*100}\n")

    print("```")
    print("InMemorySaver (메모리 체크포인터)")
    print("├── HANA-007 (thread_id)")
    print("│   ├── 1번 대화: SystemMessage + HumanMessage + AIMessage")
    print("│   └── 2번 대화: 위의 메시지 + HumanMessage + AIMessage")
    print("│       → 같은 thread_id이므로 1번 대화의 맥락 유지")
    print("├── HANA-002 (thread_id)")
    print("│   └── 1번 대화: SystemMessage + HumanMessage + AIMessage")
    print("│       → 새로운 thread_id이므로 HANA-007의 맥락 없음")
    print("```")


def main():
    """메인 함수"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    test_memory_agent()


if __name__ == "__main__":
    main()
