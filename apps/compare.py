# [1-2] RAG 있음/없음 비교
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hanabot.rag import answer_question, answer_question_no_rag

test_cases = [
    ("지각 몇 번이면 결석이야?", ["3회", "3번"]),
    ("수료하려면 출석률이 얼마나 돼야 해?", ["80%", "80"]),
    ("실무반 수강료는 얼마야?", ["50만", "50만 원"]),
    ("화요일 오후에는 뭘 배워?", ["RAG"]),
    ("GPU PC는 하루에 몇 시간 쓸 수 있어?", ["4시간", "4시간"]),
    ("몇 시까지 있어도 돼?", ["21:00", "21시"]),
    ("결석은 언제까지 알려야 해?", ["전날 18시", "18시"]),
    ("몇 번 빠지면 결석이야?", ["지각 3회", "조퇴 2회"]),
    ("할인 같이 받을 수 있어?", ["중복 안 됨", "중복"]),
]


def check_answer(answer, keywords):
    """답변에 정답 키워드가 있는지 확인"""
    answer_lower = answer.lower()
    for keyword in keywords:
        if keyword.lower() in answer_lower:
            return "O"
    return "X"


print()
print("=" * 80)
print("하나 AI 학원 규정 - RAG 있음/없음 비교 (질문 9개)")
print("=" * 80)
print()

results = []
no_rag_score = 0
rag_score = 0

for i, (question, keywords) in enumerate(test_cases, 1):
    print(f"[{i}] {question}")

    # RAG 없이
    answer_no_rag = answer_question_no_rag(question)
    score_no_rag = check_answer(answer_no_rag, keywords)
    if score_no_rag == "O":
        no_rag_score += 1

    # RAG로
    answer_rag, sources = answer_question(question)
    score_rag = check_answer(answer_rag, keywords)
    if score_rag == "O":
        rag_score += 1

    results.append((question, score_no_rag, score_rag))
    print(f"  RAG 없이: {score_no_rag}")
    print(f"  RAG:     {score_rag}")
    print()

# 결과 표
print("=" * 80)
print("채점 결과")
print("=" * 80)
print()

print(f"{'질문':<35} {'RAG 없이':<10} {'RAG':<10}")
print("-" * 55)

for question, score_no_rag, score_rag in results:
    print(f"{question:<35} {score_no_rag:<10} {score_rag:<10}")

print("-" * 55)
print(f"{'합계':<35} {no_rag_score}/9{'':<5} {rag_score}/9")
print()

improvement = rag_score - no_rag_score
print(f"✓ 성능 개선: RAG 없이 {no_rag_score}/9 · RAG로 {rag_score}/9 (+{improvement}점)")
print()

input("계속하려면 Enter를 누르세요...")
