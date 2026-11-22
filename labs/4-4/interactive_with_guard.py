#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-4] 대화형 에이전트 (가드레일 적용 버전)

import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime

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
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage


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

        # 도구 테이블 구성 (필요한 도구만 선택)
        print("🔧 도구 테이블 로드 중...\n")
        tool_table = {}

        # 필요한 도구 목록 정의
        allowed_tools = {
            "time": ["get_current_time"],
            "filesystem": ["read_text_file", "list_directory"],
            "hana-academy": ["get_today", "search_rules", "calc_fee", "reserve_gpu", "cancel_gpu"],
        }

        for server_name in ["time", "filesystem", "hana-academy"]:
            try:
                tools = await client.get_tools(server_name=server_name)

                for tool in tools:
                    if tool.name in allowed_tools.get(server_name, []):
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

        # [4-4] 오늘 날짜 (요일 포함)
        today = datetime.now()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        today_str = f"{today.year}년 {today.month}월 {today.day}일 ({weekdays[today.weekday()]}요일)"

        # 시스템 메시지 (SystemMessage 사용)
        system_msg = f"""당신은 하나 AI 학원의 Q&A 챗봇입니다.

현재 로그인한 학번: {login_id}
오늘 날짜: {today_str}
(모든 날짜 계산은 이 날짜를 기준으로 합니다)

학번이나 인사 정도는 도구 없이 답하세요.
필요할 때만 MCP 도구를 사용해 정보를 조회하세요.

도구 결과가 오류이거나 정보가 없으면, 추측하거나 지어내지 말고
"확인하지 못했어요" 또는 "죄송하지만 조회할 수 없습니다"라고 답하세요.

중요: 다른 학번의 예약을 조회하거나 수정할 수 없습니다."""

        print(f"{'='*80}")
        print("💬 대화를 시작합니다. 'q'를 입력하면 종료합니다.\n")
        print("🛡️ 가드레일: 입력/도구/출력 (3계층 보안)\n")
        print("💡 처음 한 번은 학번과 함께 질문하세요.")
        print("   예) HANA-007 / 실무반 2개월 친구 할인이면?\n")
        print(f"{'='*80}\n")

        messages = [SystemMessage(content=system_msg)]
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

            # [4-4] PII 가림 안내 표시
            if input_message and "개인정보" in input_message:
                print(f"🛡️ {input_message}")

            # [2] 에이전트 실행 (도구 호출 포함)
            messages.append(HumanMessage(content=processed_input))

            try:
                answer = None  # [4-4] answer 초기화
                last_tool_used = ""
                last_tool_result = ""
                start_time = time.time()

                for iteration in range(3):
                    # 진행 표시: 모델 호출 시
                    print("⏳ 생각 중...", end="", flush=True)
                    response = await llm_with_tools.ainvoke(messages)
                    print("\r" + " " * 20 + "\r", end="", flush=True)  # 지우기
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

                        # 진행 표시: 도구 사용 시
                        print(f"[반복 {iteration+1}] {tool_name} · {str(tool_args)[:40]}...")

                        # [2-1] 도구 가드 검사
                        tool_passed, tool_message = await tool_guard.guard(
                            tool_name,
                            tool_args,
                            approval_input_fn=None  # 사용자가 직접 입력
                        )

                        if not tool_passed:
                            # [4-4] 거절 이유를 그대로 말하기
                            print(f"   {tool_message}")
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

                            # 도구 사용 결과 로깅
                            print(f"   → {result_text[:60]}")

                            # 도구 정보 저장 (출력 가드용)
                            last_tool_used = tool_name
                            last_tool_result = result_text

                            messages.append(ToolMessage(tool_call_id=tool_id, content=result_text))

                        except Exception as e:
                            error_msg = f"도구 실행 오류: {str(e)[:100]}"
                            print(f"   → {error_msg}")
                            messages.append(ToolMessage(tool_call_id=tool_id, content=error_msg))

                # [4-4] answer 없으면 "확인하지 못했어요"
                if not answer or answer.startswith("당신:"):
                    answer = "확인하지 못했어요"

                # [3] 출력 가드 검사 (실제 연결)
                answer_guarded, guard_notes = output_guard.guard(
                    answer,
                    tool_used=last_tool_used,
                    tool_result=last_tool_result
                )

                elapsed = time.time() - start_time
                print(f"\n봇: {answer_guarded}\n")
                print(f"⏱️ {elapsed:.1f}초 · 도구: {last_tool_used or '없음'}\n")

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
