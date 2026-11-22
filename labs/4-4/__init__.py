#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [4-4] 안전장치 평가 모듈

"""
4-4: AI 에이전트 안전장치 평가 (3계층 가드레일 + Red Team)

구성:
  1. guard_input.py           - 입력 가드레일 (개인정보, 프롬프트 인젝션, 범위 벗어남 차단)
  2. guard_tool.py            - 도구 가드레일 (승인, 권한, 인자, 반복 제한)
  3. guard_output.py          - 출력 가드레일 (PII 마스킹, 미검증 숫자, 근거 추가)
  4. red_team.py              - 10개 공격 테스트 (가드 미적용)
  5. red_team_with_guard.py   - 입력 가드 적용 비교
  6. red_team_with_guard_tool.py - 입력+도구 가드 적용 비교
  7. red_team_with_guard_output.py - 출력 가드 적용 비교 (최종)

사용법:
  python labs/4-4/guard_input.py                  # 입력 가드 규칙 & 테스트
  python labs/4-4/guard_tool.py                   # 도구 가드 규칙 & 테스트
  python labs/4-4/guard_output.py                 # 출력 가드 규칙 & 테스트
  python labs/4-4/red_team.py                     # 공격 10개 (가드 미적용)
  python labs/4-4/red_team_with_guard.py          # 공격 10개 (입력 가드)
  python labs/4-4/red_team_with_guard_tool.py     # 공격 11개 (입력+도구 가드)
  python labs/4-4/red_team_with_guard_output.py   # 공격 4개 (출력 가드 비교)

출력:
  - labs/4-4/data/red_team_report.json              - 가드 미적용
  - labs/4-4/data/red_team_comparison.json          - 입력 가드
  - labs/4-4/data/red_team_final_report.json        - 입력+도구 가드
  - labs/4-4/data/red_team_output_guard_report.json - 출력 가드
  - labs/4-4/data/guard_log.json                    - 도구 가드 위반 로그
"""

from .guard_input import InputGuard
from .guard_tool import ToolGuard
from .guard_output import OutputGuard

__all__ = ["InputGuard", "ToolGuard", "OutputGuard"]
