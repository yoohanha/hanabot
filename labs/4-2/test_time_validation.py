#!/usr/bin/env python3
# [4-2] 시간 값 검사 · 저장 확인 테스트

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


def validate_time_value(key: str, value: str) -> tuple:
    """시간 관련 값이 올바른 형식인지 검사"""
    if '시간' not in key.lower() and '시' not in key.lower():
        return True, value

    # 허용되는 시간 형식:
    # 1. "오전/오후 + 숫자 + 시" (예: 오후 2시, 오전 10시)
    # 2. "HH:MM" (예: 14:00)

    # 형식 1: 오전/오후 + 숫자 + 시
    if re.match(r'^(오전|오후)\s*\d{1,2}시$', value):
        return True, value

    # 형식 2: HH:MM
    if re.match(r'^\d{1,2}:\d{2}$', value):
        return True, value

    return False, "시간을 다시 알려주세요 (예: 오후 2시, 14:00)"


def save_memory_test(student_id: str, key: str, value: str) -> str:
    """메모리 저장 및 확인 테스트"""
    # 시간 값 검증
    is_valid_time, time_msg = validate_time_value(key, value)
    if not is_valid_time:
        return f"❌ {time_msg}"

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

        # 저장 확인: 파일에서 다시 읽어서 실제 저장된 값 반환
        with open(memory_file, 'r', encoding='utf-8') as f:
            saved_memory = json.load(f)
        saved_value = saved_memory.get(key, value)

        return f"✅ {key} = {saved_value} 로 저장했어요"

    except Exception as e:
        return f"❌ 저장 오류: {str(e)}"


# ============================================================================
# 테스트 실행
# ============================================================================

def main():
    print(f"\n🕐 시간 값 검사 · 저장 확인 테스트\n")

    student_id = "HANA-007"
    memory_file = MEMORY_DIR / f"{student_id}.json"

    # 기존 파일 삭제
    if memory_file.exists():
        memory_file.unlink()
        print(f"✅ 기존 메모리 파일 삭제됨\n")

    # "선호 시간은 오후 2시야" 3번 반복
    print("=" * 100)
    print("[테스트] '선호 시간은 오후 2시야' 를 3번 반복 테스트")
    print("=" * 100)

    for round_num in range(1, 4):
        print(f"\n[라운드 {round_num}]")
        question = "선호 시간은 오후 2시야"
        print(f"질문: {question}")

        # 모델이 도구 인자를 올바르게 만든다고 가정하면
        # key="선호_시간", value="오후 2시"
        result = save_memory_test(student_id, "선호_시간", "오후 2시")
        print(f"결과: {result}")

    # 최종 파일 확인
    print(f"\n{'='*100}")
    print("📁 최종 메모리 파일 (HANA-007.json)")
    print('='*100)

    if memory_file.exists():
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)

        print(f"\n✅ 파일 내용:")
        print(json.dumps(memory, ensure_ascii=False, indent=2))

        # 검증
        print(f"\n🔐 검증:")
        saved_time = memory.get("선호_시간", "")
        if saved_time == "오후 2시":
            print(f"   ✅ '오후 2시'가 올바르게 저장됨!")
        else:
            print(f"   ❌ 잘못된 값: {saved_time}")
    else:
        print(f"\n❌ 파일이 없습니다")


if __name__ == "__main__":
    main()
