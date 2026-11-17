# [1-4] Langfuse 추적 테스트
import sys
sys.path.insert(0, '.')

from hanabot.rag import answer_question

questions = [
    '지각 몇 번이면 결석이야?',
    '몇 번 빠지면 결석이야?',
    '점심 메뉴 뭐야?'
]

print('=' * 60)
print('Langfuse 추적 테스트 (3개 질문)')
print('=' * 60)
print()

for i, q in enumerate(questions, 1):
    print(f'[{i}] 질문: {q}')
    try:
        ans, src = answer_question(q)
        print(f'    답변: {ans[:60]}...' if len(ans) > 60 else f'    답변: {ans}')
        print(f'    근거: {src[0]}')
        print()
    except Exception as e:
        print(f'    오류: {e}')
        print()

print('=' * 60)
print('✓ 테스트 완료')
print('=' * 60)
print()
print('📌 Langfuse 웹에서 보는 방법:')
print('1. https://cloud.langfuse.com 에 가입')
print('2. .env에 LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY 추가')
print('3. 프로젝트 생성 후 본 스크립트 다시 실행')
print('4. Langfuse 대시보드에서 "hanabot-rag" trace 확인')
print('   - retrieve 단계: 검색한 조각 3개와 점수')
print('   - generate 단계: 모델, 답변, 소요 시간')
