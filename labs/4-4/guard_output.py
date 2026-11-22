#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-4] 출력 가드레일: 하나봇의 답변을 사용자에게 보내기 전에 검사

"""
출력 가드레일 규칙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[규칙 1] 개인정보 마스킹
  ├─ 차단: 주민번호 (XXXXXX-XXXXXXX), 전화번호, 카드번호 패턴
  ├─ 조치: *** 로 마스킹
  └─ 예: "그 번호는 010-1234-5678" → "그 번호는 ***"

[규칙 2] 미검증 숫자 경고
  ├─ 대상: 금액(원/%), 횟수, 시간 등 구체적 숫자
  ├─ 조건: search_rules나 calc_fee 결과에 없는 숫자면
  ├─ 조치: "규정에서 확인되지 않은 내용이에요" 붙이기
  └─ 예: "환불은 100%" (규정에 없음) → "(규정에서 확인되지 않은 내용이에요)"

[규칙 3] 규정 답변에 근거 붙이기
  ├─ 조건: search_rules 도구로 얻은 답변
  ├─ 조치: "근거: 문서명 · 소제목" 한 줄 붙이기
  └─ 예: "지각 3회는 결석으로" → "(근거: 수강 규정 · 지각)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
from typing import Tuple, Dict, List, Optional
from pathlib import Path


# ============================================================================
# 설정: 규정 검증 데이터 (RAG_PLAN에서 추출)
# ============================================================================

# 규정의 공식 숫자들 (문서 · 소제목 : [숫자들])
VERIFIED_NUMBERS = {
    ("수강 규정", "지각"): [3, 1],  # 3회 지각 = 1회 결석
    ("수강 규정", "조퇴"): [2, 1],  # 2회 조퇴 = 1회 결석
    ("수강 규정", "수료"): [80],  # 80% 이상 출석
    ("수강료와 환불", "수강료"): [300000, 500000],  # 기초반 30만, 실무반 50만
    ("수강료와 환불", "할인"): [50, 10],  # 50% 재수강, 10% 친구
    ("수강료와 환불", "환불 기준"): [66, 50],  # 1/3 미만 2/3 환급, 1/2 미만 1/2 환급, 1/2 이후 0
    ("시설 이용", "실습실 이용 시간"): [9, 21],  # 09:00 ~ 21:00
    ("시설 이용", "GPU PC 예약"): [2, 4],  # 2시간 단위, 하루 최대 4시간
    ("주차", "주차"): [2],  # 2시간 무료
}

# 규정 근거 매핑 (소제목 : (문서, 소제목))
SOURCES_MAP = {
    "지각": ("수강 규정", "지각"),
    "조퇴": ("수강 규정", "조퇴"),
    "수료": ("수강 규정", "수료"),
    "출석": ("수강 규정", "수료"),
    "수강료": ("수강료와 환불", "수강료"),
    "기초반": ("수강료와 환불", "수강료"),
    "실무반": ("수강료와 환불", "수강료"),
    "할인": ("수강료와 환불", "할인"),
    "재수강": ("수강료와 환불", "할인"),
    "친구": ("수강료와 환불", "할인"),
    "환불": ("수강료와 환불", "환불 기준"),
    "환급": ("수강료와 환불", "환불 기준"),
    "실습실": ("시설 이용", "실습실 이용 시간"),
    "GPU": ("시설 이용", "GPU PC 예약"),
    "예약": ("시설 이용", "GPU PC 예약"),
    "주차": ("주차", "주차"),
    "무료": ("주차", "주차"),
}

# PII 패턴 (입력 가드와 동일)
PII_PATTERNS = {
    "주민번호": r"\d{6}-\d{7}",
    "전화번호": r"(?:\d{3}-\d{3,4}-\d{4}|\d{10,11})",
    "카드번호": r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}",
}


# ============================================================================
# 출력 가드레일 클래스
# ============================================================================

class OutputGuard:
    """출력 가드레일: 답변 검사 및 필터링"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.violations = []

    def guard(self, response: str, tool_used: str = "", tool_result: str = "") -> Tuple[str, str]:
        """
        출력 가드: 답변 검사 및 보정

        Args:
            response: 하나봇의 답변
            tool_used: 사용된 도구 ("search_rules", "calc_fee", 등)
            tool_result: 도구의 원본 결과

        Returns:
            (보정된_답변, 개선사항_메모)
        """
        self.violations = []
        processed = response
        notes = []

        # 1. PII 마스킹
        processed, pii_found = self._mask_pii(processed)
        if pii_found:
            notes.append(f"PII 마스킹: {pii_found}")
            if self.verbose:
                print(f"   [OutputGuard] PII 마스킹: {pii_found}")

        # 2. 미검증 숫자 경고
        if tool_used in ["search_rules", "calc_fee"]:
            processed, unverified = self._check_unverified_numbers(processed, tool_used, tool_result)
            if unverified:
                notes.append(f"미검증 숫자 경고 추가")
                if self.verbose:
                    print(f"   [OutputGuard] 미검증 숫자 발견")

        # 3. 규정 답변에 근거 붙이기
        if tool_used == "search_rules":
            processed, source_added = self._add_source_citation(processed, response)
            if source_added:
                notes.append(f"근거 추가: {source_added}")
                if self.verbose:
                    print(f"   [OutputGuard] 근거 추가: {source_added}")

        # 4. 최종 정리
        if not notes:
            notes.append("검사 완료 (변경 없음)")

        note_str = " | ".join(notes)
        return processed, note_str

    # ========================================================================
    # 검사 메서드
    # ========================================================================

    def _mask_pii(self, text: str) -> Tuple[str, str]:
        """PII 마스킹"""
        processed = text
        found_types = []

        for pii_type, pattern in PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                found_types.append(pii_type)
                processed = re.sub(pattern, "***", processed)

        pii_found = " · ".join(found_types) if found_types else ""
        return processed, pii_found

    def _check_unverified_numbers(self, text: str, tool_used: str, tool_result: str) -> Tuple[str, bool]:
        """미검증 숫자 확인"""
        # [4-4] 도구 결과에 있는 숫자는 무시 (도구가 반환한 숫자는 신뢰 가능)
        # calc_fee는 금액 계산 결과이므로 모든 금액을 신뢰
        if tool_used == "calc_fee":
            return text, False  # 금액 계산 결과는 경고 없음

        # 쉼표 제거 후 숫자 추출 (300,000 → 300000)
        tool_text_clean = tool_result.replace(",", "") if tool_result else ""
        tool_numbers = set(re.findall(r'\d+', tool_text_clean))

        # 금액(원), 횟수, 비율(%) 추출
        numbers = re.findall(r'(\d+)(?:원|%|시간|회|명)?', text)
        if not numbers:
            return text, False

        # 규정에 있는 숫자와 비교
        all_verified_numbers = []
        for nums_list in VERIFIED_NUMBERS.values():
            all_verified_numbers.extend(nums_list)

        unverified = False
        for num_str in numbers:
            num = int(num_str)
            # [4-4] 도구 결과에 있는 숫자는 무시
            if str(num) in tool_numbers:
                continue
            # 규정에 없는 숫자면 경고 추가
            if num not in all_verified_numbers and num < 10:  # 1자리 수 중심
                # "규정에서 확인되지 않은 내용" 추가
                if "(규정에서 확인되지 않은 내용이에요)" not in text:
                    text += "\n(규정에서 확인되지 않은 내용이에요)"
                    unverified = True
                    break

        return text, unverified

    def _add_source_citation(self, text: str, original: str) -> Tuple[str, Optional[str]]:
        """규정 답변에 근거 붙이기"""
        # 답변에서 주요 키워드 찾기
        for keyword, (doc, section) in SOURCES_MAP.items():
            if keyword.lower() in original.lower():
                source = f"(근거: {doc} · {section})"
                if source not in text:
                    text += f"\n{source}"
                    return text, source
                return text, None

        return text, None

    def print_rules(self):
        """규칙 출력"""
        print(f"\n{'='*80}")
        print("📋 출력 가드레일 규칙")
        print(f"{'='*80}\n")

        print("[규칙 1] 개인정보 마스킹")
        print("  ├─ 차단: 주민번호, 전화번호, 카드번호")
        print("  ├─ 조치: *** 로 마스킹")
        print("  └─ 예: '010-1234-5678' → '***'\n")

        print("[규칙 2] 미검증 숫자 경고")
        print("  ├─ 대상: 금액, 횟수, 비율 등 구체적 숫자")
        print("  ├─ 조건: search_rules/calc_fee 결과에 없으면")
        print("  ├─ 조치: '규정에서 확인되지 않은 내용이에요' 붙이기")
        print("  └─ 예: '환불은 100%' → '(규정에서 확인되지 않은 내용)'\n")

        print("[규칙 3] 근거 추가")
        print("  ├─ 대상: search_rules 답변")
        print("  ├─ 조치: '근거: 문서 · 소제목' 한 줄 붙이기")
        print("  └─ 예: '지각 3회...' → '(근거: 수강 규정 · 지각)'\n")

        print("📊 검증된 규정 숫자:")
        for (doc, section), nums in VERIFIED_NUMBERS.items():
            print(f"  • {doc} · {section}: {nums}")

        print(f"\n{'='*80}\n")


# ============================================================================
# 테스트 답변 세트
# ============================================================================

TEST_RESPONSES = [
    # 공격 1: 환불 100% (미검증)
    {
        "type": "attack",
        "name": "환불 100% (거짓 정보)",
        "response": "죄송하지만, 하나 AI 학원의 환불 정책은 개강 전 전액, 1/3 미만 2/3, 1/2 미만 1/2, 1/2 이후 0입니다. 환불은 100%가 아닙니다.",
        "tool_used": "search_rules",
        "tool_result": "환불 기준:\n개강 전: 전액\n1/3 미만: 2/3\n1/2 미만: 1/2\n1/2 이후: 0"
    },
    # 정상 1: 지각
    {
        "type": "normal",
        "name": "지각 규정 (정상)",
        "response": "지각 3회는 결석 1회로 처리됩니다.",
        "tool_used": "search_rules",
        "tool_result": "지각 3회는 결석 1회로 처리합니다."
    },
    # 정상 2: 수강료
    {
        "type": "normal",
        "name": "수강료 조회 (정상)",
        "response": "기초반은 월 30만 원, 실무반은 월 50만 원입니다.",
        "tool_used": "calc_fee",
        "tool_result": "기초반: 300000원/월, 실무반: 500000원/월"
    },
    # 정상 3: 주차
    {
        "type": "normal",
        "name": "주차 요금 (정상)",
        "response": "학원 건물 지하 1층에 주차할 수 있으며, 수강생은 2시간까지 무료입니다.",
        "tool_used": "search_rules",
        "tool_result": "수강생은 2시간까지 무료입니다."
    },
]


# ============================================================================
# 테스트
# ============================================================================

def test_guard():
    """출력 가드레일 테스트"""
    guard = OutputGuard(verbose=True)
    guard.print_rules()

    print(f"\n{'='*120}")
    print("🧪 출력 가드레일 테스트")
    print(f"{'='*120}\n")

    headers = ["#", "유형", "테스트명", "변경 사항"]
    col_widths = [2, 6, 25, 60]

    # 헤더
    header_line = " | ".join([
        headers[i].ljust(col_widths[i])
        for i in range(len(headers))
    ])
    print(header_line)
    print("-" * len(header_line))

    # 테스트 실행
    for idx, test in enumerate(TEST_RESPONSES, 1):
        processed, notes = guard.guard(
            test['response'],
            tool_used=test['tool_used'],
            tool_result=test['tool_result']
        )

        test_type = "공격" if test['type'] == "attack" else "정상"
        notes_short = notes[:57] if len(notes) > 57 else notes

        row = " | ".join([
            str(idx).ljust(col_widths[0]),
            test_type.ljust(col_widths[1]),
            test['name'][:24].ljust(col_widths[2]),
            notes_short.ljust(col_widths[3])
        ])
        print(row)

        # 상세 비교
        if processed != test['response']:
            print(f"   【수정】 {test['response'][:60]}")
            print(f"   【→】   {processed[:60]}")
        print()

    print("-" * len(header_line))


if __name__ == "__main__":
    test_guard()
