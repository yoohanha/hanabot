#!/usr/bin/env python3
# [3-3] 웹 서비스 함수 (상담 신청 등)

import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).parent.parent
CONSULTS_FILE = PROJECT_ROOT / 'web' / 'data' / 'consults.json'

# [3-3] 상담 신청 함수
def create_consult(student_id: str, course: str, desired_time: str, inquiry: str) -> dict:
    """
    상담 신청을 받고 저장.

    Args:
        student_id: 학번 (예: HANA-001)
        course: 관심 과정 (기초반, 실무반, 모름)
        desired_time: 희망 시간 (예: 10:30, 14:00)
        inquiry: 문의 내용

    Returns:
        dict: {'success': bool, 'message': str, 'consult_id': str (성공 시)}
    """

    # 1. 입력 검증
    empty_fields = []
    if not student_id or not student_id.strip():
        empty_fields.append('학번')
    if not course or course == '':
        empty_fields.append('관심 과정')
    if not desired_time or not desired_time.strip():
        empty_fields.append('희망 시간')
    if not inquiry or not inquiry.strip():
        empty_fields.append('문의 내용')

    if empty_fields:
        return {
            'success': False,
            'message': f"다음 항목을 입력해주세요: {', '.join(empty_fields)}"
        }

    # 2. 시간 검증 (평일 10:00~18:00만 가능)
    try:
        # 희망 시간 파싱 (HH:MM 형식)
        time_parts = desired_time.strip().split(':')
        if len(time_parts) != 2:
            raise ValueError()
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        # 현재 요일 확인 (월=0, 일=6)
        now = datetime.now(ZoneInfo('Asia/Seoul'))
        weekday = now.weekday()

        # 주말 (토=5, 일=6) 확인
        if weekday >= 5:
            return {
                'success': False,
                'message': '상담은 평일 10:00~18:00에 가능해요'
            }

        # 평일이면 시간 확인 (10:00 ~ 18:00)
        total_minutes = hour * 60 + minute
        start_time = 10 * 60  # 10:00
        end_time = 18 * 60    # 18:00

        if total_minutes < start_time or total_minutes > end_time:
            return {
                'success': False,
                'message': '상담은 평일 10:00~18:00에 가능해요'
            }
    except (ValueError, IndexError):
        return {
            'success': False,
            'message': '시간을 HH:MM 형식으로 입력해주세요 (예: 14:30)'
        }

    # 3. 접수 번호 생성
    # 기존 파일에서 마지막 번호 읽기
    consult_number = 1
    if CONSULTS_FILE.exists():
        try:
            with open(CONSULTS_FILE, 'r', encoding='utf-8') as f:
                consults = json.load(f)
                if consults:
                    last_id = consults[-1]['consult_id']
                    # C-0001 형식에서 숫자만 추출
                    consult_number = int(last_id.split('-')[1]) + 1
        except (json.JSONDecodeError, IndexError):
            consult_number = 1

    consult_id = f"C-{consult_number:04d}"

    # 4. 데이터 저장
    consult_data = {
        'consult_id': consult_id,
        'student_id': student_id.strip(),
        'course': course,
        'desired_time': desired_time.strip(),
        'inquiry': inquiry.strip(),
        'created_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    }

    # 파일 로드 (없으면 빈 배열)
    consults = []
    if CONSULTS_FILE.exists():
        try:
            with open(CONSULTS_FILE, 'r', encoding='utf-8') as f:
                consults = json.load(f)
        except json.JSONDecodeError:
            consults = []

    # 데이터 추가
    consults.append(consult_data)

    # 파일 저장
    CONSULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(consults, f, ensure_ascii=False, indent=2)

    return {
        'success': True,
        'message': f'접수 완료했습니다. 접수 번호: {consult_id}',
        'consult_id': consult_id
    }
