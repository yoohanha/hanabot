#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] MCP 도구 대화형 에이전트 (모델이 도구 선택)

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


async def agent_loop(client, llm_with_tools, tool_table, user_question: str, messages: list, max_iterations: int = 5):
    """
    [4-3] 에이전트 루프: 모델이 도구를 선택하고 실행
    """
    messages.append(HumanMessage(content=user_question))

    for iteration in range(max_iterations):
        # 모델 호출 (도구 선택)
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        # 도구 호출 확인
        if not hasattr(response, "tool_calls") or not response.tool_calls:
            # 도구 미선택 → 최종 답변
            answer = response.content if hasattr(response, "content") else str(response)
            if answer.strip():
                return answer, messages
            elif iteration == max_iterations - 1:
                return "확인하지 못했어요", messages
            else:
                continue

        # 도구 실행
        for tool_call in response.tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "call_1")

            if tool_name not in tool_table:
                messages.append(ToolMessage(tool_call_id=tool_id, content="도구를 찾을 수 없음"))
                continue

            server_name, tool = tool_table[tool_name]

            try:
                # 비동기 도구 실행
                result = await tool.ainvoke(tool_args)

                # [{'type':'text','text':...}]에서 text만 추출
                if isinstance(result, list) and len(result) > 0:
                    result_text = result[0].get('text', str(result))
                else:
                    result_text = result if isinstance(result, str) else str(result)

                messages.append(ToolMessage(tool_call_id=tool_id, content=result_text))

            except Exception as e:
                error_msg = f"도구 실행 오류: {str(e)[:100]}"
                messages.append(ToolMessage(tool_call_id=tool_id, content=error_msg))

    # 최대 반복 초과
    return "확인하지 못했어요", messages


async def main():
    print(f"\n{'='*80}")
    print("[4-3] 하나봇 · MCP 도구 에이전트 (대화형)")
    print(f"{'='*80}\n")

    # MCP 서버 연결
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

    # 도구 테이블 구성 (한 번만)
    print("📦 도구 테이블 구성 중...\n")
    tool_table = {}

    for server_name in ["time", "filesystem", "hana-academy"]:
        try:
            tools = await client.get_tools(server_name=server_name)

            for tool in tools:
                # Filesystem: 읽기만
                if server_name == "filesystem":
                    if not any(x in tool.name.lower() for x in ["read", "list", "search"]):
                        continue

                tool_table[tool.name] = (server_name, tool)

        except Exception as e:
            print(f"   ⚠️  {server_name}: {str(e)[:50]}")

    print(f"   ✅ {len(tool_table)}개 도구 로드됨\n")

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
필요할 때만 MCP 도구를 사용해 정보를 조회하세요.

도구 결과가 오류이거나 정보가 없으면, 추측하거나 지어내지 말고
"확인하지 못했어요" 또는 "죄송하지만 조회할 수 없습니다"라고 답하세요."""

    # 입력 예시
    print(f"{'='*80}")
    print("💡 입력 예시:")
    print("   - 나는 HANA-007, 지금 몇 시야?")
    print("   - 12월 첫 주 시간표 알려줘")
    print("   - 실무반 2개월 친구 할인이면?\n")

    print("📌 가상 학번 안내:")
    print("   - HANA-001 ~ HANA-999 (유효한 학번)")
    print("   - 주의: 이름, 전화번호, 이메일은 입력하지 마세요\n")

    print(f"{'='*80}")
    print("대화를 시작합니다. 'q'를 입력하면 종료합니다.\n")

    messages = [HumanMessage(content=system_msg)]

    while True:
        try:
            user_input = input("당신: ").strip()

            if user_input.lower() == 'q':
                print("\n프로그램을 종료합니다. 👋\n")
                break

            if not user_input:
                continue

            # 에이전트 실행
            try:
                answer, messages = await agent_loop(client, llm_with_tools, tool_table, user_input, messages)
                # 안전한 출력 처리
                answer_safe = answer.encode('utf-8', errors='replace').decode('utf-8')
                print(f"\n봇: {answer_safe}\n")
            except UnicodeEncodeError:
                print(f"\n봇: (응답 인코딩 오류)\n")

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다. 👋\n")
            break
        except Exception as e:
            print(f"오류: {str(e)[:100]}\n")
            continue


if __name__ == "__main__":
    asyncio.run(main())
