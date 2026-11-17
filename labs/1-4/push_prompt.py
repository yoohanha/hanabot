# [1-4] Langfuse에 RAG 프롬프트 등록
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hanabot.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_ENABLED

# v1: 기본 프롬프트 (production)
RAG_PROMPT_V1 = """다음 규정 문서를 읽고 질문에 답해주세요.

규정:
{{documents}}

질문: {{question}}

규칙:
- 문서에 있는 내용으로만 답하세요
- 문서에 없는 내용이면 "규정에 없는 내용입니다"라고만 답하세요
- 간결하게 답하세요
"""

# v2: 근거 추가 프롬프트 (staging)
RAG_PROMPT_V2 = """다음 규정 문서를 읽고 질문에 답해주세요.

규정:
{{documents}}

질문: {{question}}

규칙:
- 문서에 있는 내용으로만 답하세요
- 문서에 없는 내용이면 "규정에 없는 내용입니다"라고만 답하세요
- 답 끝에 근거를 "(근거: 섹션 > 소제목)" 형식으로 붙이세요
- 모두 한국어로 답하고, 숫자는 원문 그대로 쓰세요
- 간결하게 답하세요
"""


def push_prompts():
    """v1과 v2 프롬프트를 Langfuse에 등록"""

    if not LANGFUSE_ENABLED:
        print("⚠️  Langfuse가 비활성화되어 있습니다.")
        print("   .env에 LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY를 설정하세요.")
        return False

    try:
        from langfuse import Langfuse

        langfuse = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY
        )

        print("=" * 70)
        print("📤 Langfuse에 프롬프트 업로드 중...")
        print("=" * 70)
        print()

        # v1 등록 (production)
        prompt_v1 = langfuse.create_prompt(
            name="hanabot-rag",
            prompt=RAG_PROMPT_V1,
            labels=["production"],
            tags=["rag", "baseline"],
            version=1
        )

        print(f"✓ v1 등록 완료 (production)")
        print(f"  버전: v{prompt_v1.version}")
        print(f"  라벨: {', '.join(prompt_v1.labels)}")
        print()

        # v2 등록 (staging)
        prompt_v2 = langfuse.create_prompt(
            name="hanabot-rag",
            prompt=RAG_PROMPT_V2,
            labels=["staging"],
            tags=["rag", "with-citations"],
            version=2
        )

        print(f"✓ v2 등록 완료 (staging)")
        print(f"  버전: v{prompt_v2.version}")
        print(f"  라벨: {', '.join(prompt_v2.labels)}")
        print(f"  변경: 답 끝에 근거 붙이기")
        print()
        print("=" * 70)
        print("✅ Langfuse 대시보드에서 확인하세요:")
        print("   https://cloud.langfuse.com → Prompts → hanabot-rag")
        print("=" * 70)
        print()

        return True

    except Exception as e:
        print(f"❌ 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = push_prompts()
    sys.exit(0 if success else 1)
