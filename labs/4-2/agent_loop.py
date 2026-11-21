#!/usr/bin/env python3
# [4-2] 에이전트 루프 직접 구현 (LangGraph 없이 반복문으로)

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# 4-1 도구 임포트
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-1"))
from hana_tools import create_agent_with_tools, execute_tool

from langchain_core.messages import HumanMessage, ToolMessage


# ============================================================================
# 에이전트 루프 (직접 구현)
# ============================================================================

def agent_loop(llm_with_tools, user_question: str, max_iterations: int = 5) -> dict:
    """
    에이전트 루프를 직접 구현

    도구 호출 → 실행 → 결과를 모델에게 → 또 필요하면 반복
    최대 5번까지만 반복, 넘으면 멈추기

    Returns:
        dict: {'question', 'iterations', 'tools_used', 'final_answer'}
    """
    print(f"\n{'='*100}")
    print(f"🤖 질문: {user_question}")
    print('='*100)

    messages = [HumanMessage(content=user_question)]
    tools_used = []
    iteration_logs = []

    # ========== 에이전트 루프 (최대 max_iterations회) ==========
    for iteration in range(1, max_iterations + 1):
        print(f"\n{'─'*100}")
        print(f"[반복 {iteration}] 모델 호출")
        print('─'*100)

        try:
            # 1. 모델 호출
            response = llm_with_tools.invoke(messages)

            # 2. tool_calls 확인
            if hasattr(response, 'tool_calls') and response.tool_calls:
                print(f"🔧 {len(response.tool_calls)}개 도구 호출됨\n")

                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '알 수 없음')
                    tool_args = tool_call.get('args', {})
                    tool_id = tool_call.get('id', f'call_{iteration}')

                    print(f"   • 도구: {tool_name}")
                    print(f"   • 인자: {tool_args}")

                    # 3. 도구 실행
                    tool_result = execute_tool(tool_name, tool_args)
                    print(f"   • 결과: {tool_result[:80]}")
                    if len(tool_result) > 80:
                        print(f"           ...")

                    # 로그 저장
                    tools_used.append(tool_name)
                    iteration_logs.append({
                        'iteration': iteration,
                        'tool': tool_name,
                        'args': str(tool_args)[:50],
                        'result': tool_result[:60]
                    })

                    # 4. 메시지에 추가 (다음 반복을 위해)
                    messages.append(response)
                    messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=tool_result
                    ))

            else:
                # 도구 없음 → 최종 답변
                print("💬 도구 필요 없음 → 최종 답변 생성\n")
                final_answer = response.content if hasattr(response, 'content') else str(response)

                print(f"✅ [최종 답변]")
                print(f"   {final_answer[:200]}")
                if len(final_answer) > 200:
                    print(f"   ...")

                return {
                    'question': user_question,
                    'iterations': iteration,
                    'tools_used': tools_used,
                    'iteration_logs': iteration_logs,
                    'final_answer': final_answer
                }

        except Exception as e:
            error_msg = f"오류: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                'question': user_question,
                'iterations': iteration,
                'tools_used': tools_used,
                'iteration_logs': iteration_logs,
                'final_answer': error_msg
            }

    # ========== 최대 반복 횟수 초과 ==========
    print(f"\n{'='*100}")
    print(f"⚠️  최대 반복 횟수({max_iterations}회) 도달")
    print('='*100)

    # 마지막 모델 호출로 최종 답변 생성
    try:
        final_response = llm_with_tools.invoke(messages)
        final_answer = final_response.content if hasattr(final_response, 'content') else str(final_response)
    except:
        final_answer = "최종 답변 생성 실패"

    print(f"\n✅ [최종 답변]")
    print(f"   {final_answer[:200]}")

    return {
        'question': user_question,
        'iterations': max_iterations,
        'tools_used': tools_used,
        'iteration_logs': iteration_logs,
        'final_answer': final_answer
    }


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

    # 테스트 질문
    test_question = "내일 오후 2시에 GPU PC 1번 2시간 예약하고, 실무반 2개월 수강료도 알려줘. 내 학번은 HANA-007"

    # 에이전트 루프 실행
    result = agent_loop(llm_with_tools, test_question, max_iterations=5)

    # ========== 결과 표 ==========
    print(f"\n\n{'='*120}")
    print("📊 에이전트 루프 실행 결과")
    print('='*120)

    print(f"\n질문: {result['question']}")
    print(f"반복 횟수: {result['iterations']}회")
    print(f"사용한 도구 수: {len(result['tools_used'])}개")

    if result['iteration_logs']:
        print(f"\n도구 사용 순서:")
        print(f"\n{'반복':<5} | {'도구':<25} | {'인자':<30} | {'결과':<50}")
        print("-"*120)

        for log in result['iteration_logs']:
            iteration = log['iteration']
            tool = log['tool']
            args = log['args']
            result_text = log['result']

            print(f"{iteration:<5} | {tool:<25} | {args:<30} | {result_text:<50}")

    print("="*120)

    print(f"\n최종 답변:")
    print(f"   {result['final_answer'][:300]}")
    if len(result['final_answer']) > 300:
        print(f"   ...")

    # ========== 통계 ==========
    print(f"\n\n{'='*120}")
    print("📈 루프 통계")
    print('='*120)

    tool_counts = {}
    for tool in result['tools_used']:
        tool_counts[tool] = tool_counts.get(tool, 0) + 1

    print(f"\n도구 사용 횟수:")
    for tool, count in tool_counts.items():
        print(f"  • {tool}: {count}회")

    print(f"\n총 반복 횟수: {result['iterations']}")
    print(f"도구 호출 총: {len(result['tools_used'])}회")

    if result['iterations'] >= 5:
        print(f"\n⚠️  최대 반복 횟수 도달!")


if __name__ == "__main__":
    main()
