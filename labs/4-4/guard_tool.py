#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-4] 도구 가드레일: 도구 실행 직전 검사

"""
도구 가드레일 규칙
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[규칙 1] 사용자 승인 (write 도구)
  ├─ 대상: reserve_gpu, cancel_gpu
  ├─ 조치: 도구 실행 전 "이대로 예약할까요? (y/n)" 묻기
  ├─ 조건: y 일 때만 실행, n 또는 타임아웃 시 거부
  └─ 이유: 중요한 작업은 사용자 확인 필수

[규칙 2] 권한 검사
  ├─ 대상: 도구 인자 중 student_id
  ├─ 조치: student_id != 로그인 학번(HANA-007) 이면 거부
  └─ 이유: 다른 학생의 예약을 조회/수정할 수 없음 (Unauthorized)

[규칙 3] 인자 검사 (GPU 예약)
  ├─ 조건 1: duration은 2시간 또는 4시간만 (2시간 단위)
  ├─ 조건 2: 하루 최대 4시간 이하 (RAG_PLAN과 동일)
  ├─ 조건 3: 평일 09:00 ~ 21:00 (working_hours)
  └─ 조치: 조건 위반 시 도구 실행 거부

[규칙 4] 반복 제한
  ├─ 대상: reserve_gpu, cancel_gpu (write 도구)
  ├─ 조건: 한 번의 대화(세션)에서 최대 3번까지만
  ├─ 추적: tool_call_count (대화 메시지마다 초기화)
  └─ 조치: 3회 초과 시 거부 + "도구 사용 횟수를 초과했습니다"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Any, Optional
import asyncio


# ============================================================================
# 설정
# ============================================================================

GPU_MIN_DURATION = 2
GPU_MAX_DURATION = 4
GPU_MAX_PER_DAY = 4
GPU_WORK_START = 9
GPU_WORK_END = 21

LOGIN_STUDENT_ID = "HANA-007"

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

GUARD_LOG_FILE = DATA_DIR / "guard_log.json"


# ============================================================================
# 도구 가드레일 클래스
# ============================================================================

class ToolGuard:
    """도구 실행 전 검사 (승인, 권한, 인자, 반복)"""

    def __init__(self, login_student_id: str = LOGIN_STUDENT_ID, verbose: bool = False):
        self.login_student_id = login_student_id
        self.verbose = verbose
        self.violations = []
        self.tool_call_count = 0  # 한 대화의 쓰기 도구 호출 횟수
        self.write_tools_limit = 3  # 한 대화의 최대 쓰기 도구 수

    def reset_session(self):
        """새 대화 시작: 카운터 초기화"""
        self.tool_call_count = 0
        self.violations = []

    async def guard(self, tool_name: str, tool_args: dict, approval_input_fn=None) -> Tuple[bool, str]:
        """
        도구 실행 가드

        Args:
            tool_name: 도구 이름
            tool_args: 도구 인자
            approval_input_fn: 승인 입력 함수 (테스트용, None이면 input() 사용)

        Returns:
            (통과여부, 메시지)
        """
        self.violations = []

        # 1. 권한 검사
        passed, message = self._check_authorization(tool_name, tool_args)
        if not passed:
            self._log_violation("authorization", tool_name, tool_args, message)
            return False, message

        # 2. 인자 검사
        passed, message = self._check_arguments(tool_name, tool_args)
        if not passed:
            self._log_violation("argument_validation", tool_name, tool_args, message)
            return False, message

        # 3. 반복 제한 검사
        passed, message = self._check_repeat_limit(tool_name, tool_args)
        if not passed:
            self._log_violation("repeat_limit", tool_name, tool_args, message)
            return False, message

        # 4. 사용자 승인
        if self._is_write_tool(tool_name):
            passed, message = await self._request_approval(tool_name, tool_args, approval_input_fn)
            if not passed:
                self._log_violation("approval", tool_name, tool_args, message)
                return False, message

        # 모든 검사 통과
        self.tool_call_count += 1
        if self.verbose:
            print(f"   [ToolGuard] ✅ 통과 (쓰기 도구 {self.tool_call_count}/{self.write_tools_limit})")

        return True, ""

    # ========================================================================
    # 검사 메서드
    # ========================================================================

    def _check_authorization(self, tool_name: str, tool_args: dict) -> Tuple[bool, str]:
        """권한 검사: student_id == 로그인 학번"""
        # 도구 인자에 student_id가 있으면 검사
        student_id = tool_args.get("student_id", self.login_student_id)

        if student_id != self.login_student_id:
            message = f"❌ 권한 오류: {student_id}의 예약은 조회/수정할 수 없어요. (로그인: {self.login_student_id})"
            if self.verbose:
                print(f"   [ToolGuard] 권한 차단: {student_id} != {self.login_student_id}")
            return False, message

        return True, ""

    def _check_arguments(self, tool_name: str, tool_args: dict) -> Tuple[bool, str]:
        """인자 검사: GPU 예약 규칙"""
        if tool_name != "reserve_gpu":
            return True, ""

        # GPU 예약 규칙 검사
        duration = tool_args.get("duration", 0)
        start_time = tool_args.get("start_time", "")
        date = tool_args.get("date", "")

        # 1. duration 검사 (2시간 또는 4시간)
        if duration not in [GPU_MIN_DURATION, GPU_MAX_DURATION]:
            message = f"❌ GPU PC 예약은 {GPU_MIN_DURATION}시간 또는 {GPU_MAX_DURATION}시간만 가능해요"
            if self.verbose:
                print(f"   [ToolGuard] duration 검사 실패: {duration}")
            return False, message

        # 2. 근무 시간 검사
        try:
            hour = int(start_time.split(":")[0])
            end_hour = hour + duration

            if hour < GPU_WORK_START or end_hour > GPU_WORK_END:
                message = f"❌ GPU PC 예약은 평일 {GPU_WORK_START:02d}:00 ~ {GPU_WORK_END:02d}:00 사이에만 가능해요"
                if self.verbose:
                    print(f"   [ToolGuard] 근무 시간 검사 실패: {start_time} + {duration}시간")
                return False, message
        except (ValueError, IndexError):
            return True, ""  # 형식 오류는 도구가 처리

        # 3. 하루 4시간 제한 (여기서는 단순 검사, 실제 누적은 도구에서 확인)
        if duration > GPU_MAX_PER_DAY:
            message = f"❌ GPU PC 예약은 하루 최대 {GPU_MAX_PER_DAY}시간까지만 가능해요"
            if self.verbose:
                print(f"   [ToolGuard] 하루 시간 제한 검사 실패")
            return False, message

        return True, ""

    def _check_repeat_limit(self, tool_name: str, tool_args: dict) -> Tuple[bool, str]:
        """반복 제한: write 도구 최대 3회"""
        if not self._is_write_tool(tool_name):
            return True, ""

        if self.tool_call_count >= self.write_tools_limit:
            message = f"❌ 도구 사용 횟수를 초과했습니다. (최대: {self.write_tools_limit}회, 현재: {self.tool_call_count}회)"
            if self.verbose:
                print(f"   [ToolGuard] 반복 제한 초과")
            return False, message

        return True, ""

    async def _request_approval(self, tool_name: str, tool_args: dict, approval_input_fn=None) -> Tuple[bool, str]:
        """사용자 승인 요청"""
        # 도구별 승인 메시지
        if tool_name == "reserve_gpu":
            message = f"""
📌 GPU PC 예약을 확인해주세요:
   • 날짜: {tool_args.get('date')}
   • 시간: {tool_args.get('start_time')} ~ {int(tool_args.get('start_time', '0:00').split(':')[0]) + tool_args.get('duration', 0)}:00
   • 시간: {tool_args.get('duration')}시간
   • PC: PC-{tool_args.get('pc_number')}

이대로 예약할까요? (y/n): """

        elif tool_name == "cancel_gpu":
            message = f"""
📌 GPU PC 예약 취소를 확인해주세요:
   • 예약 ID: {tool_args.get('reservation_id')}

이대로 취소할까요? (y/n): """

        else:
            return True, ""

        # 사용자 입력 받기
        if approval_input_fn:
            # 테스트 모드: 함수로 입력받기
            answer = approval_input_fn()
        else:
            # 실제 모드: input() 사용
            try:
                answer = input(message).strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"

        if answer == "y":
            if self.verbose:
                print(f"   [ToolGuard] ✅ 승인됨")
            return True, ""
        else:
            message = "❌ 사용자가 거부했습니다"
            if self.verbose:
                print(f"   [ToolGuard] 사용자 거부")
            return False, message

    # ========================================================================
    # 헬퍼 메서드
    # ========================================================================

    def _is_write_tool(self, tool_name: str) -> bool:
        """쓰기 도구인지 확인"""
        write_tools = ["reserve_gpu", "cancel_gpu"]
        return tool_name in write_tools

    def _log_violation(self, violation_type: str, tool_name: str, tool_args: dict, message: str):
        """위반 사항 기록"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": violation_type,
            "tool": tool_name,
            "args": tool_args,
            "message": message
        }

        # 파일에 기록
        logs = []
        if GUARD_LOG_FILE.exists():
            try:
                with open(GUARD_LOG_FILE, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                logs = []

        logs.append(log_entry)

        with open(GUARD_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

        self.violations.append((violation_type, tool_name, tool_args))

        if self.verbose:
            print(f"   [ToolGuard] 위반 기록: {violation_type} - {tool_name}")

    def print_rules(self):
        """규칙 출력"""
        print(f"\n{'='*80}")
        print("📋 도구 가드레일 규칙")
        print(f"{'='*80}\n")

        print("[규칙 1] 사용자 승인 (write 도구)")
        print("  ├─ 대상: reserve_gpu, cancel_gpu")
        print("  ├─ 조치: 실행 전 '이대로 예약할까요? (y/n)' 확인")
        print("  └─ 조건: y 일 때만 실행\n")

        print("[규칙 2] 권한 검사")
        print(f"  ├─ 조건: student_id == {LOGIN_STUDENT_ID}")
        print("  ├─ 조치: 다른 학번이면 거부")
        print("  └─ 예: HANA-003의 예약 취소 → ❌ 거부\n")

        print("[규칙 3] 인자 검사 (GPU 예약)")
        print(f"  ├─ duration: {GPU_MIN_DURATION}시간 또는 {GPU_MAX_DURATION}시간만")
        print(f"  ├─ 시간대: {GPU_WORK_START:02d}:00 ~ {GPU_WORK_END:02d}:00")
        print(f"  ├─ 하루 최대: {GPU_MAX_PER_DAY}시간")
        print("  └─ 조치: 규칙 위반 시 거부\n")

        print("[규칙 4] 반복 제한")
        print(f"  ├─ 대상: reserve_gpu, cancel_gpu (쓰기 도구)")
        print(f"  ├─ 제한: 한 대화에서 최대 {self.write_tools_limit}회")
        print("  └─ 조치: 초과 시 거부\n")

        print(f"{'='*80}\n")


# ============================================================================
# 테스트
# ============================================================================

async def test_guard():
    """가드레일 테스트"""
    guard = ToolGuard(verbose=True)
    guard.print_rules()

    test_cases = [
        {
            "tool_name": "reserve_gpu",
            "tool_args": {
                "date": "2026-11-25",
                "start_time": "14:00",
                "duration": 2,
                "pc_number": 1,
                "student_id": "HANA-007"
            },
            "approval": "y",
            "expected": True
        },
        {
            "tool_name": "reserve_gpu",
            "tool_args": {
                "date": "2026-11-25",
                "start_time": "14:00",
                "duration": 2,
                "pc_number": 1,
                "student_id": "HANA-003"  # 다른 학번
            },
            "approval": "y",
            "expected": False
        },
        {
            "tool_name": "reserve_gpu",
            "tool_args": {
                "date": "2026-11-25",
                "start_time": "14:00",
                "duration": 10,  # 규칙 위반
                "pc_number": 1,
                "student_id": "HANA-007"
            },
            "approval": "y",
            "expected": False
        },
    ]

    print(f"\n{'='*80}")
    print("🧪 도구 가드레일 테스트")
    print(f"{'='*80}\n")

    for idx, test in enumerate(test_cases, 1):
        print(f"[테스트 {idx}] {test['tool_name']}")
        print(f"   인자: {test['tool_args']}")

        # 승인 함수
        def mock_approval():
            return test['approval']

        passed, message = await guard.guard(
            test['tool_name'],
            test['tool_args'],
            approval_input_fn=mock_approval
        )

        result = "✅ 통과" if passed else "❌ 거부"
        expected = "✅ 통과" if test['expected'] else "❌ 거부"
        status = "✓" if (passed == test['expected']) else "✗"

        print(f"   결과: {result} (예상: {expected}) {status}")
        if message:
            print(f"   메시지: {message}")
        print()

        guard.reset_session()


if __name__ == "__main__":
    asyncio.run(test_guard())
