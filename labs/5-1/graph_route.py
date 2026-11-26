#!/usr/bin/env python3
# [5-1] LangGraph 상태 그래프 · 라우팅

import os
import sys
import json
from pathlib import Path
from typing import Annotated
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [5-1] 4-1 도구 import (복사 금지)
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))
from hana_tools import (
    get_today,
    search_rules,
    calculate_course_fee,
    reserve_gpu_pc
)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import StreamWriter
from typing_extensions import TypedDict


# ============================================================================
# State 정의
# ============================================================================

class AgentState(TypedDict):
    """에이전트 상태"""
    question: str          # 사용자 질문
    route: str            # 분류 결과 (규정, 수강료, 예약, 기타)
    answer: str           # 최종 답변


# ============================================================================
# 도구 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# LLM 초기화
# ============================================================================

def create_llm():
    """LLM 초기화 (5-1 규칙에 따라)"""
    today = datetime.now().strftime("%Y년 %m월 %d일 (%A)")
    today_kr = today.replace("Monday", "월").replace("Tuesday", "화").replace(
        "Wednesday", "수").replace("Thursday", "목").replace(
        "Friday", "금").replace("Saturday", "토").replace("Sunday", "일")

    system_message = f"""당신은 하나봇 AI 에이전트입니다.
오늘 날짜: {today_kr}
역할: 학원 관련 질문을 분류하고 적절한 답변을 제공합니다.
질문 분류: 규정, 수강료, 예약, 기타 중 정확히 하나로 분류해야 합니다."""

    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,          # [5-1] 에이전트 결정성 필요
        num_ctx=8192,          # [5-1] 컨텍스트 윈도우
        num_predict=512,       # [5-1] 최대 출력 토큰
        timeout=120            # [5-1] 타임아웃 120초
    )

    return llm, system_message


# ============================================================================
# 노드: classify
# ============================================================================

def classify_node(state: AgentState) -> AgentState:
    """
    질문을 분류하는 노드
    규정 · 수강료 · 예약 · 기타 중 정확히 하나로 분류
    """
    llm, system_msg = create_llm()

    prompt = f"""다음 질문을 정확히 하나의 단어로 분류하세요:
질문: {state['question']}

분류 옵션:
- "규정" - 학원 규정, 정책, 기초반/실무반 개수, GPU 예약 시간, 지각 정책 등
- "수강료" - 수강료, 가격, 할인 계산 등
- "예약" - GPU PC 예약 같은 시스템 예약 요청
- "기타" - 학원 관련이 아닌 질문

답변 형식: 분류 결과만 한 단어로 (예: 규정)"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        route = response.content.strip().split()[0]  # 첫 단어만 추출

        # 유효한 분류 확인
        valid_routes = ["규정", "수강료", "예약", "기타"]
        if route not in valid_routes:
            route = "기타"  # 기본값

    except Exception as e:
        print(f"❌ 분류 오류: {str(e)}")
        route = "기타"

    state['route'] = route
    return state


# ============================================================================
# 노드: 규정 처리
# ============================================================================

def search_rules_node(state: AgentState) -> AgentState:
    """규정 검색 도구 사용"""
    try:
        result = search_rules.invoke({'question': state['question']})
        state['answer'] = result
    except Exception as e:
        state['answer'] = f"❌ 규정 검색 오류: {str(e)}"

    return state


# ============================================================================
# 노드: 수강료 계산
# ============================================================================

def calc_fee_node(state: AgentState) -> AgentState:
    """수강료 계산 도구 사용"""
    try:
        # 간단한 추출 (실제로는 더 정교한 NLU 필요)
        question = state['question']

        # 기초반/실무반 판단
        course = "기초반" if "기초반" in question else "실무반"

        # 개월 수 추출 (1~12)
        months = 1
        for word in question.split():
            if word.isdigit() and 1 <= int(word) <= 12:
                months = int(word)
                break

        # 할인 종류 판단
        discount = "없음"
        if "재수강" in question:
            discount = "재수강"
        elif "친구" in question or "친구 할인" in question:
            discount = "친구"

        result = calculate_course_fee.invoke({
            'course': course,
            'months': months,
            'discount_type': discount
        })
        state['answer'] = result

    except Exception as e:
        state['answer'] = f"❌ 수강료 계산 오류: {str(e)}"

    return state


# ============================================================================
# 노드: 예약 안내
# ============================================================================

def reserve_guide_node(state: AgentState) -> AgentState:
    """예약 요청에 대한 안내 (다음 단계에서 구현)"""
    state['answer'] = "⏳ GPU PC 예약 기능은 다음 단계(5-2)에서 구현됩니다.\n예약 요청: " + state['question']
    return state


# ============================================================================
# 노드: 기타 응답
# ============================================================================

def other_node(state: AgentState) -> AgentState:
    """학원 관련이 아닌 질문 처리"""
    state['answer'] = "❓ 학원 관련 질문만 답변해드립니다.\n예) 규정, 수강료, 예약 등"
    return state


# ============================================================================
# 조건 엣지 함수
# ============================================================================

def route_decision(state: AgentState) -> str:
    """route 값에 따라 다음 노드 결정"""
    return state['route']


# ============================================================================
# 그래프 생성
# ============================================================================

def create_graph():
    """LangGraph StateGraph 생성"""
    graph = StateGraph(AgentState)

    # 노드 추가
    graph.add_node("classify", classify_node)
    graph.add_node("search_rules", search_rules_node)
    graph.add_node("calc_fee", calc_fee_node)
    graph.add_node("reserve_guide", reserve_guide_node)
    graph.add_node("other", other_node)

    # 엣지 추가
    graph.add_edge(START, "classify")

    # 조건 엣지 (classify 이후)
    graph.add_conditional_edges(
        "classify",
        route_decision,
        {
            "규정": "search_rules",
            "수강료": "calc_fee",
            "예약": "reserve_guide",
            "기타": "other"
        }
    )

    # END로 연결
    graph.add_edge("search_rules", END)
    graph.add_edge("calc_fee", END)
    graph.add_edge("reserve_guide", END)
    graph.add_edge("other", END)

    return graph.compile()


# ============================================================================
# 테스트 및 시각화
# ============================================================================

def save_mermaid_diagram(compiled_graph):
    """그래프를 Mermaid 다이어그램으로 저장"""
    diagram = compiled_graph.get_graph().draw_mermaid()

    output_file = Path(__file__).parent / "graph.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# [5-1] LangGraph 라우팅 그래프\n\n")
        f.write("```mermaid\n")
        f.write(diagram)
        f.write("\n```\n")

    print(f"✅ 그래프 저장: {output_file}")


def test_graph():
    """그래프 테스트"""
    # 그래프 생성
    compiled_graph = create_graph()

    # 다이어그램 저장
    save_mermaid_diagram(compiled_graph)

    # 테스트 질문 4개
    test_questions = [
        "지각하면 어떻게 돼?",           # 규정
        "실무반 2개월 친구 할인이면?",  # 수강료
        "내일 GPU 예약해줘",            # 예약
        "오늘 서울 날씨 어때?"          # 기타
    ]

    print(f"\n{'='*80}")
    print("[5-1] LangGraph 라우팅 테스트")
    print(f"{'='*80}\n")

    results = []

    for idx, question in enumerate(test_questions, 1):
        print(f"[질문 {idx}] {question}")

        # 그래프 실행
        try:
            state = {
                "question": question,
                "route": "",
                "answer": ""
            }

            result = compiled_graph.invoke(state)

            route = result['route']
            answer = result['answer']

            print(f"  → 분류: {route}")
            print(f"  → 답변: {answer[:60]}{'...' if len(answer) > 60 else ''}\n")

            results.append({
                "question": question,
                "route": route,
                "answer": answer
            })

        except Exception as e:
            print(f"  ❌ 오류: {str(e)}\n")

    # 결과 표
    print(f"{'='*80}")
    print("📊 테스트 결과 (질문 · 고른 길 · 답)")
    print(f"{'='*80}\n")

    # Markdown 표
    print("| # | 질문 | 고른 길 | 답 |")
    print("|---|------|--------|-----|")

    for idx, result in enumerate(results, 1):
        question = result['question']
        route = result['route']
        answer = result['answer'][:40]
        if len(result['answer']) > 40:
            answer += "..."

        print(f"| {idx} | {question} | {route} | {answer} |")

    # JSON 저장
    result_file = DATA_DIR / "graph_test_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 테스트 결과 저장: {result_file}")


def main():
    """메인 함수"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    test_graph()


if __name__ == "__main__":
    main()
