#!/usr/bin/env python3
# [4-2] 짧은 기억 (최근 10개 메시지 유지)

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# 4-1 도구 임포트
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-1"))
from hana_tools import create_agent_with_tools, execute_tool

from langchain_core.messages import HumanMessage, ToolMessage, AIMessage


# ============================================================================
# 대화 목록 (no_memory.py와 동일)
# ============================================================================

CONVERSATIONS = [
    {
        'question': "나는 HANA-007 이야",
        'expected': "학번 등록",
    },
    {
        'question': "내 학번 뭐야?",
        'expected': "HANA-007",
    },
    {
        'question': "실무반 수강료 얼마야?",
        'expected': "500,000원 (할인 없음)",
    },
    {
        'question': "그럼 3개월이면?",
        'expected': "1,500,000원",
    },
    {
        'question': "내일 오후 2시에 GPU PC 1번 2시간 예약해줘",
        'expected': "예약 완료",
    },
]


# ============================================================================
# 에이전트 루프 (기억 포함)
# ============================================================================

def agent_loop_with_memory(llm_with_tools, user_question: str, messages: list, max_iterations: int = 3) -> tuple:
    """
    기억을 유지하면서 에이전트 루프 실행

    Args:
        llm_with_tools: 도구 연결된 LLM
        user_question: 사용자 질문
        messages: 기존 메시지 리스트 (대화 이력)
        max_iterations: 최대 반복 횟수

    Returns:
        (최종 답변, 업데이트된 messages 리스트)
    """
    # 현재 메시지에 질문 추가
    messages.append(HumanMessage(content=user_question))

    print(f"\n[질문] {user_question}")
    print(f"[기억 상태] 현재 {len(messages)}개 메시지")

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
                    print(f"  📌 [메모리 정리] 최근 10개만 유지")

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
        print(f"✅ 도구 로드됨: {', '.join([t.name for t in tools])}\n")
    except Exception as e:
        print(f"❌ 도구 로드 실패: {str(e)}")
        return

    print(f"\n{'#'*100}")
    print("# 짧은 기억 (최근 10개 메시지 유지)")
    print(f"{'#'*100}\n")

    # 기억 없는 버전의 결과 (no_memory.py 결과 임포트)
    no_memory_results = {
        1: "네, 알겠습니다",
        2: "말씀해주신 학번을 모름",
        3: "500,000원",
        4: "'실무반'을 모르고...",
        5: "HANA-001로 예약됨"
    }

    results = []
    messages = []  # 기억할 메시지 리스트

    # 5개 대화 순차 처리
    for idx, conv in enumerate(CONVERSATIONS, 1):
        question = conv['question']
        expected = conv['expected']

        print(f"\n{'='*100}")
        print(f"[대화 {idx}] {question}")
        print('='*100)

        # 에이전트 루프 실행 (기억 유지)
        answer, messages = agent_loop_with_memory(llm_with_tools, question, messages, max_iterations=3)

        results.append({
            'idx': idx,
            'question': question,
            'expected': expected,
            'with_memory': answer[:60],
            'without_memory': no_memory_results.get(idx, "?"),
        })

    # ========== 비교 표 ==========
    print(f"\n\n{'='*150}")
    print("📊 기억 없을 때 vs 기억 있을 때")
    print('='*150)

    print(f"\n{'#':<2} | {'질문':<35} | {'기억 없음':<40} | {'기억 있음':<40}")
    print("-"*150)

    for result in results:
        idx = result['idx']
        question = result['question'][:35]
        without = result['without_memory'][:40]
        with_mem = result['with_memory'][:40]

        print(f"{idx:<2} | {question:<35} | {without:<40} | {with_mem:<40}")

    print("="*150)

    # ========== 최종 메모리 상태 ==========
    print(f"\n\n{'='*100}")
    print("📌 최종 기억 상태 (메시지 리스트)")
    print('='*100)
    print(f"\n총 {len(messages)}개 메시지\n")

    for idx, msg in enumerate(messages, 1):
        msg_type = type(msg).__name__

        if isinstance(msg, HumanMessage):
            content = f"🧑 {msg.content[:60]}"
        elif isinstance(msg, AIMessage):
            content = f"🤖 {msg.content[:60]}"
        elif isinstance(msg, ToolMessage):
            content = f"🔧 {msg.content[:60]}"
        else:
            content = str(msg)[:60]

        if len(content) > 70:
            content += "..."

        print(f"{idx:2}. [{msg_type:<12}] {content}")

    print(f"\n{'='*100}")
    print("✅ 최근 10개 메시지만 메모리에 유지됨")
    print("   → 다음 대화도 이 메시지들을 기억하면서 처리")
    print('='*100)


if __name__ == "__main__":
    main()
