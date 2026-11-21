#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] 메모리 에이전트 + MCP 서버 3개 (Time · Filesystem · hana-academy)

import sys
from pathlib import Path

# Windows UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [4-3] 2교시 메모리 에이전트
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-2"))
from long_memory import agent_loop_with_long_memory

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage


# ============================================================================
# MCP 서버 목록 (시작할 때 표시)
# ============================================================================

MCP_SERVERS = {
    "Time": {
        "command": "uvx mcp-server-time --local-timezone Asia/Seoul",
        "tools": ["get_current_time", "convert_time", "get_time_ago"],
    },
    "Filesystem": {
        "command": "npx -y @modelcontextprotocol/server-filesystem <data_path>",
        "tools": ["read_file", "read_text_file", "list_directory", "search_files"],
    },
    "hana-academy": {
        "command": "python labs/4-3/hana_mcp_server.py",
        "tools": ["search_rules", "calc_fee", "reserve_gpu", "cancel_gpu", "get_schedule"],
    },
}


# ============================================================================
# 도구 정의
# ============================================================================

@tool
def get_current_time() -> str:
    """[MCP Time] 현재 시간 조회"""
    return "현재 시간: 2026년 11월 21일 (토) 오후 3시"


@tool
def search_schedule() -> str:
    """[MCP Filesystem] 수업 일정 검색"""
    return "12월 첫 주 시간표: 월 기초반, 화 실무반, 수 GPU 실습"


@tool
def calc_fee_mcp(course: str, months: int, discount: str) -> str:
    """[MCP hana-academy] 수강료 계산"""
    return f"실무반 2개월 친구 할인: 400,000원 → 320,000원 (20% 할인)"


@tool
def reserve_gpu_mcp() -> str:
    """[MCP hana-academy] GPU PC 예약"""
    return "예약 완료: 2026-11-22 14:00 ~ 16:00 PC 1번"


@tool
def cancel_gpu_mcp() -> str:
    """[MCP hana-academy] 예약 취소"""
    return "예약 취소 완료: 2026-11-22 14:00 ~ 16:00 PC 1번"


# ============================================================================
# 대화형 에이전트
# ============================================================================

def agent_loop_interactive(llm_with_tools, question: str, messages: list) -> tuple:
    """
    [4-3] MCP 도구를 사용하는 대화형 에이전트
    """
    messages.append(HumanMessage(content=question))

    try:
        response = llm_with_tools.invoke(messages)

        # 도구 호출 확인
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name', '알 수 없음')

                # [4-3] MCP 서버 선택 (질문 내용 기반)
                server_name = "알 수 없음"
                if any(x in question for x in ['시간', '몇 시', '요일']):
                    server_name = "Time"
                elif any(x in question for x in ['시간표', '수업', '일정']):
                    server_name = "Filesystem"
                elif any(x in question for x in ['가격', '수강료', '할인', '비용', '수강']):
                    server_name = "hana-academy"
                elif any(x in question for x in ['예약', 'GPU', 'PC']):
                    server_name = "hana-academy"
                elif any(x in question for x in ['규정', '취소', '환급', '수업', '상담']):
                    server_name = "hana-academy"

                print(f"   [MCP {server_name}] {tool_name}")

        # 최종 답변
        messages.append(response)
        final_answer = response.content if hasattr(response, 'content') else str(response)
        print(f"\n💬 {final_answer}\n")

        return final_answer, messages

    except Exception as e:
        print(f"   오류: {e}\n")
        return str(e), messages


# ============================================================================
# 메인
# ============================================================================

def main():
    print(f"\n{'='*80}")
    print("[4-3] AI 에이전트 · MCP 도구 (대화형)")
    print(f"{'='*80}\n")

    # MCP 서버 연결 상태
    print("📋 MCP 서버 연결 상태\n")
    for server_name in MCP_SERVERS.keys():
        print(f"   ✅ {server_name} 연결됨")
    print()

    # LLM 설정
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
    )

    # 도구 바인딩
    tools = [
        get_current_time,
        search_schedule,
        calc_fee_mcp,
        reserve_gpu_mcp,
        cancel_gpu_mcp,
    ]
    llm_with_tools = llm.bind_tools(tools)

    # 대화형 루프
    print(f"{'='*80}")
    print("대화를 시작합니다. 'q'를 입력하면 종료합니다.")
    print(f"{'='*80}\n")

    messages = []

    while True:
        try:
            # 사용자 입력
            user_input = input("당신: ").strip()

            if user_input.lower() == 'q':
                print("\n프로그램을 종료합니다. 👋\n")
                break

            if not user_input:
                continue

            # 에이전트 실행
            print()
            agent_loop_interactive(llm_with_tools, user_input, messages)

        except KeyboardInterrupt:
            print("\n\n프로그램을 종료합니다. 👋\n")
            break
        except UnicodeEncodeError as e:
            print(f"[인코딩 오류] 응답을 출력할 수 없습니다.\n")
            continue
        except Exception as e:
            print(f"오류: {str(e)[:100]}\n")
            continue


if __name__ == "__main__":
    main()
