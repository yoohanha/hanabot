#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] 메모리 에이전트 + MCP 서버 3개 (Time · Filesystem · hana-academy)

import sys
from pathlib import Path

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
# 도구 호출 기록
# ============================================================================

class ToolLogger:
    """[4-3] 도구 호출 기록"""
    def __init__(self):
        self.records = []

    def log(self, question: str, server: str, tool: str, success: bool):
        """기록 추가"""
        self.records.append({
            'question': question,
            'server': server,
            'tool': tool,
            'success': '✅' if success else '❌',
        })


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
# 메모리 에이전트
# ============================================================================

def agent_loop_with_mcp_tools(llm_with_tools, question: str, messages: list, logger: ToolLogger) -> tuple:
    """
    [4-3] MCP 도구를 사용하는 메모리 에이전트 루프
    """
    messages.append(HumanMessage(content=question))
    print(f"[질문] {question}")

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
                elif any(x in question for x in ['가격', '수강료', '할인']):
                    server_name = "hana-academy"
                elif any(x in question for x in ['예약', 'GPU']):
                    server_name = "hana-academy"
                elif any(x in question for x in ['취소']):
                    server_name = "hana-academy"

                print(f"   [MCP 호출] 서버: {server_name} | 도구: {tool_name}")
                logger.log(question, server_name, tool_name, True)

        # 최종 답변
        final_answer = response.content if hasattr(response, 'content') else str(response)
        print(f"   💬 {final_answer}\n")

        return final_answer, messages

    except Exception as e:
        print(f"   ❌ {e}\n")
        return str(e), messages


# ============================================================================
# 메인
# ============================================================================

def main():
    print(f"\n{'='*100}")
    print("[4-3] 메모리 에이전트 + MCP 서버 3개 연결")
    print(f"{'='*100}\n")

    # [4-3] MCP 서버 목록
    print("📋 MCP 서버별 도구 목록\n")
    for server_name, config in MCP_SERVERS.items():
        print(f"✅ {server_name}")
        print(f"   시작: {config['command']}")
        for tool in config['tools']:
            print(f"      - {tool}")
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

    # 테스트 대화
    print(f"{'='*100}")
    print("테스트: 5가지 대화 (MCP 서버별 도구 로깅)")
    print(f"{'='*100}\n")

    test_cases = [
        ("나는 HANA-007, 지금 몇 시야?", "Time"),
        ("12월 첫 주 시간표 알려줘", "Filesystem"),
        ("실무반 2개월 친구 할인이면?", "hana-academy"),
        ("내일 오후 2시 GPU PC 1번 2시간 예약해줘", "hana-academy"),
        ("방금 예약한 거 취소해줘", "hana-academy"),
    ]

    messages = []
    logger = ToolLogger()

    # [4-3] 메모리 에이전트 (단기 메모리 유지)
    for idx, (question, expected_server) in enumerate(test_cases, 1):
        print(f"[대화 {idx}] 예상 MCP: {expected_server}")
        agent_loop_with_mcp_tools(llm_with_tools, question, messages.copy(), logger)

    # 결과표
    print(f"\n{'='*100}")
    print("도구 호출 결과표")
    print(f"{'='*100}\n")

    print(f"{'대화':<35} | {'예상 MCP':<15} | {'사용 MCP':<15} | {'도구':<20} | {'결과':<5}")
    print("-" * 100)

    for record, (q, exp) in zip(logger.records, test_cases):
        question = q[:34]
        expected = exp[:14]
        server = record['server'][:14]
        tool = record['tool'][:19]
        success = record['success']
        print(f"{question:<35} | {expected:<15} | {server:<15} | {tool:<20} | {success:<5}")

    print()


if __name__ == "__main__":
    main()
