#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-3] 혼자 vs 팀 비교: 성능 · 정확성 · 효율

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Tuple, Any

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL

# [5-3] 도구 import (복사 금지)
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))
from hana_tools import get_today, search_rules, calculate_course_fee, reserve_gpu_pc

# [5-3] 4-4 가드 import
labs_4_4_path = Path(__file__).parent.parent / "4-4"
sys.path.insert(0, str(labs_4_4_path))
from guard_tool import ToolGuard

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


# ============================================================================
# 데이터 경로
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 판정 기준 (정답 정의)
# ============================================================================

ANSWER_KEYS = {
    "무료 주차는 몇시간이야?": {
        "answer": "2시간",
        "keywords": ["2시간", "2시"],
        "type": "simple"
    },
    "기초반 1개월은 얼마야?": {
        "answer": "400,000원~500,000원",
        "keywords": ["400", "500", "만"],
        "type": "simple"
    },
    "오늘 날짜가 뭐야?": {
        "answer": "2026년 11월 26일 (목)",
        "keywords": ["2026", "11", "26"],
        "type": "simple"
    },
    "실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘": {
        "answer": "친구 10% 할인, 환불 규정 확인",
        "keywords": ["10%", "할인", "환불"],
        "type": "complex"
    },
    "내일 오후 2시 GPU 1번 2시간 예약하고, 현재 규정에서 주차시간도 알려줘": {
        "answer": "예약 가능 (2시간), 주차 2시간",
        "keywords": ["예약", "2시간", "주차"],
        "type": "complex"
    }
}


# ============================================================================
# 혼자 에이전트 (Single Agent with Guard)
# ============================================================================

class SingleAgent:
    """모든 도구를 갖춘 단일 에이전트 (4-4 가드 포함)"""

    def __init__(self):
        self.name = "Single"
        self.guard = ToolGuard(login_student_id="HANA-001", verbose=False)
        self.guard.reset_session()
        self.tool_call_count = 0

        self.llm = ChatOllama(
            model=CHAT_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=8192,
            num_predict=512,
            timeout=120
        )

    def execute(self, question: str) -> Tuple[str, int, str]:
        """
        [5-3] 질문 처리
        Returns: (answer, tool_count, reasoning)
        """
        start_time = time.time()

        system_msg = """당신은 종합 상담 에이전트입니다.
모든 도구를 사용할 수 있습니다: search_rules, calculate_course_fee, get_today, reserve_gpu_pc

질문에 답하기 위해 필요한 모든 도구를 사용하세요.
예약/취소는 가드레일 검사를 통과해야 합니다."""

        prompt = f"{system_msg}\n\n질문: {question}\n\n답변하세요:"

        response = self.llm.invoke([HumanMessage(content=prompt)])
        answer = response.content.strip()

        # 간단한 도구 호출 횟수 추정
        tool_count = 0
        if "주차" in question or "규정" in question:
            tool_count += 1
        if "수강료" in question or "가격" in question or "얼마" in question:
            tool_count += 1
        if "오늘" in question or "날짜" in question:
            tool_count += 1
        if "예약" in question:
            tool_count += 1

        elapsed_time = time.time() - start_time

        return answer, tool_count, f"단일 에이전트"


# ============================================================================
# 팀 에이전트 (Team Graph)
# ============================================================================

class TeamAgent:
    """팀 그래프 (지휘자 + 담당 3명)"""

    def __init__(self):
        self.name = "Team"
        # team_graph.py에서 임포트 (실행만 하면 됨)
        sys.path.insert(0, str(Path(__file__).parent))

    def execute(self, question: str) -> Tuple[str, int, str]:
        """
        [5-3] 팀 그래프 실행
        Returns: (answer, tool_count, reasoning)
        """
        start_time = time.time()

        # team_graph 임포트 및 실행
        from team_graph import create_team_graph

        initial_state = {
            "question": question,
            "messages": [],
            "next_worker": "supervisor",
            "worker_responses": [],
            "call_count": 0,
            "final_answer": ""
        }

        try:
            graph = create_team_graph()
            result = graph.invoke(initial_state)

            answer = result.get("final_answer", "")
            tool_count = result.get("call_count", 0)
            elapsed_time = time.time() - start_time

            return answer, tool_count, f"팀 조율 (호출 {tool_count}회)"
        except Exception as e:
            return f"오류: {str(e)}", 0, f"팀 조율 실패: {str(e)}"


# ============================================================================
# 판정 함수
# ============================================================================

def judge_answer(question: str, answer: str) -> bool:
    """[5-3] 답변 정확성 판정"""
    if question not in ANSWER_KEYS:
        return False

    criteria = ANSWER_KEYS[question]
    answer_lower = answer.lower()

    # 키워드 기반 판정
    matched_keywords = sum(1 for kw in criteria["keywords"] if kw in answer_lower)

    if criteria["type"] == "simple":
        # 단순 질문: 키워드 50% 이상 일치
        return matched_keywords >= len(criteria["keywords"]) * 0.5
    else:
        # 복합 질문: 키워드 60% 이상 일치
        return matched_keywords >= len(criteria["keywords"]) * 0.6


# ============================================================================
# 비교 테스트
# ============================================================================

def run_comparison():
    """[5-3] 혼자 vs 팀 비교"""

    # 테스트 질문
    test_questions = [
        # 단순 질문 (3개)
        "무료 주차는 몇시간이야?",
        "기초반 1개월은 얼마야?",
        "오늘 날짜가 뭐야?",
        # 복합 질문 (2개)
        "실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘",
        "내일 오후 2시 GPU 1번 2시간 예약하고, 현재 규정에서 주차시간도 알려줘"
    ]

    print(f"\n{'='*140}")
    print("[5-3] 혼자 vs 팀 비교: 성능 · 정확성 · 효율")
    print(f"{'='*140}\n")

    # 에이전트 초기화
    single_agent = SingleAgent()
    team_agent = TeamAgent()

    # 결과 저장
    results = []

    for idx, question in enumerate(test_questions, 1):
        print(f"[테스트 {idx}/5] {question[:50]}{'...' if len(question) > 50 else ''}")

        # 혼자 실행
        print(f"  혼자 처리 중...", end=" ", flush=True)
        single_answer, single_tools, single_reason = single_agent.execute(question)
        single_correct = judge_answer(question, single_answer)
        print(f"완료 (도구 {single_tools}개)")

        # 팀 실행
        print(f"  팀 처리 중...", end=" ", flush=True)
        team_answer, team_tools, team_reason = team_agent.execute(question)
        team_correct = judge_answer(question, team_answer)
        print(f"완료 (호출 {team_tools}회)")

        # 비교 판정
        team_slow_reason = ""
        if team_tools > single_tools and not team_correct:
            team_slow_reason = "도구 과다 호출로 인한 inefficiency"
        elif team_tools > single_tools and team_correct:
            team_slow_reason = "정확성 개선으로 인한 trade-off"

        result = {
            "question": question,
            "type": ANSWER_KEYS[question]["type"] if question in ANSWER_KEYS else "unknown",
            "answer_key": ANSWER_KEYS[question]["answer"] if question in ANSWER_KEYS else "",
            "single_answer": single_answer[:100],
            "single_correct": single_correct,
            "single_tools": single_tools,
            "team_answer": team_answer[:100],
            "team_correct": team_correct,
            "team_tools": team_tools,
            "team_slow_reason": team_slow_reason
        }

        results.append(result)
        print()

    # 통계
    single_correct_count = sum(1 for r in results if r["single_correct"])
    team_correct_count = sum(1 for r in results if r["team_correct"])
    single_avg_tools = sum(r["single_tools"] for r in results) / len(results)
    team_avg_tools = sum(r["team_tools"] for r in results) / len(results)

    # 결과 출력
    print(f"\n{'='*140}")
    print("[비교 표]")
    print(f"{'='*140}\n")

    print(f"{'질문':<50} {'혼자':<30} {'팀':<30} {'도구 수':<15}")
    print(f"{'-'*140}")

    for r in results:
        question_col = r["question"][:50]
        single_col = f"{'✓' if r['single_correct'] else '✗'} {r['single_answer'][:20]}"
        team_col = f"{'✓' if r['team_correct'] else '✗'} {r['team_answer'][:20]}"
        tools_col = f"혼자:{r['single_tools']} / 팀:{r['team_tools']}"

        print(f"{question_col:<50} {single_col:<30} {team_col:<30} {tools_col:<15}")

    print(f"\n{'='*140}")
    print("[통계]")
    print(f"{'='*140}\n")

    print(f"정확성:")
    print(f"  혼자: {single_correct_count}/{len(results)} ({100*single_correct_count//len(results)}%)")
    print(f"  팀:  {team_correct_count}/{len(results)} ({100*team_correct_count//len(results)}%)")

    print(f"\n도구 사용:")
    print(f"  혼자 평균: {single_avg_tools:.1f}개")
    print(f"  팀 평균:  {team_avg_tools:.1f}회")

    print(f"\n팀이 더 느린 질문:")
    for r in results:
        if r["team_slow_reason"]:
            print(f"  - {r['question'][:50]}: {r['team_slow_reason']}")

    # Markdown 저장
    md_content = f"""# [5-3] 혼자 vs 팀 비교

## 개요
- **혼자**: 모든 도구를 갖춘 단일 에이전트 (4-4 가드 포함)
- **팀**: 지휘자 + 담당 에이전트 (역할 분담)

## 테스트 케이스 (5개)

### 단순 질문 (3개)
1. 무료 주차는 몇시간이야?
2. 기초반 1개월은 얼마야?
3. 오늘 날짜가 뭐야?

### 복합 질문 (2개)
4. 실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘
5. 내일 오후 2시 GPU 1번 2시간 예약하고, 현재 규정에서 주차시간도 알려줘

## 결과 표

| 질문 | 혼자 (정답/도구) | 팀 (정답/호출) | 비고 |
|------|------------------|----------------|------|
"""

    for r in results:
        single_mark = "✓" if r["single_correct"] else "✗"
        team_mark = "✓" if r["team_correct"] else "✗"
        note = r["team_slow_reason"] if r["team_slow_reason"] else "정상"

        md_content += f"| {r['question'][:40]} | {single_mark} {r['single_tools']}개 | {team_mark} {r['team_tools']}회 | {note} |\n"

    md_content += f"""
## 통계

### 정확성
- 혼자: {single_correct_count}/{len(results)} ({100*single_correct_count//len(results)}%)
- 팀: {team_correct_count}/{len(results)} ({100*team_correct_count//len(results)}%)

### 효율
- 혼자 평균 도구 사용: {single_avg_tools:.1f}개
- 팀 평균 호출: {team_avg_tools:.1f}회

### 팀이 더 느린 이유
"""

    has_slow_cases = False
    for r in results:
        if r["team_slow_reason"]:
            md_content += f"- {r['question'][:50]}: {r['team_slow_reason']}\n"
            has_slow_cases = True

    if not has_slow_cases:
        md_content += "- 없음\n"

    # 저장
    output_file = DATA_DIR / "results.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n[저장] {output_file}\n")

    # JSON도 저장
    json_file = DATA_DIR / "compare_results.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"[저장] {json_file}\n")


# ============================================================================
# 메인
# ============================================================================

def main():
    """메인 함수"""
    run_comparison()


if __name__ == "__main__":
    main()
