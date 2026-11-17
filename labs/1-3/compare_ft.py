# [1-3] 파인튜닝 모델 비교 (4가지 조합)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from hanabot.rag import answer_question, answer_question_no_rag

# 질문 9개 & 정답
questions = [
    # 사실: RAG_PLAN.md CHECK 표
    ("지각 몇 번이면 결석이야?", "3회", "fact"),
    ("수료하려면 출석률이 얼마나 돼야 해?", "80%", "fact"),
    ("화요일 오후에는 뭘 배워?", "RAG", "fact"),

    # 형식: 아무 규정 질문 (형식만 테스트)
    ("환불 기준에 대해 알려줄래?", "", "format"),
    ("준비물은 뭐야?", "", "format"),
    ("수업 시간이 몇 시부터예요?", "", "format"),

    # 거절: 규정에 없는 새 질문
    ("강사 연락처 알려줄래?", "없음", "reject"),
    ("와이파이 비밀번호 뭐야?", "없음", "reject"),
    ("내일 날씨 어때?", "없음", "reject"),
]

# 모델 선택
MODEL_BASE = "llama3.1"
MODEL_FT = "hanabot-ft"

print("=" * 120)
print("파인튜닝 모델 비교 (4가지 조합)")
print("=" * 120)
print()

# 채점 함수
def check_fact(answer, keyword):
    """사실: 정답 키워드 포함"""
    return keyword.lower() in answer.lower()

def check_format(answer):
    """형식: 3가지 규칙"""
    rules = {
        "시작": answer.startswith("[하나봇]"),
        "항목": "- " in answer,
        "끝": "문의해 주세요." in answer
    }
    return all(rules.values())

def check_reject(answer):
    """거절: 없음 표현 포함"""
    reject_keywords = ["찾을 수 없습니다", "규정에 없는", "없습니다"]
    return any(kw in answer for kw in reject_keywords)

# 결과 저장
results = []

# 각 질문에 대해 4가지 모델로 답변
for i, (question, keyword, q_type) in enumerate(questions, 1):
    print(f"[{i}/9] {question}")

    # ① 기본 llama3.1 (RAG 없음)
    ans1 = answer_question_no_rag(question, model=MODEL_BASE)

    # ② hanabot-ft (RAG 없음)
    try:
        ans2 = answer_question_no_rag(question, model=MODEL_FT)
    except:
        ans2 = "⚠️ 모델 로드 실패 (models/hanabot-ft에 파일 필요)"

    # ③ RAG + llama3.1
    ans3, _ = answer_question(question, model=MODEL_BASE)

    # ④ RAG + hanabot-ft
    try:
        ans4, _ = answer_question(question, model=MODEL_FT)
    except:
        ans4 = "⚠️ 모델 로드 실패"

    # 채점
    if q_type == "fact":
        score1 = "O" if check_fact(ans1, keyword) else "X"
        score2 = "O" if check_fact(ans2, keyword) else "X"
        score3 = "O" if check_fact(ans3, keyword) else "X"
        score4 = "O" if check_fact(ans4, keyword) else "X"
    elif q_type == "format":
        score1 = "O" if check_format(ans1) else "X"
        score2 = "O" if check_format(ans2) else "X"
        score3 = "O" if check_format(ans3) else "X"
        score4 = "O" if check_format(ans4) else "X"
    else:  # reject
        score1 = "O" if check_reject(ans1) else "X"
        score2 = "O" if check_reject(ans2) else "X"
        score3 = "O" if check_reject(ans3) else "X"
        score4 = "O" if check_reject(ans4) else "X"

    results.append({
        "question": question,
        "type": q_type,
        "ans1": score1,
        "ans2": score2,
        "ans3": score3,
        "ans4": score4,
    })

    print(f"  ① {score1}  ② {score2}  ③ {score3}  ④ {score4}")
    print()

# 결과 표
print("=" * 120)
print("결과 비교표")
print("=" * 120)
print()

print(f"{'질문':<30} {'타입':<8} {'① 기본':<10} {'② FT':<10} {'③ RAG':<10} {'④ RAG+FT':<10}")
print("-" * 120)

for r in results:
    print(f"{r['question']:<30} {r['type']:<8} {r['ans1']:<10} {r['ans2']:<10} {r['ans3']:<10} {r['ans4']:<10}")

print()

# 점수 계산
score1 = sum(1 for r in results if r["ans1"] == "O")
score2 = sum(1 for r in results if r["ans2"] == "O")
score3 = sum(1 for r in results if r["ans3"] == "O")
score4 = sum(1 for r in results if r["ans4"] == "O")

print("=" * 120)
print(f"최종 점수 (9개 중)")
print("=" * 120)
print(f"① 기본 llama3.1:        {score1}/9 ({100*score1//9}%)")
print(f"② hanabot-ft:           {score2}/9 ({100*score2//9}%)")
print(f"③ RAG + llama3.1:       {score3}/9 ({100*score3//9}%)")
print(f"④ RAG + hanabot-ft:     {score4}/9 ({100*score4//9}%)")
print()

# 개선도
if score2 > score1:
    print(f"✓ 파인튜닝 효과: +{score2-score1}점 (말투 개선)")
else:
    print(f"⚠️  파인튜닝: {score2-score1:+d}점 (hanabot-ft가 아직 없거나 학습 중)")

if score4 > score3:
    print(f"✓ RAG+FT 시너지: +{score4-score3}점 (형식 + 지식)")
else:
    print(f"ℹ️  RAG+FT 균형: {score4-score3:+d}점")
