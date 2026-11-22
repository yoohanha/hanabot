#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-4] 최종 테스트: 출력 가드레일 적용 전/후 비교

import sys
import json
from pathlib import Path
from datetime import datetime

# Windows UTF-8 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# [4-4] guard_output import
from guard_output import OutputGuard, TEST_RESPONSES


# ============================================================================
# 설정
# ============================================================================

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_REPORT = DATA_DIR / "red_team_output_guard_report.json"


# ============================================================================
# 테스트 실행
# ============================================================================

def run_output_guard_test():
    """출력 가드레일 테스트 실행"""
    guard = OutputGuard(verbose=False)

    print(f"\n{'='*140}")
    print("[4-4] 출력 가드레일 테스트: 답변 보정 전/후")
    print(f"{'='*140}\n")

    print(f"🎯 테스트 대상: 7번(공격 환불 100%) + 정상 3개(지각 · 수강료 · 주차)\n")

    # 테스트 실행
    results = []
    for idx, test in enumerate(TEST_RESPONSES, 1):
        # 가드 적용 전
        before = test['response']

        # 가드 적용 후
        after, notes = guard.guard(
            test['response'],
            tool_used=test['tool_used'],
            tool_result=test['tool_result']
        )

        # 변경 여부
        changed = before != after

        result = {
            "index": idx,
            "type": test['type'],
            "name": test['name'],
            "before": before,
            "after": after,
            "changed": changed,
            "notes": notes,
            "tool_used": test['tool_used']
        }
        results.append(result)

    # ========================================================================
    # 결과 출력: 비교 테이블
    # ========================================================================

    print(f"{'='*140}")
    print("📊 비교 테이블: 가드 미적용 vs 가드 적용")
    print(f"{'='*140}\n")

    headers = ["#", "유형", "테스트명", "도구", "변경", "개선 사항"]
    col_widths = [2, 6, 25, 15, 6, 60]

    # 헤더
    header_line = " | ".join([
        headers[i].ljust(col_widths[i])
        for i in range(len(headers))
    ])
    print(header_line)
    print("-" * len(header_line))

    # 데이터 행
    for result in results:
        test_type = "공격" if result['type'] == "attack" else "정상"
        changed = "✅" if result['changed'] else "❌"
        notes_short = result['notes'][:57] if len(result['notes']) > 57 else result['notes']

        row = " | ".join([
            str(result['index']).ljust(col_widths[0]),
            test_type.ljust(col_widths[1]),
            result['name'][:24].ljust(col_widths[2]),
            result['tool_used'][:14].ljust(col_widths[3]),
            changed.ljust(col_widths[4]),
            notes_short.ljust(col_widths[5])
        ])
        print(row)

    print("-" * len(header_line))

    # ========================================================================
    # 상세 비교: 가드 미적용 vs 가드 적용
    # ========================================================================

    print(f"\n\n{'='*140}")
    print("📋 상세 비교: 답변 변경 내용")
    print(f"{'='*140}\n")

    for result in results:
        idx = result['index']
        name = result['name']
        changed = result['changed']

        print(f"[{idx}] {name}")
        print(f"    도구: {result['tool_used']}")
        print(f"    상태: {'✅ 변경됨' if changed else '❌ 변경 없음'}")

        if changed:
            print(f"\n    【가드 미적용】")
            for line in result['before'].split('\n'):
                print(f"    > {line}")

            print(f"\n    【가드 적용】")
            for line in result['after'].split('\n'):
                print(f"    > {line}")

            print(f"\n    개선: {result['notes']}")
        else:
            print(f"    내용: {result['before'][:70]}")

        print()

    # ========================================================================
    # 성능 요약
    # ========================================================================

    print(f"\n{'='*140}")
    print("📈 성능 요약")
    print(f"{'='*140}\n")

    total = len(results)
    changed_count = sum(1 for r in results if r['changed'])
    attack_improved = sum(1 for r in results if r['type'] == "attack" and r['changed'])
    normal_safe = sum(1 for r in results if r['type'] == "normal" and not r['changed'])

    print(f"총 테스트: {total}개")
    print(f"  • 공격 테스트: 1개")
    print(f"    - 개선됨: {attack_improved}/1 ({'✅' if attack_improved == 1 else '❌'})")
    print(f"  • 정상 테스트: 3개")
    print(f"    - 안전함: {normal_safe}/3 ({'✅' if normal_safe == 3 else '⚠️'})")
    print(f"    - 근거 추가: {sum(1 for r in results if r['type'] == 'normal' and r['changed'])}/3")

    print(f"\n개선 효과:")
    print(f"  • 미검증 정보 경고: {'✅' if attack_improved > 0 else '❌'}")
    print(f"  • 근거 추가: {'✅' if any('근거' in r['notes'] for r in results) else '❌'}")
    print(f"  • PII 마스킹: {'✅' if any('PII' in r['notes'] for r in results) else '❌'}")

    # ========================================================================
    # 보고서 저장
    # ========================================================================

    report = {
        "timestamp": datetime.now().isoformat(),
        "test_config": {
            "total_tests": len(TEST_RESPONSES),
            "attacks": 1,
            "normal": 3
        },
        "summary": {
            "total": total,
            "changed": changed_count,
            "attack_improved": attack_improved,
            "normal_safe": normal_safe,
            "metrics": {
                "unverified_number_warning": attack_improved > 0,
                "source_citation": any('근거' in r['notes'] for r in results),
                "pii_masking": any('PII' in r['notes'] for r in results)
            }
        },
        "detailed_results": results
    }

    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*140}")
    print(f"✅ 보고서 저장: {OUTPUT_REPORT}\n")

    return results


if __name__ == "__main__":
    # 규칙 출력
    guard = OutputGuard(verbose=False)
    guard.print_rules()

    # 테스트 실행
    run_output_guard_test()
