# [1-2] RAG 없이 llama3.1 답변 테스트
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from hanabot.config import CHAT_MODEL, OLLAMA_BASE_URL
from langchain_ollama import OllamaLLM

# 모델 초기화
llm = OllamaLLM(model=CHAT_MODEL, base_url=OLLAMA_BASE_URL)

# 질문과 정답
questions = [
    ("지각 몇 번이면 결석이야?", "3회"),
    ("수료하려면 출석률이 얼마나 돼야 해?", "80% 이상"),
    ("실무반 수강료는 얼마야?", "월 50만 원"),
    ("화요일 오후에는 뭘 배워?", "RAG"),
    ("GPU PC는 하루에 몇 시간 쓸 수 있어?", "최대 4시간"),
    ("몇 시까지 있어도 돼?", "실습실 21:00"),
    ("결석은 언제까지 알려야 해?", "전날 18시"),
    ("몇 번 빠지면 결석이야?", "지각 3회 · 조퇴 2회"),
    ("할인 같이 받을 수 있어?", "중복 안 됨"),
]

print("=" * 80)
print("하나 AI 학원 규정 - RAG 없이 테스트")
print("=" * 80)
print()

# 각 질문에 대해 모델 답 얻기
for i, (question, answer) in enumerate(questions, 1):
    print(f"[{i}] 질문: {question}")
    response = llm.invoke(question)
    print(f"    모델: {response.strip()}")
    print(f"    정답: {answer}")
    print()

print("=" * 80)
print("모델은 하나 AI 학원 규정을 모릅니다")
print("=" * 80)
