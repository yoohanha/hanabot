# [1-2] 하나봇과 대화 (RAG 사용)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from hanabot.rag import answer_question

print()
print("=" * 60)
print("하나 AI 학원 규정 - 하나봇 (RAG)")
print("=" * 60)
print("q를 입력하면 메뉴로 돌아갑니다")
print()

while True:
    question = input("질문: ").strip()

    if question.lower() == 'q':
        break

    if not question:
        continue

    print()
    answer, sources = answer_question(question)
    print(f"답변: {answer}")
    print(f"근거: {', '.join(sources)}")
    print()
