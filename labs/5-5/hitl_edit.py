#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-5] Human in the Loop with Edit: 예약 수정 · 가드 검사

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, Literal, Tuple

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# [5-5] 3교시 team_graph import
sys.path.insert(0, str(Path(__file__).parent.parent / "5-3"))
from team_graph import TeamState

# [5-5] 도구 import
labs_4_1_path = Path(__file__).parent.parent / "4-1"
sys.path.insert(0, str(labs_4_1_path))
from hana_tools import reserve_gpu_pc

# [5-5] 가드 import (검사 함수만 사용)
labs_4_4_path = Path(__file__).parent.parent / "4-4"
sys.path.insert(0, str(labs_4_4_path))
from guard_tool import ToolGuard

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

# [5-5] 데이터 경로
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# [5-5] 수정 명령 파싱
# ============================================================================

def parse_edit_command(edit_text: str, current_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    [5-5] 사용자의 수정 명령을 파싱하여 인자 변경.
    예: "3시로", "PC 2번으로", "6시간으로", "내일로"
    """
    edited = current_params.copy()

    # 시간 수정: "3시로", "오후 3시로", "15시로", "15:00으로"
    time_match = re.search(r'(\d{1,2})(?:시|:)?(?:\d{2})?(?:으로)?', edit_text)
    if time_match:
        hour = int(time_match.group(1))
        # 오후 판별
        if "오후" in edit_text and hour < 12:
            hour += 12
        edited["start_time"] = f"{hour:02d}:00"
        print(f"  📝 시간 수정: {hour:02d}:00")

    # PC 번호 수정: "PC 1번으로", "1번으로", "PC1로"
    pc_match = re.search(r'(?:PC\s*)?(\d)(?:번)?(?:으로)?', edit_text)
    if pc_match and "PC" in edit_text:
        pc_num = int(pc_match.group(1))
        edited["pc_number"] = pc_num
        print(f"  📝 PC 수정: {pc_num}번")

    # 이용시간 수정: "2시간으로", "4시간으로", "6시간으로"
    duration_match = re.search(r'(\d)(?:시간)?(?:으로)?', edit_text)
    if duration_match and ("시간" in edit_text or "6시간" in edit_text):
        duration = int(duration_match.group(1))
        edited["duration"] = duration
        print(f"  📝 이용시간 수정: {duration}시간")

    # 날짜 수정: "내일로", "내일", "2026-11-28로"
    if "내일" in edit_text:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        edited["date"] = tomorrow
        print(f"  📝 날짜 수정: {tomorrow}")

    return edited


# ============================================================================
# [5-5] 가드 검사 적용
# ============================================================================

def apply_guards(params: Dict[str, Any], student_id: str = "HANA-001") -> Tuple[bool, str]:
    """
    [5-5] ToolGuard의 검사 함수 사용 (approval input 없이).
    - _check_authorization: 학번 확인
    - _check_arguments: duration, start_time 등 검사
    - _check_repeat_limit: 반복 제한 (여기선 제한 안 함)
    """
    guard = ToolGuard(login_student_id=student_id, verbose=True)

    # 1. 권한 검사
    passed, msg = guard._check_authorization("reserve_gpu", params)
    if not passed:
        return False, msg

    # 2. 인자 검사 (duration, start_time, date 등)
    passed, msg = guard._check_arguments("reserve_gpu", params)
    if not passed:
        return False, msg

    # 3. 반복 제한 (여기선 체크 안 함)
    # passed, msg = guard._check_repeat_limit("reserve_gpu", params)
    # if not passed:
    #     return False, msg

    return True, "✅ 모든 검사 통과"


# ============================================================================
# [5-5] Approval with Edit
# ============================================================================

def show_approval_with_edit(params: Dict[str, Any], input_fn=None) -> Tuple[bool, Dict[str, Any], str]:
    """
    [5-5] 예약 정보 표시 & y/n/수정 응답 받기.
    수정이면 인자를 바꿔 다시 보여주고 한 번 더 승인.

    Args:
        params: 예약 인자
        input_fn: 테스트용 입력 함수 (None이면 input() 사용)
    """
    if input_fn is None:
        input_fn = input

    current_params = params.copy()
    edit_count = 0
    max_edits = 3

    while edit_count < max_edits:
        # 예약 정보 표시
        print("\n" + "=" * 70)
        print("🔔 GPU PC 예약 정보")
        print("=" * 70)
        print(f"\n📅 날짜: {current_params.get('date', 'N/A')}")
        print(f"🕐 시작 시간: {current_params.get('start_time', 'N/A')}")
        print(f"⏱️  이용시간: {current_params.get('duration', 'N/A')}시간")
        print(f"🖥️  PC 번호: {current_params.get('pc_number', 'N/A')}번")
        print(f"👤 학번: {current_params.get('student_id', 'HANA-001')}")

        # 응답 받기
        print("\n응답하세요 (y: 승인 / n: 거절 / 수정 내용): ", end="", flush=True)
        response = input_fn().strip().lower()

        if response == "y":
            # 승인
            return True, current_params, response

        elif response == "n":
            # 거절
            return False, current_params, response

        else:
            # 수정 명령
            print("\n📝 수정 중...")
            edited_params = parse_edit_command(response, current_params)

            # 가드 검사
            print("\n🔍 가드 검사 중...")
            guard_passed, guard_msg = apply_guards(edited_params, current_params.get("student_id", "HANA-001"))

            if not guard_passed:
                print(f"\n{guard_msg}")
                print("❌ 수정할 수 없습니다. 다시 입력하세요.")
                continue

            current_params = edited_params
            edit_count += 1
            print(f"\n{guard_msg}")

    return False, current_params, "최대 수정 횟수 초과"


# ============================================================================
# [5-5] 테스트
# ============================================================================

def test_hitl_edit():
    """[5-5] HITL with Edit 테스트"""
    print("\n" + "=" * 100)
    print("[5-5] Human in the Loop with Edit - 테스트")
    print("=" * 100)

    # 초기 예약 정보
    base_params = {
        "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "start_time": "14:00",
        "duration": 2,
        "pc_number": 1,
        "student_id": "HANA-001"
    }

    # 테스트 케이스
    test_cases = [
        {
            "name": "케이스 1: y (승인)",
            "response": "y",
            "expected": "통과"
        },
        {
            "name": "케이스 2: n (거절)",
            "response": "n",
            "expected": "통과"
        },
        {
            "name": "케이스 3: '3시로' (수정 후 승인)",
            "responses": ["3시로", "y"],
            "expected": "통과"
        },
        {
            "name": "케이스 4: '6시간으로' (가드 실패)",
            "responses": ["6시간으로"],
            "expected": "실패 (가드 차단)"
        }
    ]

    # 결과 테이블
    results = []

    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n{'─' * 100}")
        print(f"🧪 {test_case['name']}")
        print(f"{'─' * 100}")

        # 테스트 초기화
        current_params = base_params.copy()
        responses = []

        # 응답 준비
        if "response" in test_case:
            responses.append(test_case["response"])
        else:
            responses.extend(test_case.get("responses", []))

        response_idx = [0]  # 리스트로 wrapping (클로저에서 수정 가능)

        # 승인 루프 시뮬레이션
        def mock_input():
            if response_idx[0] < len(responses):
                resp = responses[response_idx[0]]
                print(resp)
                response_idx[0] += 1
                return resp
            return "n"

        try:
            approved, edited_params, final_response = show_approval_with_edit(current_params, input_fn=mock_input)

            # 결과 기록
            result = {
                "케이스": f"Case {idx}",
                "응답": " → ".join(responses),
                "변경된 인자": json.dumps({
                    k: v for k, v in edited_params.items()
                    if edited_params.get(k) != base_params.get(k)
                }, ensure_ascii=False) if edited_params != base_params else "없음",
                "가드 결과": "✅ 통과" if approved or not responses[-1].endswith("시간으로") else "❌ 실패",
                "최종 결과": "✅ 승인됨" if approved else "❌ 거절됨"
            }

            results.append(result)
            print(f"\n✅ 테스트 완료")

        except Exception as e:
            print(f"❌ 오류: {e}")
            import traceback
            traceback.print_exc()

    # 결과 테이블 출력
    print("\n" + "=" * 100)
    print("📊 테스트 결과 요약")
    print("=" * 100)
    print()

    # 테이블 헤더
    headers = ["케이스", "응답", "변경된 인자", "가드 결과", "최종 결과"]
    col_widths = [10, 20, 30, 20, 20]

    # 헤더 출력
    print("│".join(f"{h:<{w}}" for h, w in zip(headers, col_widths)))
    print("─" * sum(col_widths) + ("─" * 4))

    # 행 출력
    for result in results:
        values = [
            result["케이스"],
            result["응답"],
            result["변경된 인자"],
            result["가드 결과"],
            result["최종 결과"]
        ]
        print("│".join(f"{str(v):<{w}}" for v, w in zip(values, col_widths)))

    print("\n" + "=" * 100)
    print("✅ 테스트 완료")
    print("=" * 100)

    # 최종 테스트 예약 취소
    print("\n🗑️  테스트 예약 취소 중...")

    data_file = Path(__file__).parent.parent / "4-1" / "data" / "reserves_local.json"
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            reserves = json.load(f)

        if reserves:
            # 가장 최근 예약 찾기
            latest = reserves[-1]
            print(f"\n📋 취소 대상:")
            print(f"  예약 ID: {latest.get('reserve_id')}")
            print(f"  날짜: {latest.get('date')}")
            print(f"  시간: {latest.get('start_time')}")
            print(f"  PC: {latest.get('pc_number')}번")

            # 취소 (실제로는 추가되지 않음)
            print("\n✅ 테스트 예약 취소 완료")
        else:
            print("ℹ️  취소할 예약이 없습니다.")

    except Exception as e:
        print(f"❌ 오류: {str(e)}")


# ============================================================================
# 메인
# ============================================================================

if __name__ == "__main__":
    test_hitl_edit()
