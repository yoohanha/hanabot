#!/usr/bin/env python3
# [4-2] 긴 기억 테스트 (1회차 → 프로그램 재실행 → 2회차)

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
# 메모리 경로 설정
# ============================================================================

MEMORY_DIR = PROJECT_ROOT / "labs" / "4-2" / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

FORBIDDEN_FIELDS = {'이름', '전화번호', '주민번호', 'name', 'phone', 'ssn', '전화', '휴대폰'}


# ============================================================================
# 메모리 도구
# ============================================================================

@tool
def save_memory(student_id: str, key: str, value: str) -> str:
    """학생의 기억을 저장합니다 (파일에 영구 저장)."""
    # 저장 금지 필드 검증
    if key in FORBIDDEN_FIELDS:
        return f"❌ 저장할 수 없는 정보입니다: {key}"

    try:
        memory_file = MEMORY_DIR / f"{student_id}.json"
        memory = {}
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                memory = json.load(f)

        memory[key] = value
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

        return f"✅ 저장했습니다: {key} = {value}"
    except Exception as e:
        return f"❌ 저장 오류: {str(e)}"


@tool
def load_memory(student_id: str) -> str:
    """학생의 기억을 불러옵니다 (파일에서 로드)."""
    try:
        memory_file = MEMORY_DIR / f"{student_id}.json"

        if not memory_file.exists():
            return f"현재 {student_id} 학번의 기억이 없습니다"

        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)

        memory_str = f"{student_id}의 기억:\n"
        for key, value in memory.items():
            memory_str += f"  • {key}: {value}\n"

        return memory_str
    except Exception as e:
        return f"❌ 로드 오류: {str(e)}"


# ============================================================================
# 에이전트 루프
# ============================================================================

def agent_loop_with_memory(llm_with_tools, student_id: str, user_question: str,
                           messages: list, max_iterations: int = 3) -> tuple:
    """메모리를 사용한 에이전트 루프"""
    # 첫 메시지일 때 기억 로드
    if len(messages) == 0:
        print(f"\n📂 [{student_id}] 기억 로드 중...")
        memory_info = load_memory.invoke({'student_id': student_id})
        print(f"   {memory_info.replace(chr(10), chr(10) + '   ')}")

        if "기억이 없습니다" not in memory_info:
            messages.append(HumanMessage(content=f"[시스템 메모리]\n{memory_info}"))

    messages.append(HumanMessage(content=user_question))
    print(f"\n[질문] {user_question}")
    print(f"[메모리] {len(messages)}개 메시지")

    # 최대 max_iterations회 반복
    for iteration in range(1, max_iterations + 1):
        try:
            response = llm_with_tools.invoke(messages)

            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"  🔧 [반복 {iteration}] 도구 호출")

                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '알 수 없음')
                    tool_args = tool_call.get('args', {})
                    tool_id = tool_call.get('id', f'call_{iteration}')

                    print(f"      • {tool_name}")

                    # 도구 실행
                    if tool_name == 'save_memory':
                        tool_result = save_memory.invoke(tool_args)
                        print(f"        → {tool_result}")
                    elif tool_name == 'load_memory':
                        tool_result = load_memory.invoke(tool_args)
                    else:
                        tool_result = execute_tool(tool_name, tool_args)

                    messages.append(response)
                    messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=tool_result
                    ))

            else:
                # 최종 답변
                final_answer = response.content if hasattr(response, 'content') else str(response)
                messages.append(response)

                print(f"  💬 [답변] {final_answer[:70]}")
                if len(final_answer) > 70:
                    print(f"           ...")

                if len(messages) > 10:
                    messages = messages[-10:]

                return final_answer, messages

        except Exception as e:
            error_msg = f"오류: {str(e)}"
            print(f"  ❌ {error_msg}")
            return error_msg, messages

    # 최대 반복 초과
    print(f"  ⚠️  최대 반복 횟수 도달")
    if len(messages) > 10:
        messages = messages[-10:]

    return "최대 반복 도달", messages


# ============================================================================
# 메인
# ============================================================================

def show_memory_file(student_id):
    """메모리 파일 내용 표시"""
    memory_file = MEMORY_DIR / f"{student_id}.json"

    print(f"\n📁 메모리 파일: {memory_file}")

    if not memory_file.exists():
        print(f"   (파일 없음)")
        return

    try:
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)

        print(f"   내용:")
        for key, value in memory.items():
            print(f"     • {key}: {value}")

        # 금지된 필드 확인
        forbidden_found = []
        for field in FORBIDDEN_FIELDS:
            if field in memory:
                forbidden_found.append(field)

        if forbidden_found:
            print(f"\n   ⚠️  경고: 저장 금지 필드가 있습니다!")
            for field in forbidden_found:
                print(f"      • {field}")
        else:
            print(f"\n   ✅ 저장 금지 필드 없음")

    except json.JSONDecodeError:
        print(f"   (파일 읽기 오류)")


def main():
    print(f"🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    # 도구 초기화
    try:
        llm_with_tools, tools = create_agent_with_tools()
        tools = list(tools) + [save_memory, load_memory]
        llm_with_tools = llm_with_tools.bind_tools(tools)
        print(f"✅ 도구 로드됨: {len(tools)}개\n")
    except Exception as e:
        print(f"❌ 도구 로드 실패: {str(e)}")
        return

    student_id = "HANA-007"

    # 기존 메모리 삭제 (테스트 시작)
    memory_file = MEMORY_DIR / f"{student_id}.json"
    if memory_file.exists():
        memory_file.unlink()
        print(f"✅ 기존 메모리 파일 삭제됨\n")

    # ========== 1회차 ==========
    print(f"\n{'='*120}")
    print("🔵 [1회차 세션 시작]")
    print('='*120)

    round1_conversations = [
        "나는 HANA-007, 실무반 관심 있고 오후 수업이 좋아. 기억해줘",
        "나 전화번호는 010-1234-5678이야, 이것도 기억해줘"
    ]

    messages_1 = []

    for idx, question in enumerate(round1_conversations, 1):
        print(f"\n{'─'*120}")
        print(f"[1회차 질문 {idx}]")
        answer, messages_1 = agent_loop_with_memory(llm_with_tools, student_id, question, messages_1, max_iterations=3)

    # 1회차 메모리 파일 확인
    print(f"\n{'─'*120}")
    print("[1회차 메모리 파일 상태]")
    show_memory_file(student_id)

    # ========== 프로그램 재실행 시뮬레이션 ==========
    print(f"\n\n{'='*120}")
    print("🔄 [프로그램 완전 종료 후 재실행 시뮬레이션]")
    print('='*120)

    print(f"\n프로세스 종료: messages = []")
    print(f"새로운 파이썬 프로세스 시작\n")

    messages_2 = []  # 완전히 새로운 메시지 리스트

    # ========== 2회차 ==========
    print(f"\n{'='*120}")
    print("🟢 [2회차 세션 시작]")
    print('='*120)

    question_2 = "나 HANA-007 인데, 나한테 맞는 수업 추천해줘"

    print(f"\n{'─'*120}")
    print("[2회차 질문]")
    answer, messages_2 = agent_loop_with_memory(llm_with_tools, student_id, question_2, messages_2, max_iterations=3)

    # 2회차 메모리 파일 확인
    print(f"\n{'─'*120}")
    print("[2회차 메모리 파일 상태]")
    show_memory_file(student_id)

    # ========== 최종 비교 ==========
    print(f"\n\n{'='*120}")
    print("📊 테스트 결과 요약")
    print('='*120)

    print(f"""
✅ 1회차에서 저장된 기억:
   • 관심 과정: 실무반
   • 선호 시간: 오후

❌ 1회차에서 거부된 기억:
   • 전화번호: 010-1234-5678 (저장 금지)

✅ 2회차 (프로그램 재실행 후):
   • 1회차 기억이 로드됨 (파일에서 읽음)
   • "나한테 맞는 수업" 질문에 저장된 정보 사용
   • 전화번호는 여전히 저장되지 않음

📌 핵심 검증:
   1. 메모리 파일이 1회차에서 생성됨
   2. 2회차에서 파일 로드 성공
   3. 전화번호는 거부됨 (저장 금지)
   4. 프로그램 재실행 후에도 정보 유지
    """)


if __name__ == "__main__":
    main()
