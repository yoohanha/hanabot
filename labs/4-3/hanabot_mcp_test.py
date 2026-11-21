#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] MCP 도구 비동기 테스트 (빠른 버전)

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


async def main():
    print(f"\n{'='*80}")
    print("[4-3] MCP 도구 비동기 테스트")
    print(f"{'='*80}\n")

    # MCP 클라이언트 생성
    hana_mcp_server_path = PROJECT_ROOT / "labs" / "4-3" / "hana_mcp_server.py"
    data_path = PROJECT_ROOT / "data"

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

    print("📋 MCP 서버 연결 중...\n")
    client = MultiServerMCPClient(connections=connections)

    # 도구 테이블 생성
    print("📦 도구 테이블 구성 중...\n")
    tool_table = {}

    for server_name in ["time", "filesystem", "hana-academy"]:
        try:
            tools = await client.get_tools(server_name=server_name)

            for tool in tools:
                if server_name == "filesystem":
                    if not any(x in tool.name.lower() for x in ["read", "list", "search"]):
                        continue

                tool_table[tool.name] = (server_name, tool)
                print(f"   ✅ {server_name}: {tool.name}")

        except Exception as e:
            print(f"   ❌ {server_name}: {str(e)[:50]}")

    print(f"\n✅ {len(tool_table)}개 도구 로드됨\n")

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
    tools_list = [tool for _, tool in tool_table.values()]
    llm_with_tools = llm.bind_tools(tools_list)

    # 시스템 메시지
    system_msg = """당신은 하나 AI 학원의 Q&A 챗봇입니다.

학번이나 인사 정도는 도구 없이 답하세요.
필요한 경우에만 MCP 도구를 사용해 정보를 조회하세요.

중요: 도구 결과가 오류이거나 정보가 없으면, 추측하거나 지어내지 말고
"확인하지 못했어요" 또는 "죄송하지만 조회할 수 없습니다"라고 답하세요."""

    # 테스트 대화 (5개)
    print(f"{'='*80}")
    print("테스트: 5가지 대화 (비동기)")
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
        print(f"[대화 {idx}] {question}\n")

        messages.append(HumanMessage(content=question))

        # 1회차 LLM 호출
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        result_server = "-"
        result_tool = "-"
        result_content = "-"
        bot_answer = ""

        # 도구 호출 처리
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})
                tool_id = tool_call.get("id", "call_1")

                if tool_name not in tool_table:
                    continue

                result_server, tool = tool_table[tool_name]
                result_tool = tool_name

                try:
                    # 비동기 도구 실행
                    result = await tool.ainvoke(tool_args)
                    result_text = result if isinstance(result, str) else str(result)

                    result_content = result_text[:50] if len(result_text) > 50 else result_text

                    print(f"   [MCP {result_server}] {result_tool}")
                    print(f"       결과: {result_content}...\n" if len(result_text) > 50 else f"       결과: {result_content}\n")

                    # ToolMessage 추가
                    messages.append(ToolMessage(tool_call_id=tool_id, content=result_text))

                except Exception as e:
                    error_msg = f"[오류] {str(e)[:50]}"
                    result_content = error_msg
                    messages.append(ToolMessage(tool_call_id=tool_id, content=error_msg))

            # 2회차 LLM 호출 (도구 결과로 답변 생성)
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

        # 최종 답변
        bot_answer = response.content if hasattr(response, "content") else str(response)
        print(f"봇: {bot_answer[:50]}...\n" if len(bot_answer) > 50 else f"봇: {bot_answer}\n")

        all_results.append(
            {
                "question": question[:30],
                "server": result_server,
                "tool": result_tool[:20] if result_tool != "-" else "-",
                "result": result_content[:35],
                "answer": bot_answer[:30],
            }
        )

    # 결과표
    print(f"{'='*80}")
    print("[서버 · 도구 · 결과 앞부분 · 봇 답] 결과표")
    print(f"{'='*80}\n")

    print(
        f"{'질문':<35} | {'서버':<15} | {'도구':<20} | {'결과':<35} | {'봇 답':<30}"
    )
    print("-" * 150)

    for result in all_results:
        q = result["question"][:34]
        s = result["server"][:14]
        t = result["tool"][:19] if result["tool"] != "-" else "-"
        r = result["result"][:34]
        a = result["answer"][:29]
        print(f"{q:<35} | {s:<15} | {t:<20} | {r:<35} | {a:<30}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
