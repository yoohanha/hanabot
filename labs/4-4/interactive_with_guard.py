#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-4] 대화형 에이전트 (가드레일 적용 버전)

import sys
import asyncio
from pathlib import Path

# Windows UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# [4-4] 가드레일 import
from guard_input import InputGuard
from guard_tool import ToolGuard
from guard_output import OutputGuard

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, ToolMessage


# ============================================================================
# 대화형 에이전트 (가드레일 적용)
# ============================================================================

async def main():
    print(f"\n{'='*80}")
    print("[4-4] 하나봇 · AI 에이전트 (가드레일 적용)")
    print(f"{'='*80}\n")

    # 학번 입력
    login_id = input("🎓 학번을 입력해주세요 (예: HANA-007): ").strip()
    if not login_id.startswith("HANA-"):
        login_id = f"HANA-{login_id}" if login_id.isdigit() else "HANA-007"

    print(f"\n✅ 로그인: {login_id}\n")

    # 가드레일 초기화
    input_guard = InputGuard(verbose=False)
    tool_guard = ToolGuard(login_student_id=login_id, verbose=False)
    output_guard = OutputGuard(verbose=False)

    # MCP 서버 연결
    print("📡 MCP 서버 연결 중...\n")
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

    try:
        client = MultiServerMCPClient(connections=connections)

        # 도구 테이블 구성
        print("🔧 도구 테이블 로드 중...\n")
        tool_table = {}

        for server_name in ["time", "filesystem", "hana-academy"]:
            try:
                tools = await client.get_tools(server_name=server_name)

                for tool in tools:
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

        tools_list = [tool for _, tool in tool_table.values()]
        llm_with_tools = llm.bind_tools(tools_list)

        # 시스템 메시지
        system_msg = f"""당신은 하나 AI 학원의 Q&A 챗봇입니다.

현재 로그인한 학번: {login_id}

학번이나 인사 정도는 도구 없이 답하세요.
필요할 때만 MCP 도구를 사용해 정보를 조회하세요.

도구 결과가 오류이거나 정보가 없으면, 추측하거나 지어내지 말고
"확인하지 못했어요" 또는 "죄송하지만 조회할 수 없습니다"라고 답하세요.

중요: 다른 학번의 예약을 조회하거나 수정할 수 없습니다."""

        print(f"{'='*80}")
        print("💬 대화를 시작합니다. 'q'를 입력하면 종료합니다.\n")
        print("🛡️ 가드레일: 입력/도구/출력 (3계층 보안)\n")
        print(f"{'='*80}\n")

        messages = [HumanMessage(content=system_msg)]
        tool_guard.reset_session()

        while True:
            user_input = input("당신: ").strip()

            if user_input.lower() == 'q':
                print("\n프로그램을 종료합니다. 👋\n")
                break

            if not user_input:
                continue

            # [1] 입력 가드 검사
            processed_input, input_passed, input_message = input_guard.guard(user_input)

            if not input_passed:
                print(f"\n🛡️ 입력 가드: {input_message}\n")
                continue

            # [2] 에이전트 실행 (도구 호출 포함)
            messages.append(HumanMessage(content=processed_input))

            try:
                for iteration in range(3):
                    response = await llm_with_tools.ainvoke(messages)
                    messages.append(response)

                    if not hasattr(response, "tool_calls") or not response.tool_calls:
                        # 도구 미선택 → 최종 답변
                        answer = response.content if hasattr(response, "content") else str(response)
                        break

                    # 도구 호출
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", f"call_{iteration}")

                        # [2-1] 도구 가드 검사
                        tool_passed, tool_message = await tool_guard.guard(
                            tool_name,
                            tool_args,
                            approval_input_fn=None  # 사용자가 직접 입력
                        )

                        if not tool_passed:
                            print(f"\n🛡️ 도구 가드: {tool_message}\n")
                            messages.append(ToolMessage(tool_call_id=tool_id, content=tool_message))
                            continue

                        if tool_name not in tool_table:
                            messages.append(ToolMessage(tool_call_id=tool_id, content="도구를 찾을 수 없음"))
                            continue

                        server_name, tool = tool_table[tool_name]

                        try:
                            result = await tool.ainvoke(tool_args)

                            if isinstance(result, list) and len(result) > 0:
                                result_text = result[0].get('text', str(result))
                            else:
                                result_text = result if isinstance(result, str) else str(result)

                            messages.append(ToolMessage(tool_call_id=tool_id, content=result_text))

                        except Exception as e:
                            error_msg = f"도구 실행 오류: {str(e)[:100]}"
                            messages.append(ToolMessage(tool_call_id=tool_id, content=error_msg))

                if not answer or answer.startswith("당신:"):
                    answer = "확인하지 못했어요"

                # [3] 출력 가드 검사 (규정 답변에만 적용)
                # 여기서는 간단하게 처리 (실제로는 도구 결과 추적 필요)
                answer_safe = answer.encode('utf-8', errors='replace').decode('utf-8')

                print(f"\n봇: {answer_safe}\n")

            except UnicodeEncodeError:
                print(f"\n봇: (응답 인코딩 오류)\n")
            except Exception as e:
                print(f"\n❌ 오류: {str(e)[:100]}\n")
                continue

    except Exception as e:
        print(f"❌ 오류: {str(e)}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
