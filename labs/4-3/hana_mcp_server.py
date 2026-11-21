#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-3] "hana-academy" MCP 서버 (mcp SDK 2.x)

import sys
import json
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# [4-3] 1~2교시 도구 import
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-1"))
from hana_tools import (
    search_rules,
    calculate_course_fee,
    reserve_gpu_pc,
)

# [4-3] 4-2 메모리 도구 import
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-2"))
from long_memory import cancel_gpu_pc

from mcp.server import Server
from mcp.types import Tool, TextContent, CallToolResult


# ============================================================================
# MCP 서버 생성
# ============================================================================

server = Server("hana-academy")

# [4-3] 도구 정의
TOOLS = [
    Tool(
        name="search_rules",
        description="규정 문서에서 정보를 검색합니다. 학원의 운영 규칙, 환급 정책, GPU PC 예약 규칙, 상담 시간 등을 알아야 할 때 사용합니다.",
        inputSchema={
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "규정에 관한 질문 (예: '기초반은 며칠 운영돼?')"
                }
            },
            "required": ["question"]
        }
    ),
    Tool(
        name="calc_fee",
        description="수강료를 계산합니다. 과정별 월 단위 가격과 할인을 계산해야 할 때 사용합니다.",
        inputSchema={
            "type": "object",
            "properties": {
                "course": {
                    "type": "string",
                    "description": "과정 이름 ('기초반' 또는 '실무반')"
                },
                "months": {
                    "type": "integer",
                    "description": "수강 개월 수"
                },
                "discount_type": {
                    "type": "string",
                    "description": "할인 종류 ('없음', '재수강', '친구')",
                    "default": "없음"
                }
            },
            "required": ["course", "months"]
        }
    ),
    Tool(
        name="reserve_gpu",
        description="GPU PC를 예약합니다. GPU PC가 필요한 프로젝트 작업 시간을 미리 예약할 때 사용합니다.",
        inputSchema={
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "예약 날짜 (YYYY-MM-DD 형식)"
                },
                "start_time": {
                    "type": "string",
                    "description": "시작 시각 (HH:MM 형식)"
                },
                "duration": {
                    "type": "integer",
                    "description": "이용 시간 (2 또는 4시간만 가능)"
                },
                "pc_number": {
                    "type": "integer",
                    "description": "PC 번호 (1~4)"
                },
                "student_id": {
                    "type": "string",
                    "description": "학번",
                    "default": "HANA-001"
                }
            },
            "required": ["date", "start_time", "duration", "pc_number"]
        }
    ),
    Tool(
        name="cancel_gpu",
        description="GPU PC 예약을 취소합니다. 이미 예약한 GPU PC를 더 이상 사용하지 않을 때 사용합니다.",
        inputSchema={
            "type": "object",
            "properties": {
                "reservation_id": {
                    "type": "string",
                    "description": "예약 ID 또는 '조회' 명령"
                },
                "student_id": {
                    "type": "string",
                    "description": "학번",
                    "default": "HANA-001"
                }
            },
            "required": ["reservation_id"]
        }
    ),
    Tool(
        name="get_schedule",
        description="특정 월의 수업 일정을 조회합니다. 학원의 월별 수업 일정, 휴원일, 특별 수업 날짜를 알아야 할 때 사용합니다.",
        inputSchema={
            "type": "object",
            "properties": {
                "month": {
                    "type": "integer",
                    "description": "월 (1~12)"
                }
            },
            "required": ["month"]
        }
    ),
]


# ============================================================================
# 도구 목록 반환
# ============================================================================

@server.list_tools()
async def list_tools():
    """[4-3] 도구 목록 반환"""
    return TOOLS


# ============================================================================
# 도구 호출 처리
# ============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> CallToolResult:
    """[4-3] 도구 호출 처리"""
    try:
        if name == "search_rules":
            result = search_rules.invoke({"question": arguments.get("question", "")})

        elif name == "calc_fee":
            result = calculate_course_fee.invoke({
                "course": arguments.get("course"),
                "months": arguments.get("months"),
                "discount_type": arguments.get("discount_type", "없음"),
            })

        elif name == "reserve_gpu":
            result = reserve_gpu_pc.invoke({
                "date": arguments.get("date"),
                "start_time": arguments.get("start_time"),
                "duration": arguments.get("duration"),
                "pc_number": arguments.get("pc_number"),
                "student_id": arguments.get("student_id", "HANA-001"),
            })

        elif name == "cancel_gpu":
            result = cancel_gpu_pc.invoke({
                "reservation_id": arguments.get("reservation_id"),
                "student_id": arguments.get("student_id", "HANA-001"),
            })

        elif name == "get_schedule":
            # [4-3] 기본 구현 (1~2교시에 없음)
            try:
                from web.services import get_schedule as web_get_schedule
                schedule = web_get_schedule(arguments.get("month", 12))
                result = json.dumps(schedule, ensure_ascii=False, indent=2)
            except Exception as e:
                result = f"일정 조회 오류: {str(e)}"

        else:
            result = f"알 수 없는 도구: {name}"

        return CallToolResult(
            content=[TextContent(type="text", text=result)],
            isError=False,
        )

    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"도구 실행 오류: {str(e)}")],
            isError=True,
        )


# ============================================================================
# 메인
# ============================================================================

async def main():
    # [4-3] stdio transport로 실행
    from mcp.server.stdio import stdio_server

    async with stdio_server(server):
        pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
