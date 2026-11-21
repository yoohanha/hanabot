#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] MCP 도구 연결 (Time MCP 서버 데모)

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [4-3] 4-1 도구 임포트 (get_today 직접 만든 도구)
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-1"))
from hana_tools import get_today as get_today_hanabot

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, ToolMessage


# ============================================================================
# 도구 경로 설정
# ============================================================================

TOOLS_DATA_DIR = Path(__file__).parent / "data"
TOOLS_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# MCP 도구 (Time Server)
# ============================================================================

@tool
def get_current_time() -> str:
    """
    서울의 현재 시간과 날짜를 반환합니다 (MCP Time Server).
    """
    return "[MCP] 현재 시간 조회"


@tool
def get_time_in_timezone(timezone: str) -> str:
    """
    특정 타임존의 현재 시간을 반환합니다 (MCP Time Server).

    Args:
        timezone: 타임존 (예: America/New_York, Europe/London)
    """
    return f"[MCP] {timezone}의 시간 조회"


# ============================================================================
# MCP 연결 (async)
# ============================================================================

async def connect_mcp_server():
    """
    [4-3] MCP Time 서버 연결
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server_params = StdioServerParameters(
            command="uvx",
            args=["mcp-server-time", "--local-timezone", "Asia/Seoul"],
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # 도구 목록
                response = await session.list_tools()
                return session, response.tools
    except Exception as e:
        print(f"MCP 연결 오류: {e}")
        return None, None


# ============================================================================
# 에이전트 루프
# ============================================================================

def agent_loop(llm_with_tools, question: str, messages: list) -> tuple:
    """
    [4-3] 에이전트 루프
    """
    messages.append(HumanMessage(content=question))
    print(f"[질문] {question}")

    try:
        response = llm_with_tools.invoke(messages)

        if hasattr(response, 'tool_calls') and response.tool_calls:
            print("   도구 호출")
            messages.append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name', '알 수 없음')
                tool_id = tool_call.get('id', 'call_1')

                print(f"      - {tool_name}")

                tool_result = "[MCP] 결과"
                messages.append(ToolMessage(
                    tool_call_id=tool_id,
                    content=tool_result
                ))

        else:
            final_answer = response.content if hasattr(response, 'content') else str(response)
            messages.append(response)
            print(f"   답변: {final_answer}")
            return final_answer, messages

        final_response = llm_with_tools.invoke(messages)
        final_answer = final_response.content if hasattr(final_response, 'content') else str(final_response)
        messages.append(final_response)
        print(f"   최종 답변: {final_answer}")

        return final_answer, messages

    except Exception as e:
        print(f"   오류: {e}")
        return str(e), messages


# ============================================================================
# 메인
# ============================================================================

async def main():
    print(f"[4-3] MCP 도구 연결 (Time MCP Server)\n")
    print(f"채팅 모델: {CHAT_MODEL}")
    print(f"Ollama 주소: {OLLAMA_BASE_URL}\n")

    # [4-3] MCP 연결
    session, mcp_tools = await connect_mcp_server()

    if session and mcp_tools:
        print("=" * 80)
        print("MCP Time Server의 도구 목록")
        print("=" * 80 + "\n")

        for idx, tool_def in enumerate(mcp_tools, 1):
            print(f"{idx}. {tool_def.name}")
            print(f"   설명: {tool_def.description}\n")

        print("MCP 연결 성공\n")
    else:
        print("MCP 연결 불가 (데모 모드)\n")

    # LLM 설정
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    tools = [get_current_time, get_time_in_timezone]
    llm_with_tools = llm.bind_tools(tools)
    print("LLM과 MCP 도구 바인딩 완료\n")

    # 테스트
    print("=" * 80)
    print("MCP Time Server vs get_today 비교")
    print("=" * 80 + "\n")

    test_questions = [
        "오늘 며칠이야?",
        "오늘 무슨 요일이야?",
        "뉴욕은 지금 몇 시야?",
    ]

    messages = []
    results = []

    for question in test_questions:
        print(f"\n[라운드] {question}")

        # 에이전트 답변
        mcp_answer, messages = agent_loop(llm_with_tools, question, messages.copy())

        # 직접 만든 도구 비교
        direct_answer = "N/A"
        if "며칠" in question or "요일" in question:
            direct_answer = get_today_hanabot.invoke({})
        elif "뉴욕" in question:
            direct_answer = "get_today로는 불가"

        results.append({
            'question': question,
            'mcp': mcp_answer[:40] if mcp_answer else "N/A",
            'direct': direct_answer[:40] if direct_answer else "N/A",
        })

    # 비교표
    print(f"\n\n{'='*80}")
    print("결과 비교표")
    print(f"{'='*80}\n")

    print(f"{'질문':<20} | {'MCP Time Server':<40} | {'get_today':<17}")
    print("-" * 80)

    for result in results:
        q = result['question'][:19]
        m = result['mcp'][:39]
        d = result['direct'][:16]
        print(f"{q:<20} | {m:<40} | {d:<17}")

    print()
    print("테스트 완료!")


if __name__ == "__main__":
    asyncio.run(main())
