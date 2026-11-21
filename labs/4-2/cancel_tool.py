#!/usr/bin/env python3
# [4-2] 취소 도구 추가 (메모리 에이전트)

import sys
import json
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# 4-1 도구 임포트
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-1"))
from hana_tools import create_agent_with_tools, execute_tool

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage


# ============================================================================
# 도구 경로
# ============================================================================

TOOLS_DATA_DIR = PROJECT_ROOT / "labs" / "4-1" / "data"
TOOLS_DATA_DIR.mkdir(parents=True, exist_ok=True)
RESERVES_FILE = TOOLS_DATA_DIR / "reserves_local.json"


# ============================================================================
# 취소 도구
# ============================================================================

@tool
def cancel_gpu_pc(reservation_id: str) -> str:
    """
    GPU PC 예약을 취소합니다.

    에이전트가 GPU PC 예약 취소를 해야 할 때 사용합니다.
    예약 번호를 모르면 대화 기록에서 방금 한 예약을 찾아 써라.
    예: "R-20261122-01"

    Args:
        reservation_id: 예약 번호 (R-YYYYMMDD-NN 형식)

    Returns:
        str: 취소 결과 (성공/실패)
    """
    try:
        # 예약 파일 읽기
        if not RESERVES_FILE.exists():
            return f"❌ 예약 기록이 없습니다"

        with open(RESERVES_FILE, 'r', encoding='utf-8') as f:
            reserves = json.load(f)

        # 예약 찾기
        found = False
        new_reserves = []

        for reserve in reserves:
            if reserve.get('reserve_id') == reservation_id:
                found = True
                print(f"   [삭제] {reservation_id} - {reserve['date']} {reserve['start_time']}")
            else:
                new_reserves.append(reserve)

        if not found:
            return f"❌ 예약 번호 {reservation_id}를 찾을 수 없습니다"

        # 파일 저장
        with open(RESERVES_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_reserves, f, ensure_ascii=False, indent=2)

        return f"✅ 예약 번호 {reservation_id}가 취소되었습니다"

    except Exception as e:
        return f"❌ 취소 오류: {str(e)}"


# ============================================================================
# 에이전트 루프 (메모리 + 취소 도구)
# ============================================================================

def agent_loop_with_cancel(llm_with_tools, user_question: str, messages: list, max_iterations: int = 3) -> tuple:
    """
    취소 도구를 포함한 에이전트 루프

    Returns:
        (최종 답변, 업데이트된 messages 리스트)
    """
    messages.append(HumanMessage(content=user_question))

    print(f"\n[질문] {user_question}")
    print(f"[메모리] {len(messages)}개 메시지 유지 중")

    # 최대 max_iterations회 반복
    for iteration in range(1, max_iterations + 1):
        try:
            response = llm_with_tools.invoke(messages)

            # tool_calls 확인
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"  🔧 [반복 {iteration}] 도구 호출")

                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '알 수 없음')
                    tool_args = tool_call.get('args', {})
                    tool_id = tool_call.get('id', f'call_{iteration}')

                    print(f"      • {tool_name}")

                    # 도구 실행 (cancel_gpu_pc도 포함)
                    if tool_name == 'cancel_gpu_pc':
                        tool_result = cancel_gpu_pc.invoke({'reservation_id': tool_args.get('reservation_id', '')})
                    else:
                        tool_result = execute_tool(tool_name, tool_args)

                    # 메시지 추가
                    messages.append(response)
                    messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=tool_result
                    ))

            else:
                # 도구 없음 → 최종 답변
                final_answer = response.content if hasattr(response, 'content') else str(response)
                messages.append(response)

                print(f"  💬 [답변] {final_answer[:60]}")

                # 최근 10개 메시지만 유지
                if len(messages) > 10:
                    messages = messages[-10:]

                return final_answer, messages

        except Exception as e:
            error_msg = f"오류: {str(e)}"
            print(f"  ❌ {error_msg}")
            return error_msg, messages

    # 최대 반복 초과
    print(f"  ⚠️  최대 반복 횟수 도달")
    try:
        final_response = llm_with_tools.invoke(messages)
        final_answer = final_response.content if hasattr(final_response, 'content') else str(final_response)
        messages.append(final_response)
    except:
        final_answer = "최종 답변 생성 실패"

    if len(messages) > 10:
        messages = messages[-10:]

    return final_answer, messages


# ============================================================================
# 메인
# ============================================================================

def show_reserves_file():
    """현재 예약 파일 내용 표시"""
    if not RESERVES_FILE.exists():
        print(f"  📁 예약 파일 없음")
        return

    try:
        with open(RESERVES_FILE, 'r', encoding='utf-8') as f:
            reserves = json.load(f)

        if not reserves:
            print(f"  📁 예약 파일 (비어있음)")
            return

        print(f"  📁 현재 예약 ({len(reserves)}개):")
        for idx, reserve in enumerate(reserves, 1):
            print(f"      {idx}. {reserve['reserve_id']} - {reserve['student_id']} - {reserve['date']} {reserve['start_time']} (GPU-{reserve['pc_number']})")

    except json.JSONDecodeError:
        print(f"  📁 예약 파일 읽기 오류")


def main():
    print(f"🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    # 도구 초기화 (cancel_gpu_pc 도구 추가)
    try:
        llm_with_tools, tools = create_agent_with_tools()

        # cancel_gpu_pc 도구 추가
        # LLM에 새 도구 바인딩
        from langchain_core.tools import tool as tool_decorator
        tools = list(tools) + [cancel_gpu_pc]
        llm_with_tools = llm_with_tools.bind_tools(tools)

        print(f"✅ 도구 로드됨: {', '.join([t.name for t in tools])}\n")
    except Exception as e:
        print(f"❌ 도구 로드 실패: {str(e)}")
        return

    print(f"\n{'#'*100}")
    print("# 메모리 에이전트 + 취소 도구")
    print(f"{'#'*100}\n")

    # 예약 파일 초기화
    if RESERVES_FILE.exists():
        RESERVES_FILE.unlink()
    print("✅ 예약 파일 초기화됨\n")

    # 3개 대화 순차 처리
    conversations = [
        "나는 HANA-007, 내일 오후 2시에 GPU PC 1번 2시간 예약해줘",
        "아 미안, 방금 예약한 거 취소해줘",
        "내 예약 남아 있어?"
    ]

    messages = []

    for idx, question in enumerate(conversations, 1):
        print(f"\n{'='*100}")
        print(f"[대화 {idx}] {question}")
        print('='*100)

        # 에이전트 루프 실행
        answer, messages = agent_loop_with_cancel(llm_with_tools, question, messages, max_iterations=3)

        # 예약 파일 상태 표시
        print(f"\n[예약 파일 상태]")
        show_reserves_file()

    # ========== 최종 메모리 상태 ==========
    print(f"\n\n{'='*100}")
    print("📌 최종 메모리 상태")
    print('='*100)
    print(f"\n총 {len(messages)}개 메시지\n")

    for idx, msg in enumerate(messages, 1):
        msg_type = type(msg).__name__

        if isinstance(msg, HumanMessage):
            content = f"🧑 {msg.content[:50]}"
        elif isinstance(msg, AIMessage):
            content = f"🤖 {msg.content[:50]}"
        elif isinstance(msg, ToolMessage):
            content = f"🔧 {msg.content[:50]}"
        else:
            content = str(msg)[:50]

        if len(content) > 60:
            content += "..."

        print(f"{idx:2}. [{msg_type:<12}] {content}")


if __name__ == "__main__":
    main()
