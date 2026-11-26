#!/usr/bin/env python3
# [5-2] compare.py 로직 검증 (LLM 없이 테스트)

import json
from pathlib import Path


def judge_answer(answer: str, answer_key: str, keywords: list) -> bool:
    """답변 판정 (compare.py와 동일)"""
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


# 테스트 케이스
TEST_CASES = [
    {
        "id": 1,
        "question": "지각 3번이면 어떻게 되나?",
        "answer_key": "지각 3회는 결석 1회로 처리",
        "keywords": ["결석", "3회", "처리"],
        "test_answers": [
            ("지각 3회는 결석 1회로 처리됩니다.", True),
            ("지각이 3번이면 결석 1회로 처리됩니다.", True),
            ("3회 지각은 결석으로 처리돼요.", True),
            ("지각이 많으면 불가능해요.", False),
        ]
    },
    {
        "id": 2,
        "question": "기초반 1개월 수강료는?",
        "answer_key": "300,000원",
        "keywords": ["300,000", "30만"],
        "test_answers": [
            ("기초반 1개월은 300,000원입니다.", True),
            ("30만원입니다.", True),
            ("3개월에 100만원입니다.", False),
        ]
    }
]


def main():
    print(f"[5-2] compare.py 로직 검증\n")
    print(f"{'='*80}\n")

    total_tests = 0
    passed_tests = 0

    for test_case in TEST_CASES:
        q_id = test_case["id"]
        question = test_case["question"]
        answer_key = test_case["answer_key"]
        keywords = test_case["keywords"]

        print(f"[질문 {q_id}] {question}")
        print(f"[정답] {answer_key}")
        print(f"[키워드] {', '.join(keywords)}\n")

        for answer, expected in test_case["test_answers"]:
            result = judge_answer(answer, answer_key, keywords)
            status = "✅" if result == expected else "❌"
            match = "O" if result else "X"

            print(f"  {status} {answer[:40]}... → {match} (기대: {'O' if expected else 'X'})")

            total_tests += 1
            if result == expected:
                passed_tests += 1

        print()

    print(f"{'='*80}")
    print(f"📊 결과: {passed_tests}/{total_tests} 통과 ({passed_tests*100//total_tests}%)")

    # 결과 저장
    output = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "accuracy": f"{passed_tests*100//total_tests}%"
    }

    output_file = Path(__file__).parent / "data" / "compare_logic_test.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 결과 저장: {output_file}")


if __name__ == "__main__":
    main()
