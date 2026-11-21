#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] MCP 도구 실제 연결 (Time · Filesystem · hana-academy)

import sys
import asyncio
from pathlib import Path

# Windows UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, ToolMessage


# ============================================================================
# MCP 서버 연결 설정
# ============================================================================

async def setup_mcp_client():
    """
    [4-3] MCP 서버 3개 실제 연결
    """
    # 절대 경로 계산
    hana_mcp_server_path = PROJECT_ROOT / "labs" / "4-3" / "hana_mcp_server.py"
    data_path = PROJECT_ROOT / "data"

    # MCP 서버 연결 설정
    connections = {
        "time": {
            "transport": "stdio",
            "command": "uvx",
            "args": ["mcp-server-time", "--local-timezone", "Asia/Seoul"],
        },
        "filesystem": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", str(data_path)],
        },
        "hana-academy": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(hana_mcp_server_path)],
        },
    }

    # MultiServerMCPClient 생성
    client = MultiServerMCPClient(connections=connections)

    return client


# ============================================================================
# 도구 필터링
# ============================================================================

def filter_tools_by_server(all_tools, allowed_servers=None):
    """
    [4-3] 도구 필터링: Filesystem은 읽기만, hana-academy는 모두
    """
    if allowed_servers is None:
        allowed_servers = ["time", "filesystem", "hana-academy"]

    filtered = []

    for tool in all_tools:
        # 도구의 서버 이름 확인 (도구 이름에 포함됨)
        tool_name_lower = tool.name.lower()

        # 서버별 필터링
        keep = False

        if "time" in tool_name_lower and "time" in allowed_servers:
            keep = True
        elif "filesystem" in tool_name_lower or "file" in tool_name_lower:
            # Filesystem: 읽기 도구만
            if any(x in tool_name_lower for x in ["read", "list", "search"]):
                keep = True
        elif any(x in tool_name_lower for x in ["rule", "fee", "reserve", "cancel", "schedule"]):
            # hana-academy 도구
            keep = True

        if keep:
            filtered.append(tool)

    return filtered


# ============================================================================
# 에이전트 루프
# ============================================================================

async def agent_loop(
    client, llm_with_tools, user_question: str, messages: list, max_iterations: int = 5
):
    """
    [4-3] MCP 도구를 사용하는 에이전트 루프
    - 도구 호출 → 실행 → ToolMessage → 다시 모델 호출
    - 최대 5회 반복
    """
    messages.append(HumanMessage(content=user_question))
    print(f"당신: {user_question}\n")

    tool_results = []

    for iteration in range(max_iterations):
        # 모델 호출
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        # 도구 호출 확인
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            # 도구 없음 → 최종 답변
            answer = response.content if hasattr(response, "content") else str(response)
            if answer.strip():
                print(f"봇: {answer}\n")
                return answer, messages, tool_results
            elif iteration == max_iterations - 1:
                # 마지막 반복에서도 답이 없으면
                print("봇: 죄송하지만 그 질문에는 답할 수 없습니다.\n")
                return "No answer", messages, tool_results
            else:
                # 다시 시도
                continue

        # 도구 호출 처리
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "call_1")

            # 도구 실행 (MCP 도구는 LangChain 도구이므로 자동 실행)
            try:
                # LangChain 도구 실행
                tool_to_call = None
                for t in (await client.get_tools()):
                    if t.name == tool_name:
                        tool_to_call = t
                        break

                if tool_to_call:
                    result = tool_to_call.invoke(tool_args)
                    result_text = result if isinstance(result, str) else str(result)

                    # 도구가 온 서버 판단 (도구 이름 기반)
                    server_name = "?"
                    if "time" in tool_name.lower():
                        server_name = "time"
                    elif "filesystem" in tool_name.lower() or "file" in tool_name.lower():
                        server_name = "filesystem"
                    else:
                        server_name = "hana-academy"

                    tool_results.append(
                        {
                            "server": server_name,
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result_text,
                        }
                    )

                    print(f"   [MCP {server_name}] {tool_name}")
                    print(
                        f"       결과: {result_text[:60]}...\n"
                        if len(result_text) > 60
                        else f"       결과: {result_text}\n"
                    )

                    # ToolMessage 추가
                    messages.append(ToolMessage(tool_call_id=tool_id, content=result_text))
                else:
                    error_msg = f"도구를 찾을 수 없음: {tool_name}"
                    messages.append(ToolMessage(tool_call_id=tool_id, content=error_msg))

            except Exception as e:
                error_msg = f"도구 실행 오류: {str(e)[:100]}"
                messages.append(ToolMessage(tool_call_id=tool_id, content=error_msg))
                print(f"   오류: {error_msg}\n")

    # 최대 반복 초과
    print("봇: (도구 호출 최대 횟수 초과)\n")
    return "Max iterations", messages, tool_results


# ============================================================================
# 메인
# ============================================================================

async def main():
    print(f"\n{'='*80}")
    print("[4-3] AI 에이전트 · MCP 도구 (실제 연결)")
    print(f"{'='*80}\n")

    # MCP 서버 연결
    print("📋 MCP 서버 연결 중...\n")

    client = None
    try:
        client = await setup_mcp_client()
        print("   ✅ MultiServerMCPClient 생성됨\n")
    except Exception as e:
        print(f"   ❌ 클라이언트 생성 실패: {e}\n")
        return

    # 도구 로드
    all_tools = []
    try:
        all_tools = await client.get_tools()
        filtered_tools = filter_tools_by_server(all_tools)

        print(f"   📦 전체 {len(all_tools)}개 도구 중 {len(filtered_tools)}개 사용")
        for tool in filtered_tools[:5]:
            print(f"      - {tool.name}")
        if len(filtered_tools) > 5:
            print(f"      ... 외 {len(filtered_tools) - 5}개")
        print()

    except Exception as e:
        print(f"   ❌ 도구 로드 실패: {e}\n")
        return

    # LLM 설정
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        num_ctx=8192,
        num_predict=512,
        client_kwargs={"timeout": 120},
    )

    # 도구 바인딩
    llm_with_tools = llm.bind_tools(filtered_tools) if filtered_tools else llm

    # 시스템 메시지
    system_msg = """당신은 하나 AI 학원의 Q&A 챗봇입니다.

학번이나 인사 정도는 도구 없이 답하세요.
필요한 경우에만 MCP 도구를 사용해 정보를 조회하세요."""

    # 테스트 대화 (12p 프롬프트4)
    print(f"{'='*80}")
    print("테스트: 5가지 대화")
    print(f"{'='*80}\n")

    test_cases = [
        "나는 HANA-007, 지금 몇 시야?",
        "12월 첫 주 시간표 알려줘",
        "실무반 2개월 친구 할인이면?",
        "내일 오후 2시 GPU PC 1번 2시간 예약해줄 수 있어?",
        "기초반은 주 며칠 운영돼?",
    ]

    messages = [HumanMessage(content=system_msg)]
    all_results = []

    for idx, question in enumerate(test_cases, 1):
        print(f"[대화 {idx}]\n")

        try:
            answer, messages, tool_results = await agent_loop(
                client, llm_with_tools, question, messages
            )

            # 결과 기록
            if tool_results:
                for result in tool_results:
                    all_results.append(
                        {
                            "question": question[:30],
                            "server": result["server"],
                            "tool": result["tool"][:20],
                            "answer": answer[:30],
                        }
                    )
            else:
                all_results.append(
                    {
                        "question": question[:30],
                        "server": "-",
                        "tool": "-",
                        "answer": answer[:30] if answer else "(답변 없음)",
                    }
                )

        except Exception as e:
            print(f"오류: {e}\n")
            all_results.append(
                {
                    "question": question[:30],
                    "server": "❌",
                    "tool": "-",
                    "answer": str(e)[:30],
                }
            )

    # 결과표
    print(f"{'='*80}")
    print("도구 호출 결과표 [고른 서버 · 도구 · 답]")
    print(f"{'='*80}\n")

    print(f"{'질문':<35} | {'서버':<15} | {'도구':<20} | {'답변':<30}")
    print("-" * 100)

    for result in all_results:
        q = result["question"][:34]
        s = result["server"][:14]
        t = result["tool"][:19] if result["tool"] != "-" else "-"
        a = result["answer"][:29]
        print(f"{q:<35} | {s:<15} | {t:<20} | {a:<30}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
