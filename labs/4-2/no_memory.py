#!/usr/bin/env python3
# [4-2] 메모리 없이 각 질문을 독립적으로 처리 (문제점 시연)

import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
from langchain_core.messages import HumanMessage

# 4-1 도구 임포트
sys.path.insert(0, str(PROJECT_ROOT / "labs" / "4-1"))
from hana_tools import create_agent_with_tools


# ============================================================================
# 대화 목록 (메모리 없이 매번 새로 처리)
# ============================================================================

CONVERSATIONS = [
    {
        'question': "나는 HANA-007 이야",
        'expected': "학번 등록",
        'problem': "메모리가 없어 다음 질문에서 학번을 모름"
    },
    {
        'question': "내 학번 뭐야?",
        'expected': "HANA-007",
        'problem': "앞 대화를 메모리하지 않아서 학번을 모름"
    },
    {
        'question': "실무반 수강료 얼마야?",
        'expected': "500,000원 (할인 없음)",
        'problem': "할인 대상 여부를 모름 (학번 정보 없음)"
    },
    {
        'question': "그럼 3개월이면?",
        'expected': "1,500,000원",
        'problem': "앞 질문('실무반')을 모르고, 3개월 단위도 불명확"
    },
    {
        'question': "내일 오후 2시에 GPU PC 1번 2시간 예약해줘",
        'expected': "예약 완료",
        'problem': "학번 정보 없어 예약 불가 (기본값 HANA-001으로 예약됨)"
    },
]


# ============================================================================
# 에이전트 실행
# ============================================================================

def run_no_memory_conversation():
    """메모리 없이 각 질문을 독립적으로 처리"""
    print(f"🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    # 도구 초기화
    try:
        llm_with_tools, tools = create_agent_with_tools()
        print(f"✅ 도구 로드됨: {', '.join([t.name for t in tools])}\n")
    except Exception as e:
        print(f"❌ 도구 로드 실패: {str(e)}")
        return

    results = []

    print(f"\n{'#'*80}")
    print("# 메모리 없는 대화 (각 질문이 독립적)")
    print(f"{'#'*80}\n")

    for idx, conv in enumerate(CONVERSATIONS, 1):
        question = conv['question']
        expected = conv['expected']
        problem = conv['problem']

        print(f"\n{'='*80}")
        print(f"[질문 {idx}] {question}")
        print('='*80)

        # 🔴 중요: 매번 새로운 메시지 리스트 (메모리 없음)
        messages = [HumanMessage(content=question)]

        try:
            response = llm_with_tools.invoke(messages)

            # 도구 분석
            tools_used = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '알 수 없음')
                    tools_used.append(tool_name)
                    print(f"🔧 도구: {tool_name}")

            # 답변
            answer = response.content if hasattr(response, 'content') else str(response)
            print(f"\n💬 답변:")
            print(f"   {answer[:150]}")

            results.append({
                'idx': idx,
                'question': question,
                'expected': expected,
                'answer': answer[:80],
                'tools_used': ", ".join(tools_used) if tools_used else "없음",
                'problem': problem
            })

        except Exception as e:
            error_msg = f"오류: {str(e)}"
            print(f"❌ {error_msg}")
            results.append({
                'idx': idx,
                'question': question,
                'expected': expected,
                'answer': error_msg,
                'tools_used': "없음",
                'problem': problem
            })

    # ========== 결과 표 ==========
    print(f"\n\n{'='*180}")
    print("📊 메모리 없이 처리할 때의 문제점")
    print('='*180)

    print(f"\n{'#':<2} | {'질문':<40} | {'기대 답변':<30} | {'실제 답변':<40} | {'왜 틀렸는지':<50}")
    print("-"*180)

    for result in results:
        idx = result['idx']
        question = result['question'][:40]
        if len(result['question']) > 40:
            question += "..."

        expected = result['expected'][:30]
        answer = result['answer'][:40]
        problem = result['problem'][:50]

        print(f"{idx:<2} | {question:<40} | {expected:<30} | {answer:<40} | {problem:<50}")

    print("="*180)

    # ========== 상세 분석 ==========
    print(f"\n\n{'='*100}")
    print("🔍 상세 분석")
    print('='*100)

    for result in results:
        print(f"\n[{result['idx']}] {result['question']}")
        print(f"    기대: {result['expected']}")
        print(f"    실제: {result['answer']}")
        print(f"    문제: {result['problem']}")

    print(f"\n\n{'='*100}")
    print("⚠️  메모리 없이 처리할 때의 문제")
    print('='*100)
    print("""
1️⃣  질문 1-2: "학번을 말해도 다음 질문에서 모름"
   - 각 질문이 독립적으로 처리됨
   - 대화 이력이 없음

2️⃣  질문 3-4: "앞 질문의 맥락을 모름"
   - "그럼 3개월이면?"에서 "실무반"을 모름
   - 과정 정보를 반복해야 함

3️⃣  질문 5: "예약이 기본값 학번(HANA-001)으로 됨"
   - 사용자가 말한 HANA-007이 반영 안 됨
   - 데이터 오류 발생

✅ 해결방법: 메모리 시스템 필요!
   • 사용자별 메모리 파일 (labs/4-2/memory/)
   • 대화 이력 저장
   • 다음 질문에서 메모리 로드
    """)


if __name__ == "__main__":
    run_no_memory_conversation()
