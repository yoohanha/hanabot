#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] MCP 도구 비동기 실행 (Time · Filesystem · hana-academy)

import sys
import asyncio
from pathlib import Path

# Windows UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():
    print(f"\n{'='*80}")
    print("[4-3] MCP 도구 비동기 실행 테스트")
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

    # 서버별 도구 조회 (한 번만)
    print("📦 도구 테이블 구성 중...\n")
    tool_table = {}

    for server_name in ["time", "filesystem", "hana-academy"]:
        try:
            tools = await client.get_tools(server_name=server_name)

            for tool in tools:
                # Filesystem: 읽기 도구만
                if server_name == "filesystem":
                    if not any(x in tool.name.lower() for x in ["read", "list", "search"]):
                        continue

                tool_table[tool.name] = (server_name, tool)

        except Exception as e:
            print(f"   ⚠️  {server_name}: {str(e)[:50]}")

    print(f"   ✅ {len(tool_table)}개 도구 로드됨\n")

    # 테스트 대화 (5개)
    print(f"{'='*80}")
    print("테스트: 5가지 도구 호출")
    print(f"{'='*80}\n")

    test_cases = [
        ("나는 HANA-007, 지금 몇 시야?", "get_current_time", {}),
        ("12월 첫 주 시간표 알려줘", "list_directory", {"path": ""}),
        ("실무반 2개월 친구 할인이면?", "calc_fee", {"course": "실무반", "months": 2, "discount_type": "친구"}),
        ("내일 오후 2시 GPU PC 1번 2시간 예약해줄 수 있어?", "reserve_gpu", {"date": "2026-11-22", "start_time": "14:00", "duration": 2, "pc_number": 1}),
        ("기초반은 주 며칠 운영돼?", "search_rules", {"question": "기초반은 주 며칠"}),
    ]

    all_results = []

    for idx, (question, tool_name, tool_args) in enumerate(test_cases, 1):
        print(f"[대화 {idx}] {question[:40]}\n")

        result_server = "-"
        result_tool = "-"
        result_content = "-"

        if tool_name not in tool_table:
            print(f"   도구 없음: {tool_name}\n")
        else:
            result_server, tool = tool_table[tool_name]

            try:
                # [4-3] 비동기 도구 실행
                result = await tool.ainvoke(tool_args)
                result_text = result if isinstance(result, str) else str(result)

                result_tool = tool_name
                result_content = result_text[:35] if len(result_text) > 35 else result_text

                print(f"   [MCP {result_server}] {tool_name}")
                print(f"       결과: {result_content}...\n" if len(result_text) > 35 else f"       결과: {result_content}\n")

            except Exception as e:
                result_tool = tool_name
                error = str(e)[:35]
                result_content = f"[오류] {error}"

                print(f"   [MCP {result_server}] {tool_name}")
                print(f"       결과: {result_content}\n")

        all_results.append(
            {
                "question": question[:30],
                "server": result_server,
                "tool": result_tool[:18] if result_tool != "-" else "-",
                "result": result_content[:34],
            }
        )

    # 결과표
    print(f"{'='*80}")
    print("[서버 · 도구 · 결과 앞부분] 결과표")
    print(f"{'='*80}\n")

    print(f"{'질문':<35} | {'서버':<15} | {'도구':<20} | {'결과':<35}")
    print("-" * 110)

    for result in all_results:
        q = result["question"][:34]
        s = result["server"][:14]
        t = result["tool"][:19] if result["tool"] != "-" else "-"
        r = result["result"][:34]
        print(f"{q:<35} | {s:<15} | {t:<20} | {r:<35}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
