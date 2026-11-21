#!/usr/bin/env python3
# [4-1] 하나봇 도구 모음 (Tool Collection for Agent)

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Any

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
from hanabot.rag import answer_question
from web.services import reserve_gpu as web_reserve_gpu

# LangChain 임포트
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


# ============================================================================
# 도구 경로 설정
# ============================================================================

TOOLS_DATA_DIR = Path(__file__).parent / "data"
TOOLS_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 도구 정의 (Tools with Korean docstrings)
# ============================================================================

@tool
def get_today() -> str:
    """
    오늘의 날짜와 요일을 반환합니다.

    에이전트가 현재 날짜를 알아야 할 때 사용합니다.
    예: "오늘 몇 월 며칠이야?" 같은 질문에 대답할 때

    Returns:
        str: "2026년 11월 21일 (금)" 형식의 날짜 문자열
    """
    today = datetime.now()
    days = ["월", "화", "수", "목", "금", "토", "일"]
    weekday = days[today.weekday()]
    return f"{today.year}년 {today.month}월 {today.day}일 ({weekday})"


@tool
def search_rules(question: str) -> str:
    """
    규정 문서에서 정보를 검색하고 답변합니다.

    에이전트가 규정 문서(RAG)에 있는 정보를 찾아야 할 때 사용합니다.
    예: "기초반은 며칠 운영돼?", "GPU PC 예약 최대 몇 시간?", "상담 시간은?"

    Args:
        question: 규정에 관한 질문

    Returns:
        str: 규정 문서에서 찾은 답변
    """
    try:
        answer, sources = answer_question(question)
        return f"답변: {answer}\n\n근거: {', '.join(sources)}"
    except Exception as e:
        return f"규정 검색 오류: {str(e)}"


@tool
def calculate_course_fee(course: str, months: int, discount_type: str = "없음") -> str:
    """
    수강료를 계산하고 반환합니다.

    에이전트가 과정별 가격을 계산해야 할 때 사용합니다.
    예: "실무반 3개월에 친구 할인 받으면 얼마야?", "기초반 2개월 재수강 가격은?"

    Args:
        course: 과정 이름 ("기초반" 또는 "실무반")
        months: 개월 수 (정수)
        discount_type: 할인 종류 ("없음", "재수강", "친구")

    Returns:
        str: 금액 계산 결과 (원 단위)
    """
    from web.services import calc_fee
    try:
        result = calc_fee(course, months, discount_type)
        if 'error' in result:
            return f"오류: {result['error']}"
        return result.get('message', '')
    except Exception as e:
        return f"계산 실패: {str(e)}"


@tool
def reserve_gpu_pc(date: str, start_time: str, duration: int, pc_number: int, student_id: str = "HANA-001") -> str:
    """
    GPU PC를 예약합니다.

    에이전트가 GPU PC 예약을 해야 할 때 사용합니다.
    예: "내일 오후 2시에 GPU PC 2시간 예약해줘", "2026-11-22 14:00부터 4시간 예약"

    Args:
        date: 예약 날짜 (YYYY-MM-DD 형식)
        start_time: 시작 시각 (HH:MM 형식)
        duration: 이용 시간 (2 또는 4시간만 가능)
        pc_number: PC 번호 (1~4)
        student_id: 학번 (기본: HANA-001)

    Returns:
        str: 예약 결과 (성공/실패)
    """
    try:
        # web/services.py의 reserve_gpu 호출
        result = web_reserve_gpu(student_id, date, start_time, duration, pc_number)

        if result.get('success'):
            # 성공한 예약을 labs/4-1/data/로도 저장
            reserve_id = result.get('reserve_id', '')
            save_to_local_data(
                "reserves_local.json",
                {
                    'reserve_id': reserve_id,
                    'student_id': student_id,
                    'date': date,
                    'start_time': start_time,
                    'duration': duration,
                    'pc_number': pc_number,
                    'created_at': datetime.now().isoformat()
                }
            )
            return f"✅ {result['message']}"
        else:
            return f"❌ {result['message']}"

    except Exception as e:
        return f"예약 오류: {str(e)}"


# ============================================================================
# 보조 함수
# ============================================================================

def save_to_local_data(filename: str, data: dict) -> None:
    """도구 실행 결과를 labs/4-1/data/로 저장"""
    file_path = TOOLS_DATA_DIR / filename

    # 기존 데이터 로드
    records = []
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
        except json.JSONDecodeError:
            records = []

    # 새 데이터 추가
    records.append(data)

    # 저장
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


# ============================================================================
# 에이전트 초기화
# ============================================================================

def create_agent_with_tools():
    """도구와 함께 LLM 초기화"""
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3
    )

    # 도구 바인딩 (4개 도구)
    tools = [get_today, search_rules, calculate_course_fee, reserve_gpu_pc]
    llm_with_tools = llm.bind_tools(tools)

    return llm_with_tools, tools


# ============================================================================
# 에이전트 실행
# ============================================================================

def run_agent_question(llm_with_tools, question: str, question_num: int, expected_tools: list = None) -> dict:
    """
    에이전트로 질문 실행

    Returns:
        dict: {'question', 'tools_used', 'final_answer', 'expected_tools', 'is_correct'}
    """
    print(f"\n{'='*80}")
    print(f"[질문 {question_num}] {question}")
    print('='*80)

    # 1. 에이전트에 질문 전송
    print(f"\n📝 [질문 전송]")

    try:
        response = llm_with_tools.invoke([HumanMessage(content=question)])

        # 2. 응답 분석
        print(f"\n🤔 [LLM 응답 분석]")
        tools_called = []

        # tool_calls가 있는지 확인
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get('name', '알 수 없음')
                tool_args = tool_call.get('args', {})
                tools_called.append({
                    'name': tool_name,
                    'args': tool_args
                })
                print(f"   • 도구: {tool_name}")
                print(f"   • 인자: {tool_args}")

        # 3. 최종 답변 추출
        print(f"\n💬 [최종 답변]")
        final_answer = response.content if hasattr(response, 'content') else str(response)
        print(f"   {final_answer[:200]}")

        # 4. 도구 선택 평가
        tools_names = [t['name'] for t in tools_called]
        expected_tools = expected_tools or []
        is_correct = set(tools_names) == set(expected_tools)

        return {
            'question': question,
            'tools_used': tools_called,
            'final_answer': final_answer,
            'expected_tools': expected_tools,
            'is_correct': is_correct
        }

    except Exception as e:
        error_msg = f"오류: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'question': question,
            'tools_used': [],
            'final_answer': error_msg,
            'expected_tools': expected_tools or [],
            'is_correct': False
        }


# ============================================================================
# 질문 세트 (6개 질문)
# ============================================================================

QUESTIONS = [
    {
        'question': "지각 몇 번이면 결석이야?",
        'expected_tools': ['search_rules'],
        'description': '규정 검색'
    },
    {
        'question': "기초반 2개월 재수강이면 얼마야?",
        'expected_tools': ['calculate_course_fee'],
        'description': '요금 계산'
    },
    {
        'question': "내일 오후 2시에 GPU PC 1번 2시간 예약해줘",
        'expected_tools': ['get_today', 'reserve_gpu_pc'],
        'description': '예약 (날짜 계산 필요)'
    },
    {
        'question': "오늘 무슨 요일이야?",
        'expected_tools': ['get_today'],
        'description': '날짜 조회'
    },
    {
        'question': "안녕!",
        'expected_tools': [],
        'description': '도구 불필요'
    },
    {
        'question': "주차는 몇 시간 무료야?",
        'expected_tools': ['search_rules'],
        'description': '규정 검색'
    },
]


# ============================================================================
# 메인 (대화형)
# ============================================================================

def interactive_mode(llm_with_tools):
    """대화형 에이전트"""
    print(f"\n{'='*80}")
    print("💬 AI 에이전트 대화형 모드")
    print('='*80)
    print("도구 4개: get_today, search_rules, calculate_course_fee, reserve_gpu_pc")
    print("명령: 질문을 입력하세요. 'q'를 입력하면 종료합니다.\n")

    results = []

    while True:
        print("-"*80)
        user_input = input("🧑 질문 > ").strip()

        if user_input.lower() == 'q':
            print("\n대화형 모드를 종료합니다.\n")
            break

        if not user_input:
            print("❌ 질문을 입력해주세요.\n")
            continue

        # 에이전트 실행
        try:
            response = llm_with_tools.invoke([HumanMessage(content=user_input)])

            # 도구 분석
            tools_used = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '알 수 없음')
                    tool_args = tool_call.get('args', {})
                    tools_used.append({'name': tool_name, 'args': tool_args})

                print(f"\n🔧 도구 호출:")
                for tool in tools_used:
                    print(f"   • {tool['name']}")
                    if tool['args']:
                        for key, val in tool['args'].items():
                            print(f"     - {key}: {val}")

            # 답변
            final_answer = response.content if hasattr(response, 'content') else str(response)
            print(f"\n💬 답변:")
            print(f"   {final_answer}\n")

            results.append({
                'question': user_input,
                'tools_used': tools_used,
                'final_answer': final_answer
            })

        except Exception as e:
            print(f"\n❌ 오류: {str(e)}\n")

    # 대화 요약
    if results:
        print(f"\n{'='*80}")
        print("📊 대화 요약")
        print('='*80)
        print(f"\n총 {len(results)}개 질문\n")

        for idx, result in enumerate(results, 1):
            question = result['question'][:50]
            if len(result['question']) > 50:
                question += "..."

            tools_str = ", ".join([t['name'] for t in result['tools_used']]) if result['tools_used'] else "없음"

            print(f"{idx}. {question}")
            print(f"   도구: {tools_str}\n")


def demo_mode(llm_with_tools):
    """데모 모드 (6개 질문 자동 실행)"""
    print(f"\n{'#'*80}")
    print("# 데모 모드: 6개 질문 자동 실행")
    print(f"{'#'*80}\n")

    results = []

    for idx, q_data in enumerate(QUESTIONS, 1):
        question = q_data['question']
        expected_tools = q_data['expected_tools']
        result = run_agent_question(llm_with_tools, question, idx, expected_tools)
        results.append(result)

    # ========== 평가 표 ==========
    print(f"\n\n{'='*130}")
    print("📊 도구 선택 평가 표 (고른 도구 · 정답 도구 · 맞음/틀림)")
    print('='*130)

    headers = ["#", "질문", "고른 도구", "정답 도구", "결과"]
    print(f"\n{headers[0]:<2} | {headers[1]:<40} | {headers[2]:<20} | {headers[3]:<20} | {headers[4]:<10}")
    print("-"*130)

    correct_count = 0
    for idx, result in enumerate(results, 1):
        question = result['question'][:40]
        if len(result['question']) > 40:
            question += "..."

        # 고른 도구
        tools_used = [t['name'] for t in result['tools_used']]
        tools_used_str = ", ".join(tools_used) if tools_used else "없음"

        # 정답 도구
        expected = result['expected_tools']
        expected_str = ", ".join(expected) if expected else "없음"

        # 결과
        if result['is_correct']:
            result_str = "✅ 맞음"
            correct_count += 1
        else:
            result_str = "❌ 틀림"

        print(f"{idx:<2} | {question:<40} | {tools_used_str:<20} | {expected_str:<20} | {result_str:<10}")

    print("="*130)
    print(f"\n📈 정확도: {correct_count}/{len(results)} ({correct_count*100//len(results)}%)\n")

    # 저장된 도구 데이터 확인
    print(f"\n📁 저장된 도구 데이터:")
    for data_file in TOOLS_DATA_DIR.glob("*.json"):
        print(f"   • {data_file.name}")
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"     - 기록 {len(data)}개")
        except:
            pass


def main():
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}")
    print(f"💾 도구 데이터 저장: {TOOLS_DATA_DIR}\n")

    # 도구 초기화
    try:
        llm_with_tools, tools = create_agent_with_tools()
        print(f"✅ 도구 로드됨: {', '.join([t.name for t in tools])}\n")
    except Exception as e:
        print(f"❌ 도구 로드 실패: {str(e)}")
        return

    # 모드 선택
    print("실행 모드:")
    print("1. 대화형 (질문 입력 후 답변)")
    print("2. 데모 (6개 질문 자동 실행)")
    print("-"*80)

    mode = input("모드 선택 (1 또는 2) > ").strip()

    if mode == '1':
        interactive_mode(llm_with_tools)
    elif mode == '2':
        demo_mode(llm_with_tools)
    else:
        print("❌ 잘못된 선택입니다.\n")


if __name__ == "__main__":
    main()
