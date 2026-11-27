#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-4] Sequential vs Hierarchical 비교 테스트

import sys
import time
import re
from pathlib import Path
from typing import Tuple, Dict

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from crew_hana import run_crew as run_crew_sequential
from crew_hierarchical import run_crew_hierarchical


# ============================================================================
# [5-4] 정답 기준 정의 (data/RAG_PLAN.md 기반)
# ============================================================================

ANSWER_KEYS = {
    "실무반 2개월 친구 할인 금액이랑 환불 규정 알려줘": {
        "keywords": ["90만원", "900000", "환불", "2/3", "1/2"],
        "description": "실무반 50만원 × 2개월 × 10% 할인 = 90만원 + 환불 규정",
    },
    "기초반 3개월 재수강 가격은?": {
        "keywords": ["45만원", "450000", "50%", "할인"],
        "description": "기초반 30만원 × 3개월 × 50% 할인 = 45만원",
    },
    "환불은 개강 전에 취소하면 얼마 돌려받아?": {
        "keywords": ["전액", "100%", "전액 환불"],
        "description": "개강 전 취소시 전액 환불",
    },
}

TEST_QUESTIONS = list(ANSWER_KEYS.keys())


# ============================================================================
# [5-4] 답변 검증 함수
# ============================================================================

def validate_answer(question: str, answer: str) -> Tuple[bool, str]:
    """
    실제 답변이 정답 기준을 만족하는지 검증합니다.

    Args:
        question (str): 테스트 질문
        answer (str): LLM의 답변

    Returns:
        Tuple[bool, str]: (맞음 여부, 판정 사유)
    """
    if question not in ANSWER_KEYS:
        return False, "정답 기준이 없는 질문"

    answer_lower = answer.lower()
    keywords = ANSWER_KEYS[question]["keywords"]

    # 키워드 매칭 (최소 하나 이상 포함)
    matched_keywords = [kw for kw in keywords if kw.lower() in answer_lower]

    if len(matched_keywords) >= 1:
        return True, f"키워드 매칭: {', '.join(matched_keywords)}"
    else:
        return False, f"필수 키워드 없음: {', '.join(keywords[:2])}"


# ============================================================================
# [5-4] 테스트 실행
# ============================================================================

def run_test() -> Dict:
    """
    Sequential과 Hierarchical을 테스트합니다.

    Returns:
        Dict: 테스트 결과
    """
    results = {
        "sequential": [],
        "hierarchical": [],
    }

    print("=" * 100)
    print("[5-4] Sequential vs Hierarchical 비교 테스트")
    print("=" * 100)
    print()

    for idx, question in enumerate(TEST_QUESTIONS, 1):
        print(f"\n📌 질문 {idx}: {question}")
        print("-" * 100)

        # Sequential 테스트
        print("\n⏱  Sequential 실행 중...")
        try:
            start_time = time.time()
            answer_seq = run_crew_sequential(question)
            elapsed_seq = time.time() - start_time

            if elapsed_seq < 1.0:
                print(f"⚠️  Sequential 처리 시간: {elapsed_seq:.2f}초 (너무 빠름 - 의심)")
                is_valid_seq = False
                answer_seq = "시간 초과"
            else:
                is_valid_seq, reason_seq = validate_answer(question, answer_seq)
                print(f"✓ Sequential 완료: {elapsed_seq:.2f}초 | 판정: {'맞음' if is_valid_seq else '틀림'}")

            results["sequential"].append({
                "question": question,
                "time": elapsed_seq,
                "answer": answer_seq[:50] + "..." if len(answer_seq) > 50 else answer_seq,
                "correct": is_valid_seq,
            })
        except Exception as e:
            print(f"✗ Sequential 오류: {str(e)[:50]}")
            results["sequential"].append({
                "question": question,
                "time": 0,
                "answer": "시간 초과",
                "correct": False,
            })

        # Hierarchical 테스트
        print("\n⏱  Hierarchical 실행 중...")
        try:
            start_time = time.time()
            answer_hier = run_crew_hierarchical(question)
            elapsed_hier = time.time() - start_time

            if elapsed_hier < 1.0:
                print(f"⚠️  Hierarchical 처리 시간: {elapsed_hier:.2f}초 (너무 빠름 - 의심)")
                is_valid_hier = False
                answer_hier = "시간 초과"
            else:
                is_valid_hier, reason_hier = validate_answer(question, answer_hier)
                print(f"✓ Hierarchical 완료: {elapsed_hier:.2f}초 | 판정: {'맞음' if is_valid_hier else '틀림'}")

            results["hierarchical"].append({
                "question": question,
                "time": elapsed_hier,
                "answer": answer_hier[:50] + "..." if len(answer_hier) > 50 else answer_hier,
                "correct": is_valid_hier,
            })
        except Exception as e:
            print(f"✗ Hierarchical 오류: {str(e)[:50]}")
            results["hierarchical"].append({
                "question": question,
                "time": 0,
                "answer": "시간 초과",
                "correct": False,
            })

    return results


# ============================================================================
# [5-4] 결과 표시
# ============================================================================

def display_results(results: Dict):
    """
    테스트 결과를 표 형식으로 표시합니다.

    Args:
        results (Dict): 테스트 결과
    """
    print("\n\n" + "=" * 100)
    print("📊 비교 결과 테이블")
    print("=" * 100)
    print()

    # 테이블 헤더
    print(f"{'질문':<30} | {'방식':<12} | {'시간(초)':<8} | {'결과':<6} | {'비고':<20}")
    print("-" * 100)

    for idx in range(len(TEST_QUESTIONS)):
        question = TEST_QUESTIONS[idx][:27]

        # Sequential 행
        seq_result = results["sequential"][idx]
        seq_time = seq_result["time"]
        seq_correct = "✓ 맞음" if seq_result["correct"] else "✗ 틀림"
        seq_note = seq_result["answer"][:18]
        print(f"{question:<30} | {'Sequential':<12} | {seq_time:>7.2f}s | {seq_correct:<6} | {seq_note:<20}")

        # Hierarchical 행
        hier_result = results["hierarchical"][idx]
        hier_time = hier_result["time"]
        hier_correct = "✓ 맞음" if hier_result["correct"] else "✗ 틀림"
        hier_note = hier_result["answer"][:18]
        print(f"{'':<30} | {'Hierarchical':<12} | {hier_time:>7.2f}s | {hier_correct:<6} | {hier_note:<20}")
        print("-" * 100)

    # 통계
    seq_times = [r["time"] for r in results["sequential"]]
    hier_times = [r["time"] for r in results["hierarchical"]]
    seq_correct_count = sum(1 for r in results["sequential"] if r["correct"])
    hier_correct_count = sum(1 for r in results["hierarchical"] if r["correct"])

    print(f"\n📈 통계:")
    print(f"  Sequential: 평균 {sum(seq_times)/len(seq_times):.2f}초 | 정답률 {seq_correct_count}/{len(TEST_QUESTIONS)}")
    print(f"  Hierarchical: 평균 {sum(hier_times)/len(hier_times):.2f}초 | 정답률 {hier_correct_count}/{len(TEST_QUESTIONS)}")
    print(f"  시간 차이: Hierarchical이 {sum(hier_times) - sum(seq_times):.2f}초 {'느림' if sum(hier_times) > sum(seq_times) else '빠름'}")


if __name__ == "__main__":
    try:
        results = run_test()
        display_results(results)
    except KeyboardInterrupt:
        print("\n\n중단됨 (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
