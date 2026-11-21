#!/usr/bin/env python3
# [4-2] 개인정보 거부 테스트

import sys
import json
import re
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

MEMORY_DIR = PROJECT_ROOT / "labs" / "4-2" / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# 금지 필드 및 패턴
FORBIDDEN_FIELD_KEYWORDS = {'이름', '전화', '전화번호', '연락처', '휴대폰', '주민', '주민번호', 'name', 'phone', 'ssn'}

FORBIDDEN_PATTERNS = [
    r'\d{3}-\d{3,4}-\d{4}',  # 휴대폰: 010-1234-5678
    r'\d{3}\d{4}\d{4}',      # 휴대폰: 01012345678
    r'\d{6}-\d{7}',           # 주민번호: 900101-1234567
]


def is_forbidden_field(key: str) -> bool:
    """항목 이름이 금지된 개인정보인지 검사"""
    key_lower = key.lower()
    for forbidden in FORBIDDEN_FIELD_KEYWORDS:
        if forbidden.lower() in key_lower:
            return True
    return False


def is_forbidden_value(value: str) -> bool:
    """값이 금지된 개인정보 패턴인지 검사"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, str(value)):
            return True
    return False


def save_memory_test(student_id: str, key: str, value: str) -> str:
    """메모리 저장 테스트"""
    # 1. 저장 금지 필드명 검증
    if is_forbidden_field(key):
        return f"❌ 저장할 수 없는 정보입니다: {key} (보안/프라이버시)"

    # 2. 저장 금지 패턴 검증
    if is_forbidden_value(value):
        return f"❌ 저장할 수 없는 정보입니다: {value} (개인정보 패턴 감지)"

    try:
        memory_file = MEMORY_DIR / f"{student_id}.json"

        # 기존 기억 로드
        memory = {}
        if memory_file.exists():
            with open(memory_file, 'r', encoding='utf-8') as f:
                memory = json.load(f)

        # 새 항목 추가
        memory[key] = value
        memory['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 파일 저장
        with open(memory_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)

        return f"✅ 저장했습니다: {key} = {value}"

    except Exception as e:
        return f"❌ 저장 오류: {str(e)}"


def show_memory_file(student_id):
    """메모리 파일 내용 표시"""
    memory_file = MEMORY_DIR / f"{student_id}.json"

    if not memory_file.exists():
        print(f"  📁 메모리 파일 없음")
        return

    with open(memory_file, 'r', encoding='utf-8') as f:
        memory = json.load(f)

    print(f"  📁 메모리 파일 내용 ({student_id}.json):")
    for key, value in memory.items():
        if key != 'updated_at':
            print(f"      • {key}: {value}")
    if 'updated_at' in memory:
        print(f"      • 업데이트: {memory['updated_at']}")

    # 전화번호 확인
    if any('전' in key.lower() or '휴' in key.lower() for key in memory.keys()):
        print(f"  ⚠️  경고: 전화번호 관련 필드 발견!")
    else:
        print(f"  ✅ 전화번호 없음 (안전)")


# ============================================================================
# 테스트 실행
# ============================================================================

def main():
    print(f"\n🔒 개인정보 거부 강화 테스트\n")

    student_id = "HANA-007"
    memory_file = MEMORY_DIR / f"{student_id}.json"

    # 기존 파일 삭제
    if memory_file.exists():
        memory_file.unlink()
        print(f"✅ 기존 메모리 파일 삭제됨\n")

    # 테스트 1: 항목 이름으로 거부 (전화번호)
    print("=" * 100)
    print("[테스트 1] 항목 이름으로 거부: '연락처'는 '전화' 포함 → 거부")
    print("=" * 100)
    question1 = "내 연락처는 010-1234-5678이야 기억해줘"
    print(f"\n질문: {question1}\n")

    result1 = save_memory_test(student_id, "연락처", "010-1234-5678")
    print(f"결과: {result1}\n")

    show_memory_file(student_id)

    # 테스트 2: 값으로 거부 (휴대폰 번호 패턴)
    print(f"\n{'='*100}")
    print("[테스트 2] 값으로 거부: '01012345678' 패턴 감지 → 거부")
    print('='*100)
    question2 = "내 휴대폰 01012345678 저장해줘"
    print(f"\n질문: {question2}\n")

    result2 = save_memory_test(student_id, "연락처_번호", "01012345678")
    print(f"결과: {result2}\n")

    show_memory_file(student_id)

    # 테스트 3: 허용된 정보 저장
    print(f"\n{'='*100}")
    print("[테스트 3] 허용된 정보 저장: 관심_과정 = 실무반 → 성공")
    print('='*100)
    question3 = "나는 실무반에 관심 있어 기억해줘"
    print(f"\n질문: {question3}\n")

    result3 = save_memory_test(student_id, "관심_과정", "실무반")
    print(f"결과: {result3}\n")

    show_memory_file(student_id)

    # 최종 확인
    print(f"\n{'='*100}")
    print("📋 최종 검증")
    print('='*100)

    with open(memory_file, 'r', encoding='utf-8') as f:
        memory = json.load(f)

    print(f"\n✅ 최종 메모리 파일 ({student_id}.json):")
    print(json.dumps(memory, ensure_ascii=False, indent=2))

    # 보안 체크
    print(f"\n🔐 보안 체크:")
    if any(re.search(r'\d{3}-?\d{3,4}-?\d{4}', str(v)) or re.search(r'\d{6}-\d{7}', str(v)) for v in memory.values()):
        print("   ❌ 개인정보 감지! 보안 위반!")
    else:
        print("   ✅ 개인정보 없음 - 안전!")


if __name__ == "__main__":
    main()
