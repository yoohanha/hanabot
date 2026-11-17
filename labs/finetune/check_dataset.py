# [1-3] STYLE.md 형식 검증
import json
from pathlib import Path

def check_style_format(answer):
    """STYLE.md 형식 검증"""
    rules = {
        "rule1_start": answer.startswith("[하나봇]\n") or answer.startswith("[하나봇]"),
        "rule2_items": "- " in answer,
        "rule3_end": answer.endswith("자세한 내용은 학원 데스크로 문의해 주세요."),
    }
    return rules


def validate_dataset(jsonl_file):
    """JSONL 파일 검증"""
    total = 0
    passed = 0
    failed = 0
    failures = []

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            try:
                item = json.loads(line.strip())
                conversations = item.get('conversations', [])

                for conv in conversations:
                    if conv['role'] == 'assistant':
                        answer = conv['content']
                        total += 1

                        rules = check_style_format(answer)
                        all_pass = all(rules.values())

                        if all_pass:
                            passed += 1
                        else:
                            failed += 1
                            failures.append({
                                'line': line_no,
                                'answer': answer[:50] + '...' if len(answer) > 50 else answer,
                                'rules': rules
                            })
            except Exception as e:
                print(f"⚠️  파일 오류 (줄 {line_no}): {e}")
                failed += 1

    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'failures': failures,
        'pass_rate': (passed / total * 100) if total > 0 else 0
    }


if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent.parent / "data" / "finetune"

    print()
    print("=" * 70)
    print("✅ STYLE.md 형식 검증\n")

    # 훈련 데이터 검증
    train_file = base_dir / "hanabot_train.jsonl"
    if train_file.exists():
        result = validate_dataset(train_file)
        print(f"📊 훈련 데이터 (hanabot_train.jsonl)")
        print(f"   총 답변: {result['total']}개")
        print(f"   규칙 통과: {result['passed']}개 ✓")
        print(f"   규칙 위반: {result['failed']}개")
        print(f"   통과율: {result['pass_rate']:.1f}%")
        if result['pass_rate'] == 100:
            print(f"   ✅ 100% 통과!\n")
        else:
            print(f"   ⚠️  위반 사항:")
            for failure in result['failures'][:3]:
                print(f"      줄 {failure['line']}: {failure['answer']}")
            print()

    # 평가 데이터 검증
    eval_file = base_dir / "hanabot_eval.jsonl"
    if eval_file.exists():
        result = validate_dataset(eval_file)
        print(f"📊 평가 데이터 (hanabot_eval.jsonl)")
        print(f"   총 답변: {result['total']}개")
        print(f"   규칙 통과: {result['passed']}개 ✓")
        print(f"   규칙 위반: {result['failed']}개")
        print(f"   통과율: {result['pass_rate']:.1f}%")
        if result['pass_rate'] == 100:
            print(f"   ✅ 100% 통과!\n")
        else:
            print(f"   ⚠️  위반 사항:")
            for failure in result['failures'][:3]:
                print(f"      줄 {failure['line']}: {failure['answer']}")
            print()

    print("=" * 70)
    print("📋 세 가지 규칙:")
    print("   규칙 1: 첫 줄은 항상 '[하나봇]'으로 시작")
    print("   규칙 2: 내용에 '- '로 시작하는 항목 1~3개 포함")
    print("   규칙 3: 마지막 줄은 항상 '자세한 내용은 학원 데스크로 문의해 주세요.'")
    print("=" * 70)
    print()
