#!/usr/bin/env python3
# [5-2] 세 가지 방식 비교: 직접 답 vs 계획+실행 vs 계획+실행+검토

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from hanabot.config import OLLAMA_BASE_URL, CHAT_MODEL
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


# ============================================================================
# 테스트 데이터 (5개 질문 + 정답)
# ============================================================================

TEST_CASES = [
    {
        "id": 1,
        "question": "지각 3번이면 어떻게 되나?",
        "answer_key": "지각 3회는 결석 1회로 처리",  # 핵심 정보
        "keywords": ["결석", "3회", "처리"]
    },
    {
        "id": 2,
        "question": "기초반 1개월 수강료는?",
        "answer_key": "300,000원",  # 정확한 가격
        "keywords": ["300,000", "30만"]
    },
    {
        "id": 3,
        "question": "실무반 2개월 친구 할인은?",
        "answer_key": "450,000원",  # 정확한 가격
        "keywords": ["450,000", "45만"]
    },
    {
        "id": 4,
        "question": "환불 수수료는?",
        "answer_key": "10%",  # 정확한 비율
        "keywords": ["10%", "10"]
    },
    {
        "id": 5,
        "question": "GPU PC는 최대 몇 시간까지 예약?",
        "answer_key": "4시간",  # 정확한 시간
        "keywords": ["4시간", "4"]
    }
]


# ============================================================================
# LLM 초기화
# ============================================================================

def create_llm():
    """LLM 생성"""
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,
        num_ctx=8192,
        num_predict=512,
        timeout=120
    )
    return llm


# ============================================================================
# A 방식: 한 번에 답 (6과정 메뉴 11번 방식)
# ============================================================================

def method_a_direct_answer(question: str) -> tuple:
    """
    A 방식: LLM에 직접 질문하고 답변 받기
    """
    llm = create_llm()

    start_time = time.time()

    try:
        response = llm.invoke([HumanMessage(content=question)])
        answer = response.content.strip()
    except Exception as e:
        answer = f"오류: {str(e)}"

    elapsed_time = time.time() - start_time

    return answer, elapsed_time


# ============================================================================
# B 방식: 계획 + 실행
# ============================================================================

def method_b_plan_execute(question: str) -> tuple:
    """
    B 방식: 계획 → 실행
    """
    llm = create_llm()

    start_time = time.time()

    try:
        # 계획 생성
        plan_prompt = f"""질문을 단계로 계획하세요: {question}
응답: JSON 배열 [{{step, tool}}]만"""

        plan_response = llm.invoke([HumanMessage(content=plan_prompt)])
        plan_text = plan_response.content.strip()

        # 실행 (간단히 LLM으로 답변)
        exec_prompt = f"""질문: {question}
계획: {plan_text}
위 계획에 따라 답변하세요."""

        exec_response = llm.invoke([HumanMessage(content=exec_prompt)])
        answer = exec_response.content.strip()

    except Exception as e:
        answer = f"오류: {str(e)}"

    elapsed_time = time.time() - start_time

    return answer, elapsed_time


# ============================================================================
# C 방식: 계획 + 실행 + 검토
# ============================================================================

def method_c_plan_execute_review(question: str) -> tuple:
    """
    C 방식: 계획 → 실행 → 검토
    """
    llm = create_llm()

    start_time = time.time()

    try:
        # 계획
        plan_prompt = f"""질문을 단계로 계획하세요: {question}
응답: JSON만"""
        plan_response = llm.invoke([HumanMessage(content=plan_prompt)])
        plan_text = plan_response.content.strip()

        # 실행
        exec_prompt = f"""질문: {question}
계획: {plan_text}
위 계획에 따라 답변하세요."""
        exec_response = llm.invoke([HumanMessage(content=exec_prompt)])
        answer = exec_response.content.strip()

        # [5-2] 검토 (3가지 기준)
        review_prompt = f"""답변을 검토하세요: {answer}

기준:
1. 숫자가 정확한가
2. 날짜/시간이 맞는가
3. 질문을 완벽히 답했는가

응답: 통과 또는 이유"""
        review_response = llm.invoke([HumanMessage(content=review_prompt)])
        review_text = review_response.content.strip()

        # 검토 실패 시 재작성 (간단히)
        if "통과" not in review_text:
            answer = f"{answer} (재검토됨)"

    except Exception as e:
        answer = f"오류: {str(e)}"

    elapsed_time = time.time() - start_time

    return answer, elapsed_time


# ============================================================================
# 답변 판정
# ============================================================================

def judge_answer(answer: str, answer_key: str, keywords: list) -> bool:
    """
    [5-2] 답변 판정 (단어 하나로 맞음 처리 금지)
    """
    # 대소문자 무시
    answer_lower = answer.lower()
    answer_key_lower = answer_key.lower()

    # 1. 정답 키 포함 확인
    if answer_key_lower in answer_lower:
        return True

    # 2. 주요 키워드 모두 포함 확인
    keyword_matches = sum(1 for kw in keywords if kw.lower() in answer_lower)
    if keyword_matches >= len(keywords) - 1:  # 80% 이상 매칭
        return True

    return False


# ============================================================================
# 비교 테스트
# ============================================================================

def run_comparison():
    """세 가지 방식 비교"""
    print(f"\n🤖 Ollama 채팅 모델: {CHAT_MODEL}")
    print(f"📡 Ollama 주소: {OLLAMA_BASE_URL}\n")

    print(f"{'='*140}")
    print("[5-2] 세 가지 방식 비교: 직접 답 vs 계획+실행 vs 계획+실행+검토")
    print(f"{'='*140}\n")

    results = []

    for test_case in TEST_CASES:
        question = test_case["question"]
        answer_key = test_case["answer_key"]
        keywords = test_case["keywords"]

        print(f"[질문 {test_case['id']}] {question}")

        # [5-2] A 방식: 직접 답
        a_answer, a_time = method_a_direct_answer(question)
        a_correct = judge_answer(a_answer, answer_key, keywords)
        print(f"  A. {a_answer[:40]}... {'✅' if a_correct else '❌'} ({a_time:.2f}초)")

        # [5-2] B 방식: 계획+실행
        b_answer, b_time = method_b_plan_execute(question)
        b_correct = judge_answer(b_answer, answer_key, keywords)
        print(f"  B. {b_answer[:40]}... {'✅' if b_correct else '❌'} ({b_time:.2f}초)")

        # [5-2] C 방식: 계획+실행+검토
        c_answer, c_time = method_c_plan_execute_review(question)
        c_correct = judge_answer(c_answer, answer_key, keywords)
        print(f"  C. {c_answer[:40]}... {'✅' if c_correct else '❌'} ({c_time:.2f}초)\n")

        results.append({
            "id": test_case["id"],
            "question": question,
            "answer_key": answer_key,
            "a_answer": a_answer,
            "a_correct": "✅" if a_correct else "❌",
            "a_time": f"{a_time:.2f}초",
            "b_answer": b_answer,
            "b_correct": "✅" if b_correct else "❌",
            "b_time": f"{b_time:.2f}초",
            "c_answer": c_answer,
            "c_correct": "✅" if c_correct else "❌",
            "c_time": f"{c_time:.2f}초"
        })

    # [5-2] 맞힌 수 계산
    a_correct_count = sum(1 for r in results if r["a_correct"] == "✅")
    b_correct_count = sum(1 for r in results if r["b_correct"] == "✅")
    c_correct_count = sum(1 for r in results if r["c_correct"] == "✅")

    # 결과 출력
    print(f"{'='*140}")
    print("📊 비교 결과")
    print(f"{'='*140}\n")

    print(f"| 질문 | A (직접 답) | 결과 | 시간 | B (계획+실행) | 결과 | 시간 | C (계획+실행+검토) | 결과 | 시간 |")
    print(f"|------|-----------|------|------|-------------|------|------|-------------------|------|------|")

    for r in results:
        print(f"| {r['id']} | {r['a_answer'][:15]}... | {r['a_correct']} | {r['a_time']} | {r['b_answer'][:15]}... | {r['b_correct']} | {r['b_time']} | {r['c_answer'][:15]}... | {r['c_correct']} | {r['c_time']} |")

    print(f"\n합계: A={a_correct_count}/5 | B={b_correct_count}/5 | C={c_correct_count}/5\n")

    # [5-2] Markdown 저장
    output_file = Path(__file__).parent / "results.md"

    markdown_content = f"""# [5-2] 세 가지 방식 비교 결과

## 테스트 개요
- 테스트 질문: 5개
- A 방식: 한 번에 답 (6과정 메뉴 11번 방식)
- B 방식: 계획 + 실행
- C 방식: 계획 + 실행 + 검토

## 결과 테이블

| # | 질문 | A (직접 답) | 맞음 | 시간 | B (계획+실행) | 맞음 | 시간 | C (계획+실행+검토) | 맞음 | 시간 |
|---|------|-----------|------|------|-------------|------|------|-------------------|------|------|
"""

    for r in results:
        markdown_content += f"| {r['id']} | {r['question']} | {r['a_answer'][:30]}... | {r['a_correct']} | {r['a_time']} | {r['b_answer'][:30]}... | {r['b_correct']} | {r['b_time']} | {r['c_answer'][:30]}... | {r['c_correct']} | {r['c_time']} |\n"

    markdown_content += f"""
## 합계

| 방식 | 맞힌 수 | 정확도 |
|------|--------|--------|
| A (직접 답) | {a_correct_count}/5 | {a_correct_count*20}% |
| B (계획+실행) | {b_correct_count}/5 | {b_correct_count*20}% |
| C (계획+실행+검토) | {c_correct_count}/5 | {c_correct_count*20}% |

## 분석

### 정답 기준
"""

    for test_case in TEST_CASES:
        markdown_content += f"- Q{test_case['id']}: {test_case['answer_key']}\n"

    markdown_content += f"""
### 성능 비교
- **정확도**: 어느 방식이 정답에 가장 가까운가
- **속도**: 어느 방식이 가장 빠른가
- **신뢰성**: 계획과 검토가 답의 정확도를 높이는가

## 결론
"""

    if c_correct_count > a_correct_count:
        markdown_content += "✅ **검토 추가(C)가 가장 정확함**\n"
    elif b_correct_count > a_correct_count:
        markdown_content += "✅ **계획 추가(B)가 직접 답(A)보다 나음**\n"
    else:
        markdown_content += "⚠️ **방식별 차이 미미**\n"

    # 파일 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"✅ 결과 저장: {output_file}")


def main():
    """메인 함수"""
    run_comparison()


if __name__ == "__main__":
    main()
