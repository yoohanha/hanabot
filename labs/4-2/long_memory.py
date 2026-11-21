#!/usr/bin/env python3
# [4-2] 긴 기억 (학번별 파일로 프로그램 재시작 후에도 기억)

import sys
import json
import re
from datetime import datetime
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

# 저장 금지 필드
FORBIDDEN_FIELD_KEYWORDS = {'이름', '전화', '전화번호', '연락처', '휴대폰', '주민', '주민번호', 'name', 'phone', 'ssn'}

# 저장 금지 패턴 (정규식)
FORBIDDEN_PATTERNS = [
    r'\d{3}-\d{3,4}-\d{4}',  # 휴대폰 번호: 010-1234-5678
    r'\d{3}\d{4}\d{4}',      # 휴대폰 번호: 01012345678
    r'\d{6}-\d{7}',           # 주민번호: 900101-1234567
]


# ============================================================================
# 메모리 도구
# ============================================================================

def is_forbidden_field(key: str) -> bool:
    """항목 이름이 금지된 개인정보인지 검사"""
    key_lower = key.lower()
    for forbidden in FORBIDDEN_FIELD_KEYWORDS:
        if forbidden.lower() in key_lower:
            return True
    return False


def is_forbidden_value(value: str) -> bool:
    """값이 금지된 개인정보 패턴인지 검사"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, str(value)):
            return True
    return False


@tool
def save_memory(student_id: str, key: str, value: str) -> str:
    """
    학생의 기억을 저장합니다 (파일에 영구 저장).

    저장 허용: 관심 과정, 선호 시간, 자주 묻는 것
    저장 금지:
      • 항목 이름: 이름, 전화, 전화번호, 연락처, 휴대폰, 주민, 주민번호
      • 값: 휴대폰 번호(010-1234-5678), 주민번호(900101-1234567)

    Args:
        student_id: 학번 (예: HANA-007)
        key: 저장할 항목 (예: 관심_과정)
        value: 값 (예: 실무반)

    Returns:
        str: 저장 결과
    """
    # 1. 저장 금지 필드명 검증
    if is_forbidden_field(key):
        return f"❌ 저장할 수 없는 정보입니다: {key} (보안/프라이버시)"

    # 2. 저장 금지 패턴 검증
    if is_forbidden_value(value):
        return f"❌ 저장할 수 없는 정보입니다: {value} (개인정보 패턴 감지)"

    try:
        memory_file = MEMORY_DIR / f"{student_id}.json"

        # 기존 기억 로드
        memory = {}
        if memory_file.exists():
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory = json.load(f)
            except json.JSONDecodeError:
                memory = {}

        # 새 항목 추가
        memory[key] = value
        memory['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 파일 저장
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

        return f"✅ 저장했습니다: {key} = {value}"

    except Exception as e:
        return f"❌ 저장 오류: {str(e)}"


@tool
def load_memory(student_id: str) -> str:
    """
    학생의 기억을 불러옵니다 (파일에서 로드).

    Args:
        student_id: 학번 (예: HANA-007)

    Returns:
        str: 저장된 기억 (JSON 형식)
    """
    try:
        memory_file = MEMORY_DIR / f"{student_id}.json"

        if not memory_file.exists():
            return f"현재 {student_id} 학번의 기억이 없습니다"

        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)

        # 기억 정보 포맷팅
        memory_str = f"{student_id}의 기억:\n"
        for key, value in memory.items():
            if key != 'updated_at':
                memory_str += f"  • {key}: {value}\n"

        return memory_str

    except Exception as e:
        return f"❌ 로드 오류: {str(e)}"


# ============================================================================
# 에이전트 루프 (메모리 로드 + 저장)
# ============================================================================

def agent_loop_with_long_memory(llm_with_tools, student_id: str, user_question: str,
                                messages: list, max_iterations: int = 3) -> tuple:
    """
    긴 기억을 사용한 에이전트 루프

    Returns:
        (최종 답변, 업데이트된 messages 리스트)
    """
    # 프로그램 시작 시 학생의 기억 로드
    if len(messages) == 0:
        print(f"\n📂 [{student_id}] 기억 로드 중...")
        memory_info = load_memory.invoke({'student_id': student_id})
        print(f"   {memory_info.replace(chr(10), chr(10) + '   ')}")

        # 기억을 시스템 프롬프트처럼 사용
        if "기억이 없습니다" not in memory_info:
            messages.append(HumanMessage(content=f"[시스템 메모리]\n{memory_info}"))

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

                    # 도구 실행
                    if tool_name == 'save_memory':
                        tool_result = save_memory.invoke(tool_args)
                    elif tool_name == 'load_memory':
                        tool_result = load_memory.invoke(tool_args)
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

                # 최근 10개 메시지만 메모리에 유지
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

def main():
    print(f"🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    # 도구 초기화
    try:
        llm_with_tools, tools = create_agent_with_tools()

        # save_memory, load_memory 도구 추가
        tools = list(tools) + [save_memory, load_memory]
        llm_with_tools = llm_with_tools.bind_tools(tools)

        print(f"✅ 도구 로드됨: {', '.join([t.name for t in tools])}\n")
    except Exception as e:
        print(f"❌ 도구 로드 실패: {str(e)}")
        return

    print(f"\n{'#'*100}")
    print("# 긴 기억 (학번별 파일에 영구 저장)")
    print(f"{'#'*100}\n")

    # 테스트 대화
    student_id = "HANA-007"
    test_conversations = [
        ("나는 HANA-007, 나 AI 과정에 관심 있어", "[라운드 1] 기억 저장"),
        ("내가 뭐에 관심 있었어?", "[라운드 2] 기억 확인"),
        ("선호 시간은 오후 2시야", "[라운드 3] 추가 기억"),
    ]

    messages = []

    for idx, (question, label) in enumerate(test_conversations, 1):
        print(f"\n{'='*100}")
        print(f"{label}: {question}")
        print('='*100)

        # 에이전트 루프 실행
        answer, messages = agent_loop_with_long_memory(llm_with_tools, student_id, question, messages.copy(), max_iterations=3)

    # ========== 메모리 파일 확인 ==========
    print(f"\n\n{'='*100}")
    print("📁 저장된 기억 파일")
    print('='*100)

    memory_file = MEMORY_DIR / f"{student_id}.json"
    if memory_file.exists():
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)

        print(f"\n파일: {memory_file}")
        print(f"내용:\n")
        for key, value in memory.items():
            print(f"  • {key}: {value}")
    else:
        print(f"\n기억 파일이 없습니다")

    # ========== 프로그램 재시작 시뮬레이션 ==========
    print(f"\n\n{'='*100}")
    print("🔄 프로그램 재시작 시뮬레이션")
    print('='*100)

    print(f"\n[프로그램 재실행]")
    print(f"messages = []  # 메모리 초기화")
    print(f"새로운 세션 시작\n")

    # 새 세션
    new_messages = []
    restart_question = f"안녕, 나는 {student_id}야. 내가 뭐에 관심 있었는지 기억해?"

    print(f"\n{'='*100}")
    print(f"[라운드 4] 프로그램 재시작 후: {restart_question}")
    print('='*100)

    answer, new_messages = agent_loop_with_long_memory(llm_with_tools, student_id, restart_question, new_messages, max_iterations=3)

    print(f"\n✅ 프로그램을 재시작해도 기억이 유지됨!")


if __name__ == "__main__":
    main()
