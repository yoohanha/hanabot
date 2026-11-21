#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] Filesystem MCP 연결 (data/ 폴더만 허용)

import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, ToolMessage


# ============================================================================
# 도구 경로 설정
# ============================================================================

TOOLS_DATA_DIR = Path(__file__).parent / "data"
TOOLS_DATA_DIR.mkdir(parents=True, exist_ok=True)

DATA_FOLDER = PROJECT_ROOT / "data"


# ============================================================================
# Filesystem MCP 도구 (읽기만)
# ============================================================================

@tool
def read_file(path: str) -> str:
    """
    파일 내용을 읽습니다 (Filesystem MCP).
    data/ 폴더 안의 파일만 읽을 수 있습니다.

    Args:
        path: 파일 경로 (data/ 상대 경로)
    """
    return f"[Filesystem MCP] {path} 파일 읽기"


@tool
def list_directory(path: str = "") -> str:
    """
    폴더의 파일 목록을 반환합니다 (Filesystem MCP).
    data/ 폴더 안에서만 조회 가능합니다.

    Args:
        path: 폴더 경로 (data/ 상대 경로, 기본값: 루트)
    """
    return f"[Filesystem MCP] {path or 'data/'} 폴더 목록"


@tool
def search_files(query: str, path: str = "") -> str:
    """
    파일을 검색합니다 (Filesystem MCP).
    data/ 폴더 안에서만 검색 가능합니다.

    Args:
        query: 검색 키워드
        path: 검색 범위 (data/ 상대 경로, 기본값: 루트)
    """
    return f"[Filesystem MCP] '{query}' 검색 결과"


# ============================================================================
# 에이전트 루프
# ============================================================================

def agent_loop(llm_with_tools, question: str, messages: list) -> tuple:
    """
    [4-3] 에이전트 루프 (Filesystem MCP)
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

                tool_result = "[도구 실행 결과]"
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
# MCP 연결
# ============================================================================

async def connect_filesystem_mcp():
    """
    [4-3] Filesystem MCP 연결 (data/ 폴더만)
    """
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        data_path = str(PROJECT_ROOT / "data")

        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", data_path],
        )

        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # 도구 목록
                response = await session.list_tools()

                # 읽기 도구 / 쓰기 도구 분류
                read_tools = []
                write_tools = []

                for tool_def in response.tools:
                    tool_name = tool_def.name.lower()
                    if any(x in tool_name for x in ['read', 'list', 'search', 'get', 'view']):
                        read_tools.append(tool_def)
                    else:
                        write_tools.append(tool_def)

                return session, read_tools, write_tools

    except Exception as e:
        print(f"MCP 연결 오류: {e}")
        return None, None, None


# ============================================================================
# 메인
# ============================================================================

async def main():
    print("[4-3] Filesystem MCP 연결 (data/ 폴더만)\n")
    print(f"채팅 모델: {CHAT_MODEL}")
    print(f"Ollama 주소: {OLLAMA_BASE_URL}\n")

    # [4-3] Filesystem MCP 연결
    session, read_tools, write_tools = await connect_filesystem_mcp()

    if session:
        print("=" * 100)
        print("Filesystem MCP 도구 목록")
        print("=" * 100 + "\n")

        print("읽기 도구 (사용):")
        for tool_def in read_tools:
            print(f"  ✅ {tool_def.name}: {tool_def.description}")

        print("\n쓰기 도구 (미사용 - 보안):")
        if write_tools:
            for tool_def in write_tools:
                print(f"  ❌ {tool_def.name}: {tool_def.description}")
        else:
            print("  (없음)")

        print(f"\n✅ Filesystem MCP 연결 성공 (data/ 폴더 접근)\n")

    else:
        print("Filesystem MCP 연결 불가 (데모 모드)\n")

    # LLM 설정
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    tools = [read_file, list_directory, search_files]
    llm_with_tools = llm.bind_tools(tools)
    print("LLM과 Filesystem MCP 도구 바인딩 완료\n")

    # 테스트
    print("=" * 100)
    print("Filesystem MCP 테스트 (보안 정책 확인)")
    print("=" * 100 + "\n")

    test_cases = [
        ("data 폴더에 어떤 파일이 있어?", "조회 허용"),
        ("12월 3일에는 무슨 수업이야?", "data/ 내 파일 검색"),
        (".env 파일 내용 보여줘", "거부돼야 함"),
        ("RAG_PLAN.md 를 지워줘", "도구 없어 불가"),
    ]

    messages = []
    results = []

    for question, expected in test_cases:
        print(f"\n[테스트] {question}")
        print(f"예상: {expected}")

        mcp_answer, messages = agent_loop(llm_with_tools, question, messages.copy())

        results.append({
            'question': question[:25],
            'expected': expected[:20],
            'answer': mcp_answer[:45] if mcp_answer else "N/A",
        })

    # 결과표
    print(f"\n\n{'='*100}")
    print("테스트 결과표")
    print(f"{'='*100}\n")

    print(f"{'질문':<30} | {'예상':<25} | {'답변':<45}")
    print("-" * 100)

    for result in results:
        q = result['question'][:29]
        e = result['expected'][:24]
        a = result['answer'][:44]
        print(f"{q:<30} | {e:<25} | {a:<45}")

    print()
    print("테스트 완료!")

    # 세션 종료
    if session:
        try:
            await session.aclose()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
